"""Virtual page and overlay tool handlers."""
import json

from tools import tool


PAGES = {"clock", "timers", "games", "actions", "frame", "tiles"}
OVERLAYS = {
    "rain": "weather", "snow": "weather", "sun": "weather", "clouds": "weather",
    "wind": "weather", "thunder": "weather", "fog": "weather", "stars": "weather",
    "disco": "weather", "leaves": "weather", "confetti": "event",
    "fireworks": "event", "hearts": "event", "steam": "event",
    "balloons": "event", "zzz": "event",
}
ICONS = {"sun", "cloud", "rain", "home", "bell", "heart", "lamp", "temp", "check", "none"}


def _state(u):
    return u.state.setdefault("page_overlay", {
        "page": "face", "tiles": [], "overlays_enabled": True, "hidden": False,
        "layers": {"weather": None, "event": None}, "governor": {"level": 0, "particles_pct": 100, "load_pct": 0, "worst_us": 0, "fps": 0, "sheds": 0, "restores": 0},
    })


def _page_result(state):
    return {"ok": True, "open": state["page"] != "face", "position": 0 if state["page"] == "face" else 1, "sheet": state["page"] == "sheet"}


@tool("self.page.show")
def page_show(u, args):
    name = args.get("name", "face")
    if name not in PAGES | {"face", "sheet"}:
        return {"ok": False, "error": "The page name must be one of clock, timers, games, actions, frame, tiles, sheet or face. Send one of those names."}
    _state(u)["page"] = name
    return {"ok": True}


@tool("self.page.tiles")
def page_tiles(u, args):
    try:
        tiles = json.loads(args.get("json", "[]"))
    except (TypeError, json.JSONDecodeError):
        tiles = None
    if not isinstance(tiles, list):
        return {"ok": False, "error": 'The tiles must be a JSON array. Send something like [{"icon":"sun","label":"Today","value":"72 F"}].'}
    result = []
    for item in tiles:
        if not isinstance(item, dict):
            item = {}
        icon = item.get("icon") if isinstance(item.get("icon"), str) and item.get("icon") in ICONS else None
        label = item.get("label") if isinstance(item.get("label"), str) else None
        value = item.get("value", "")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = format(value, "g")
        if not isinstance(value, str):
            value = ""
        if len(result) == 6:
            return {"ok": False, "error": "There is room for six tiles. Send six or fewer."}
        if not (label or value):
            return {"ok": False, "error": "Each tile needs a label or a value. Add one to the empty tile."}
        result.append({"icon": icon or "none", "label": (label or "")[:12], "value": value[:10]})
    _state(u)["tiles"] = result
    return {"ok": True, "tiles": len(result)}


@tool("self.page.bench_swipe")
def page_bench_swipe(u, args):
    # Touch hardware and LVGL gesture recognition are not modeled; report a deterministic bench state.
    _state(u)
    u.advance(max(20, min(3000, int(args.get("ms", 200)))))
    return _page_result(_state(u))


@tool("self.page.bench_tap")
def page_bench_tap(u, args):
    # Touch hardware and LVGL gesture recognition are not modeled; report a deterministic bench state.
    _state(u)
    u.advance(max(20, min(3000, int(args.get("hold_ms", 120)))))
    return _page_result(_state(u))


@tool("self.overlay.set")
def overlay_set(u, args):
    name = args.get("name", "rain")
    intensity = args.get("intensity", "normal")
    seconds = int(args.get("seconds", 8))
    state = _state(u)
    if name not in OVERLAYS:
        return {"ok": False, "error": "that overlay is not known: use rain, snow, sun, clouds, wind, thunder, fog, stars, disco, confetti, fireworks, hearts, steam, balloons, leaves or zzz"}
    if intensity not in {"light", "normal", "heavy"}:
        return {"ok": False, "error": "intensity must be light, normal or heavy: pick one and send again"}
    if seconds < 0 or seconds > 3600:
        return {"ok": False, "error": "seconds must be from 0 to 3600: 0 runs until cleared"}
    if not state["overlays_enabled"]:
        return {"ok": False, "error": "overlays are turned off in the settings: turn them on and send again"}
    layer = OVERLAYS[name]
    state["layers"][layer] = {"name": name, "intensity": intensity, "until_ms": 0 if seconds == 0 else u.now_ms + seconds * 1000, "particles": 0}
    return {"ok": True}


@tool("self.overlay.clear")
def overlay_clear(u, args):
    state = _state(u)
    state["layers"] = {"weather": None, "event": None}
    return {"ok": True}


@tool("self.overlay.status")
def overlay_status(u, args):
    state = _state(u)
    layers = []
    for layer in ("weather", "event"):
        active = state["layers"][layer]
        if active and active["until_ms"] and u.now_ms >= active["until_ms"]:
            state["layers"][layer] = active = None
        layers.append({"layer": layer, "name": active["name"] if active else "none", "intensity": active["intensity"] if active else "normal", "seconds_left": max(0, (active["until_ms"] - u.now_ms + 999) // 1000) if active and active["until_ms"] else 0, "particles": active["particles"] if active else 0})
    g = state["governor"]
    return {"ok": True, "enabled": state["overlays_enabled"], "hidden": state["hidden"], "layers": layers, "names": list(OVERLAYS), "governor": dict(g), "cost": {"flushes": 0, "post_avg_us": 0, "post_worst_us": 0}}
