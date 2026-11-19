"""Tier 1 languages (nl, pl, tr, sv, da, nb, cs): machine drafts, shape checks that need no native speaker.
Every key present, nothing empty, placeholders kept, lengths within the review pack's limits, robot screen text drawable, the importer round trip."""
import importlib.util
import json
import re
from pathlib import Path

import pytest

from maipai_body import i18n, i18n_tier1, language_packs

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("translation_pack", ROOT / "scripts" / "translation-pack.py")
tp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tp)

CODES = list(i18n_tier1.CODES)
FIELD = re.compile(r"\{[^{}]*\}")
LATIN1 = re.compile(r"^[\x20-\x7e\xa0-\xff]*$")


@pytest.fixture(scope="module")
def rows():
    return {code: tp.rows_for(code) for code in CODES}


def test_the_seven_languages_are_registered():
    assert CODES == ["nl", "pl", "tr", "sv", "da", "nb", "cs"]
    for code in CODES:
        assert code in i18n.ALL_LANGUAGES and code not in i18n.SUPPORTED and code in i18n.CATALOG and i18n.normalize(code) == code
        assert i18n_tier1.NATIVE[code] and tp.LANGS[code] == i18n_tier1.NAMES[code]


@pytest.mark.parametrize("code", CODES)
def test_every_catalog_key_has_a_draft(code):
    missing = [k for k in i18n.CATALOG["en"] if not i18n.CATALOG[code].get(k)]
    assert not missing, f"{code}: {len(missing)} catalog keys have no draft, first: {missing[:3]}. Draft them in host/maipai_body/i18n_tier1/{code}_<n>.json"
    unknown = [k for k in i18n_tier1.load(code) if not k.startswith(i18n_tier1.NON_CATALOG_PREFIXES) and k not in i18n.CATALOG["en"]]
    assert not unknown, f"{code}: keys that are not in the catalog: {unknown[:3]}"


@pytest.mark.parametrize("code", CODES)
def test_every_review_row_is_filled_and_clean(code, rows):
    bad = []
    for row in rows[code]:
        assert row["translation"].strip(), f"{code}: {row['key']} is empty"
        assert row["status"] == "machine draft", f"{code}: {row['key']} is {row['status']}"
        for level, text in tp.problems(row):
            if level == "error" or not row["key"].startswith(("unit.", "pack.")) and level == "warning":
                bad.append(f"{row['key']}: {text}")
    assert not bad, f"{code}: {len(bad)} problems, first: {bad[:3]}"


@pytest.mark.parametrize("code", CODES)
def test_placeholders_formats_and_no_em_dash(code):
    english = i18n.CATALOG["en"]
    for key, text in i18n.CATALOG[code].items():
        assert sorted(FIELD.findall(text)) == sorted(FIELD.findall(english[key])), f"{code}: {key} changed a {{placeholder}}: keep it exactly"
        assert "\u2014" not in text, f"{code}: {key} has an em dash"
        text.format(**{re.split(r"[:!]", n[1:-1])[0]: 1 for n in FIELD.findall(text)})
    assert i18n.t(code, "settings.title") != "settings.title"


@pytest.mark.parametrize("code", CODES)
def test_robot_screen_rows_are_drawable_in_latin1(code, rows):
    units = [r for r in rows[code] if r["key"].startswith("unit.screen.")]
    assert len(units) == 60
    for r in units:
        assert LATIN1.match(r["translation"]), f"{code}: {r['key']} has letters the screen font lacks"
    drawn, proper = i18n_tier1.drawn(code), i18n_tier1.load(code)
    for key, text in drawn.items():
        assert LATIN1.match(text) and key in proper and not LATIN1.match(proper[key]), f"{code}: {key} is listed as drawn but its proper spelling is Latin-1 already (or missing)"
    if code in ("nl", "sv", "da", "nb"):
        assert not drawn, f"{code} needs no Latin-2 letters"


def test_every_tier1_language_has_a_shipped_screen_words_pack():
    assert set(language_packs.TIER1) == set(CODES) and set(CODES) <= set(language_packs.CODES)
    assert not set(language_packs.BEFORE_K11) & set(CODES)


