"""One plain text file per person; one note per line: ``- 2026-11-18 [ab12cd] the note``."""

from __future__ import annotations

import os
import re
import secrets
import threading
from collections.abc import Callable
from datetime import date
from pathlib import Path

from maipai_packages.memory_notes.admission import (
    HOUSEHOLD,
    MAX_NOTES_PER_PERSON,
    AdmissionError,
    check_note,
)

_LINE = re.compile(r"^- (\d{4}-\d{2}-\d{2}) \[([0-9a-f]{6})\] (.+)$")
_NAME = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")


class NotesStore:
    def __init__(self, folder: Path, today: Callable[[], date] = date.today) -> None:
        self.folder = Path(folder)
        self._today = today
        self._lock = threading.Lock()

    def _path(self, person: str) -> Path:
        if not _NAME.match(person):
            raise AdmissionError("A person's name for notes uses lowercase letters, digits, dash or underscore.")
        return self.folder / f"{person}.md"

    def read(self, person: str) -> list[tuple[str, str, str]]:
        """(day, id, text) rows, oldest first. Lines that are not notes are left alone and ignored."""
        try:
            lines = self._path(person).read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        return [m.groups() for m in map(_LINE.match, lines) if m]

    def add(self, person: str, text: str) -> str:
        note = check_note(text)
        with self._lock:
            rows = self.read(person)
            if len(rows) >= MAX_NOTES_PER_PERSON:
                raise AdmissionError(f"The notes for {person} are full ({MAX_NOTES_PER_PERSON}). Forget some first.")
            if any(r[2].lower() == note.lower() for r in rows):
                return "I already have that."
            self._write_line(person, f"- {self._today().isoformat()} [{secrets.token_hex(3)}] {note}")
        return "Okay, I will remember that."

    def _write_line(self, person: str, line: str) -> None:
        self.folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = self._path(person)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def forget(self, person: str, query: str) -> int:
        """Remove every note that holds all the words of ``query``; returns how many."""
        words = [w for w in re.findall(r"[\w']+", query.lower()) if w not in {"the", "a", "an", "that", "my", "about"}]
        if not words:
            return 0
        with self._lock:
            path = self._path(person)
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError:
                return 0
            kept, removed = [], 0
            for line in lines:
                m = _LINE.match(line)
                if m and all(w in m.group(3).lower() for w in words):
                    removed += 1
                else:
                    kept.append(line)
            if removed:
                path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
                path.chmod(0o600)
            return removed

    def forget_all(self, person: str) -> int:
        with self._lock:
            count = len(self.read(person))
            try:
                self._path(person).unlink()
            except OSError:
                pass
            return count


class Notes:
    """The package's one object: turns a spoken request into a store action and builds the prompt text."""

    _REMEMBER = re.compile(r"^\s*(?:please\s+)?remember\s+(?:that\s+)?(.+?)\s*[.!]?\s*$", re.I)
    _FORGET_ALL = re.compile(r"^\s*(?:please\s+)?forget\s+everything(?:\s+(?:about me|i (?:told|said).*))?\s*[.!]?\s*$", re.I)
    _FORGET = re.compile(r"^\s*(?:please\s+)?forget\s+(?:that\s+)?(.+?)\s*[.!]?\s*$", re.I)
    _READ = re.compile(r"^\s*(?:what do you remember|what (?:have|did) i (?:told|tell) you|read (?:me )?my notes)(?:\s+about me)?\s*[?.!]?\s*$", re.I)
    _EVERYONE = re.compile(r"^(?:for everyone|for the (?:whole )?(?:family|household))[ ,:]+(?:that )?(.+)$", re.I)

    def __init__(self, store: NotesStore, people: list[str], default_person: str = "") -> None:
        self.store = store
        self.people = [p.lower() for p in people]
        self.default_person = default_person.lower() if default_person.lower() in self.people else ""

    def person_for(self, speaker: str | None) -> str:
        if not speaker:
            return self.default_person  # nobody was identified: the person named in robot.toml
        who = speaker.lower()
        return who if who in self.people else ""  # a speaker who is not a listed adult has no notes

    def handle(self, text: str, speaker: str | None = None) -> str | None:
        """The spoken reply when ``text`` is a notes request, else None (the model answers as usual)."""
        forget_all = self._FORGET_ALL.match(text)
        remember = None if forget_all else self._REMEMBER.match(text)
        read = None if (forget_all or remember) else self._READ.match(text)
        forget = None if (forget_all or remember or read) else self._FORGET.match(text)
        if not (forget_all or remember or read or forget):
            return None
        person = self.person_for(speaker)
        if not person:
            return "I do not know who is asking. Ask the owner to set who is speaking in the settings."
        try:
            if forget_all:
                count = self.store.forget_all(person)
                return f"Done. I forgot {count} thing{'s' if count != 1 else ''}." if count else "I had nothing to forget."
            if remember:
                body = remember.group(1)
                shared = self._EVERYONE.match(body)
                if shared:
                    self.store.add(HOUSEHOLD, shared.group(1))
                    return "Okay, I will remember that for everyone."
                return self.store.add(person, body)
            if read:
                rows = self.store.read(person)[-5:]
                if not rows:
                    return "I do not have anything for you yet."
                return "Here is what I remember: " + "; ".join(r[2] for r in rows) + "."
            removed = self.store.forget(person, forget.group(1))
            return f"Done. I forgot {removed} thing{'s' if removed != 1 else ''}." if removed else "I did not find that."
        except AdmissionError as error:
            return str(error)

    def context(self, speaker: str | None = None) -> str:
        """Prompt text for the speaker's own turn: their notes and the household notes, nobody else's."""
        person = self.person_for(speaker)
        if not person:
            return ""
        rows = self.store.read(person)[-20:] + self.store.read(HOUSEHOLD)[-10:]
        if not rows:
            return ""
        return "Things the person talking to you asked you to remember:\n" + "\n".join(f"- {r[2]}" for r in rows)
