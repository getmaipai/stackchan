# ruff: noqa: E501
"""Patches FM01 to FM05 (the fixes from the Fable memory and risk review, 2026-11-16): header lines, replay order, and the PC tests of
their pure cores (compiled from the patch text, so the test runs the code the patch ships)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PATCHES = HERE.parents[1] / "firmware" / "patches"
FM = [
    "FM01-first-boot-trial.patch",
    "FM02-flash-core-dump.patch",
    "FM03-remote-second-floor.patch",
    "FM04-pack-boot-on-first-standby.patch",
    "FM05-flash-rule-for-psram-stacks.patch",
]
HAL = "firmware/main/hal/"
CC = shutil.which("cc")


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


def _chunk(patch: str, path: str) -> str:
    body = (PATCHES / patch).read_text()
    return (
        "diff --git a/"
        + path
        + body.split("diff --git a/" + path, 1)[1].split("\ndiff --git", 1)[0].rstrip("\n")
        + "\n"
    )


def _run_c(tmp_path: Path, test: str, root: Path) -> None:
    binary = tmp_path / test
    built = subprocess.run(
        ["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{root}", str(HERE / "firmware" / f"{test}.c"), "-o", str(binary)],
        capture_output=True, text=True,
    )  # fmt: skip
    assert built.returncode == 0, built.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0 and "all passed" in run.stdout, run.stdout


def test_the_fm_patches_replay_last_in_order_with_their_header_lines() -> None:
    order = (PATCHES / "ORDER").read_text().split()
    assert (
        order[
            order.index("TC04-remote-cue-sound-light-setting-look.patch") + 1 : order.index(FM[0])
            + len(FM)
        ]
        == FM
    )
    for name in FM:
        text = (PATCHES / name).read_text()
        head = text.split("diff --git", 1)[0]
        for label in ("# Intent:", "# Placement:", "# Upstream:", "# Check after a flash:"):
            assert label in head, (name, label)
        assert chr(0x2014) not in text, name  # no em dash


@pytest.mark.skipif(CC is None, reason="no C compiler")
def test_the_first_boot_trial_core_passes_its_scripted_boots(tmp_path: Path) -> None:
    (tmp_path / "maipai_update_core.h").write_text(_added(FM[0], HAL + "maipai_update_core.h"))
    _run_c(tmp_path, "update_core_test", tmp_path)


@pytest.mark.skipif(CC is None or shutil.which("git") is None, reason="no C compiler or git")
def test_the_remote_second_floor_core_passes_on_the_header_the_patch_chain_leaves(
    tmp_path: Path,
) -> None:
    root = tmp_path / "tree"
    (root / "firmware/main/hal").mkdir(parents=True)
    header = HAL + "maipai_remote_core.h"
    (root / header).write_text(_added("TB05-visible-remote-control.patch", header))
    for number, name in enumerate(
        ("TC01-remote-token-gate.patch", "TC04-remote-cue-sound-light-setting-look.patch", FM[2])
    ):
        diff = tmp_path / f"gate{number}.diff"
        diff.write_text(_chunk(name, header))
        applied = subprocess.run(
            ["git", "apply", str(diff)], cwd=root, capture_output=True, text=True
        )
        assert applied.returncode == 0, (name, applied.stderr)
    _run_c(tmp_path, "remote_floor_test", root / "firmware/main/hal")
    _run_c(
        tmp_path, "remote_gate_test", root / "firmware/main/hal"
    )  # the older gate scenarios still hold


@pytest.mark.skipif(CC is None, reason="no C compiler")
def test_the_pack_boot_rule_core_passes(tmp_path: Path) -> None:
    (tmp_path / "maipai_packboot_core.h").write_text(_added(FM[3], HAL + "maipai_packboot_core.h"))
    _run_c(tmp_path, "packboot_core_test", tmp_path)


def test_the_pack_boot_task_has_no_timer_any_more_and_starts_from_the_main_loop() -> None:
    text = (PATCHES / FM[3]).read_text()
    assert (
        "esp_timer_create(&boot_args" in text
        and text.count("-    static esp_timer_handle_t boot_timer") == 1
    )
    assert "maipai_packs_boot_poll(hal_bridge::is_xiaozhi_ready())" in text
    assert (
        "xTaskCreate(boot_task" in text and "WithCaps" not in text
    )  # an internal stack that ends itself, not a kept PSRAM one


def test_the_trial_marks_the_image_good_first_and_counts_a_crash_only_after_the_camera() -> None:
    text = (PATCHES / FM[0]).read_text()
    assert (
        "esp_ota_mark_app_valid_cancel_rollback();" in text
    )  # the boot loader's blind rule cannot fire
    assert "maipai_update_board_ready();" in text and "MUC_CAMERA_SETTLE_MS" in text
    assert text.count("firmware_update_rolled_back") >= 1 and '"path\\":\\"quiet' in text


def test_the_core_dump_switches_and_the_boot_event_are_in_the_patch() -> None:
    text = (PATCHES / FM[1]).read_text()
    assert (
        "+CONFIG_ESP_COREDUMP_ENABLE_TO_FLASH=y" in text and "+CONFIG_ESP_COREDUMP_LOGS=n" in text
    )
    assert 'device_events_push("boot_core"' in text and "espcoredump" in text
    assert "rr != ESP_RST_BROWNOUT" in text  # a brownout writes no dump: never report an old one
