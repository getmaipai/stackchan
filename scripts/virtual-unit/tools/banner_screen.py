"""Virtual handlers for banner face reports and screen level reads."""
from tools import tool


@tool("self.banner.face_seen")
def face_seen(u, args):
    state = u.state.setdefault("banner_screen", {})
    seconds = int(args.get("seconds", 3))
    if seconds <= 0:
        seconds = 3
    seconds = min(seconds, 10)

    now = u.now_ms
    last = state.get("face_last_ms", 0)
    if not state.get("status_icons", False) or (last and now - last < 500):
        return {"ok": True, "shown": False, "reason": "status_icons_off_or_rate_limited"}

    state["face_last_ms"] = now | 1
    state["face_until_ms"] = now + seconds * 1000
    return {"ok": True, "shown": True}


@tool("self.screen.get_level")
def get_level(u, args):
    state = u.state.setdefault("banner_screen", {})
    if not state.get("backlight_present", True):
        return {"saved": 0, "live": 0}

    raw = state.get("saved_raw")
    saved = 75 if raw is None else (10 if raw <= 0 else min(raw, 100))
    live = max(0, min(100, int(state.get("live", saved))))
    return {"saved": saved, "live": live}
