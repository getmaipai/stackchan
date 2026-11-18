#!/usr/bin/env python3
"""The translator review pack: every user-facing string per language in a plain CSV a native speaker can read and correct, and the importer that takes the corrections back with checks.

  uv run --project host python scripts/translation-pack.py export           write docs/dev/translation-review/<lang>.csv for es fr de pt it, README.md and STATUS.md
  uv run --project host python scripts/translation-pack.py check FILE.csv   check a returned file and print every problem (changes nothing)
  uv run --project host python scripts/translation-pack.py import FILE.csv --reviewer NAME [--date YYYY-MM-DD]
                                                       check, then apply the corrected and confirmed rows: host page and message rows go to host/maipai_body/i18n_reviewed/<lang>.json
                                                       (read last, so a reviewed word always wins); unit screen, language pack and document title rows go to
                                                       docs/dev/translation-review/pending/<lang>.csv for the track that owns them; status.json and STATUS.md are updated
  uv run --project host python scripts/translation-pack.py status           print the status table

Columns: key, english, translation, context, max_chars, limit, screenshot, status, note. A reviewer edits `translation` (and may write in `note`), and marks a row they read and accept as it is
by putting `ok` in `status`. A row that is changed or marked `ok` becomes `reviewed` on import; the rest stay `machine draft` (or `missing` where there is no translation yet).
Checks (the same on every row): not empty; the same {placeholders} as the English; no leading or trailing space; no control characters, no em dash; no < or > or square brackets unless the English has them;
the length within max_chars (`hard` limits fail, `soft` limits warn); and on a row that is drawn on the robot, only the letters the robot's screen font draws (Latin-1: no oe ligature, no curly quotes) and,
for the language pack words, plain ASCII.
Placement: docs and host tooling. Upstream: none."""
from __future__ import annotations

import csv
import functools
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "host"))
sys.path.insert(0, str(ROOT / "host" / "tests"))
OUT = Path(os.environ.get("MAIPAI_TRANSLATION_OUT", ROOT / "docs" / "dev" / "translation-review"))   # the folders can be moved for a test
REVIEWED = Path(os.environ.get("MAIPAI_TRANSLATION_REVIEWED", ROOT / "host" / "maipai_body" / "i18n_reviewed"))
LANGS = {"es": "Spanish", "fr": "French", "de": "German", "pt": "Portuguese", "it": "Italian"}
from maipai_body import i18n_tier1 as tier1   # noqa: E402  tier 1 (Dutch, Polish, Turkish, Swedish, Danish, Norwegian, Czech): machine drafts, data in host/maipai_body/i18n_tier1/

LANGS.update(tier1.NAMES)
COLUMNS = ["key", "english", "translation", "context", "max_chars", "limit", "screenshot", "status", "note"]
GROUPS = {"fam": "parent view", "lk": "lock settings", "pair": "pairing", "pol": "sound and speech", "ww": "wake word", "ln": "language", "net": "network", "nav": "page menu", "g": "general",
          "char": "character", "beh": "behavior", "face": "face and look", "voice": "voice", "state": "face names", "rem": "remote controls", "ra": "remote access", "ts": "settings help",
          "pg": "swipe pages", "units": "units", "sys": "system", "home": "home", "theme": "theme", "day": "days", "react": "reactions", "time": "timers and clock", "phone": "phone link",
          "games": "games", "privacy": "privacy", "people": "people", "look": "look", "system": "system"}
SCREENS = {"lk": "docs/images/vu-lock-screen.png", "pair": "docs/images/vu-pairing.png", "fam": "docs/images/web-features.svg", "time": "docs/images/vu-timers.png"}
LATIN1 = re.compile(r"^[\x20-\x7e\xa0-\xff]*$")
PLACEHOLDER = re.compile(r"\{[^{}]*\}")


def english_catalog() -> tuple[dict, dict]:
    import maipai_body.i18n as i18n

    return i18n.CATALOG["en"], i18n.CATALOG


