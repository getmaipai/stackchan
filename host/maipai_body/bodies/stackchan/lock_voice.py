# ruff: noqa: E501
"""The spoken word "lock" (Spanish "bloquear") locks the robot that heard it, with no model call.

Only a whole utterance that is one of the fixed phrases counts, so "lock the door" still goes to the model. Nothing else is accepted:
a spoken code, spoken digits, "unlock" and anything with a digit in it are never matched, never forwarded and never logged (the code is
meant for the keypad on the robot, where a person can see nobody is listening; speech can be overheard). The robot's own lock refuses a
lock request when it has no code, and this module says so in a fixed line. The utterance itself is never logged here.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("maipai_body.bodies.stackchan.lock_voice")

_FILLERS = re.compile(
    r"\b(please|ok|okay|hey|hi|um|uh|now|thanks|thank you|stack ?chan|por favor|ahora|gracias)\b"
)

_ENGLISH = frozenset(
    {
        "lock",
        "lock up",
        "lock it",
        "lock the robot",
        "lock the screen",
        "lock yourself",
        "lock the stackchan",
    }
)
_SPANISH = frozenset(
    {
        "bloquear",
        "bloquea",
        "bloquealo",
        "bloquéalo",
        "bloquéate",
        "bloquearte",
        "bloquear el robot",
        "bloquea el robot",
        "bloquear la pantalla",
        "bloquea la pantalla",
    }
)

LINES: dict[str, dict[str, str]] = {
    "no_code": {
        "en": "I have no code yet. Set one on the settings page, then ask me to lock.",
        "es": "Todavía no tengo un código. Crea uno en la página de ajustes y luego pídeme que me bloquee.",
    },
    "offline": {
        "en": "I could not lock just now. Try again.",
        "es": "No pude bloquearme ahora. Inténtalo de nuevo.",
    },
}


@dataclass(frozen=True)
class LockCommand:
    lang: str  # "en" or "es": the language of the words that were said


def normalize(text: str | None) -> str:
    spoken = re.sub(r"[^\w' ]+", " ", (text or "").lower().replace("-", " "))
    return re.sub(r"\s+", " ", _FILLERS.sub(" ", spoken)).strip()


def parse_lock_command(text: str | None) -> LockCommand | None:
    """The lock command when the whole utterance is a fixed phrase, else None. Any digit, spoken or typed, means None."""
    raw = text or ""
    if any(ch.isdigit() for ch in raw):
        return None
    spoken = normalize(raw)
    if spoken in _ENGLISH:
        return LockCommand("en")
    if spoken in _SPANISH:
        return LockCommand("es")
    return None


class LockVoice:
    """Locks the unit that heard the word. ``service`` returns the settings page's ``LockService`` (None until it exists)."""

    def __init__(self, service: Callable[[], Any]) -> None:
        self._service = service

    def parse(self, text: str | None) -> LockCommand | None:
        return parse_lock_command(text)

    def run(self, command: LockCommand, device_id: str) -> str:
        """Ask the unit to lock. Returns a line to speak, or "" when the unit locked (its lock screen is the answer)."""
        service = self._service()
        if service is None:
            return LINES["offline"][command.lang]
        reply = service.lock_now(device_id, command.lang)
        if reply.get("ok") is True:
            logger.info("voice: the unit was asked to lock")
            return ""
        key = "no_code" if reply.get("reason") == "no_code" else "offline"
        return LINES[key][command.lang]
