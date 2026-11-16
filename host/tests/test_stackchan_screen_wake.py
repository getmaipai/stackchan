# ruff: noqa: E501
"""Patches W01 (screen wake and saved level) and R04 (restart guard back-off): the C cores, the patch files, and the
host's night rule, which must not leave a dimmed unit dim when the face tool is missing."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PATCHES = ROOT / "firmware" / "patches"
C_TESTS = HERE / "firmware"
W01 = "W01-screen-wake-and-saved-level.patch"
R04 = "R04-restart-guard-back-off.patch"


def _split(name: str) -> dict[str, str]:
    """The patch's files by path (the text of each file's diff)."""
    text = (PATCHES / name).read_text()
    out: dict[str, str] = {}
    for block in re.split(r"(?=^diff --git )", text, flags=re.M):
        match = re.match(r"diff --git a/(\S+) b/", block)
        if match:
            out[match.group(1)] = block
    return out


def _added(name: str, path: str) -> str:
    """A new file's content from its patch."""
    block = _split(name)[path]
    body = block.split("\n@@", 1)[1].split("\n", 1)[1]
    return "".join(line[1:] + "\n" for line in body.splitlines() if line.startswith("+"))


@pytest.fixture(scope="module")
def headers(tmp_path_factory: pytest.TempPathFactory) -> Path:
    work = tmp_path_factory.mktemp("cores_w01")
    (work / "maipai_screen_core.h").write_text(
        _added(W01, "firmware/main/hal/maipai_screen_core.h")
    )
    (work / "maipai_heal_core.h").write_text(_added(R04, "firmware/main/hal/maipai_heal_core.h"))
    return work


def _c_test(headers: Path, source: str, tmp_path: Path) -> str:
    if shutil.which("cc") is None:
        pytest.skip("no C compiler on this machine")
    binary = tmp_path / "t"
    build = subprocess.run(
        ["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{headers}", str(C_TESTS / source), "-o", str(binary)],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    return run.stdout


@pytest.mark.parametrize("source", ["screen_core_test.c", "heal_core_test.c"])
def test_the_c_cores_pass_their_tests(headers: Path, source: str, tmp_path: Path) -> None:
    assert "all passed" in _c_test(headers, source, tmp_path)


def test_the_patches_are_in_order_and_carry_their_header_lines() -> None:
    order = (PATCHES / "ORDER").read_text().split()
    assert order.index(W01) > order.index("I01-orientation-event.patch")
    assert order.index(R04) > order.index(W01)
    for name in (W01, R04):
        head = (PATCHES / name).read_text().split("diff --git", 1)[0]
        for key in ("# Intent:", "# Placement:", "# Upstream:", "# Check after a flash:"):
            assert key in head, f"{name}: {key}"
        assert "\u2014" not in (PATCHES / name).read_text()


def test_the_hosts_brightness_is_no_longer_saved_by_the_stock_tool() -> None:
    """The root cause: the stock tool saved the host's dim level. It must be live only."""
    mcp = _split(W01)["firmware/xiaozhi-esp32/main/mcp_server.cc"]
    assert "-                    backlight->SetBrightness(brightness, true);" in mcp
    assert "+                    backlight->SetBrightness(brightness, false);" in mcp


def test_every_input_that_should_wake_the_screen_calls_the_wake_function() -> None:
    patch = (PATCHES / W01).read_text()
    for why in ("touch", "touch bar", "shake", "tilt", "wake word"):
        assert f'maipai_screen_wake("{why}")' in patch or f'maipai_screen_touch(num)' in patch, why
    # the glass: through the one function every touch passes, before the point is stored
    assert "maipai_screen_touch(num);" in _split(W01)["firmware/main/hal/board/hal_bridge.cc"]
    # the press that only woke the screen starts no listen and toggles nothing
    assert "maipai_screen_take_wake_touch()" in _split(W01)["firmware/main/hal/board/stackchan_display.cc"]


def test_the_wake_path_never_reads_flash_from_a_task_with_its_stack_in_external_ram() -> None:
    """The motion and head touch tasks call maipai_screen_wake; a flash read there aborts the unit (patch V03)."""
    source = _added(W01, "firmware/main/hal/maipai_screen.cc")
    wake = source.split("bool maipai_screen_wake", 1)[1].split("\n}\n", 1)[0]
    for forbidden in ("Settings", "nvs_", "RestoreBrightness()"):
        assert forbidden not in wake, forbidden
    assert "RestoreSavedLevel" in source
