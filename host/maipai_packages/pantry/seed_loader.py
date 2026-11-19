# ruff: noqa: E501
"""The built-in set (docs/dev/pantry-seed.md): jokes, riddles and trivia shipped in ``seed/``, put into the library on first run with no model.

Each seed file is loaded once. A marker (``seed-loaded.json`` in the library folder) records the files loaded and their hashes, so a record the owner deleted does not come
back, and a later release that changes a file adds only the records the library does not already hold. A record marked "never again" is never added. Only the
languages the owner chose are loaded."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from maipai_packages.pantry.library import Library
from maipai_packages.pantry.record import Record, RecordError, check

SEED_DIR = Path(__file__).parent / "seed"
MARKER = "seed-loaded.json"


def seed_files(languages: tuple[str, ...] | None = None) -> list[Path]:
    return [p for p in sorted(SEED_DIR.glob("*.json")) if languages is None or p.stem.partition("-")[0] in languages]


def seed_records(path: Path) -> list[Record]:
    out = []
    for row in json.loads(path.read_text(encoding="utf-8")):
        try:
            out.append(check(Record.from_json(row)))
        except (ValueError, KeyError, RecordError):
            continue  # a damaged row is skipped, never fatal
    return out


def seed_ids(languages: tuple[str, ...] | None = None) -> set[str]:
    return {r.id_hex for p in seed_files(languages) for r in seed_records(p)}


def load_seed(library: Library, languages: tuple[str, ...], adult_allowed: bool = False) -> int:
    """Add the seed files that were not loaded yet (or changed). Returns how many records were added. Never raises."""
    marker_path = library.folder / MARKER
    try:
        done = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        done = {}
    added = 0
    try:
        for path in seed_files(languages):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if done.get(path.name) == digest:
                continue
            have = {r.id_hex for r in library.records()} | library.refused()
            fresh = [r for r in seed_records(path) if r.id_hex not in have and (r.rating == "kid" or adult_allowed)]
            if fresh:
                added += library.add(fresh)
            done[path.name] = digest
        marker_path.write_text(json.dumps(done, indent=1, sort_keys=True), encoding="utf-8")
    except Exception:
        return added
    return added


def built_in_state(library: Library, languages: tuple[str, ...]) -> dict:
    """What the dashboard card says about the built-in set: how many of its records the library still holds."""
    ids = seed_ids(languages)
    held = len(ids & {r.id_hex for r in library.records()})
    text = f"Built-in set: {held} jokes, riddles and trivia questions ready, no model needed." if held else ""
    return {"state": "Built-in set" if held else "", "records": held, "text": text, "ids": sorted(ids)}
