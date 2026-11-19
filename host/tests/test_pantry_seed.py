"""The built-in pantry seed library (docs/dev/pantry-seed.md): every file parses, every record passes the shape rules, the counts are the promised ones,
no two records share an id, and the master library accepts them all."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from maipai_packages.pantry import record as record_module
from maipai_packages.pantry.library import Library
from maipai_packages.pantry.dedupe import dedupe
from maipai_packages.pantry.record import SITUATIONS, Record, check

SEED = Path(record_module.__file__).parent / "seed"
COUNTS = {
    "en": {"joke": 100, "riddle": 100, "trivia": 100, "line": 120, "object": 106},
    **{lang: {"joke": 40, "riddle": 40, "trivia": 40, "line": 120, "object": 106} for lang in ("es", "fr", "de", "pt", "it")},
}
FILES = sorted(SEED.glob("*.json"))
MAX_LINE_CHARS = 36  # one subtitle strip row (docs/design/offline-lines-screens.md)


def _load(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, list), f"{path.name} must hold a JSON list of records."
    return data


def test_every_expected_file_exists_and_nothing_else():
    expected = {f"{lang}-{kind}.json" for lang, kinds in COUNTS.items() for kind in kinds}
    assert {p.name for p in FILES} == expected


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_file_records_are_valid_kid_records_of_the_named_language_and_kind(path):
    language, _, rest = path.stem.partition("-")
    rows = _load(path)
    assert len(rows) == COUNTS[language][rest], f"{path.name} has {len(rows)} records."
    for row in rows:
        rec = Record.from_json(row)
        assert (rec.language, rec.kind, rec.rating) == (language, rest, "kid"), row
        assert check(rec) == rec, f"{path.name}: the record is not stored in its checked form: {row['text']!r}"
        for field in ("text", "answer", "extra"):
            assert "\u2014" not in row[field] and "\u2013" not in row[field], f"{path.name}: a dash in {field}."


@pytest.mark.parametrize("path", [p for p in FILES if p.stem.endswith("-trivia")], ids=lambda p: p.name)
def test_trivia_wrong_answers_differ_from_each_other_and_from_the_right_one(path):
    for row in _load(path):
        wrong = row["extra"].split("|")
        assert len(wrong) == 2 and wrong[0] != wrong[1], row
        assert row["answer"] not in wrong, row


@pytest.mark.parametrize("path", [p for p in FILES if p.stem.endswith("-line")], ids=lambda p: p.name)
def test_every_situation_has_six_lines_and_the_lines_pass_the_dedupe(path):
    records = [Record.from_json(row) for row in _load(path)]
    per_situation = {tag: sum(1 for r in records if r.extra == tag) for tag in SITUATIONS}
    assert per_situation == {tag: 6 for tag in SITUATIONS}, f"{path.name}: every situation needs exactly 6 lines, found {per_situation}."
    kept, report = dedupe(records, [])
    assert len(kept) == len(records), f"{path.name}: the dedupe drops lines that are too alike: {report.dropped}."


@pytest.mark.parametrize("path", [p for p in FILES if p.stem.endswith("-line")], ids=lambda p: p.name)
def test_every_line_fits_one_subtitle_row_and_ids_are_unique(path):
    rows = _load(path)
    too_long = [(len(row["text"]), row["text"]) for row in rows if row["kind"] == "line" and len(row["text"]) > MAX_LINE_CHARS]
    assert not too_long, f"{path.name}: lines over {MAX_LINE_CHARS} characters do not fit one subtitle row; shorten them: {too_long}."
    records = [Record.from_json(row) for row in rows]
    assert len(records) == 6 * len(SITUATIONS)
    assert all(sum(1 for r in records if r.extra == tag) == 6 for tag in SITUATIONS)
    assert len({r.id_hex for r in records}) == len(records), f"{path.name} repeats a line."


def test_no_duplicate_ids_across_all_files():
    seen: dict[str, str] = {}
    for path in FILES:
        for row in _load(path):
            rec = Record.from_json(row)
            assert rec.id_hex not in seen, f"{path.name} repeats a record from {seen.get(rec.id_hex)}: {rec.text!r}"
            seen[rec.id_hex] = path.name
    assert len(seen) == sum(n for kinds in COUNTS.values() for n in kinds.values())


def test_library_accepts_every_seed_record(tmp_path):
    library = Library(tmp_path / "library")
    records = [Record.from_json(row) for path in FILES for row in _load(path)]
    assert library.add(records) == len(records)
    for language, kinds in COUNTS.items():
        for kind, count in kinds.items():
            assert len(library.records(kind=kind, language=language)) == count
