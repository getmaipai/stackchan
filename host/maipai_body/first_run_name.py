"""The robot's name from the first run (firmware patches SF09 and UX11).

The first run on the robot has a name step with seven tiles; the robot saves the index exactly as picked and tells the host in a `first_run_done` event ({"lang", "name", "mode"}). The index
is the unit's own record: 0 to 5 are Astro, Clover, Ember, Nova, Pippa and Rover (the names that shipped first, so their meaning never moves) and 6 is StackChan, the product's own name and the
default. This module turns the index into the unit's name on the host: when the unit has no name saved on the settings page, the picked name is saved there, so the settings page and the
parent view show what the person picked. A name the person already typed on the page is never replaced. Placement: host. Upstream: none."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

LOG = logging.getLogger("maipai_body.first_run_name")

NAMES = ("Astro", "Clover", "Ember", "Nova", "Pippa", "Rover", "StackChan")
DEFAULT_NAME = "StackChan"   # the name when nothing was picked and nothing was typed: the first tile of the name step


def name_for_index(index: object) -> str | None:
    """The name for a saved index, or None when the unit sent something that is not one of the seven."""
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(NAMES):
        return None
    return NAMES[index]


class FirstRunNames:
    """Applies the name from a `first_run_done` event to the unit's saved settings, once, without overwriting a typed name."""

    def __init__(self, store: Any) -> None:
        self._store = store

    def on_event(self, device_id: str | None, extra: Mapping[str, object] | None) -> str | None:
        """The name that was saved, or None when nothing was (no unit, no valid index, or the unit already has a name)."""
        if not device_id or not extra:
            return None
        name = name_for_index(extra.get("name"))
        if name is None:
            LOG.info("first run: the unit sent a name index the host does not know (%r); nothing saved", extra.get("name"))
            return None
        if self._store.get(device_id).get("name"):
            return None
        self._store.update(device_id, {"name": name})
        LOG.info("first run: the unit's name is %s", name)
        return name


def disambiguate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Two units with the same name (both left at the default) get the last five characters of their Device-Id so the unit picker tells them apart; a unit alone keeps the plain name."""
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["name"].lower()] = counts.get(row["name"].lower(), 0) + 1
    for row in rows:
        if counts[row["name"].lower()] > 1:
            row["name"] = f"{row['name']} {row['device_id'][-5:]}"
    return rows
