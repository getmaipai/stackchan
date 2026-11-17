"""Home brain adapter. Existing clients retain transport behavior and timing."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from maipai_body.brain.interface import BrainFeature, TurnRequest, VisionRequest
from maipai_body.speech.turn_client import TurnClient, TurnEvent


class HomeBrain:
    def __init__(
        self,
        *,
        turn_client: Any = None,
        stt_client: Any = None,
        tts_client: Any = None,
        vision_poster: Any = None,
        people_provider: Callable[[], Any] | None = None,
        settings_provider: Callable[[], Any] | None = None,
        reminder_handler: Callable[[str, dict], Any] | None = None,
    ) -> None:
        self.turn_client = turn_client
        self.stt_client = stt_client
        self.tts_client = tts_client
        self.vision_poster = vision_poster
        self.people_provider = people_provider
        self.settings_provider = settings_provider
        self.reminder_handler = reminder_handler

    def capabilities(self) -> frozenset[BrainFeature]:
        result = {BrainFeature.LLM}
        if self.stt_client is not None:
            result.add(BrainFeature.STT)
        if self.tts_client is not None:
            result.add(BrainFeature.TTS)
        if self.vision_poster is not None:
            result.add(BrainFeature.VISION_DESCRIBE)
        if self.people_provider is not None:
            result.add(BrainFeature.PEOPLE)
        if self.settings_provider is not None:
            result.add(BrainFeature.SETTINGS)
        if self.reminder_handler is not None:
            result.add(BrainFeature.REMINDERS)
            result.add(BrainFeature.TIMERS)
        return frozenset(result)

    def stream_turn(self, request: TurnRequest) -> Iterator[TurnEvent]:
        if self.turn_client is None:
            raise RuntimeError("Home turn client is unavailable; configure the Home brain")
        return self.turn_client.stream(
            request.text,
            speaker_evidence=request.speaker_evidence,
            present=request.present,
            conversation_id=request.conversation_id,
            ask_answer=request.ask_answer,
        )

    def cancel_turn(self, turn_id: str) -> bool:
        if self.turn_client is None:
            raise RuntimeError("Home turn client is unavailable; configure the Home brain")
        return self.turn_client.cancel(turn_id)

    def transcribe_stream(self, *args: Any, **kwargs: Any) -> Any:
        return self.stt_client.stream(*args, **kwargs)

    def speak(self, *args: Any, **kwargs: Any) -> Any:
        return self.tts_client.speak(*args, **kwargs)

    def describe(self, request: VisionRequest) -> Any:
        return self.vision_poster.post(
            request.jpeg, purpose=request.purpose, people=request.people,
            light=request.light, timeout=request.timeout
        )

    def people(self) -> Any:
        return self.people_provider()

    def settings(self) -> Any:
        return self.settings_provider()

    def reminders(self, operation: str, payload: dict | None = None) -> Any:
        return self.reminder_handler(operation, payload or {})


def home_turn_client(base_url: str, session_cookie: str) -> TurnClient:
    """Default Home transport constructor used by injected call sites."""
    return TurnClient(base_url, session_cookie)
