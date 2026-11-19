"""Sync (docs/design/content-pantry.md, section 5): when to refill a unit's shelves, how a shelf is built, and how the heard list comes back.

The unit protocol is a small object passed in (``status``, ``heard_since``, ``install_shelf``, ``deny``), so the rules are tested with no unit and the real
tools (`self.pantry.*`, `self.assets.*`, still being shaped by the firmware track) plug in later. Flash is protected: at most three shelf swaps a window, one at a
time, never while the unit is busy, and the heard list is read in batches."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from maipai_packages.pantry import shelf
from maipai_packages.pantry.library import Library
from maipai_packages.pantry.record import Record

LOW_FRACTION = 0.25  # refill when unheard records fall below this share of the shelf
MAX_SWAPS_PER_WINDOW = 3
DENY_BATCH = 16  # ids in one self.pantry.deny call (the unit writes flash once per call that holds a new id)
DENY_BATCHES_PER_PASS = 8
FLOOR_SECTORS = 8  # below this the owner is asked to remove a pack


class UnitLink(Protocol):
    def status(self, unit: str) -> list[dict]: ...  # per shelf: {"kind", "language", "count", "unheard", "bytes"}
    def heard_since(self, unit: str, seq: int) -> tuple[list[dict], int]: ...
    def install_shelf(self, unit: str, kind: str, language: str, body: bytes) -> bool: ...
    def deny(self, unit: str, ids: list[str]) -> bool: ...  # True only when the unit took every id in the call


@dataclass
class UnitState:
    idle: bool = True
    muted_for_other_than_night: bool = False
    on_power_or_over_half: bool = True
    in_game: bool = False
    free_bytes: int = shelf.ITEM_CAP_BYTES
    known: bool = True  # False when the unit did not answer one of the state questions: nothing is installed


def read_unit_state(call: Callable[[str, str, dict], object], unit: str, *, idle: bool) -> UnitState:
    """What the unit says about its battery, privacy switches, game and free room (`self.battery.get_status`, `self.privacy.get`, `self.game.list`, `self.assets.list`).

    ``idle`` is the host's own view (no turn running, nothing being said). A question the unit does not answer, or answers without the field, makes the
    state unknown, and an unknown state installs nothing: the heard list is still read, the shelves wait for the next pass."""
    from maipai_packages.pantry.unit_link import _dict

    def ask(tool: str) -> dict:
        try:
            return _dict(call(unit, tool, {}))
        except Exception:
            return {}

    battery, privacy, games, assets = (ask(t) for t in ("self.battery.get_status", "self.privacy.get", "self.game.list", "self.assets.list"))
    percent, charging = battery.get("percent"), battery.get("charging")
    free = assets.get("free_bytes")
    ints = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (percent, free))
    known = (
        battery.get("ok") is not False and ints and isinstance(charging, bool)
        and "muted" in privacy and games.get("ok") is True and "playing" in games and assets.get("ok") is True
    )
    if not known:
        return UnitState(idle=idle, known=False)
    return UnitState(
        idle=idle,
        muted_for_other_than_night=bool(privacy.get("muted") or privacy.get("quiet")),
        on_power_or_over_half=bool(charging) or percent > 50,
        in_game=bool(games.get("playing")),
        free_bytes=int(free),
    )


def _hour(now: float) -> int:
    return time.localtime(now).tm_hour


def in_window(now: float, start: float = 2, end: float = 5) -> bool:
    """True inside the refill window; the bounds are hours of the local day and may carry a fraction (21.5 is 21:30)."""
    local = time.localtime(now)
    hour = local.tm_hour + local.tm_min / 60
    return start <= hour < end if start < end else hour >= start or hour < end


def plan(shelves: list[dict], state: UnitState, now: float, *, window: tuple[float, float] = (2, 5), nightly_done: set[tuple[str, str]] = frozenset()) -> list[tuple[str, str, str]]:
    """The shelves to refill now, at most three, as (kind, language, why). Nightly in the quiet window, or at once when stock is low; never while busy."""
    if not (state.known and state.idle and not state.in_game and not state.muted_for_other_than_night and state.on_power_or_over_half):
        return []
    out = []
    for item in shelves:
        key = (item["kind"], item["language"])
        count, unheard = int(item.get("count", 0)), int(item.get("unheard", 0))
        low = count == 0 or unheard < LOW_FRACTION * count
        if low:
            out.append((*key, "low stock"))
        elif in_window(now, *window) and key not in nightly_done:
            out.append((*key, "nightly"))
        if len(out) >= MAX_SWAPS_PER_WINDOW:
            break
    return out


def build_shelf(library: Library, unit: str, kind: str, language: str, free_bytes: int, *, rating: str = "kid") -> bytes | None:
    """A shelf for one unit: unheard records first, older heard ones only to fill the size. None when there is not enough room for a useful shelf."""
    heard = library.heard(unit)
    refused = library.refused()
    pool = [r for r in library.records(kind, language) if r.id_hex not in refused and (rating == "adult" or r.rating == "kid")]
    unheard = [r for r in pool if r.id_hex not in heard]
    old = sorted((r for r in pool if r.id_hex in heard), key=lambda r: heard[r.id_hex].get("counter", 0))
    ordered: list[Record] = unheard + old
    if not ordered:
        return None
    room = min(free_bytes, shelf.ITEM_CAP_BYTES)
    if shelf.sectors(room) < FLOOR_SECTORS and room < FLOOR_SECTORS * shelf.SECTOR:
        return None  # not enough free room for a useful shelf: the owner is asked to remove a pack
    take = ordered[: max(1, shelf.capacity_for(kind, room, ordered[:50]))]
    while take:
        try:
            body = shelf.pack(take, rating_ceiling=rating)
        except Exception:
            take = take[: int(len(take) * 0.9)]
            continue
        if len(body) <= room:
            return body
        take = take[: int(len(take) * 0.9)]
    return None


def run_unit(library: Library, link: UnitLink, unit: str, state: UnitState, *, now: float | None = None, window: tuple[float, float] = (2, 5), nightly_done: set[tuple[str, str]] | None = None) -> dict:
    """One sync pass for one unit: take its heard list, send denials, refill what the rule says. Returns what happened, for the log and the dashboard."""
    now = time.time() if now is None else now
    result = {"heard": 0, "swapped": [], "skipped": ""}
    seq = int(library._read_json(f"seq-{unit}.json", {}).get("seq", 0))
    entries, seq = link.heard_since(unit, seq)
    if entries:
        result["heard"] = library.note_heard(unit, entries)
    library._write_json(f"seq-{unit}.json", {"seq": seq})
    # Only ids this unit has not yet acknowledged, in small batches: an id already denied is never sent again, so the unit writes no flash for it.
    pending = sorted(library.refused() - library.denied_on(unit))
    for start in range(0, min(len(pending), DENY_BATCH * DENY_BATCHES_PER_PASS), DENY_BATCH):
        batch = pending[start : start + DENY_BATCH]
        if not link.deny(unit, batch):
            break  # the rest goes on the next pass
        library.note_denied(unit, batch)
    shelves = link.status(unit)
    todo = plan(shelves, state, now, window=window, nightly_done=nightly_done or set())
    if not todo:
        result["skipped"] = "nothing due, or the unit is busy"
    for kind, language, why in todo:
        body = build_shelf(library, unit, kind, language, state.free_bytes)
        if body is None:
            result["skipped"] = f"no records to build the {language} {kind} shelf yet"
            continue
        if link.install_shelf(unit, kind, language, body):
            result["swapped"].append({"kind": kind, "language": language, "why": why, "bytes": len(body)})
            if nightly_done is not None:
                nightly_done.add((kind, language))
        else:
            result["skipped"] = f"the unit did not take the {language} {kind} shelf"
            break  # one at a time: a refusal ends this pass
    return result