def reviewed_overlay(lang: str) -> dict[str, str]:
    path = REVIEWED / f"{lang}.json"
    return json.loads(path.read_text(encoding="utf-8")).get("strings", {}) if path.is_file() else {}


def fill_keys(lang: str) -> set[str]:
    keys: set[str] = set()
    for path in (ROOT / "host" / "maipai_body" / "i18n_fill").glob(f"{lang}_*.json"):
        keys |= set(json.loads(path.read_text(encoding="utf-8"))["strings"])
    return keys


@functools.lru_cache(maxsize=1)
def unit_screen_pairs() -> tuple[tuple[str, str], ...]:
    """The English and Spanish words in the unit's apps table (firmware patches replayed, maipai_apps_core.h): the only language built into the unit besides English."""
    from firmware_order_cores import build_cores

    with tempfile.TemporaryDirectory(prefix="tr-cores-") as work:
        subprocess.run(["git", "init", "-q", work], check=True)
        header = (build_cores(Path(work)) / "maipai_apps_core.h").read_text(encoding="utf-8")
    pairs = []
    for m in re.finditer(r'^\s*\{"((?:[^"\\]|\\.)*)",\s*"((?:[^"\\]|\\.)*)"\},\s*$', header, re.M):
        pairs.append((m.group(1), m.group(2)))
    return tuple(pairs)


def doc_titles() -> list[tuple[str, str]]:
    rows = []
    for path in sorted((ROOT / "docs" / "user").glob("*.md")):
        first = path.read_text(encoding="utf-8").split("\n", 1)[0]
        if first.startswith("# "):
            rows.append((path.stem, first[2:].strip()))
    return rows


