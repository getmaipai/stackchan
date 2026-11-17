# ruff: noqa: E501
"""The PSRAM-stack lint (scripts/psram-stack-lint.py, patch FM05) and the core dump reader (scripts/fw-coredump.py, patch FM02)."""

from __future__ import annotations

import importlib.util
import struct
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


PATCHED = Path.home() / "esp/stackchan-rebase/fable/firmware"


@pytest.mark.skipif(
    not (PATCHED / "main").is_dir(), reason="the patched firmware tree is not on this machine"
)
def test_the_patched_tree_has_no_psram_stack_path_to_flash() -> None:
    tree = lint.Tree(PATCHED)
    names = {t for t, _p, _b in tree.tasks()}
    assert {
        "ring_task",
        "worker_task",
        "_imu_task",
    } <= names  # the scan really found the old trouble spots
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
