"""What may be stored, and who may read it (shaped like the shared memory admission concept).

Stored: short plain facts and preferences an adult asked the robot to remember.
Refused: credentials and payment or identity numbers, text over the length limit, empty text.
Read: a person's notes go only into that person's own turns. Notes filed under "household"
go into every listed adult's turns. Nobody else's notes are ever read into a turn.
"""

from __future__ import annotations

import re

MAX_NOTE_CHARS = 300
MAX_NOTES_PER_PERSON = 200
HOUSEHOLD = "household"

_REFUSED = (
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "a card or account number"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "a government id number"),
    (re.compile(r"\b(?:password|passcode|pass phrase|passphrase|pin code|\bpin\b|api key|secret key|private key|token)\b", re.I), "a password, code or key"),
    (re.compile(r"\b(?:sk|ghp|gho|tskey|xox[abprs])[-_][A-Za-z0-9_-]{8,}"), "a password, code or key"),
)


class AdmissionError(ValueError):
    """The note was not stored; the message says why and what to do instead."""


def check_note(text: str) -> str:
    """The cleaned note, or AdmissionError with a plain reason."""
    note = " ".join(text.split()).strip(" .")
    if not note:
        raise AdmissionError("There was nothing to remember. Say what to remember after the word remember.")
    if len(note) > MAX_NOTE_CHARS:
        raise AdmissionError(f"That is longer than {MAX_NOTE_CHARS} characters. Say it in a shorter way.")
    for pattern, what in _REFUSED:
        if pattern.search(note):
            raise AdmissionError(f"I do not keep {what}. Keep it somewhere safer, like a password manager.")
    return note
