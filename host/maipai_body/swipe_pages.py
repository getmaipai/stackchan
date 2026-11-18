# ruff: noqa: E501
"""Swipe pages and the control sheet, host side (firmware patches P10 to P13).

The unit draws the pages; this module keeps the owner's choice per unit, checks it with the same rules as the unit
(``maipai_pages_core.h``: a page at most once, three on each side of the face, closing times, quick actions, sheet items),
saves it in the host's own unit settings and sends it in one call when the unit has the tools:

    self.pages.status {}               -> {"ok": true, ...}    (also the probe)
    self.pages.set    {"json": "{...}"} -> {"ok": true}
    self.page.show    {"name": "clock"} -> {"ok": true}         (a page name, "sheet" or "face")
    self.page.tiles   {"json": "[...]"} -> {"ok": true}         (up to six tiles, pushed by the host or Home; the unit has no data source)

A unit without the tools gets the page's "coming with the next unit update" note and nothing is sent; the choice is kept and goes out
when the unit connects with the tools. ``pages_table.json`` is what the firmware core prints (``pages_core_test --table``); a test
keeps it and this module equal to the core.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from maipai_body.hal.errors import BodyLost
from maipai_body.unit_tools import ToolProbe, dumps, is_unknown_tool, unwrap

logger = logging.getLogger("maipai_body.swipe_pages")

KEY = "swipe_pages"
TABLE_PATH = Path(__file__).with_name("pages_table.json")

PAGES = ("clock", "timers", "games", "actions", "frame", "tiles")
ACTIONS = ("beep", "dance", "game", "hello")
LEGACY_LIGHT = "light"  # patch NX01: the sheet item saved as "light" is the Lock tile now; the old name is read as the same item in the same place
LEGACY_FIND = "find"  # the removed find-me button: an old saved choice or an old caller may still name it; it is read and dropped
SHEET_ITEMS = (
    "volume",
    "brightness",
    "mute",
    "quiet",
    "lock",
    "timers",
    "games",
    "wifi",
    "battery",
    "tailnet",
    "address",
)
ICONS = ("none", "sun", "cloud", "rain", "home", "bell", "heart", "lamp", "temp", "check")
SIDE_MAX = 3
SHEET_S = (8, 30)
SHEET_S_OLD_MIN = 5  # before patch UI01 the shortest was 5 s: 5 to 7 are read as 8
IDLE_S = (5, 300)
ACTIONS_COUNT = (2, 4)
MAX_SLIDERS, MAX_TILES, MAX_STATUS = 2, 5, 4
SLIDERS = ("volume", "brightness")
TILE_ITEMS = ("mute", "quiet", "lock", "timers", "games")
STATUS_ITEMS = ("wifi", "battery", "tailnet", "address")
TILES_MAX = 6
TILE_LABEL = 12
TILE_VALUE = 10

DEFAULTS: dict[str, Any] = {
    "left": ["clock"],
    "right": ["games"],
    "sheet_s": 10,
    "idle_s": 20,
    "actions": ["beep", "dance", "game", "hello"],
    "sheet_items": [
        "volume",
        "brightness",
        "mute",
        "quiet",
        "lock",
        "timers",
        "games",
        "wifi",
        "battery",
    ],
}

# Sentences as the unit says them (maipai_pages_core.h), so the page and the unit never disagree.
ERR_PAGE = "A page name must be one of clock, timers, games, actions, frame or tiles. Send one of those names."
ERR_DUP = "Each page can be in the strip once. Remove the repeated page and send the list again."
ERR_LONG = "Each side of the face holds up to three pages. Send three or fewer on each side."
ERR_SHEET_S = "The control sheet closes after 8 to 30 seconds. Send a number from 8 to 30."
ERR_IDLE_S = "A page returns to the face after 5 to 300 seconds. Send a number from 5 to 300."
ERR_ACTION = (
    "Quick actions are beep, dance, game and hello. Send 2 to 4 of those names, each once."
)
ERR_ITEM = "A sheet item is volume, brightness, mute, quiet, lock, timers, games, wifi, battery, tailnet or address, each once."
ERR_ITEM_FULL = "The sheet holds up to 2 sliders, 5 buttons and 4 status lines. Remove one and send the list again."

SAY: dict[str, tuple[str, str]] = {
    "soon": (
        "Saved. This unit gets the swipe pages with its next update; nothing was sent yet.",
        "Guardado. Esta unidad recibe las páginas deslizables con su próxima actualización; todavía no se envió nada.",
    ),
    "sent": ("Saved and sent to the unit.", "Guardado y enviado a la unidad."),
    "kept": (
        "Saved. The unit is not connected; it gets the choice when it connects.",
        "Guardado. La unidad no está conectada; recibe la elección cuando se conecte.",
    ),
    "offline": (
        "The unit is not connected. Turn it on and try again.",
        "La unidad no está conectada. Enciéndela e inténtalo de nuevo.",
    ),
    "show_soon": (
        "Showing a page comes with the next unit update.",
        "Mostrar una página llega con la próxima actualización de la unidad.",
    ),
    "tiles_soon": (
        "Sending tiles comes with the next unit update.",
        "Enviar paneles llega con la próxima actualización de la unidad.",
    ),
    "shown": ("The unit is showing it.", "La unidad lo está mostrando."),
    "tiles_sent": (
        "Tiles sent. The unit shows them on its Dashboard page.",
        "Paneles enviados. La unidad los muestra en su página Panel.",
    ),
}


def say(lang: str | None, code: str) -> str:
    english, spanish = SAY[code]
    return spanish if (lang or "").lower().startswith("es") else english


def table() -> dict[str, Any]:
    """What the firmware core prints (``pages_core_test --table``): names, limits, icon shapes and the default sheet layout."""
    return json.loads(TABLE_PATH.read_text())


def _names(
    value: object, allowed: tuple[str, ...], error: type[Exception], message: str
) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(x, str) and x in allowed for x in value):
        raise error(message)
    return list(value)


def migrate(values: dict[str, Any]) -> dict[str, Any]:
    """An older choice, read the way the unit reads it (patches UI01 and NX01): the old "light" sheet item is the Lock tile, find me is dropped from the actions and the sheet, too few actions left
    after that are topped up in their usual order, and a sheet time under the new shortest is raised to it. Never an error."""
    out = dict(values)
    had_find = isinstance(out.get("actions"), list) and LEGACY_FIND in out["actions"]
    for key in ("actions", "sheet_items"):
        if isinstance(out.get(key), list):
            out[key] = [x for x in out[key] if x != LEGACY_FIND]
    if isinstance(out.get("sheet_items"), list):
        mapped = ["lock" if x == LEGACY_LIGHT else x for x in out["sheet_items"]]
        out["sheet_items"] = [x for i, x in enumerate(mapped) if x != "lock" or "lock" not in mapped[:i]]
    if had_find and all(isinstance(x, str) for x in out["actions"]):
        for name in ACTIONS:
            if len(out["actions"]) >= ACTIONS_COUNT[0]:
                break
            if name not in out["actions"]:
                out["actions"].append(name)
    sheet_s = out.get("sheet_s")
    if isinstance(sheet_s, int) and not isinstance(sheet_s, bool) and SHEET_S_OLD_MIN <= sheet_s < SHEET_S[0]:
        out["sheet_s"] = SHEET_S[0]
    return out


def clean(
    values: dict[str, Any], current: dict[str, Any] | None, error: type[Exception]
) -> dict[str, Any]:
    """The whole choice: ``current`` (or the defaults) with ``values`` laid over it, every rule of the unit applied."""
    out = migrate({**DEFAULTS, **(current or {})})
    values = migrate(values)
    for key in ("left", "right"):
        if key in values:
            out[key] = _names(values[key], PAGES, error, ERR_PAGE)
    if len(out["left"]) > SIDE_MAX or len(out["right"]) > SIDE_MAX:
        raise error(ERR_LONG)
    both = list(out["left"]) + list(out["right"])
    if len(set(both)) != len(both):
        raise error(ERR_DUP)
    for key, bounds, message in (("sheet_s", SHEET_S, ERR_SHEET_S), ("idle_s", IDLE_S, ERR_IDLE_S)):
        if key in values:
            value = values[key]
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not bounds[0] <= value <= bounds[1]
            ):
                raise error(message)
            out[key] = value
    if "actions" in values:
        actions = _names(values["actions"], ACTIONS, error, ERR_ACTION)
        if (
            len(set(actions)) != len(actions)
            or not ACTIONS_COUNT[0] <= len(actions) <= ACTIONS_COUNT[1]
        ):
            raise error(ERR_ACTION)
        out["actions"] = actions
    if "sheet_items" in values:
        items = _names(values["sheet_items"], SHEET_ITEMS, error, ERR_ITEM)
        if len(set(items)) != len(items):
            raise error(ERR_ITEM)
        if (
            sum(i in SLIDERS for i in items) > MAX_SLIDERS
            or sum(i in TILE_ITEMS for i in items) > MAX_TILES
            or sum(i in STATUS_ITEMS for i in items) > MAX_STATUS
        ):
            raise error(ERR_ITEM_FULL)
        out["sheet_items"] = items
    return {k: out[k] for k in DEFAULTS}


def clean_tiles(tiles: object, error: type[Exception]) -> list[dict[str, str]]:
    """Up to six tiles with a known icon and plain text of the unit's lengths (the same cleaning as the unit)."""
    if not isinstance(tiles, list):
        raise error(
            "The tiles must be a list. Send up to six tiles, each with an icon, a label and a value."
        )
    if len(tiles) > TILES_MAX:
        raise error("There is room for six tiles. Send six or fewer.")
    out = []
    for tile in tiles:
        if not isinstance(tile, dict):
            raise error(
                "Each tile is an object with an icon, a label and a value. Fix the tile and send again."
            )
        icon = tile.get("icon", "none")
        label = _plain(tile.get("label", ""), TILE_LABEL)
        value = _plain(str(tile.get("value", "")), TILE_VALUE)
        if not label and not value:
            raise error("Each tile needs a label or a value. Add one to the empty tile.")
        out.append({"icon": icon if icon in ICONS else "none", "label": label, "value": value})
    return out


