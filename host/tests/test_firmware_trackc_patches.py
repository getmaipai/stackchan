"""Patch TC01 (the remote token gate) and the flash-key rule that joins TA01 and TB01 (2026-11-16)."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PATCHES = HERE.parents[1] / "firmware" / "patches"
TC01 = "TC01-remote-token-gate.patch"
HEADER = "firmware/main/hal/maipai_remote_core.h"


def _order() -> list[str]:
    return (PATCHES / "ORDER").read_text().split()


def _added(patch: str, path: str) -> str:
    text = (PATCHES / patch).read_text()
    block = text.split(f"+++ b/{path}\n", 1)[1].split("\n", 1)[1]
    lines = []
    for line in block.splitlines():
        if line.startswith("diff --git"):
            break
        if line.startswith("+"):
            lines.append(line[1:])
    return "\n".join(lines) + "\n"


def test_tc01_replays_last_after_the_two_tracks() -> None:
    order = _order()
    assert order.index(TC01) > order.index("TA04-speech-bubble.patch") > order.index("TB05-visible-remote-control.patch")
    assert order[order.index(TC01) : order.index(TC01) + 4] == [TC01, "TC02-flash-reads-off-psram-stacks.patch", "TC03-boot-internal-ram.patch", "TC04-remote-cue-sound-light-setting-look.patch"] and (PATCHES / TC01).is_file()
    head = (PATCHES / TC01).read_text().split("diff --git", 1)[0]
    for label in ("# Intent:", "# Placement:", "# Upstream:", "# Check after a flash:"):
        assert label in head
    assert "\u2014" not in (PATCHES / TC01).read_text()


@pytest.mark.skipif(shutil.which("cc") is None or shutil.which("git") is None, reason="no C compiler or git")
def test_the_gate_core_test_passes_on_the_header_tc01_leaves(tmp_path: Path) -> None:
    root = tmp_path / "tree"
    (root / "firmware/main/hal").mkdir(parents=True)
    (root / HEADER).write_text(_added("TB05-visible-remote-control.patch", HEADER))
    for number, name in enumerate((TC01, "TC04-remote-cue-sound-light-setting-look.patch")):
        patch = tmp_path / f"gate{number}.diff"
        body = (PATCHES / name).read_text()
        chunk = "diff --git a/" + HEADER + body.split("diff --git a/" + HEADER, 1)[1].split("\ndiff --git", 1)[0] + "\n"
        patch.write_text(chunk)
        applied = subprocess.run(["git", "apply", str(patch)], cwd=root, capture_output=True, text=True)
        assert applied.returncode == 0, applied.stderr
    binary = tmp_path / "gate"
    build = subprocess.run(
        ["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{root / 'firmware/main/hal'}", str(HERE / "firmware" / "remote_gate_test.c"), "-o", str(binary)],
        capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0 and "all passed" in run.stdout, run.stdout


@pytest.mark.parametrize(
    ("kind", "call"),
    [
        ("move", 'maipai_remote_gate(cue_kind.c_str(), "remote"'),
        ("dance", 'maipai_remote_gate("dance"'),
        ("game", 'maipai_remote_gate("game"'),
        ("find", 'maipai_remote_gate("find"'),
        ("listen", 'maipai_remote_gate("listen"'),
        ("photo", 'maipai_remote_gate("photo"'),
    ],
)
def test_every_remote_facing_tool_asks_the_gate_for_its_kind(kind: str, call: str) -> None:
    text = (PATCHES / TC01).read_text()
    assert call in text, kind
    assert text.count('Property("source", kPropertyTypeString') >= 5  # head moves already had one
    assert text.count('Property("token", kPropertyTypeInteger') >= 6


def test_only_the_find_chirp_is_gated_never_its_end() -> None:
    text = (PATCHES / TC01).read_text()
    assert 'properties["find"].value<int>() == 1' in text


def test_a_flash_key_is_the_first_15_characters_in_both_tracks() -> None:
    rows = re.findall(r'\{"([a-z_]+)", "([a-z_]+)", MP_', _added("TA01-prefs-store-and-tools.patch", "firmware/main/hal/maipai_prefs_core.h"))
    assert len(rows) >= 14
    for key, nvs in rows:
        assert len(nvs) <= 15, (key, nvs)
        assert nvs == key[:15], f"{key}: TA01 stores it under {nvs}, TB01's maipai_tb_nvs_key reads {key[:15]}"
    reader = _added("TB01-listening-cues.patch", "firmware/main/hal/maipai_tbprefs.cc")
    assert "strncpy(out, name != nullptr ? name : \"\", 15)" in reader


# A flash or NVS call on a task whose stack is in PSRAM asserts and reboots the unit (2026-11-16: the first merged image looped).
# Every task a patch adds with a PSRAM stack must be reviewed here; the reviewed ones never touch flash themselves.
REVIEWED_PSRAM_STACK_TASKS = {
    "ring_task": "TB01: reads only the cached prefs (maipai_tb_prefs asks the timer task to refresh, TC02)",
    "worker_task": "music features and picture decode: no flash",
    "_imu_task": "IMU: pickup reaction reads the cached prefs (TC02)",
    "_head_touch_update_task": "head touch: no flash",
    "reader_task": "serial tools, bench builds only",
    "seek_task": "S14: the face seeker; the setting comes through maipai_tb_prefs (cached, TC02), the gates through the FM05 guarded readers, the camera and the head touch no flash; scripts/psram-stack-lint.py walks it",
    "fd_task": "FD02: the face detector (experiment image); the model is read in place from the app image (no partition call), the camera read and the model touch no flash, the seek task passes every setting in; scripts/psram-stack-lint.py walks it",
    "snapshot_worker": "FI03: the bench snapshot; draws through LVGL and writes on the cable, no settings and no flash, bench builds only",
    "frame_task": "P13: the picture frame page decodes one frame of the held pack into a PSRAM buffer; takes the pack mutex, no settings, no flash",
    "opus_codec": "M02: decodes, resamples, encodes and queues audio; its callbacks only set event bits; no settings, no flash",
}


def test_every_psram_stack_task_a_patch_adds_has_been_reviewed_for_flash_use() -> None:
    found: set[str] = set()
    for name in _order():
        for line in (PATCHES / name).read_text().splitlines():
            if line.startswith("+") and "WithCaps(" in line and "xTaskCreate" in line and not line.lstrip("+").lstrip().startswith("//"):
                match = re.search(r"WithCaps\(\s*([A-Za-z_][A-Za-z0-9_]*)", line)
                if match:
                    found.add(match.group(1))
    unknown = found - set(REVIEWED_PSRAM_STACK_TASKS)
    assert not unknown, f"a task with a PSRAM stack was added with no review for flash or NVS use: {sorted(unknown)}; read its body and add it to REVIEWED_PSRAM_STACK_TASKS"


def test_the_prefs_reader_never_reads_flash_on_a_psram_stack() -> None:
    reader = _added("TB01-listening-cues.patch", "firmware/main/hal/maipai_tbprefs.cc")
    fixed = (PATCHES / "TC02-flash-reads-off-psram-stacks.patch").read_text()
    assert "esp_ptr_internal" in fixed and "esp_timer_start_once" in fixed
    assert "maipai_tb_prefs();" in fixed and 'maipai_sounds_gate("popup"' in fixed  # the one early read on the main task
    assert "Settings st(MAIPAI_PREFS_NAMESPACE" in reader


def test_a_static_task_with_a_psram_stack_is_reviewed_too() -> None:
    """A task made with xTaskCreateStatic on a heap_caps_malloc(..., MALLOC_CAP_SPIRAM) stack is as exposed as a WithCaps one."""
    found: set[str] = set()
    for name in _order():
        text = (PATCHES / name).read_text()
        added = "\n".join(line[1:] for line in text.splitlines() if line.startswith("+"))
        if "MALLOC_CAP_SPIRAM" not in added or "xTaskCreateStatic" not in added:
            continue
        for match in re.finditer(r'"([a-z_]+)",\s*k?[A-Za-z_0-9 *]*,\s*this,\s*\d+,\s*[a-z_]*stack', added):
            found.add(match.group(1))
        for match in re.finditer(r'xTaskCreateStatic\([^;]*?"([a-z_]+)"', added, re.S):
            found.add(match.group(1))
    reviewed = set(REVIEWED_PSRAM_STACK_TASKS) | {"audio_afe", "encode_wake_word"}  # the engine's own tasks, in the vendor code
    unknown = found - reviewed
    assert not unknown, f"a static task with a PSRAM stack has no review for flash or NVS use: {sorted(unknown)}"


def test_the_settings_reader_names_a_psram_stack_caller() -> None:
    text = (PATCHES / "M05-settings-open-from-psram-stack.patch").read_text()
    assert "esp_ptr_internal(__builtin_frame_address(0))" in text and "pcTaskGetName" in text
