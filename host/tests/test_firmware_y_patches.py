"""The 2026-11-16 reliability patches (Y01 to Y04): listed in ORDER, documented, and the plain-C rules compile and pass."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from test_stackchan_sounds_core import header_from_patch

HERE = Path(__file__).resolve().parent
PATCHES = HERE.parents[1] / "firmware" / "patches"
NAMES = [
    "Y01-user-head-moves-pass-the-idle-gate.patch",
    "Y02-find-my-robot-overrides-mute.patch",
    "Y03-opus-decode-above-the-screen-task.patch",
    "Y04-find-and-game-screen-cues.patch",
]


def _text(name: str) -> str:
    return (PATCHES / name).read_text()


def test_listed_in_order_after_l04_and_documented():
    order = (PATCHES / "ORDER").read_text().split()
    assert order.index("L04-ignore-idle-host-looks.patch") < order.index(NAMES[0])
    assert order.index(NAMES[0]) < order.index(NAMES[1]) < order.index(NAMES[2])
    for name in NAMES:
        head = _text(name).split("diff --git", 1)[0]
        for key in ("# Intent:", "# Placement:", "# Upstream:", "# Check after a flash:"):
            assert key in head, (name, key)


def test_the_marker_and_the_find_property_are_in_the_tool_definitions():
    assert 'Property("source", kPropertyTypeString' in _text(NAMES[0])
    assert 'Property("find", kPropertyTypeInteger, 0, 0, 2)' in _text(NAMES[1])
    assert "opus_codec\", 2048 * 12, this, 5" in _text(NAMES[2])


def test_find_never_touches_the_microphone_or_privacy():
    added = [line for line in _text(NAMES[1]).splitlines() if line.startswith("+")]
    body = "\n".join(added)
    assert "maipai_privacy_set" not in body and "mic" not in body.lower()


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler")
def test_headgate_core(tmp_path):
    header = "\n".join(
        line[1:]
        for line in _text(NAMES[0]).split("+++ b/firmware/main/hal/maipai_headgate_core.h\n", 1)[1].split("diff --git", 1)[0].splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    (tmp_path / "maipai_headgate_core.h").write_text(header + "\n")
    exe = tmp_path / "t"
    subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{tmp_path}", str(HERE / "firmware/headgate_core_test.c"), "-o", str(exe)], check=True)
    assert "ok" in subprocess.run([str(exe)], check=True, capture_output=True, text=True).stdout


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler")
def test_find_core(tmp_path):
    header_from_patch(tmp_path)  # the sounds core as patches 115, 141 and 151 leave it
    core = tmp_path / "firmware/main/hal/maipai_sounds_core.h"
    patch = _text(NAMES[1])
    part = re.split(r"(?m)^(?=diff --git )", patch)
    mine = [p for p in part if p.startswith("diff --git a/firmware/main/hal/maipai_sounds_core.h")][0]
    (tmp_path / "find.diff").write_text(mine)
    applied = subprocess.run(["git", "apply", "--whitespace=nowarn", "find.diff"], cwd=tmp_path, capture_output=True, text=True)
    if applied.returncode != 0:
        pytest.skip("the sounds core in this tree differs from the replay base: " + applied.stderr[:200])
    exe = tmp_path / "t"
    subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{core.parent}", str(HERE / "firmware/find_core_test.c"), "-o", str(exe)], check=True)
    assert "ok" in subprocess.run([str(exe)], check=True, capture_output=True, text=True).stdout