def _plain(text: object, limit: int) -> str:
    kept = "".join(ch for ch in str(text) if 0x20 <= ord(ch) < 0x7F)
    return kept.strip()[:limit].strip()


class SwipePagesService:
    def __init__(
        self,
        probe: ToolProbe,
        get: Callable[[str], dict[str, Any]],
        put: Callable[[str, dict[str, Any]], dict[str, Any]],
    ) -> None:
        self.probe, self._get, self._put = probe, get, put

    def values(self, device_id: str) -> dict[str, Any]:
        saved = self._get(device_id).get(KEY)
        try:
            return clean(saved if isinstance(saved, dict) else {}, None, ValueError)
        except ValueError:  # a damaged saved choice never breaks the page: the defaults come back
            return dict(DEFAULTS)

    def view(self, device_id: str, lang: str | None = None) -> dict[str, Any]:
        ready = self.probe.has(device_id, "pages")
        return {
            "values": self.values(device_id),
            "saved": isinstance(self._get(device_id).get(KEY), dict),
            "defaults": dict(DEFAULTS),
            "table": table(),
            "unit_ready": ready is True,
            "reachable": ready is not None,
            "features": {"pages": ready is True},
        }

    def save(
        self, device_id: str, values: dict[str, Any], lang: str | None = None
    ) -> dict[str, Any]:
        class _Bad(ValueError):
            pass

        try:
            merged = clean(values, self.values(device_id), _Bad)
        except _Bad as exc:
            return {"ok": False, "error": str(exc)}
        self._put(device_id, {KEY: merged})
        return {**self._send(device_id, merged, lang), "values": merged}

    def _send(self, device_id: str, merged: dict[str, Any], lang: str | None) -> dict[str, Any]:
        have = self.probe.has(device_id, "pages")
        if have is None:
            return {"ok": True, "pushed": False, "pending": False, "message": say(lang, "kept")}
        if have is False:
            return {"ok": True, "pushed": False, "pending": True, "message": say(lang, "soon")}
        try:
            reply = unwrap(self.probe.call(device_id, "self.pages.set", {"json": dumps(merged)}))
        except (BodyLost, OSError, TimeoutError):
            return {"ok": True, "pushed": False, "pending": False, "message": say(lang, "kept")}
        if reply.get("ok") is not True:
            if is_unknown_tool(reply):
                return {"ok": True, "pushed": False, "pending": True, "message": say(lang, "soon")}
            return {
                "ok": False,
                "pushed": False,
                "message": str(reply.get("error") or say(lang, "soon")),
            }
        return {"ok": True, "pushed": True, "pending": False, "message": say(lang, "sent")}

    def sync(self, device_id: str) -> None:
        """A unit connected: send the saved choice when the person made one and the unit can take it."""
        self.probe.forget(device_id)
        if isinstance(self._get(device_id).get(KEY), dict):
            self._send(device_id, self.values(device_id), None)

    def show(self, device_id: str, name: str, lang: str | None = None) -> dict[str, Any]:
        """Show a page (or the sheet, or the face) on the unit now."""
        if name not in (*PAGES, "sheet", "face"):
            return {"ok": False, "error": ERR_PAGE}
        have = self.probe.has(device_id, "pages")
        if have is None:
            return {"ok": False, "message": say(lang, "offline")}
        if have is False:
            return {"ok": False, "pending": True, "message": say(lang, "show_soon")}
        try:
            reply = unwrap(self.probe.call(device_id, "self.page.show", {"name": name}))
        except (BodyLost, OSError, TimeoutError):
            return {"ok": False, "message": say(lang, "offline")}
        if is_unknown_tool(reply):
            return {"ok": False, "pending": True, "message": say(lang, "show_soon")}
        if reply.get("ok") is not True:
            return {"ok": False, "message": str(reply.get("error") or "")}
        return {"ok": True, "message": say(lang, "shown")}

    def push_tiles(self, device_id: str, tiles: object, lang: str | None = None) -> dict[str, Any]:
        """Send up to six tiles for the unit's Dashboard page (the host or Home calls this; the unit has no data source)."""

        class _Bad(ValueError):
            pass

        try:
            clean_list = clean_tiles(tiles, _Bad)
        except _Bad as exc:
            return {"ok": False, "error": str(exc)}
        have = self.probe.has(device_id, "pages")
        if have is None:
            return {"ok": False, "message": say(lang, "offline")}
        if have is False:
            return {"ok": False, "pending": True, "message": say(lang, "tiles_soon")}
        try:
            reply = unwrap(
                self.probe.call(device_id, "self.page.tiles", {"json": dumps(clean_list)})
            )
        except (BodyLost, OSError, TimeoutError):
            return {"ok": False, "message": say(lang, "offline")}
        if is_unknown_tool(reply):
            return {"ok": False, "pending": True, "message": say(lang, "tiles_soon")}
        if reply.get("ok") is not True:
            return {"ok": False, "message": str(reply.get("error") or "")}
        return {"ok": True, "tiles": len(clean_list), "message": say(lang, "tiles_sent")}
