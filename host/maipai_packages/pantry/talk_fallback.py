# ruff: noqa: E501
"""Talk games with no model (docs/design/model-games.md, state S1): riddles and trivia played from the pantry library.

When the model cannot be reached in the middle of a riddle or trivia game, the host plays the next turn from the library with fixed lines, so the game goes on.
The host keeps the score. Twenty questions, word chain and the other model games have no library half and are left to the usual offline line. Only ``kid``
records are used unless the owner turned adult humor on. No audio and no model: the caller speaks the returned line through the host's own text to speech."""

from __future__ import annotations

import random
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from maipai_packages.pantry.library import Library
from maipai_packages.pantry.record import Record, normalize

GAME_KIND = {"riddles": "riddle", "trivia": "trivia"}

LINES = {
    "en": {
        "none": "I do not have any more of those right now, so we will stop here.",
        "right": "Right. Want another one?",
        "again": "Not quite. Try once more.",
        "reveal": "The answer is {answer}.",
        "choices": "{question} Is it {a}, {b}, or {c}?",
        "wrong": "Not quite. It is {answer}.",
    },
    "es": {
        "none": "Ya no tengo más de esas por ahora, así que paramos aquí.",
        "right": "Correcto. ¿Quieres otra?",
        "again": "Casi. Inténtalo otra vez.",
        "reveal": "La respuesta es {answer}.",
        "choices": "{question} ¿Es {a}, {b} o {c}?",
        "wrong": "Casi. Es {answer}.",
    },
}


def _lines(lang: str) -> dict[str, str]:
    return LINES.get(lang, LINES["en"])


def matches(heard: str, answer: str) -> bool:
    """The heard words say the answer: equal after normalizing, or the whole answer appears among the heard words."""
    h, a = normalize(heard), normalize(answer)
    if not h or not a:
        return False
    return h == a or f" {a} " in f" {h} "


@dataclass
class _Turn:
    record: Record
    misses: int = 0
    choices: list[str] = field(default_factory=list)
    game_started: float = 0.0  # the talk game this turn belongs to; a new game starts fresh


class PantryTalk:
    def __init__(self, library: Library, *, adult_humor: Callable[[], bool] = lambda: False, clock: Callable[[], float] = time.time, rng: random.Random | None = None) -> None:
        self._library, self._adult, self._clock = library, adult_humor, clock
        self._rng = rng or random.Random()
        self._turns: dict[str, _Turn] = {}
        self._lock = threading.Lock()

    def supports(self, game_id: str) -> bool:
        return game_id in GAME_KIND

    def reset(self, unit: str) -> None:
        with self._lock:
            self._turns.pop(unit, None)

    def _pick(self, unit: str, game_id: str, lang: str) -> Record | None:
        kind = GAME_KIND[game_id]
        pool = [r for r in self._library.unheard(unit, kind, lang) if r.rating == "kid" or self._adult()]
        if not pool:
            return None
        record = self._rng.choice(pool)
        self._library.note_heard(unit, [{"id": record.id_hex[:8], "counter": int(self._clock())}])
        return record

    def line(self, unit: str, game_id: str, lang: str, heard: str, game_started: float = 0.0) -> tuple[str, bool] | None:
        """The next fixed line for this game turn and whether the person scored a point; None when this game has no library half.

        With no riddle or question in play, the turn asks the next one whatever was heard (the game's first "go")."""
        if game_id not in GAME_KIND:
            return None
        words = _lines(lang)
        with self._lock:
            turn = self._turns.get(unit)
            if turn is not None and turn.game_started != game_started:
                turn = self._turns.pop(unit)
                turn = None
            if turn is None:
                record = self._pick(unit, game_id, lang)
                if record is None:
                    return words["none"], False
                if game_id == "trivia":
                    wrong = record.extra.split("|")
                    choices = [record.answer, *wrong]
                    self._rng.shuffle(choices)
                    self._turns[unit] = _Turn(record, choices=choices, game_started=game_started)
                    return words["choices"].format(question=record.text, a=choices[0], b=choices[1], c=choices[2]), False
                self._turns[unit] = _Turn(record, game_started=game_started)
                return record.text, False
            if matches(heard, turn.record.answer):
                del self._turns[unit]
                return words["right"], True
            turn.misses += 1
            limit = 1 if game_id == "trivia" else 2
            if turn.misses >= limit:
                del self._turns[unit]
                key = "wrong" if game_id == "trivia" else "reveal"
                return words[key].format(answer=turn.record.answer), False
            return words["again"], False
