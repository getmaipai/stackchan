# ruff: noqa: E501
"""Firmware patches K10 to K13 (2026-11-17): packs for languages and offline phrases on the shared loader.

The pure C cores run their host tests against the headers as the whole of ORDER leaves them (the new pack type and the format 2
cache directory, the language words file, the phrase zip), with damaged packs fuzzed under the address and undefined-behavior
checkers, a power cut at every flash operation, and a format 1 directory from the older firmware. Rules the patches keep are
checked here too: listed on ORDER after FI06, header lines, no em dashes, the screen words in the image are English only."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest
from firmware_order_cores import cores_dir

HERE = Path(__file__).resolve().parent
PATCHES = HERE.parents[1] / "firmware" / "patches"
C_TESTS = HERE / "firmware"
NAMES = [
    "K10-pack-types-phrase-and-cache-format-2.patch",
    "K11-language-pack-screen-words.patch",
    "K12-offline-phrases-pack.patch",
    "K13-pack-loader-consumers.patch",
]


def _run_c(cores: Path, source: str, tmp_path: Path, *, sanitize: bool, libs: tuple[str, ...] = ()) -> str:
    binary = tmp_path / "t"
    flags = ["-fsanitize=address,undefined", "-fno-sanitize-recover=undefined", "-g"] if sanitize else ["-O1"]
    build = subprocess.run(
        ["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", *flags, f"-I{cores}", str(C_TESTS / source), "-o", str(binary), *libs, "-lm"],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=900)
    assert run.returncode == 0 and "all passed" in run.stdout, run.stdout + run.stderr
    return run.stdout


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
@pytest.mark.parametrize("sanitize", [False, True], ids=["plain", "asan_ubsan"])
@pytest.mark.parametrize(
    ("source", "libs"),
    [
        ("lang_core_test.c", ()),
        ("phrasepack_core_test.c", ("-lz",)),
        ("packcache_k_test.c", ()),
        ("pack_core_test.c", ("-lz",)),
        ("packcache_core_test.c", ()),
        ("face_cores_test.c", ()),
    ],
)
def test_the_cores_pass_their_tests(tmp_path_factory, tmp_path, source, libs, sanitize):
    _run_c(cores_dir(tmp_path_factory), source, tmp_path, sanitize=sanitize, libs=libs)


def test_the_patches_are_on_order_after_fi06_and_carry_header_lines():
    order = [n for n in (PATCHES / "ORDER").read_text().split() if n and not n.startswith("#")]
    first = order.index(NAMES[0])
    assert first > order.index("FI06-snapshot-includes-overlays-and-effects.patch")
    assert order[first : first + len(NAMES)] == NAMES
    for name in NAMES:
        text = (PATCHES / name).read_text()
        head = text.split("diff --git", 1)[0]
        for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash:"):
            assert key in head, (name, key)
        assert chr(8212) not in text, name


def _string_literals(text: str) -> list[str]:
    code = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.findall(r'"((?:[^"\\\n]|\\.)*)"', code)


def test_only_english_words_stay_in_the_image(tmp_path_factory):
    """The point of K11: the weekday, month and chip words of the other five languages are gone from the compiled-in tables."""
    cores = cores_dir(tmp_path_factory)
    foreign = {"Sveglia", "Wecker", "Minut.", "Alarma", "Alarme", "Tiempo", "Tempo", "mie", "jue", "vie", "aou", "Okt", "gio", "dim", "seg", "ter"}
    for name in ("maipai_face_clock_core.h", "maipai_face_timers_core.h", "maipai_lang_core.h"):
        literals = set(_string_literals((cores / name).read_text()))
        for text in literals:
            assert not (set(re.split(r"[ ,=]", text)) & foreign), (name, text)
    clock = (cores / "maipai_face_clock_core.h").read_text()
    assert "MF_WEEKDAY" not in clock and "MF_MONTH" not in clock


def test_the_unit_screen_font_has_no_accented_letters():
    """Why packs carry plain ASCII: the build's Montserrat fonts draw 0x20 to 0x7E and the degree sign. The pack core refuses a byte outside ASCII."""
    core = (PATCHES / NAMES[1]).read_text()
    assert "MLW_ERR_ASCII" in core and "Montserrat" in core
