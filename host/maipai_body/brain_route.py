# ruff: noqa: E501
"""The two brain routes (owner decision 34): hosted by M5Stack/Xiaozhi, or custom (your own key, a community server, your own host or MaiPai Home, a model on your computer).

The host keeps one word in robot.toml, ``brain_route = "hosted" | "custom"`` (no word means custom). It tells each connected unit that word with the tool
``self.brain.route.set {"route": ...}`` (proposed contract; a unit that does not announce the tool is never sent anything). The hosted route stays planned until a test
build proves the vendor's server accepts this firmware (``docs/plan/cloud-brain-firmware-test.md``): while ``HOSTED_PROVEN`` is false the page shows it as planned and
the host refuses to save it, so nobody is moved onto a route that cannot work."""

from __future__ import annotations

import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

HOSTED_PROVEN = False
ROUTES = ("hosted", "custom")
TOOL = "self.brain.route.set"

VOICE_LINE = {
    "hosted": "Your voice goes to M5Stack/Xiaozhi's servers, outside your home.",
    "custom": "Your voice stays where you point it: your own computer, your own host, or MaiPai Home.",
}
LEAVE_NOTE = (
    "The saved link to M5Stack/Xiaozhi is removed from this host and the robot. "
    "Anything their servers already kept about your robot stays on their side; only they can delete it, so ask them if you want it gone."
)


def read(config_path: Path) -> str:
    """The saved route, ``custom`` when none is saved or the file cannot be read."""
    try:
        raw = tomllib.loads(Path(config_path).read_text(encoding="utf-8")) if Path(config_path).exists() else {}
    except tomllib.TOMLDecodeError:
        return "custom"
    return "hosted" if raw.get("brain_route") == "hosted" else "custom"


class RoutePush:
    """Tells each unit the saved route once after it connects and again when the route changes. A unit without the tool is skipped."""

    def __init__(
        self,
        *,
        route: Callable[[], str],
        units: Callable[[], list[str]],
        has_tool: Callable[[str], bool],
        send: Callable[[str, dict[str, Any]], object],
    ) -> None:
        self._route, self._units, self._has_tool, self._send = route, units, has_tool, send
        self._told: dict[str, str] = {}

    def tick(self) -> None:
        """One pass. Never raises."""
        try:
            route = self._route()
            live = set(self._units())
        except Exception:
            return
        for unit in list(self._told):
            if unit not in live:
                del self._told[unit]  # told again when it comes back
        for unit in live:
            if self._told.get(unit) == route or not self._has_tool(unit):
                continue
            try:
                self._send(unit, {"route": route})
                self._told[unit] = route
            except Exception:
                continue  # tried again next pass
