# ruff: noqa: E501
"""The two brain routes (owner decision 34): hosted by M5Stack/Xiaozhi, or custom (your own key, a community server, your own host or MaiPai Home, a model on your computer).

The host keeps one word in robot.toml, ``brain_route = "hosted" | "custom"`` (no word means custom). The unit owns the route: it sends the event ``brain_route {route}`` and the host
keeps the word in step; leaving hosted calls ``self.brain.set_route {"route": "custom"}`` on each unit (never repeated on connect: it shows the unit's notice and restarts). The hosted route stays planned until a test
build proves the vendor's server accepts this firmware (``docs/plan/cloud-brain-firmware-test.md``): while ``HOSTED_PROVEN`` is false the page shows it as planned and
the host refuses to save it, so nobody is moved onto a route that cannot work."""

from __future__ import annotations

import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

HOSTED_PROVEN = False
ROUTES = ("hosted", "custom")
TOOL = "self.brain.set_route"  # firmware SF98; the unit also answers self.brain.status and sends the event brain_route

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


def on_event(config_path: Path, kind: str, extra: dict[str, Any] | None) -> bool:
    """The unit's ``brain_route`` event (firmware patch SF98) says which route it is on; the host keeps the saved word in step. True when the file changed."""
    if kind != "brain_route":
        return False
    route = (extra or {}).get("route")
    if route not in ROUTES or read(config_path) == route:
        return False
    from maipai_body.brain_setup import modes

    modes.set_values(Path(config_path), "", {"brain_route": route})
    return True


def leave_hosted(units: list[str], has_tool: Callable[[str], bool], send: Callable[[str, dict[str, Any]], object]) -> int:
    """Ask each unit that has the tool to go to route custom (it erases the vendor link and shows its own notice). Returns how many were asked. Never raises."""
    asked = 0
    for unit in units:
        try:
            if has_tool(unit):
                send(unit, {"route": "custom"})
                asked += 1
        except Exception:
            continue
    return asked
