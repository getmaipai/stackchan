# ruff: noqa: E501
"""The PSRAM-stack lint (scripts/psram-stack-lint.py, patch FM05) and the core dump reader (scripts/fw-coredump.py, patch FM02)."""

from __future__ import annotations

import importlib.util
import os
import re
import struct
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lint = _load("psram_stack_lint", "psram-stack-lint.py")
coredump = _load("fw_coredump", "fw-coredump.py")


def _tree(tmp_path: Path, files: dict[str, str]) -> Path:
    for name, text in files.items():
        path = tmp_path / "main" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return tmp_path


def _findings(tmp_path: Path, files: dict[str, str]):
    return lint.Tree(_tree(tmp_path, files)).findings()


BAD = {
    "task.cc": """
        static void ring_task(void*) { for (;;) { helper(); } }
        void start() { xTaskCreatePinnedToCoreWithCaps(ring_task, "ring", 3072, nullptr, 1, nullptr, 0, MALLOC_CAP_SPIRAM); }
    """,
    "helper.cc": """
        void helper() { read_choices(); }
        int read_choices() { Settings st("ns", false); return st.GetInt("k", 0); }
    """,
}


def test_a_psram_stack_task_that_reaches_saved_settings_is_reported_with_its_path(tmp_path) -> None:
    found = _findings(tmp_path, BAD)
    assert found and found[0][0] == "ring_task"
    assert any(
        path == ["ring_task", "helper", "read_choices"] and word == "Settings"
        for _t, path, word in found
    )


def test_a_direct_nvs_call_in_the_task_itself_is_reported(tmp_path) -> None:
    found = _findings(
        tmp_path,
        {
            "a.cc": """
        void worker_task(void*) { nvs_handle_t h; nvs_open("x", NVS_READONLY, &h); }
        void go() { xTaskCreatePinnedToCoreWithCaps(worker_task, "w", 4096, nullptr, 1, nullptr, 1, MALLOC_CAP_SPIRAM); }
    """
        },
    )
    assert {word for _t, _p, word in found} >= {"nvs_open"}


def test_a_task_on_an_internal_stack_is_not_looked_at(tmp_path) -> None:
    files = dict(BAD)
    files["task.cc"] = (
        files["task.cc"]
        .replace("xTaskCreatePinnedToCoreWithCaps(ring_task", "xTaskCreate(ring_task")
        .replace(", 0, MALLOC_CAP_SPIRAM", "")
    )
    tree = lint.Tree(_tree(tmp_path, files))
    assert tree.tasks() == [] and tree.findings() == []


def test_a_task_that_never_reaches_flash_passes(tmp_path) -> None:
    clean = {
        "task.cc": """
            static void quiet_task(void*) { for (;;) { compute(); } }
            void start() { xTaskCreatePinnedToCoreWithCaps(quiet_task, "q", 3072, nullptr, 1, nullptr, 0, MALLOC_CAP_SPIRAM); }
        """,
        "x.cc": "int compute() { return 1; }  // Settings and nvs_open are only words in this comment\n",
    }
    assert _findings(tmp_path, clean) == []


def test_a_reviewed_guard_stops_the_walk_and_a_guard_that_lost_its_check_is_reported(
    tmp_path, monkeypatch
) -> None:
    files = dict(BAD)
    files["helper.cc"] = """
        void helper() { guarded_read(); }
        int guarded_read() { if (!stack_ok()) return 0; Settings st("ns", false); return st.GetInt("k", 0); }
    """
    monkeypatch.setitem(
        lint.GUARDED, "guarded_read", ("reads only on an internal stack", "stack_ok")
    )
    assert _findings(tmp_path, files) == []
    files["helper.cc"] = files["helper.cc"].replace("if (!stack_ok()) return 0; ", "")
    found = _findings(tmp_path, files)
    assert found and "guard for guarded_read lost" in found[0][2]


def test_a_member_call_and_a_name_many_files_define_are_not_followed(tmp_path) -> None:
    files = {
        "task.cc": """
            static void t_task(void*) { counter.load(); obj->update(); }
            void start() { xTaskCreatePinnedToCoreWithCaps(t_task, "t", 3072, nullptr, 1, nullptr, 0, MALLOC_CAP_SPIRAM); }
        """,
        "a.cc": 'void load() { Settings s("x", false); }\n',
        "b.cc": 'void update() { Settings s("y", false); }\nvoid update(int) { Settings s("z", false); }\n',
    }
    assert _findings(tmp_path, files) == []


def test_a_lambda_static_task_with_a_psram_stack_is_checked(tmp_path) -> None:
    found = _findings(
        tmp_path,
        {
            "e.cc": """
        void start() {
            uint8_t* stack = (uint8_t*)heap_caps_malloc(4096, MALLOC_CAP_SPIRAM);
            xTaskCreateStatic([](void* arg) { Settings s("x", false); }, "lam", 4096, nullptr, 1, stack, &tcb);
        }
    """
        },
    )
    assert found and found[0][0].startswith("<lambda")


# ---- the real firmware: replay firmware/patches/ORDER into a temp tree and lint that ---------------------------------


