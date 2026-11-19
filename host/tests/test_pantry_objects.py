"""The object table for twenty questions (docs/design/twenty-questions-library.md): shape, uniqueness and the name lists."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

OBJECTS = Path(__file__).resolve().parents[1] / "maipai_packages" / "pantry" / "objects"
LANGUAGES = ("es", "fr", "de", "pt", "it")


def _load(name: str) -> list:
    return json.loads((OBJECTS / f"{name}.json").read_text(encoding="utf-8"))


def test_core_has_at_least_100_objects_in_two_groups() -> None:
    rows = _load("core")
    assert len(rows) >= 100
    groups = [r["group"] for r in rows]
    assert set(groups) == {"animal", "thing"}
    assert groups.count("animal") >= 55 and groups.count("thing") >= 35


def test_core_bits_shape() -> None:
    for row in _load("core"):
        assert set(row) == {"group", "bits", "en"}, f"Bad keys in {row}: use group, bits and en."
        assert len(row["bits"]) == 12 and set(row["bits"]) <= {"0", "1"}, f"Bad bits for {row['en']}: use 12 characters of 0 and 1."


def test_no_more_than_three_objects_share_group_and_bits() -> None:
    """Twelve answers cannot tell every pair of animals apart (a cat and a kitten answer alike). The game guesses twice, so up to three alike objects are fine."""
    count: dict[tuple[str, str], list[str]] = {}
    for row in _load("core"):
        count.setdefault((row["group"], row["bits"]), []).append(row["en"])
    for key, same in count.items():
        assert len(same) <= 3, f"{', '.join(same)} answer all 12 questions alike: change one of them."


def test_the_answers_are_true_to_the_questions() -> None:
    """A spot check of attributes that were wrong once (bit order: alive, water, fly, four legs, fur or feathers, people eat it, found in a house, metal or plastic, bigger than a chair, sound, toy, wear or carry)."""
    rows = {r["en"]: r["bits"] for r in _load("core")}
    assert rows["a crab"][3] == "0" and rows["a starfish"][3] == "0"      # not four legs
    assert rows["a kitten"][8] == "0" and rows["a canary"][8] == "0"      # smaller than a chair
    assert rows["an apple"][11] == "0" and rows["a book"][11] == "1"      # nobody wears an apple; a book is carried
    assert rows["a camel"][6] == "0" and rows["a mouse"][5] == "0"        # not found in a house; not eaten
    assert rows["a trout"][6] == "0" if "a trout" in rows else True


def test_core_names_fit_the_record() -> None:
    for row in _load("core"):
        assert len(row["en"].encode("utf-8")) <= 24, f"{row['en']} is over 24 bytes: pick a shorter name."


@pytest.mark.parametrize("lang", LANGUAGES)
def test_language_list_matches_core(lang: str) -> None:
    names = _load(lang)
    assert len(names) == len(_load("core")), f"{lang}.json has {len(names)} names: it needs one per object, in the order of core.json."
    for name in names:
        assert isinstance(name, str) and name.strip(), f"{lang}.json holds an empty or non-string name: fix it."
        assert len(name.encode("utf-8")) <= 24, f"{name} in {lang}.json is over 24 bytes: pick a shorter name."
    assert len(set(names)) == len(names), f"{lang}.json repeats a name: each object needs its own name."
