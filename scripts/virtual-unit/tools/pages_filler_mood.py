"""Virtual behavior for pages, filler and mood tools."""
import json

from tools import tool


PAGES = ["clock", "timers", "games", "actions", "frame", "tiles"]
ACTIONS = ["find", "beep", "dance", "game", "hello"]
SHEET_ITEMS = ["volume", "brightness", "mute", "quiet", "light", "find", "timers", "games", "wifi", "battery", "tailnet", "address"]


def _state(u):
    return u.state.setdefault("pages_filler_mood", {
        "left": ["clock", "timers", "games"], "right": ["actions", "frame", "tiles"],
        "sheet_s": 8, "idle_s": 30, "actions": ACTIONS[:], "sheet_items": SHEET_ITEMS[:],
        "pages_open": False, "position": 0, "sheet": False, "tiles": 0, "tiles_at": 0,
        "filler_mode": "none", "played": 0, "phrases": 0, "last": "", "last_skip": "", "skipped": {},
        "care": 50, "saved_care": 50, "pets_today": 0, "day": 0, "test": False, "level": "plain",
    })


def _level(care):
    return "happy" if care >= 70 else "sad" if care < 30 else "plain"


@tool("self.pages.get")
def pages_get(u, args):
    s = _state(u)
    return {"ok": True, "left": s["left"], "right": s["right"], "sheet_s": s["sheet_s"], "idle_s": s["idle_s"], "actions": s["actions"], "sheet_items": s["sheet_items"]}


@tool("self.pages.status")
def pages_status(u, args):
    s = _state(u)
    pos = s["position"]
    page = "face"
    if s["pages_open"] and not s["sheet"]:
        page = "extra" if pos == 0 else (PAGES[pos - 1] if pos - 1 < len(PAGES) else "extra")
    age = max(0, u.now_ms // 1000 - s["tiles_at"]) if s["tiles_at"] else 0
    return {"ok": True, "version": 1, "open": s["pages_open"], "page": page, "position": pos,
            "sheet": s["sheet"], "tiles": s["tiles"], "tiles_age_s": age,
            "pages": PAGES[:], "actions": ACTIONS[:], "sheet_items": SHEET_ITEMS[:]}


@tool("self.pages.set")
def pages_set(u, args):
    s = _state(u)
    try:
        obj = json.loads(args.get("json", "{}"))
    except (TypeError, ValueError):
        return {"ok": False, "error": 'The page choice must be a JSON object. Send something like {"left":["clock"],"right":["games"]}.'}
    if not isinstance(obj, dict):
        return {"ok": False, "error": 'The page choice must be a JSON object. Send something like {"left":["clock"],"right":["games"]}.'}
    candidate = {k: (v[:] if isinstance(v, list) else v) for k, v in s.items()}
    for side in ("left", "right"):
        if side in obj:
            v = obj[side]
            if not isinstance(v, list) or len(v) > 3 or any(x not in PAGES for x in v):
                return {"ok": False, "error": "Choose up to three valid page names on each side, with no page repeated."}
            candidate[side] = v[:]
    if set(candidate["left"]) & set(candidate["right"]):
        return {"ok": False, "error": "A page can appear only once across left and right. Remove the duplicate page."}
    for key, lo, hi in (("sheet_s", 5, 15), ("idle_s", 5, 300)):
        if key in obj:
            val = obj[key]
            if isinstance(val, bool) or not isinstance(val, (int, float)) or not lo <= int(val) <= hi:
                return {"ok": False, "error": f"Choose {key} from {lo} to {hi} seconds."}
            candidate[key] = int(val)
    for key, choices, low, high, message in (
        ("actions", ACTIONS, 4, 6, "Choose four to six valid actions."),
        ("sheet_items", SHEET_ITEMS, 0, len(SHEET_ITEMS), "Choose valid control sheet items."),
    ):
        if key in obj:
            val = obj[key]
            if not isinstance(val, list) or not low <= len(val) <= high or any(x not in choices for x in val) or len(set(val)) != len(val):
                return {"ok": False, "error": message}
            candidate[key] = val[:]
    for key in ("left", "right", "actions", "sheet_items"):
        s[key] = candidate[key]
    s["sheet_s"], s["idle_s"] = candidate["sheet_s"], candidate["idle_s"]
    return {"ok": True}


@tool("self.filler.status")
def filler_status(u, args):
    s = _state(u)
    # Audio generation, pack state, and radio or speech guards are hardware-owned; counters stay fixed in this simulation.
    return {"ok": True, "mode": s["filler_mode"], "wait_ms": 0, "held": False, "sounds": 0,
            "played": s["played"], "phrases": s["phrases"], "last": s["last"], "last_skip": s["last_skip"], "skipped": dict(s["skipped"])}


@tool("self.filler.play")
def filler_play(u, args):
    s = _state(u)
    mode = args.get("mode", "tone")
    if mode not in ("none", "tone", "phrase"):
        return {"ok": False, "error": "The mode must be none, tone or phrase. Choose one of them."}
    if mode == "none":
        s["last_skip"] = "none"
        return {"ok": True, "played": False, "why": "none"}
    s["played"] += 1
    if mode == "phrase":
        s["phrases"] += 1
    s["filler_mode"] = mode
    s["last"] = mode
    s["last_skip"] = ""
    return {"ok": True, "played": True, "what": mode}


@tool("self.mood.get")
def mood_get(u, args):
    s = _state(u)
    s["level"] = _level(s["care"])
    return {"ok": True, "care": s["care"], "level": s["level"], "pets_today": s["pets_today"], "day": s["day"], "test": s["test"]}


@tool("self.mood.test")
def mood_test(u, args):
    s = _state(u)
    care = args.get("care", -1)
    if isinstance(care, bool) or not isinstance(care, int) or care < -1 or care > 100:
        return {"ok": False, "error": "Care must be -1 to restore the saved value, or 0 to 100. Choose a value in that range."}
    if care < 0:
        s["test"] = False
        s["care"] = s["saved_care"]
    else:
        s["test"] = True
        s["care"] = care
    s["level"] = _level(s["care"])
    return {"ok": True, "care": s["care"], "level": s["level"]}