@pytest.mark.parametrize("code", CODES)
def test_screen_words_pack_has_every_key_and_is_accepted(code):
    row = language_packs.WORDS[code]
    assert set(row) == {"name", "weekdays", "months", "alarm", "timer"}, f"{code}: the pack needs name, weekdays, months, alarm and timer"
    assert row["name"] == i18n_tier1.NATIVE[code]
    assert len(row["weekdays"]) == 7 and len(row["months"]) == 12 and row["alarm"] and row["timer"]
    text = language_packs.words_text(code)
    assert text.startswith(f"lang={code}\n") and text.isascii()
    lines = dict(line.split("=", 1) for line in text.splitlines())
    assert set(lines) == {"lang", "order", "weekdays", "months", "alarm", "timer"}
    assert len(lines["weekdays"].split(",")) == 7 and len(lines["months"].split(",")) == 12
    assert language_packs.build(code).size < 1200  # a few hundred bytes


@pytest.mark.parametrize("code", CODES)
def test_screen_words_pack_matches_the_review_draft(code):
    draft, row = i18n_tier1.load(code), language_packs.WORDS[code]
    assert ",".join(row["weekdays"]) == draft["pack.weekdays"] and ",".join(row["months"]) == draft["pack.months"]
    assert row["alarm"] == draft["pack.alarm"] and row["timer"] == draft["pack.timer"], f"{code}: language_packs.WORDS and i18n_tier1/{code}_*.json disagree; change both"


def test_status_label_and_export_in_sync(rows):
    status = json.loads((ROOT / "docs" / "dev" / "translation-review" / "status.json").read_text())
    table = (ROOT / "docs" / "dev" / "translation-review" / "STATUS.md").read_text()
    for code in CODES:
        assert status[code]["reviewed"] == 0 and status[code]["missing"] == 0 and status[code]["rows"] == len(rows[code])
        csv_rows = tp.read_csv(ROOT / "docs" / "dev" / "translation-review" / f"{code}.csv")
        assert [r["key"] for r in csv_rows] == [r["key"] for r in rows[code]], f"{code}.csv is out of date: run python3 scripts/translation-pack.py export"
        assert i18n_tier1.NAMES[code] in table
    assert table.count(i18n_tier1.DRAFT_LABEL) == len(CODES)


def test_importer_round_trip(tmp_path, monkeypatch, rows):
    out, reviewed = tmp_path / "review", tmp_path / "reviewed"
    out.mkdir()
    monkeypatch.setattr(tp, "OUT", out)
    monkeypatch.setattr(tp, "REVIEWED", reviewed)
    tp.write_csv(out / "pl.csv", rows["pl"])
    returned = [dict(r) for r in rows["pl"]]
    page = next(r for r in returned if r["key"] == "settings.title")
    page["translation"] = "Ustawienia StackChan (poprawione)"
    ok = next(r for r in returned if r["key"] == "settings.unit")
    ok["status"] = "ok"
    title = next(r for r in returned if r["key"].startswith("doc.title."))
    title["translation"] = title["translation"] + " X"
    tp.write_csv(tmp_path / "pl.csv", returned)
    assert tp.cmd_check(tmp_path / "pl.csv") == 0
    assert tp.cmd_import(tmp_path / "pl.csv", "Test Reviewer", "2026-11-18") == 0
    overlay = json.loads((reviewed / "pl.json").read_text(encoding="utf-8"))
    assert overlay["strings"]["settings.title"] == "Ustawienia StackChan (poprawione)" and "settings.unit" in overlay["strings"]
    after = {r["key"]: r for r in tp.read_csv(out / "pl.csv")}
    assert after["settings.title"]["status"] == "reviewed" and after["settings.unit"]["status"] == "reviewed" and after[title["key"]]["status"] == "reviewed"
    assert (out / "pending" / "pl.csv").is_file()
    broken = [dict(r) for r in rows["pl"]]
    next(r for r in broken if r["key"] == "settings.title")["translation"] = "Bez znaku {x}"
    tp.write_csv(tmp_path / "pl-bad.csv", broken)
    assert tp.cmd_check(tmp_path / "pl-bad.csv") == 1   # a placeholder the English does not have is refused
