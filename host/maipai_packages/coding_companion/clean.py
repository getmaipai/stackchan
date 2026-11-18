"""Everything the agent sends is cleaned before it is shown, and refused when it looks like a secret or a path."""

from __future__ import annotations

import re

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


def clean_text(text: object, limit: int = MAX_LINE) -> str | None:
    """Plain printable text up to ``limit`` characters, or None when it must not be shown.

    Square brackets are removed (they would be read as reply tags), hidden and control characters are removed,
    anything outside plain ASCII is dropped (the robot's font has no other letters), and text that holds a
    secret-looking value, a file path or an address is refused whole."""
    if not isinstance(text, str):
        return None
    flat = " ".join(_UNSAFE.sub("", text).replace("[", " ").replace("]", " ").split())
    if any(p.search(flat) for p in _SECRETS) or _PATH_OR_URL.search(flat):
        return None
    ascii_only = "".join(ch for ch in flat if " " <= ch <= "~")
    ascii_only = " ".join(ascii_only.split())
    return ascii_only[:limit].rstrip() or None


def clean_project(name: object) -> str:
    cleaned = clean_text(name, MAX_PROJECT)
    return cleaned or ""
