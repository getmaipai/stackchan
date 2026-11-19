# ruff: noqa: E501
"""A part that needs you, shown on the robot's own screen (firmware patch SF97: `self.banner.set {"text", "kind": "degraded"}`).

The status page says in plain words when a part failed or keeps restarting. This puts one short line (24 characters at most) in the unit's banner row too, so a person
standing at the robot sees it. The unit clears it by itself ten minutes after the last call, so the host repeats it every few minutes while the problem lasts and sends an empty
line once when everything runs again. A unit without the tool (an older image) is never sent anything. The probe is the tool list the unit announced."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

MAX_TEXT = 24
REPEAT_S = 240.0  # the unit clears it after 600 s, so repeat well inside that
TOOL = "self.banner.set"


def line_for(doc: dict[str, Any]) -> str:
    """The banner text for a health document: empty when everything runs. Plain words, 24 characters at most."""
    if doc.get("state") not in ("failed", "degraded"):
        return ""
    bad = [p for p in doc.get("parts", []) if p.get("state") in ("failed", "restarting")]
    name = (bad[0].get("plain") or bad[0].get("part") or "a part") if bad else "a part"
    text = ("Needs you: " if doc.get("state") == "failed" else "Restarting: ") + str(name)
    return text if len(text) <= MAX_TEXT else text[: MAX_TEXT - 1].rstrip() + "…"


class DegradedBanner:
    def __init__(
        self,
        *,
        health: Callable[[], dict[str, Any]],
        units: Callable[[], list[str]],
        has_tool: Callable[[str], bool],
        send: Callable[[str, dict[str, Any]], object],
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._health, self._units, self._has_tool, self._send, self._clock = health, units, has_tool, send, clock
        self._shown: dict[str, tuple[str, float]] = {}  # unit -> (text last sent, when)

    def tick(self) -> None:
        """One pass: send a changed line at once, repeat a standing one, clear once when it is over. Never raises."""
        try:
            text = line_for(self._health())
        except Exception:
            return
        now = self._clock()
        live = set(self._units())
        for unit in list(self._shown):
            if unit not in live:
                del self._shown[unit]  # a unit that left starts fresh when it comes back
        for unit in live:
            last, at = self._shown.get(unit, ("", float("-inf")))
            if text == last and (not text or now - at < REPEAT_S):
                continue  # nothing to say, or said recently
            if not self._has_tool(unit):
                continue
            try:
                self._send(unit, {"text": text, "kind": "degraded"})
            except Exception:
                continue  # the unit did not take it: asked again on the next pass
            self._shown[unit] = (text, now)
