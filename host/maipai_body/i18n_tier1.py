"""Tier 1 language packs (owner decision 18): Dutch, Polish, Turkish, Swedish, Danish, Norwegian (Bokmal), Czech.

Every string is a machine draft that no native speaker has read. The words live in plain JSON files in
``i18n_tier1/<code>_<n>.json`` (``{"lang", "strings": {key: text}}``). A key is a catalog key of the settings page and messages,
``unit.screen.NNN`` (a word on the robot's own screen), ``pack.weekdays|months|alarm|timer`` (screen words, plain ASCII) or
``doc.title.<page>`` (the title of a user page). An optional ``"drawn"`` map holds, for a robot screen key, the Latin-1 spelling the
current screen font can draw when the proper spelling needs letters it lacks (see docs/plan/languages-tiers.md, Tier 1 glyphs).
``register`` is called once by i18n.py; nothing here imports i18n, so a language that is not used costs one dictionary of strings.
Placement: host. Upstream: none."""

from __future__ import annotations

import json
from pathlib import Path

DRAFT_LABEL = "machine draft, tier 1"
NAMES: dict[str, str] = {"nl": "Dutch", "pl": "Polish", "tr": "Turkish", "sv": "Swedish", "da": "Danish", "nb": "Norwegian (Bokmal)", "cs": "Czech"}
NATIVE: dict[str, str] = {"nl": "Nederlands", "pl": "Polski", "tr": "Türkçe", "sv": "Svenska", "da": "Dansk", "nb": "Norsk bokmål", "cs": "Čeština"}
CODES = tuple(NAMES)
DIR = Path(__file__).parent / "i18n_tier1"
NON_CATALOG_PREFIXES = ("unit.screen.", "pack.", "doc.title.")


def files(code: str) -> list[Path]:
    return sorted(DIR.glob(f"{code}_*.json"))


def load(code: str) -> dict[str, str]:
    """Every drafted string of one language (catalog, robot screen, pack and title keys together)."""
    out: dict[str, str] = {}
    for path in files(code):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("lang") != code:
            raise ValueError(f"{path.name} says language {data.get('lang')!r}: name the file {data.get('lang')}_<n>.json, or fix the lang field.")
        out.update(data["strings"])
    return out


def drawn(code: str) -> dict[str, str]:
    """Robot screen rows whose proper spelling needs letters the screen font lacks: the Latin-1 spelling to draw today."""
    out: dict[str, str] = {}
    for path in files(code):
        out.update(json.loads(path.read_text(encoding="utf-8")).get("drawn", {}))
    return out


def catalog_strings(code: str) -> dict[str, str]:
    return {k: v for k, v in load(code).items() if not k.startswith(NON_CATALOG_PREFIXES)}


def register(catalog: dict[str, dict[str, str]]) -> None:
    """Add one catalog per tier 1 language (only keys of the English catalog; the page falls back to English for a missing key)."""
    english = catalog["en"]
    for code in CODES:
        words = catalog.setdefault(code, {})
        for key, text in catalog_strings(code).items():
            if key in english:
                words[key] = text
