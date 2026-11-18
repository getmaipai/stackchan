"""Glyph coverage for the smaller text font (docs/plan/optimization.md, item 1a): every non-ASCII character in a string literal of the unit's firmware sources must be a glyph of the
"basic" charset (890 codepoints), so the default text font can change from "common" (6,845 codepoints, 1.29 MB) to "basic" (about 123 KB) without a missing glyph. The six
languages' accented letters are in the first-run tables and the screens. Reads the newest replayed firmware tree and the charset file of its fonts component; skips without one."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

TREES = sorted((Path.home() / "esp" / "stackchan-rebuild").glob("b[0-9]*"), key=lambda p: int(p.name[1:]) if p.name[1:].isdigit() else 0)
TREE = TREES[-1] if TREES else None
CHARSET = TREE / "firmware/managed_components/78__xiaozhi-fonts/charsets/basic.json" if TREE else None
SKIP = TREE is None or not (CHARSET and CHARSET.exists())

# The letters and marks the six screen languages (en, es, fr, de, pt, it) need beyond ASCII.
NEEDED = "áàâãäåæçéèêëíìîïñóòôõöúùûüýÿßÁÀÂÃÄÇÉÈÊËÍÎÏÑÓÔÕÖÚÙÛÜ¡¿«»·"
# Letters the six languages use that the basic charset lacks. No unit string uses them today; text the host pushes (captions, names) reaches them through the glyph-push path of the
# font capability, so the unit keeps that capability when the font changes. A change here is a decision, so the list is pinned.
KNOWN_GAPS = {"œ", "€"}


@pytest.mark.skipif(SKIP, reason="no replayed firmware tree with the fonts component on this machine")
def test_the_basic_charset_has_every_letter_the_six_languages_need():
    basic = set(json.loads(CHARSET.read_text())["codepoints"])
    missing = [c for c in NEEDED if ord(c) not in basic]
    assert not missing, f"the basic font lacks {missing}: keep the common font or add the glyphs"


@pytest.mark.skipif(SKIP, reason="no replayed firmware tree with the fonts component on this machine")
def test_the_known_gaps_of_the_basic_charset_are_pinned():
    basic = set(json.loads(CHARSET.read_text())["codepoints"])
    assert {c for c in "œŒ€" if ord(c) not in basic} >= KNOWN_GAPS


@pytest.mark.skipif(SKIP, reason="no replayed firmware tree with the fonts component on this machine")
def test_every_non_ascii_character_in_the_unit_strings_is_in_the_basic_charset():
    basic = set(json.loads(CHARSET.read_text())["codepoints"])
    missing: dict[str, set[str]] = {}
    # our own screens and tables (main/hal); the stock sources carry log strings in other scripts that are never drawn
    for f in list((TREE / "firmware/main/hal").rglob("*.h")) + list((TREE / "firmware/main/hal").rglob("*.cc")) + list((TREE / "firmware/main/hal").rglob("*.cpp")):
        if "drivers" in f.parts:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for m in re.finditer(r'"((?:[^"\\\n]|\\.)*)"', text):
            for ch in m.group(1):
                if ord(ch) > 126 and ord(ch) not in basic:
                    missing.setdefault(ch, set()).add(f.name)
    assert not missing, "characters the basic font would lose: " + ", ".join(f"{c!r} in {sorted(v)[:2]}" for c, v in missing.items())
