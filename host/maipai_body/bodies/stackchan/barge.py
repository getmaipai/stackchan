"""Sentences that say the wake phrase must not be cut by the unit's talk-over (patch SF29).

While the unit speaks, a second wake hit within a second interrupts it. A sentence that itself says the wake phrase (the robot reading
back "say hey maipai") would interrupt itself, so the host marks that sentence `no_barge` with its length, and the unit ignores hits
while it plays.
"""

from __future__ import annotations

import re

DEFAULT_PHRASES = ("hey maipai", "hey mai pai", "hey my pie")
MIN_MS, MAX_MS, MS_PER_WORD = 2000, 20000, 450


def _plain(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def wake_phrases() -> list[str]:
    """The default phrase and every person's own wake phrase, in plain lower case."""
    phrases = list(DEFAULT_PHRASES)
    try:
        from maipai_body.unit_extras import PeopleStore

        phrases += [p.wake_phrase for p in PeopleStore().all() if p.wake_phrase]
    except Exception:
        pass
    return [p for p in (_plain(x) for x in phrases) if p]


def says_wake_phrase(text: str, phrases: list[str]) -> bool:
    plain = f" {_plain(text)} "
    return any(f" {p} " in plain for p in phrases)


def no_barge_ms(text: str) -> int:
    """How long the sentence plays, roughly: the unit ignores hits for this long."""
    words = len(_plain(text).split())
    return max(MIN_MS, min(MAX_MS, words * MS_PER_WORD + 1000))