def rows_for(lang: str) -> list[dict]:
    en, catalog = english_catalog()
    drafts, overlay = fill_keys(lang), reviewed_overlay(lang)
    out: list[dict] = []
    for key, english in en.items():
        translation = overlay.get(key) or catalog[lang].get(key, "")
        group = key.split(".")[2] if key.startswith("settings.ui.") and key.count(".") >= 3 else key.split(".")[0] if "." in key else "page"
        context = "update and command line messages" if key.startswith("update.") else "settings page, " + GROUPS.get(group, group) if key.startswith("settings.") else "settings page"
        status = "reviewed" if key in overlay else ("missing" if not translation or translation == english and lang != "en" and len(english) > 14 and key in drafts else "machine draft")
        soft = max(len(english) + 24, int(len(english) * 1.6))
        out.append({"key": key, "english": english, "translation": translation, "context": context, "max_chars": soft, "limit": "soft", "screenshot": SCREENS.get(group, "docs/images/web-features.svg"), "status": status, "note": ""})
    units = unit_screen_pairs()
    draft1 = tier1.load(lang) if lang in tier1.NAMES else {}
    drawn1 = tier1.drawn(lang) if lang in tier1.NAMES else {}
    for n, (english, spanish) in enumerate(units):
        translation = spanish if lang == "es" else drawn1.get(f"unit.screen.{n:03d}", draft1.get(f"unit.screen.{n:03d}", ""))
        out.append({"key": f"unit.screen.{n:03d}", "english": english, "translation": translation, "context": "robot screen (apps, timers, settings sheet); drawn in the robot's Latin-1 font",
                    "max_chars": max(len(english) + 6, int(len(english) * 1.4)), "limit": "soft", "screenshot": "docs/images/vu-control-sheet.png", "status": "machine draft" if translation else "missing",
                    "note": f"proper spelling (needs the Latin-2 font subset): {draft1[f'unit.screen.{n:03d}']}" if f"unit.screen.{n:03d}" in drawn1 else ""})
    import maipai_body.language_packs as packs

    words = packs.WORDS.get(lang) or ({f: draft1[f"pack.{f}"] for f in ("weekdays", "months", "alarm", "timer")} if f"pack.weekdays" in draft1 else None)
    if words:
        for field, limit in (("weekdays", 7), ("months", 7), ("alarm", 11), ("timer", 11)):
            value = words[field]
            value = ",".join(value) if isinstance(value, (tuple, list)) else str(value)
            english_value = {"weekdays": "Sun,Mon,Tue,Wed,Thu,Fri,Sat", "months": "Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec", "alarm": "Alarm", "timer": "Timer"}[field]
            out.append({"key": f"pack.{field}", "english": english_value, "translation": value, "context": f"robot screen words pack: each word at most {limit} plain ASCII letters, comma separated, Sunday first" if field in ("weekdays", "months") else "robot screen words pack: at most 11 plain ASCII letters",
                        "max_chars": 10**4 if field in ("weekdays", "months") else limit, "limit": "hard", "screenshot": "docs/images/vu-clock.png", "status": "machine draft", "note": ""})
    for stem, title in doc_titles():
        out.append({"key": f"doc.title.{stem}", "english": title, "translation": draft1.get(f"doc.title.{stem}", ""), "context": f"title of docs/user/{stem}.md (the user pages exist in English only)", "max_chars": max(len(title) + 20, int(len(title) * 1.6)), "limit": "soft",
                    "screenshot": "", "status": "machine draft" if draft1.get(f"doc.title.{stem}") else "missing", "note": ""})
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def problems(row: dict) -> list[tuple[str, str]]:
    """(level, text) for one row: level is error or warning."""
    out: list[tuple[str, str]] = []
    key, english, text = row["key"], row["english"], row["translation"]
    if not text.strip():
        return [("error", "the translation is empty")]
    if (text[:1].isspace() != english[:1].isspace()) or (text[-1:].isspace() != english[-1:].isspace()):
        out.append(("error", "the translation starts or ends with a space where the English does not (or the other way round)"))
    if PLACEHOLDER.findall(text) != PLACEHOLDER.findall(english) and sorted(PLACEHOLDER.findall(text)) != sorted(PLACEHOLDER.findall(english)):
        out.append(("error", f"placeholders differ: English has {PLACEHOLDER.findall(english)}, the translation has {PLACEHOLDER.findall(text)}"))
    if re.search(r"[\x00-\x08\x0b-\x1f\x7f]", text):
        out.append(("error", "a control character"))
    if chr(0x2014) in text:
        out.append(("error", "an em dash (use a comma, a colon or two sentences)"))
    for ch in "<>[]":
        if ch in text and ch not in english:
            out.append(("error", f"'{ch}' is not in the English (it could be read as markup or as a reply tag)"))
    limit = int(row["max_chars"] or 0)
    longest = max((len(part) for part in re.split(r"[,]", text)), default=0) if key in ("pack.weekdays", "pack.months") else len(text)
    if limit and longest > limit:
        out.append(("error" if row["limit"] == "hard" else "warning", f"{longest} characters, the limit is {limit} ({row['limit']})"))
    if key.startswith(("unit.", "pack.")) and not LATIN1.match(text):
        bad = sorted({c for c in text if not LATIN1.match(c)})
        out.append(("error", f"characters the robot's screen font does not draw: {''.join(bad)}"))
    if key.startswith("pack.") and not text.isascii():
        out.append(("error", "language pack words are plain ASCII only (the unit refuses a pack with an accent)"))
    if key == "pack.weekdays" and len(text.split(",")) != 7:
        out.append(("error", "weekdays need exactly 7 words"))
    if key == "pack.months" and len(text.split(",")) != 12:
        out.append(("error", "months need exactly 12 words"))
    return out


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"translation-pack: {path.name} lacks the columns {missing}. Keep the header row of the exported file.")
        return list(reader)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def lang_of(path: Path) -> str:
    code = path.stem.split("-")[0]
    if code not in LANGS:
        raise SystemExit(f"translation-pack: name the file <language>.csv with one of {', '.join(LANGS)} (it is {path.name}).")
    return code


