"""Caption text for the unit's subtitle strip (firmware patches N01 and N04).

The unit shows what the robot says from the ``text`` field of a ``tts sentence_start`` message. This module
turns a spoken sentence into the text to send: tags removed, whitespace collapsed, and a long sentence cut
at clause boundaries into pieces of at most ``MAX_CAPTION_CHARS`` characters. The hub's text-to-speech
speaks a whole sentence at once, so pieces are timed by their share of the sentence's characters.
"""

from __future__ import annotations

import re

MAX_CAPTION_CHARS = 200

_TAGS = re.compile(r"\[[^\[\]]{0,40}\]|<[^<>]{0,40}>|\{[^{}]{0,40}\}")
_CLAUSE_MARKS = (
    re.compile(r"[.!?…]+[\"')\]]*\s+"),
    re.compile(r"[;:]\s+"),
    re.compile(r",\s+"),
    re.compile(r"\s+"),
)


def clean(text: str) -> str:
    """The sentence as it is spoken: no tags, single spaces."""
    spaced = re.sub(r"\s+", " ", _TAGS.sub(" ", text or "")).strip()
    return re.sub(r"\s+([.!?,;:…])", r"\1", spaced)


def pieces(text: str, limit: int = MAX_CAPTION_CHARS) -> list[str]:
    """Cut ``text`` into captions of at most ``limit`` characters, at the latest clause boundary that fits."""
    rest = clean(text)
    out: list[str] = []
    while len(rest) > limit:
        cut = 0
        for mark in _CLAUSE_MARKS:
            for match in mark.finditer(rest[: limit + 1]):
                if match.end() <= limit + 1:
                    cut = max(cut, match.end())
            if cut >= limit // 3:
                break
        if cut <= 0:
            cut = limit  # one unbroken run: hard cut
        head, rest = rest[:cut].strip(), rest[cut:].strip()
        if head:
            out.append(head)
    if rest:
        out.append(rest)
    return out
