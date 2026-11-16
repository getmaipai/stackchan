"""Item 12: the cooking helper prompt pack. Text only: it rides the persona and the existing timer tool."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from maipai_body.bodies.stackchan.timers import LABEL_MAX, clean_label
from maipai_body.unit_settings import MAX_PERSONA, UnitSettingsStore

PACKS = Path(__file__).resolve().parents[1] / "personas"
UNIT = "aa:bb:cc:dd:ee:01"


@pytest.mark.parametrize("lang", ["en", "es"])
def test_the_pack_fits_the_persona_field_and_is_plain_text(lang, tmp_path):
    text = (PACKS / f"cooking.{lang}.txt").read_text(encoding="utf-8")
    assert 0 < len(text) <= MAX_PERSONA
    assert chr(8212) not in text
    assert UnitSettingsStore(tmp_path / "u.json").update(UNIT, {"persona": text})["persona"] == text


@pytest.mark.parametrize("lang", ["en", "es"])
def test_the_pack_names_the_real_timer_tools_and_the_commands(lang):
    text = (PACKS / f"cooking.{lang}.txt").read_text(encoding="utf-8")
    for tool in ("self.timer.set", "self.timer.list", "self.timer.cancel"):
        assert tool in text
    assert ("next step" if lang == "en" else "siguiente paso") in text
    assert "8" in text  # the unit holds at most 8 timers


def test_the_spanish_pack_is_spanish_and_has_no_accents_the_screen_cannot_draw():
    text = (PACKS / "cooking.es.txt").read_text(encoding="utf-8")
    assert text.isascii()
    assert "temporizador" in text and "siguiente" in text


def test_the_example_labels_survive_the_timer_label_cleaner():
    for label in ("pasta boil", "hervir pasta"):
        assert clean_label(label) == label and len(label) <= LABEL_MAX
    assert re.search(r"two or three", (PACKS / "cooking.en.txt").read_text())
