# ruff: noqa: E501
"""The newer unit features, built once and shared by the voice path and the settings page.

Emotion faces and overlay tags (reply_tags.py), the listening and look choices (unit_prefs.py), the pack library
(packs.py) and the filler sounds (fillers.py) all need the same three things: a way to call a unit tool, one
cache of which optional tools each unit has, and the per-unit settings. ``Polish`` holds them together so the two
sides see the same state.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from maipai_body import fillers as fillers_mod
from maipai_body import overlays as overlays_mod
from maipai_body import packs as packs_mod
from maipai_body import unit_prefs
from maipai_body.unit_tools import ToolProbe

logger = logging.getLogger("maipai_body.unit_polish")


class Polish:
    def __init__(
        self,
        call: Callable[..., object],
        get: Callable[[str], dict[str, Any]],
        put: Callable[[str, dict[str, Any]], dict[str, Any]],
        *,
        library: packs_mod.PackLibrary | None = None,
        active: packs_mod.ActiveStore | None = None,
        synth: Callable[[str], tuple[Any, int]] | None = None,
        tool_list: Callable[[str], set[str] | None] | None = None,
        data_dir: Path | None = None,
        tone_on_unit: Callable[[str], bool] | None = None,
    ) -> None:
        self.get = get
        self.probe = ToolProbe(call, tool_list=tool_list)
        if library is None and data_dir is not None:
            library = packs_mod.PackLibrary(data_dir / "packs", filler_root=data_dir / "fillers")
        if active is None and data_dir is not None:
            active = packs_mod.ActiveStore(data_dir / "packs-active.json")
        self.library = library or packs_mod.PackLibrary()
        self.active = active or packs_mod.ActiveStore()
        self.prefs = unit_prefs.PrefsService(self.probe, get, put)
        self.overlays = overlays_mod.OverlayDirector(self.probe)
        self.packs = packs_mod.PackService(self.probe, self.library, self.active)
        self.generator = fillers_mod.FillerGenerator(synth, self.library)
        self.player = fillers_mod.FillerPlayer(self.library, self.active, self.probe, tone_on_unit=tone_on_unit)

    def turn_prefs(self, device_id: str) -> dict[str, Any]:
        """What the voice path reads each turn."""
        return unit_prefs.prefs_of(self.get(device_id))

    def attach(self, bridge: Any) -> None:
        """Give the turn bridge its three hooks."""
        bridge.prefs_for = self.turn_prefs
        bridge.overlay_director = self.overlays
        bridge.filler_player = self.player

    def on_connect(self, device_id: str) -> None:
        """A unit connected: forget what we knew of its tools, then send what it is due."""
        self.probe.forget(device_id)
        for step in (self.prefs.sync, self.packs.sync):
            try:
                step(device_id)
            except Exception:
                logger.debug("unit features not synced to %s", device_id[-5:], exc_info=True)
