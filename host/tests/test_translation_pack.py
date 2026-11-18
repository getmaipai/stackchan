# ruff: noqa: E501
"""The translator review pack (scripts/translation-pack.py, docs/dev/translation-review/): the export covers every string, the checks catch what would break the robot or the page, a
corrected row is applied and the rest stay drafts, and a reviewed word wins over the catalog. Uses a copy of the folders (the script reads MAIPAI_TRANSLATION_OUT and _REVIEWED)."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def pack(tmp_path, monkeypatch):
    monkeypatch.setenv("MAIPAI_TRANSLATION_OUT", str(tmp_path / "out"))
    monkeypatch.setenv("MAIPAI_TRANSLATION_REVIEWED", str(tmp_path / "reviewed"))
    spec = importlib.util.spec_from_file_location("translation_pack_t", ROOT / "scripts" / "translation-pack.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["translation_pack_t"] = mod
    spec.loader.exec_module(mod)
    assert mod.cmd_export() == 0
    return mod


def _rows(path: Path):
    with path.open(newline="", encoding="utf-8") as h:
        return list(csv.DictReader(h))


def _write(path: Path, rows):
    with path.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def test_the_export_has_every_catalog_string_the_robot_screen_words_the_packs_and_the_doc_titles(pack, tmp_path):
    import maipai_body.i18n as i18n

    rows = _rows(tmp_path / "out" / "fr.csv")
    keys = {r["key"] for r in rows}
    assert set(i18n.CATALOG["en"]) <= keys
    assert any(k.startswith("unit.screen.") for k in keys) and "pack.weekdays" in keys and any(k.startswith("doc.title.") for k in keys)
    assert all(r["status"] in ("machine draft", "missing", "reviewed") for r in rows)
    assert (tmp_path / "out" / "STATUS.md").read_text().count("nobody yet") == 5


def test_the_checks_catch_what_would_break_the_page_or_the_robot(pack, tmp_path):
    by = {r["key"]: r for r in _rows(tmp_path / "out" / "de.csv")}
    placeholder_key = next(k for k, r in by.items() if "{" in r["english"] and k.startswith(("settings.", "update.")))
    def errors(key, text):
        row = dict(by[key], translation=text)
        return [t for level, t in pack.problems(row) if level == "error"]
    assert errors(placeholder_key, "ohne Platzhalter")                       # a placeholder is missing
    assert errors("settings.title", "Einstellungen " + chr(0x2014) + " jetzt")           # an em dash
    assert errors("settings.title", " mit Leerzeichen ")                     # a space at the ends
    assert errors("settings.title", "mit <b>Markup</b>")                     # markup
    assert errors("settings.title", "")                                     # empty
    unit = next(k for k in by if k.startswith("unit.screen."))
    assert errors(unit, "Crème œuf")                               # the oe ligature is not in the robot's font
    assert errors(unit, "“curly”")                                 # curly quotes are not either
    assert not errors(unit, "Grüße")                               # ordinary accents are fine
    assert errors("pack.weekdays", "So,Mo,Di,Mi,Do,Fr")                     # six words, not seven
    assert errors("pack.weekdays", "Sö,Mo,Di,Mi,Do,Fr,Sa")             # an accent in a pack
    assert errors("pack.alarm", "ein sehr langes Wort")                      # over the hard limit of 11


def test_a_corrected_row_is_applied_and_the_rest_stay_drafts_and_a_reviewed_word_wins(pack, tmp_path):
    out = tmp_path / "out"
    rows = _rows(out / "it.csv")
    target = next(r for r in rows if r["key"] == "settings.save")
    pending_row = next(r for r in rows if r["key"].startswith("doc.title."))
    sent = tmp_path / "it.csv"
    target["translation"] = "Salva ora"
    pending_row["translation"] = "Titolo corretto"
    confirmed = next(r for r in rows if r["key"] == "settings.mute")
    confirmed["status"] = "ok"
    _write(sent, rows)
    assert pack.cmd_import(sent, "Test Reviewer", "2026-11-18") == 0
    overlay = json.loads((tmp_path / "reviewed" / "it.json").read_text(encoding="utf-8"))
    assert overlay["strings"]["settings.save"] == "Salva ora" and "settings.mute" in overlay["strings"] and overlay["reviewer"] == "Test Reviewer"
    assert any(r["key"] == pending_row["key"] for r in _rows(out / "pending" / "it.csv"))   # a title goes to the owner, not into the page
    after = {r["key"]: r for r in _rows(out / "it.csv")}
    assert after["settings.save"]["status"] == "reviewed" and after["settings.title"]["status"] == "machine draft"
    assert "Test Reviewer" in (out / "STATUS.md").read_text()


def test_an_import_with_an_error_changes_nothing(pack, tmp_path):
    rows = _rows(tmp_path / "out" / "es.csv")
    next(r for r in rows if r["key"] == "settings.save")["translation"] = "Guardar " + chr(0x2014) + " ya"
    sent = tmp_path / "es.csv"
    _write(sent, rows)
    assert pack.cmd_import(sent, "Test Reviewer", "2026-11-18") == 1
    assert not (tmp_path / "reviewed").exists()


def test_the_page_reads_reviewed_words_last(tmp_path, monkeypatch):
    import maipai_body.i18n as i18n

    assert i18n.t("fr", "settings.save") == i18n.CATALOG["fr"]["settings.save"]
    path = Path(i18n.__file__).parent / "i18n_reviewed"
    assert path.name == "i18n_reviewed" and (path.is_dir() or not path.exists())   # the folder is created by the first import
