# ruff: noqa: E501
"""Best scores per person, kept on the host.

The unit keeps the best five scores of each game for itself and cannot tell who played. The host hears the unit's ``game_ended`` event (game, how it ended,
score) and files a finished game under the person who was playing, when something names that person (a recognized speaker from MaiPai Home, or a person
unlocked with the notes passphrase). With no name it files the score under "Someone", so a household without recognition still sees one honest list.
A game stopped early saves no score, as on the unit. Nothing leaves the host. One JSON file; a person's scores can be deleted from the dashboard."""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

SOMEONE = "Someone"
KEEP = 5


class ScoreBook:
    def __init__(self, path: Path, *, clock: Callable[[], float] = time.time, player: Callable[[str], str | None] | None = None) -> None:
        self._path, self._clock = Path(path), clock
        self.player = player  # unit id -> the person playing, or None when nobody is named
        self._lock = threading.Lock()

    def _load(self) -> dict[str, Any]:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(tmp, self._path)

    def on_event(self, unit: str, kind: str, extra: dict[str, Any] | None, lower_is_better: Callable[[str], bool] = lambda _g: False) -> bool:
        """File a finished game. True when a score was kept."""
        extra = extra or {}
        game, score = extra.get("game"), extra.get("score")
        if kind != "game_ended" or extra.get("how") != "finished" or not isinstance(game, str) or isinstance(score, bool) or not isinstance(score, int):
            return False
        try:
            who = (self.player(unit) if self.player else None) or SOMEONE
        except Exception:
            who = SOMEONE
        return self.record(unit, who, game, score, lower_is_better(game))

    def record(self, unit: str, person: str, game: str, score: int, lower_is_better: bool = False) -> bool:
        person = person.strip()[:40] or SOMEONE
        with self._lock:
            data = self._load()
            rows = data.setdefault(unit, {}).setdefault(person, {}).setdefault(game, [])
            rows.append({"score": score, "at": int(self._clock())})
            rows.sort(key=lambda r: (r["score"] if lower_is_better else -r["score"], r["at"]))
            del rows[KEEP:]
            self._save(data)
        return True

    def view(self, unit: str) -> list[dict[str, Any]]:
        """[{person, games: [{id, scores: [best first]}]}] for one unit, people in name order with "Someone" last."""
        data = self._load().get(unit, {})
        out = []
        for person in sorted(data, key=lambda p: (p == SOMEONE, p.lower())):
            out.append({"person": person, "games": [{"id": g, "scores": [r["score"] for r in rows]} for g, rows in sorted(data[person].items())]})
        return out

    def forget(self, unit: str, person: str) -> bool:
        with self._lock:
            data = self._load()
            if person not in data.get(unit, {}):
                return False
            del data[unit][person]
            self._save(data)
        return True
