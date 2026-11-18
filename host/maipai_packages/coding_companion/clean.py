"""Everything the agent sends is cleaned before it is shown, and refused when it looks like a secret or a path."""

from __future__ import annotations

import re
import unicodedata

MAX_LINE = 60
MAX_PROJECT = 24

_UNSAFE = re.compile("[\\u0000-\\u001f\\u007f-\\u009f\\u200b-\\u200f\\u202a-\\u202e\\u2060-\\u2069\\ufeff]")
_SECRETS = (
    re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    re.compile(r"\b(?:password|passcode|passphrase|api[ _-]?key|secret|token|bearer|authorization)\b", re.I),
    re.compile(r"\b(?:sk|ghp|gho|tskey|xox[abprs])[-_][A-Za-z0-9_-]{8,}"),
    re.compile(r"\b[A-Za-z0-9+/_-]{32,}={0,2}"),
)
_PATH_OR_URL = re.compile(r"(?:https?://|ftp://|~/|\\\\|\b[A-Za-z]:\\|(?<![\w.])/[\w.-]+/)")


_HOMOGLYPHS = str.maketrans({
    "\u0430": "a", "\u0435": "e", "\u043e": "o", "\u0440": "p", "\u0441": "c", "\u0445": "x", "\u0443": "y", "\u0456": "i",
    "\u0442": "t", "\u043d": "h", "\u043a": "k", "\u043c": "m", "\u0432": "b", "\u0455": "s", "\u0458": "j",
    "\u03b1": "a", "\u03bf": "o", "\u03c1": "p", "\u03c4": "t", "\u03bd": "v", "\u03b9": "i", "\u03ba": "k",
})  # Cyrillic and Greek letters that look like Latin ones


def _fold(text: str) -> str:
    """A plain-ASCII reading of the text for the checks: compatibility forms (fullwidth), accents and lookalike letters folded."""
    decomposed = unicodedata.normalize("NFKD", text).translate(_HOMOGLYPHS)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def clean_text(text: object, limit: int = MAX_LINE) -> str | None:
    """Plain printable text up to ``limit`` characters, or None when it must not be shown.

    Hidden and control characters are removed first, then square brackets (they would be read as reply tags).
    The secret, path and address checks run on the text as it will be shown, and on a folded reading (accents,
    fullwidth forms and lookalike letters turned into plain ones), so a trick letter cannot hide a keyword.
    Anything outside plain ASCII is then dropped (the robot's font has no other letters)."""
    if not isinstance(text, str):
        return None
    flat = " ".join(_UNSAFE.sub("", text).replace("[", " ").replace("]", " ").split())
    folded = " ".join(_UNSAFE.sub("", _fold(flat)).split())
    shown = " ".join("".join(ch for ch in flat if " " <= ch <= "~").split())
    for candidate in (shown, folded, flat):
        if any(p.search(candidate) for p in _SECRETS) or _PATH_OR_URL.search(candidate):
            return None
    return shown[:limit].rstrip() or None


def clean_project(name: object) -> str:
    cleaned = clean_text(name, MAX_PROJECT)
    return cleaned or ""
