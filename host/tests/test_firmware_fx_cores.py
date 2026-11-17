# ruff: noqa: E501
"""The unit's preferences table, screen effects and overlay engine (firmware patches TA01 to TA04): the pure C cores run
their own tests, and the unit's key table is checked against the host's (unit_prefs.PREFS) so the two never drift."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from maipai_body import reply_tags, unit_prefs
from maipai_body.spelling_aliases import to_unit_keys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PATCHES = ROOT / "firmware" / "patches"
C_TESTS = HERE / "firmware"
CHAIN = [
    "TA01-prefs-store-and-tools.patch",
    "TA02-screen-effects-and-governor.patch",
    "TA03-overlay-engine.patch",
    "TA04-speech-bubble.patch",
    "TB04-pickup-detection.patch",  # the pickup row of the table, which N02 sits beside
    "N01-banner-row-and-subtitles.patch",
    "N02-banner-row-messages.patch",
    "S11-turn-to-faces-setting.patch",  # the turn_to_faces row, between top_bar and pickup_reaction
    "O01-overlay-engine-bigger-shapes-and-combinations.patch",  # the overlay core as it is now (bigger shapes, three layers, combinations)
    "O02-overlays-leave-text-zones-and-eyes.patch",  # ml_eye_center_y and the text-zone keep-out
    "FI05-captions-default-off.patch",  # the captions row defaults to off
]


@pytest.fixture(scope="module")
def cores(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The pure headers as the patches leave them (the *_core.h files only)."""
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    work = tmp_path_factory.mktemp("fxcores")
    for name in [l.strip() for l in (PATCHES / "ORDER").read_text().splitlines() if l.strip() and not l.startswith("#")]:  # the whole of ORDER, as the parity test does
        text = (PATCHES / name).read_text()
        diff = work / "p.diff"
        diff.write_text(text[text.index("diff --git") :])
        run = subprocess.run(
            ["git", "apply", "--include=firmware/main/hal/*_core.h", str(diff)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        assert run.returncode == 0, f"{name}: {run.stderr}"
    return work / "firmware" / "main" / "hal"


@pytest.mark.parametrize("source", ["prefs_core_test.c", "fx_core_test.c", "overlay_core_test.c", "banner_core_test.c", "subs_core_test.c"])
def test_the_c_cores_pass_their_tests(cores: Path, source: str, tmp_path: Path) -> None:
    if shutil.which("cc") is None:
        pytest.skip("no C compiler on this machine")
    binary = tmp_path / "t"
    build = subprocess.run(
        [
            "cc",
            "-std=c99",
            "-Wall",
            "-Wextra",
            "-Werror",
            f"-I{cores}",
            str(C_TESTS / source),
            "-o",
            str(binary),
            "-lm",
        ],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=300)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "all passed" in run.stdout


def _unit_table(cores: Path) -> list[tuple[str, str, str, int]]:
    text = (cores / "maipai_prefs_core.h").read_text()
    body = text[text.index("MP_DEFS[MP_COUNT] = {") :]
    rows = re.findall(r'\{"(\w+)", "(\w+)", MP_(\w+), .*, (\d), (?:NULL|\w+)\},', body)
    return [(key, nvs, kind, int(unit)) for key, nvs, kind, unit in rows]


def test_the_unit_keeps_every_key_the_host_defines_under_the_same_name(cores: Path) -> None:
    table = _unit_table(cores)
    names = [row[0] for row in table]
    host = list(to_unit_keys(dict.fromkeys(unit_prefs.PREFS)))  # the unit keeps its own spelling of two keys
    assert names[: len(host)] == host  # same names, same order: never renamed
    assert names[len(host) :] == ["pickup_reaction"]  # the one extra row the pickup patch reads
    for key, nvs, _kind, _unit in table:
        assert nvs == key[:15]  # a flash key is the first 15 characters of the name
    unit_applied = [key for key, _nvs, _kind, unit in table if unit]
    assert unit_applied == list(to_unit_keys(dict.fromkeys(unit_prefs.UNIT_KEYS)))  # the keys the host sends are the keys the unit applies


def test_the_unit_accepts_every_value_the_host_can_send(cores: Path) -> None:
    text = (cores / "maipai_prefs_core.h").read_text()
    color = re.search(r"MP_NAMES_COLOUR\[\] = \{([^}]*)\}", text)
    assert color is not None
    unit_modes = set(re.findall(r'"(\w+)"', color.group(1)))
    assert set(unit_prefs.PREFS["fx_color_mode"][1]) <= unit_modes
    for key in ("filler_mode", "listen_sound", "listen_light"):
        short = {"filler_mode": "FILLER", "listen_sound": "SOUND", "listen_light": "LIGHT"}[key]
        found = re.search(rf"MP_NAMES_{short}\[\] = \{{([^}}]*)\}}", text)
        assert found is not None
        assert set(unit_prefs.PREFS[key][1]) == set(re.findall(r'"(\w+)"', found.group(1)))


def test_the_unit_draws_every_overlay_the_host_can_name(cores: Path) -> None:
    text = (cores / "maipai_overlay_core.h").read_text()
    names = re.search(r"MO_NAMES\[MO_COUNT\] = \{([^}]*)\}", text, re.S)
    combos = re.search(r"MOP_NAMES\[MOP_COUNT\] = \{([^}]*)\}", text, re.S)
    assert names is not None and combos is not None
    unit_names = [n for n in re.findall(r'"(\w*)"', names.group(1)) if n]
    unit_combos = [n for n in re.findall(r'"(\w*)"', combos.group(1)) if n]
    parts_only = {"moon", "sparkles"}  # drawn only as parts of a combination, so the host does not name them
    assert sorted(set(unit_names) - parts_only) == sorted(reply_tags.ELEMENT_OVERLAYS)  # one list, in two places that must agree
    assert sorted(unit_combos) == sorted(reply_tags.COMBINED_OVERLAYS)
    assert list(reply_tags.OVERLAYS) == list(reply_tags.ELEMENT_OVERLAYS) + list(reply_tags.COMBINED_OVERLAYS)
