"""Typed interface between the body host and its answering brain."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from maipai_body.speech.turn_client import TurnEvent


class BrainFeature(StrEnum):
    STT = "stt"
    LLM = "llm"
    TTS = "tts"
    VISION_DESCRIBE = "vision.describe"
    PEOPLE = "people"
    TIMERS = "timers"
    REMINDERS = "reminders"
    SETTINGS = "settings"


@dataclass(frozen=True)
class TurnRequest:
    text: str
    speaker_evidence: dict[str, Any] | None = None
    present: list[dict[str, Any]] | None = None
    conversation_id: str | None = None
    ask_answer: dict[str, Any] | None = None
    # Extra system instructions for this turn only (a talk game's rules); the unit's own model
    # reads them next to its persona.
    instructions: str | None = None


@dataclass(frozen=True)
class VisionRequest:
    jpeg: bytes
    purpose: str
    people: int | None = None
    light: str | None = None
    timeout: float | None = None


@runtime_checkable
class Brain(Protocol):
    def capabilities(self) -> frozenset[BrainFeature]: ...

    def stream_turn(self, request: TurnRequest) -> Iterator[TurnEvent]: ...

    def cancel_turn(self, turn_id: str) -> bool: ...

    def transcribe_stream(self, *args: Any, **kwargs: Any) -> Any: ...

    def speak(self, *args: Any, **kwargs: Any) -> Any: ...

    def describe(self, request: VisionRequest) -> Any: ...

    def people(self) -> Any: ...

    def settings(self) -> Mapping[str, Any]: ...

    def reminders(self, operation: str, payload: Mapping[str, Any] | None = None) -> Any: ...
