"""Where a StackChan turn gets its speech-to-text, answer and text-to-speech (docs/plan/seam-refactor.md, step P3).

The turn bridge asks one backend for the three clients of a turn instead of holding three factories and a special case for running
without Home. `HubBackend` builds the hub's clients (what Home mode used). `LocalBackend` swaps the speech-to-text and text-to-speech
for the local ones (a server address, or the built-in engines) and leaves the answer to the unit's own model.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class HubBackend:
    """The hub's clients: `stt_factory(base, cookie)`, `turn_factory(base, cookie)`, `tts_factory(base, cookie, playback)`."""

    local = False

    def __init__(self, stt_factory: Callable[..., Any], turn_factory: Callable[..., Any], tts_factory: Callable[..., Any]) -> None:
        self.stt_factory, self.turn_factory, self.tts_factory = stt_factory, turn_factory, tts_factory

    def stt(self, base: Any, cookie: Any) -> Any:
        return self.stt_factory(base, cookie)

    def turn(self, base: Any, cookie: Any) -> Any:
        return self.turn_factory(base, cookie)

    def tts(self, base: Any, cookie: Any, playback: Any) -> Any:
        return self.tts_factory(base, cookie, playback)


class LocalBackend(HubBackend):
    """No Home: local speech clients; the answer comes from the unit's own model (the turn factory stays only as a fallback)."""

    local = True