def touched(rows: list[dict], lang: str) -> list[dict]:
    """The rows a reviewer changed or marked ok (against the exported file); every row when there is no exported file to compare with."""
    exported = OUT / f"{lang}.csv"
    if not exported.is_file():
        return rows
    base = {r["key"]: r for r in read_csv(exported)}
    return [r for r in rows if r["key"] in base and (r["translation"].strip() != base[r["key"]]["translation"].strip() or r["status"].strip().lower() in ("ok", "reviewed"))]


def cmd_check(path: Path, quiet: bool = False) -> int:
    rows = read_csv(path)
    checked = touched(rows, lang_of(path))
    errors = 0
    for row in checked:
        if row["status"] == "missing" and not row["translation"].strip():
            continue   # nothing was supplied for this row
        for level, text in problems(row):
            errors += level == "error"
            if not quiet:
                print(f"{level}: {row['key']}: {text}")
    print(f"translation-pack: {path.name}: {len(rows)} rows, {len(checked)} changed or confirmed, {errors} error(s)")
    return 1 if errors else 0


def load_status() -> dict:
    path = OUT / "status.json"
    return json.loads(path.read_text()) if path.is_file() else {}


def render_status(status: dict) -> str:
    lines = ["# Translation status", "", "Made by `python3 scripts/translation-pack.py` (export and import); do not edit by hand. Every translation is a machine draft until a native speaker has read it.", "",
             "| Language | File | Rows | Reviewed | Machine draft | Missing | Last review | Completeness |", "|---|---|---|---|---|---|---|---|"]
    for lang, name in LANGS.items():
        s = status.get(lang, {})
        lines.append(f"| {name} | `{lang}.csv` | {s.get('rows', 0)} | {s.get('reviewed', 0)} | {s.get('machine_draft', 0)} | {s.get('missing', 0)} | {s.get('reviewer', 'nobody yet')} {s.get('date', '')} | {tier1.DRAFT_LABEL if lang in tier1.NAMES else 'machine draft'} |".replace("  ", " "))
    return "\n".join(lines) + "\n"


def refresh_status(status: dict) -> dict:
    for lang in LANGS:
        path = OUT / f"{lang}.csv"
        if not path.is_file():
            continue
        rows = read_csv(path)
        counts = {k: sum(1 for r in rows if r["status"] == k) for k in ("reviewed", "machine draft", "missing")}
        entry = status.setdefault(lang, {})
        entry.update({"rows": len(rows), "reviewed": counts["reviewed"], "machine_draft": counts["machine draft"], "missing": counts["missing"]})
    return status


def cmd_export() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    status = load_status()
    for lang in LANGS:
        write_csv(OUT / f"{lang}.csv", rows_for(lang))
    refresh_status(status)
    (OUT / "status.json").write_text(json.dumps(status, indent=1) + "\n")
    (OUT / "STATUS.md").write_text(render_status(status))
    (OUT / "README.md").write_text(README)
    print(f"wrote {len(LANGS)} files to {rel(OUT)}")
    return 0


