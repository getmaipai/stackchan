"""The spoken request: "what is my coding agent doing". Answered here from a fixed phrase, with no model call."""

from __future__ import annotations

import re

from maipai_packages.coding_companion.state import AgentStatus

_ASK = re.compile(r"^\s*(?:what(?:'s| is| are)|how(?:'s| is)|is)\s+(?:my |the )?(?:coding )?(?:agent|claude|codex)(?: code)?\s*(?:doing|up to|status|done|finished|working)?\s*[?.!]?\s*$|^\s*coding (?:agent )?status\s*[?.!]?\s*$", re.I)


class CodingStatusHandler:
    def __init__(self, status: AgentStatus) -> None:
        self.status = status

    def handle(self, text: str, speaker: str | None = None) -> str | None:
        return self.status.spoken() if _ASK.match(text) else None
