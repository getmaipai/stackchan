"""Deterministic brain for tests and the virtual unit."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from maipai_body.brain.interface import BrainFeature, TurnRequest, VisionRequest
from maipai_body.speech.turn_client import TurnEvent


class FakeBrain:
    def __init__(self, *, features: set[BrainFeature] | None = None, reply: str = "Hello.") -> None:
        self._features = frozenset(features if features is not None else BrainFeature)
        self.reply = reply
        self.turns: list[TurnRequest] = []

    def capabilities(self) -> frozenset[BrainFeature]:
        return self._features

    def stream_turn(self, request: TurnRequest) -> Iterator[TurnEvent]:
        self.turns.append(request)
        yield TurnEvent(reply_text=self.reply)

    def cancel_turn(self, turn_id: str) -> bool:
        return bool(turn_id)

    def transcribe_stream(self, *args: Any, **kwargs: Any) -> Any:
        return iter(("final", "fake transcript"))

    def speak(self, *args: Any, **kwargs: Any) -> Any:
        return None

    def describe(self, request: VisionRequest) -> dict[str, str]:
        return {"description": "A test scene."}

    def people(self) -> list[Any]:
        return []

    def settings(self) -> dict[str, Any]:
        return {}

    def reminders(self, operation: str, payload: Any = None) -> list[Any]:
        return []