def cmd_import(path: Path, reviewer: str, date: str) -> int:
    lang = lang_of(path)
    if cmd_check(path, quiet=False):
        print("translation-pack: nothing was imported. Fix the errors above and send the file again.")
        return 1
    returned = read_csv(path)
    current = {r["key"]: r for r in read_csv(OUT / f"{lang}.csv")}
    overlay = reviewed_overlay(lang)
    pending: list[dict] = []
    applied = 0
    for row in returned:
        base = current.get(row["key"])
        if base is None:
            print(f"warning: {row['key']}: not a key of the exported file, skipped")
            continue
        changed = row["translation"].strip() != base["translation"].strip()
        confirmed = row["status"].strip().lower() in ("ok", "reviewed")
        if not (changed or confirmed) or not row["translation"].strip():
            continue
        base.update({"translation": row["translation"].strip(), "status": "reviewed", "note": row["note"]})
        if row["key"].startswith("settings.") or row["key"].startswith("update.") or not row["key"].split(".")[0] in ("unit", "pack", "doc"):
            overlay[row["key"]] = row["translation"].strip()
            applied += 1
        else:
            pending.append(base)
    if overlay:
        REVIEWED.mkdir(parents=True, exist_ok=True)
        (REVIEWED / f"{lang}.json").write_text(json.dumps({"lang": lang, "reviewer": reviewer, "date": date, "strings": dict(sorted(overlay.items()))}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if pending:
        (OUT / "pending").mkdir(exist_ok=True)
        write_csv(OUT / "pending" / f"{lang}.csv", pending)
    write_csv(OUT / f"{lang}.csv", list(current.values()))
    status = load_status()
    status.setdefault(lang, {}).update({"reviewer": reviewer, "date": date})
    refresh_status(status)
    (OUT / "status.json").write_text(json.dumps(status, indent=1) + "\n")
    (OUT / "STATUS.md").write_text(render_status(status))
    print(f"translation-pack: {lang}: {applied} host page or message row(s) applied (host/maipai_body/i18n_reviewed/{lang}.json), {len(pending)} unit, pack or title row(s) kept in {rel(OUT)}/pending/{lang}.csv for the track that owns them")
    return 0


README = """# Translation review pack

For a native speaker. One file per language (`es.csv`, `fr.csv`, `de.csv`, `pt.csv`, `it.csv`); open it in a spreadsheet and keep the first row (the column names).

Each row is one thing a person reads on the robot or on the settings page. The columns:

| Column | What it is |
|---|---|
| `key` | The name of the string. Do not change it. |
| `english` | The English the translation follows. |
| `translation` | The current translation. **Correct it here.** |
| `context` | Where the text appears (settings page, parent view, update messages, robot screen, language pack, document title). |
| `max_chars` and `limit` | How long it may be. `hard` is a rule (the robot refuses a longer word); `soft` is a layout estimate (about the English length plus a margin): a longer line may be cut or wrapped on a small screen, so shorter is better. |
| `screenshot` | A picture of the screen the text belongs to (a path in this repository). |
| `status` | `machine draft` (written by a model, not read by a person), `missing` (no translation yet), or `reviewed`. Put `ok` here when you read a row and it is right as it is. |
| `note` | Say anything we should know: a word you are unsure of, a choice between two. |

Rules for a good line: the same meaning as the English and the same tone (plain, friendly, no jargon); keep every `{placeholder}` exactly as it is, in any place in the sentence; no markup, no square brackets; no em dash. Text drawn on the robot (`unit.` and `pack.` rows) can use the letters of Western European languages with accents, but not curly quotes or the oe ligature; the language pack words are plain letters with no accents at all and a short length (a weekday or month at most 7 letters, the alarm and timer words at most 11).

When you send the file back, we check it: `python3 scripts/translation-pack.py check FILE.csv` lists every problem with the row it is in. A row you changed, or marked `ok`, becomes `reviewed`.

Status of every language: see `STATUS.md`. Rows for the robot screen, the language packs and the document titles are passed to the people who own those parts (`pending/<language>.csv`); the settings page and message rows go live as soon as they are imported.
"""


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("export", "check", "import", "status"):
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd == "export":
        return cmd_export()
    if cmd == "status":
        print(render_status(refresh_status(load_status())))
        return 0
    if len(argv) < 2:
        print("translation-pack: name the CSV file.")
        return 2
    path = Path(argv[1])
    if cmd == "check":
        return cmd_check(path)
    reviewer = argv[argv.index("--reviewer") + 1] if "--reviewer" in argv else ""
    if not reviewer:
        print("translation-pack: import needs --reviewer NAME (who read the file).")
        return 2
    date = argv[argv.index("--date") + 1] if "--date" in argv else ""
    return cmd_import(path, reviewer, date)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
