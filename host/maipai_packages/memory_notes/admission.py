"""What may be stored, and who may read it (shaped like the shared memory admission concept).

Stored: short plain facts and preferences an adult asked the robot to remember.
Refused: credentials and payment or identity numbers, text over the length limit, empty text.
Read: a person's notes go only into that person's own turns, for a speaker a recognizer named, one who said the notes passphrase
they set, or the owner's default_person; a spoken "this is Sam" alone opens nothing private (store.py). Notes filed under "household"
go into every listed adult's turns. Nobody else's notes are ever read into a turn.
"""

from __future__ import annotations

import re
import unicodedata

MAX_NOTE_CHARS = 300
MAX_NOTES_PER_PERSON = 200
HOUSEHOLD = "household"

_REFUSED = (
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "a card or account number"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "a government id number"),
    (re.compile(r"\b(?:passwords?|passwds?|pwds?|pw|passcodes?|pass phrases?|passphrases?|pin codes?|pins?|api keys?|secret keys?|private keys?|tokens?)\b", re.I), "a password, code or key"),
    (re.compile(r"\b\d{3}[ .]\d{2}[ .]\d{4}\b"), "a government id number"),
    (re.compile(r"\b(?:ssn|social security(?: number)?|sin|national insurance(?: number)?)\b\D{0,12}\d{9}\b", re.I), "a government id number"),
    (re.compile(r"\bpassports?\b\D{0,20}[A-Z0-9]{6,12}\b", re.I), "a government id number"),
    (re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{12,}\b"), "a password, code or key"),
    (re.compile(r"\b(?:vault|safe|lock|alarm|door|gate|garage|locker|combination)\s*(?:code|combination|pin|number)?\b\D{0,12}\d{3,}", re.I), "a code or combination"),
    (re.compile(r"\b(?:driver'?s?|driving)\s+licen[cs]e\b\D{0,20}[A-Z0-9]{5,}", re.I), "a government id number"),
    (re.compile(r"\b(?:secret|private)\s+(?:word|phrase|code)\b", re.I), "a password, code or key"),
    (re.compile(r"\b(?:wi-?fi|wifi|router|network|account|login)\s+(?:key|pass(?:word)?|code)\b", re.I), "a password, code or key"),
    (re.compile(r"\b(?:key|code|secret)\b\D{0,12}(?=[A-Za-z0-9]*\d)[A-Za-z0-9]{8,}\b", re.I), "a password, code or key"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.?[A-Za-z0-9_-]*"), "a password, code or key"),
    (re.compile(r"\b(?:sk|ghp|gho|tskey|xox[abprs])[-_][A-Za-z0-9_-]{8,}"), "a password, code or key"),
)


_HOMOGLYPHS = str.maketrans({
    "\u0430": "a", "\u0435": "e", "\u043e": "o", "\u0440": "p", "\u0441": "c", "\u0445": "x", "\u0443": "y", "\u0456": "i",
    "\u0442": "t", "\u043d": "h", "\u043a": "k", "\u043c": "m", "\u0432": "b", "\u0455": "s", "\u0458": "j",
    "\u03b1": "a", "\u03bf": "o", "\u03c1": "p", "\u03c4": "t", "\u03bd": "v", "\u03b9": "i", "\u03ba": "k",
})  # Cyrillic and Greek letters that look like Latin ones


_LEET = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})  # digits and signs used as letters
_SPACED = re.compile(r"\b(?:[A-Za-z][ .\-_]){3,}[A-Za-z]\b")  # p a s s w o r d
_SQUASH_WORDS = re.compile(r"pass\s*word|pass\s*code|pass\s*phrase|pass\s*wd", re.I)


def _fold(text: str) -> str:
    """A plain-ASCII reading of the text for the checks: fullwidth forms, accents and lookalike letters turned into plain ones."""
    decomposed = unicodedata.normalize("NFKD", text).translate(_HOMOGLYPHS)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _readings(text: str) -> list[str]:
    """The text as written, folded, with digits read as letters, and with spaced-out letters joined (so a trick does not hide a keyword)."""
    folded = _fold(text)
    joined = _SPACED.sub(lambda m: re.sub(r"[ .\-_]", "", m.group(0)), folded)
    return [text, folded, folded.translate(_LEET), joined, _SQUASH_WORDS.sub("password", joined).translate(_LEET)]


def _hidden(ch: str) -> bool:
    """Control, format (direction marks, zero-width, soft hyphen), line and paragraph separators, private-use and unassigned characters."""
    return unicodedata.category(ch)[0] == "C" or unicodedata.category(ch) in ("Zl", "Zp")


def scrub_for_prompt(text: str) -> str:
    """A stored line made safe to hand to the model: no brackets (reply tags), no angle brackets (they could close
    the fence the notes sit in), no hidden characters."""
    swapped = text.replace("[", "(").replace("]", ")").replace("<", "(").replace(">", ")")
    return " ".join("".join(ch for ch in swapped if not _hidden(ch)).split())


class AdmissionError(ValueError):
    """The note was not stored; the message says why and what to do instead."""


def check_note(text: str) -> str:
    """The cleaned note, or AdmissionError with a plain reason."""
    note = " ".join(text.split()).strip(" .")
    if not note:
        raise AdmissionError("There was nothing to remember. Say what to remember after the word remember.")
    if len(note) > MAX_NOTE_CHARS:
        raise AdmissionError(f"That is longer than {MAX_NOTE_CHARS} characters. Say it in a shorter way.")
    if any(ch in note for ch in "[]<>"):
        raise AdmissionError("I do not keep text in brackets. Say it in plain words.")
    if any(_hidden(ch) for ch in note):
        raise AdmissionError("That has hidden or control characters. Say it again in plain words.")
    readings = _readings(note)
    for pattern, what in _REFUSED:
        if any(pattern.search(reading) for reading in readings):
            raise AdmissionError(f"I do not keep {what}. Keep it somewhere safer, like a password manager.")
    return note
