"""Own-LLM brain placeholder, independent from the Home adapter."""

from __future__ import annotations

from collections.abc import Iterator

from maipai_body.brain.interface import BrainFeature, TurnRequest
from maipai_body.speech.turn_client import TurnEvent

NOT_INSTALLED = "The own-LLM brain is not installed yet. Configure it after its release."


class NotYetBuilt:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    def capabilities(self) -> frozenset[BrainFeature]:
        return frozenset({BrainFeature.LLM})

    def stream_turn(self, request: TurnRequest) -> Iterator[TurnEvent]:
        del request
        yield TurnEvent(reply_text=NOT_INSTALLED)

    def cancel_turn(self, turn_id: str) -> bool:
        del turn_id
        return False
