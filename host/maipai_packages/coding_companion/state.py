"""The agent's latest state, as the package keeps it. Only the newest state is kept (changes are coalesced)."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from maipai_packages.coding_companion.clean import clean_project, clean_text

STATES = ("working", "waiting", "finished")
KINDS = ("permission", "question", "finished", "")
# State -> the ring light color. No red: red is kept for the security alert and the charging light.
LIGHT = {"working": "blue", "waiting": "amber", "finished": "green"}
LIGHT_SECONDS = 20
STALE_WORKING_S = 30 * 60  # a "working" state nobody refreshed for this long is not shown as working
FIXED_LINE = {"working": "Working", "waiting": "Needs you", "finished": "Finished"}


@dataclass(frozen=True)
class View:
    state: str
    kind: str
    project: str
    line: str  # what the screen may show: a fixed word, or the cleaned request text when the owner turned that on


class AgentStatus:
    def __init__(self, *, show_request_text: bool = False, clock=time.monotonic) -> None:
        self.show_request_text, self._clock = show_request_text, clock
        self._lock = threading.Lock()
        self._view: View | None = None
        self._at = 0.0

    def update(self, message: dict) -> View | None:
        """Take one message. Only the fields below are read; anything else is ignored. Returns the new view, or None."""
        state = message.get("state")
        if state not in STATES:
            return None
        kind = message.get("kind") if message.get("kind") in KINDS else ""
        text = clean_text(message.get("text")) if self.show_request_text else None
        view = View(state, kind or ("finished" if state == "finished" else ""), clean_project(message.get("project")), text or FIXED_LINE[state])
        with self._lock:
            self._view, self._at = view, self._clock()
        return view

    def current(self) -> View | None:
        with self._lock:
            return self._view

    def spoken(self) -> str:
        """The answer to "what is my coding agent doing": a fixed phrase and the cleaned project name; never the agent's text."""
        view = self.current()
        if view is None:
            return "I have not heard from your coding agent."
        if view.state == "working" and self._clock() - self._at > STALE_WORKING_S:
            return "Your coding agent has not reported for a while."
        project = f" on {view.project}" if view.project else ""
        phrase = {"working": "Your coding agent is working", "waiting": "Your coding agent needs you", "finished": "Your coding agent is finished"}[view.state]
        return phrase + project + "."


_SHARED = AgentStatus()


def shared_status() -> AgentStatus:
    """One status for the process: the endpoint writes it and the spoken-request handler reads it."""
    return _SHARED