def _releasing() -> bool:
    """Release mode (MAIPAI_RELEASE=1, or CI set): a missing base tree is a failure, not a skip."""
    return os.environ.get("MAIPAI_RELEASE") == "1" or bool(os.environ.get("CI"))


def _base_value(key: str) -> str:
    for line in (ROOT / "firmware" / "BASE").read_text().splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    raise AssertionError(f"firmware/BASE has no {key}= line; restore it.")


def _has_commit(repo: Path, commit: str) -> bool:
    return (
        subprocess.run(
            ["git", "-C", str(repo), "cat-file", "-e", f"{commit}^{{commit}}"], capture_output=True
        ).returncode
        == 0
    )


def _base_sources() -> tuple[Path, Path] | None:
    """(outer repo, nested repo) of a local copy that holds the pinned base commits, or None."""
    outer, nested = _base_value("outer_commit"), _base_value("nested_commit")
    roots = []
    if os.environ.get("MAIPAI_FW_BASE_LOCAL"):
        roots.append(Path(os.environ["MAIPAI_FW_BASE_LOCAL"]).expanduser())
    for key in ("MAIPAI_FW_TREE_ROOT", "MAIPAI_FW_REF_TREE"):
        if os.environ.get(key):
            roots.append(Path(os.environ[key]).expanduser())
    build = Path.home() / "esp" / "stackchan-rebuild"
    roots.append(build / "main-ref")
    if build.is_dir():
        roots.extend(sorted(build.iterdir(), reverse=True))
    for root in roots:
        inner = root / "firmware" / "xiaozhi-esp32"
        if (root / ".git").exists() and (inner / ".git").exists():
            if _has_commit(root, outer) and _has_commit(inner, nested):
                return root, inner
    return None


def _no_tree(reason: str) -> None:
    text = (
        f"{reason} Point MAIPAI_FW_BASE_LOCAL at a local copy of the StackChan firmware repository "
        "(with firmware/xiaozhi-esp32 inside, holding the commits named in firmware/BASE), for example "
        "a tree made by bash scripts/fw-ref-tree.sh, then run this test again."
    )
    if _releasing():
        pytest.fail("The PSRAM-stack gate cannot run in release mode: " + text)
    pytest.skip(text)


