"""Patches M01 to M06 (memory headroom, 2026-11-16): the configuration values that hold internal RAM must not drift."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PATCHES = HERE.parents[1] / "firmware" / "patches"
M_PATCHES = [
    "M01-memory-line-stack-margins.patch",
    "M02-opus-stack-in-psram.patch",
    "M03-tools-in-psram.patch",
    "M04-trim-task-stacks.patch",
    "M05-settings-open-from-psram-stack.patch",
    "M06-camera-dma-in-psram.patch",
]


def _added(name: str) -> str:
    return "\n".join(line[1:] for line in (PATCHES / name).read_text().splitlines() if line.startswith("+") and not line.startswith("+++"))


def _order() -> list[str]:
    return (PATCHES / "ORDER").read_text().split()


def test_the_m_patches_follow_the_fm_patches_in_order() -> None:
    order = _order()
    assert order[order.index(M_PATCHES[0]) :][: len(M_PATCHES)] == M_PATCHES
    assert order.index(M_PATCHES[0]) > order.index("FM05-flash-rule-for-psram-stacks.patch")


@pytest.mark.parametrize("name", M_PATCHES)
def test_every_m_patch_has_its_header_and_no_em_dash(name: str) -> None:
    text = (PATCHES / name).read_text()
    head = text.split("diff --git", 1)[0]
    for label in ("# Intent:", "# Placement:", "# Upstream:", "# Check after a flash:"):
        assert label in head, (name, label)
    assert chr(0x2014) not in text, name


def test_the_core_defaults_keep_the_values_that_free_internal_ram() -> None:
    """Values the build reads from sdkconfig.core.defaults. A change here gives back RAM the gate counted on."""
    wanted = {
        "CONFIG_ESP_SYSTEM_EVENT_TASK_STACK_SIZE": "3072",
        "CONFIG_ESP_MAIN_TASK_STACK_SIZE": "6144",
        "CONFIG_CAMERA_PSRAM_DMA": "y",
    }
    found = dict(re.findall(r"^(CONFIG_[A-Z0-9_]+)=(\S+)$", _added("M04-trim-task-stacks.patch") + "\n" + _added("M06-camera-dma-in-psram.patch"), re.M))
    for key, value in wanted.items():
        assert found.get(key) == value, f"{key} must be {value} (patches M04 and M06), found {found.get(key)}"
    # the earlier trims are kept: allocations of 256 bytes and up may come from PSRAM (TN04)
    assert re.search(r"^\+CONFIG_SPIRAM_MALLOC_ALWAYSINTERNAL=256$", (PATCHES / "TN04-travel-memory-freeing.patch").read_text(), re.M)


def test_the_two_memory_switches_default_on() -> None:
    kconfig = _added("M02-opus-stack-in-psram.patch") + "\n" + _added("M03-tools-in-psram.patch")
    for symbol in ("MAIPAI_OPUS_STACK_PSRAM", "MAIPAI_TOOLS_IN_PSRAM"):
        block = kconfig.split(f"config {symbol}\n", 1)[1].split("\nconfig ", 1)[0]
        assert re.search(r"^\s+default y$", block, re.M), symbol


def test_the_task_stack_sizes_are_the_measured_ones() -> None:
    text = _added("M04-trim-task-stacks.patch")
    assert '"audio_input", 2048 * 2' in text  # 4096, was 6144: 4,552 bytes free of 6,144
    assert '"ws_reconnect", 4096' in text  # was 6144: 3,980 free
    assert '"stackchan", 5120' in text  # was 4096: 524 bytes free, under the 1,024 floor


def test_the_opus_task_stays_on_the_reviewed_list() -> None:
    text = _added("M02-opus-stack-in-psram.patch")
    assert "MALLOC_CAP_SPIRAM" in text and "xTaskCreateStatic" in text and '"opus_codec"' in text
    # the PSRAM-stack lint in test_firmware_trackc_patches.py names this task; keep the two together
    lint = (HERE / "test_firmware_trackc_patches.py").read_text()
    assert '"opus_codec"' in lint


def test_the_tool_table_scope_restores_the_threshold() -> None:
    text = _added("M03-tools-in-psram.patch")
    assert "heap_caps_malloc_extmem_enable(0)" in text
    assert "heap_caps_malloc_extmem_enable(CONFIG_SPIRAM_MALLOC_ALWAYSINTERNAL)" in text