def _extract(repo: Path, commit: str, subdir: str, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    git = subprocess.Popen(
        ["git", "-C", str(repo), "archive", commit, subdir], stdout=subprocess.PIPE
    )
    subprocess.run(["tar", "-x", "-C", str(dest)], stdin=git.stdout, check=True)
    git.stdout.close()
    assert git.wait() == 0, f"git archive of {subdir} at {commit[:10]} failed in {repo}."


@pytest.fixture(scope="module")
def replayed(tmp_path_factory) -> Path:
    """The sources of the firmware that firmware/patches/ORDER builds today (main/ of both trees), as the firmware folder the lint reads."""
    sources = _base_sources()
    if sources is None:
        _no_tree("No local copy of the pinned firmware base was found.")
    outer, inner = sources
    work = tmp_path_factory.mktemp("psram-replay")
    _extract(outer, _base_value("outer_commit"), "firmware/main", work)
    _extract(inner, _base_value("nested_commit"), "main", work / "firmware" / "xiaozhi-esp32")
    order = [
        line.strip()
        for line in (ROOT / "firmware/patches/ORDER").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    only = ["--include=firmware/main/*", "--include=firmware/xiaozhi-esp32/main/*"]
    for name in order:
        text = (ROOT / "firmware/patches" / name).read_text()
        body = text[re.search(r"^(diff --git|--- )", text, re.M).start() :]
        diff = work / ".patch.diff"
        diff.write_text(body)
        done = subprocess.run(
            ["git", "apply", "--whitespace=nowarn", *only, str(diff)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        assert done.returncode == 0, (
            f"Patch {name} no longer applies after the patches before it: {done.stderr[:300]} "
            "Rebase it onto the tree before this check can run."
        )
    return work / "firmware"


def _created_in_patches() -> tuple[set[str], int]:
    """Task function names that patches create with a PSRAM stack (WithCaps), and how many lambda static tasks they add."""
    names: set[str] = set()
    lambdas = 0
    caps = re.compile(r"xTaskCreate(?:PinnedToCore)?WithCaps\s*\(\s*([A-Za-z_]\w*)")
    for patch in sorted((ROOT / "firmware" / "patches").glob("*.patch")):
        added = [
            line[1:]
            for line in patch.read_text(errors="replace").splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ]
        code = "\n".join(line for line in added if not line.lstrip().startswith("//"))
        names.update(caps.findall(code))
        for match in re.finditer(r"xTaskCreateStatic(?:PinnedToCore)?\s*\(\s*(\[|[A-Za-z_]\w*)", code):
            if match.group(1) == "[":
                lambdas += 1
            else:
                names.add(match.group(1))
    return names, lambdas


def test_the_patch_scan_finds_every_psram_task_the_patches_add() -> None:
    names, lambdas = _created_in_patches()
    assert {"fd_task", "seek_task", "frame_task", "reader_task", "ring_task", "worker_task"} <= names
    assert lambdas >= 1


def test_a_missing_base_tree_fails_in_release_mode_and_says_what_to_run(monkeypatch) -> None:
    monkeypatch.setenv("MAIPAI_RELEASE", "1")
    with pytest.raises(pytest.fail.Exception, match="MAIPAI_FW_BASE_LOCAL"):
        _no_tree("No tree.")
    monkeypatch.delenv("MAIPAI_RELEASE")
    monkeypatch.delenv("CI", raising=False)
    with pytest.raises(pytest.skip.Exception, match="MAIPAI_FW_BASE_LOCAL"):
        _no_tree("No tree.")


def test_the_replayed_tree_has_no_psram_stack_path_to_flash(replayed: Path) -> None:
    tree = lint.Tree(replayed)
    tasks = tree.tasks()
    names = {t for t, _p, _b in tasks}
    assert {"ring_task", "worker_task", "_imu_task"} <= names
    wanted, lambdas = _created_in_patches()
    # A name a later patch removed from the tree again is not expected; every other creation a patch adds must be in the scan.
    in_tree = "\n".join(text for text in tree.files.values())
    missing = sorted(n for n in wanted if re.search(rf"\b{re.escape(n)}\b", in_tree) and n not in names)
    assert not missing, f"The lint scan does not see the PSRAM-stack tasks {missing}; fix the scan in scripts/psram-stack-lint.py."
    assert sum(1 for n in names if n.startswith("<lambda")) >= lambdas
    assert tree.findings() == []


@pytest.mark.skipif(
    not (Path.home() / "esp/stackchan-rebase/trackB/firmware/main").is_dir(),
    reason="the earlier tree is not on this machine",
)
def test_the_lint_finds_the_first_merged_images_boot_loop_in_the_earlier_tree() -> None:
    found = lint.Tree(Path.home() / "esp/stackchan-rebase/trackB/firmware").findings()
    assert any(task == "ring_task" for task, _p, _w in found)


# ---- the core dump reader ---------------------------------------------------------------------------------


def _dump(total: int, version: int = 1, size: int = 0x10000) -> bytes:
    body = struct.pack("<III", total, version, 3) + b"\x00" * (total - 12)
    return body + b"\xff" * (size - len(body))


def test_an_erased_partition_is_no_dump_and_a_whole_one_is_recognized() -> None:
    assert coredump.inspect(b"\xff" * 0x10000) == ("empty", 0)
    assert coredump.inspect(_dump(40_000)) == ("whole", 40_000)


def test_a_cut_short_or_damaged_dump_says_what_to_do() -> None:
    with pytest.raises(coredump.DumpError, match="cut short.*MAX_TASKS_NUM"):
        coredump.inspect(_dump(40_000)[:20_000])
    with pytest.raises(coredump.DumpError, match="does not look like a core dump"):
        coredump.inspect(struct.pack("<III", 5, 0, 0) + b"\x00" * 100)
    with pytest.raises(coredump.DumpError, match="shorter than the 12 byte"):
        coredump.inspect(b"\x01")


def test_the_port_belongs_to_the_session_that_holds_the_usb_lock(tmp_path, monkeypatch) -> None:
    lock = tmp_path / "usb-switch.lock"
    lock.write_text("held")
    monkeypatch.setattr(coredump, "LOCK", lock)
    with pytest.raises(coredump.DumpError, match="another session holds"):
        coredump.read_partition("/dev/cu.fake", lock_held=False)
    assert coredump.main(["--port", "/dev/cu.fake"]) == 2


def test_reading_a_saved_file_reports_an_empty_partition_without_the_elf(tmp_path, capsys) -> None:
    saved = tmp_path / "dump.bin"
    saved.write_bytes(b"\xff" * 0x10000)
    assert coredump.main(["--file", str(saved)]) == 0
    assert "no core dump" in capsys.readouterr().out
    saved.write_bytes(_dump(1234))
    assert coredump.main(["--file", str(saved)]) == 0
    assert "whole dump of 1234 bytes" in capsys.readouterr().out
    assert coredump.main(["--file", str(saved), "--elf", str(tmp_path / "missing.elf")]) == 2


def test_a_member_call_from_the_task_into_a_method_of_the_same_file_is_followed(tmp_path):
    """The reconnect task called self->ConnectAudioChannel(), which reads saved settings; the first merged image with that task on a PSRAM stack crash-looped."""
    files = {
        "proto.cc": """
            void Proto::ReconnectTask(void* arg) { auto* self = static_cast<Proto*>(arg); for (;;) { self->ConnectAudioChannel(); } }
            bool Proto::ConnectAudioChannel() { Settings settings("websocket", false); return settings.GetInt("version") != 0; }
            void Proto::Start() { xTaskCreatePinnedToCoreWithCaps(ReconnectTask, "ws_reconnect", 4096, this, 3, &h, tskNO_AFFINITY, MALLOC_CAP_SPIRAM); }
        """
    }
    found = _findings(tmp_path, files)
    assert any(task == "ReconnectTask" and "Settings" in word for task, _path, word in found)
