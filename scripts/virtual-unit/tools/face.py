"""Virtual behavior for face bench and decorator tools."""
from tools import tool


_ORIGINAL_ADVANCE = None


def _install_clock_expiry(u):
    global _ORIGINAL_ADVANCE
    if _ORIGINAL_ADVANCE is None:
        _ORIGINAL_ADVANCE = u.advance

    def advance(ms):
        _ORIGINAL_ADVANCE(ms)
        face = u.state.get("face")
        if face is not None:
            _expire_gaze(face, u.now_ms)

    u.advance = advance


DECORATORS = ["sweat", "shy", "dizzy", "heart", "anger", "tears", "sparkles", "stars", "zzz", "notes"]
DECORATOR_ERROR = "unknown decorator: use sweat, shy, dizzy, heart, anger, tears, sparkles, stars, zzz or none"
BUSY_ERROR = "a mute, vision-off or quiet look or a ringing timer is showing: end that first"
NOT_READY_ERROR = "the face is not ready: try again in a moment"


def _face(u):
    return u.state.setdefault("face", {"caption": "", "dirty": 0, "sprite_off": 0, "ls_wide": 0, "one_buffer": 0,
                                         "gaze": {"x": 0, "y": 0}, "gaze_until": 0,
                                         "decorator": "none", "decorator_until": 0})


def _expire_gaze(face, now_ms):
    if face.get("gaze_until", 0) and now_ms >= face["gaze_until"]:
        face.update(gaze={"x": 0, "y": 0}, gaze_until=0)


def _rates(seconds):
    # Display counters cannot be observed by the host renderer's tool model.
    return {"seconds": float(seconds), "refresh_per_s": 0.0, "flush_per_s": 0.0, "full_frames_per_s": 0.0,
            "avg_refresh_ms": 0.0, "loop_per_s": 0.0, "peak_refresh_per_s": 0, "active_seconds": 0,
            "active_refresh_per_s": 0.0, "avg_px": 0.0, "avg_render_ms": 0.0, "avg_wait_ms": 0.0,
            "avg_lock_ms": 0.0, "avg_upd_ms": 0.0, "p50_refresh_ms": 0, "p99_refresh_ms": 0,
            "p50_gap_ms": 0, "p99_gap_ms": 0, "p99_upd_ms": 0, "face_task_stack_min_free": 0}


@tool("self.face.bench_caption")
def bench_caption(u, args):
    face = _face(u)
    if not face.get("ready", True):
        return {"ok": False, "error": "no face"}
    face["caption"] = args.get("text", "")
    return {"ok": True}


@tool("self.face.bench_fps")
def bench_fps(u, args):
    face = _face(u)
    previous = face.get("fps_at", u.now_ms)
    seconds = max(0.0, (u.now_ms - previous) / 1000.0)
    face["fps_at"] = u.now_ms
    return {"ok": True, **_rates(seconds)}


@tool("self.face.bench_mode")
def bench_mode(u, args):
    modes = ("dirty", "sprite_off", "ls_wide", "one_buffer")
    unknown = set(args) - set(modes)
    if unknown:
        return {"ok": False, "error": "unknown mode: use dirty, sprite_off, ls_wide or one_buffer"}
    values = {}
    for mode in modes:
        try:
            value = int(args.get(mode, 0))
        except (TypeError, ValueError):
            value = -1
        if value not in (0, 1):
            return {"ok": False, "error": f"{mode} must be 0 or 1: choose one of those values"}
        values[mode] = value
    face = _face(u)
    face.update(values)
    return {"ok": True}


@tool("self.face.bench_run")
def bench_run(u, args):
    what = args.get("what", "idle")
    seconds = int(args.get("seconds", 10))
    level = int(args.get("level", 0))
    if what not in ("idle", "talk", "move", "emotions"):
        return {"ok": False, "error": "unknown workload: use idle, talk, move or emotions"}
    if not 1 <= seconds <= 25:
        return {"ok": False, "error": "seconds must be 1 to 25: choose a value in that range"}
    if not 0 <= level <= 100:
        return {"ok": False, "error": "level must be 0 to 100: choose a value in that range"}
    _face(u)["last_workload"] = {"what": what, "level": level}
    u.advance(seconds * 1000)
    return {"ok": True, "what": what, **_rates(seconds)}


@tool("self.face.decor_list")
def decor_list(u, args):
    _face(u)
    # MD03 is later in firmware/patches/ORDER and adds notes to MD_NAMES.
    return {"ok": True, "decorators": DECORATORS.copy()}


@tool("self.face.decorate")
def decorate(u, args):
    name = args.get("name", "none")
    seconds = int(args.get("seconds", 6))
    face = _face(u)
    if name not in ["none", *DECORATORS]:
        return {"ok": False, "error": DECORATOR_ERROR}
    if not 1 <= seconds <= 60:
        return {"ok": False, "error": "seconds must be 1 to 60: choose a value in that range"}
    if name == "none":
        face.update(decorator="none", decorator_until=0)
        return {"ok": True}
    if face.get("blocked"):
        return {"ok": False, "error": BUSY_ERROR}
    if not face.get("ready", True):
        return {"ok": False, "error": NOT_READY_ERROR}
    face.update(decorator=name, decorator_until=u.now_ms + seconds * 1000)
    return {"ok": True}


@tool("self.face.gaze")
def gaze(u, args):
    _install_clock_expiry(u)
    x, y, ms = int(args.get("x", 0)), int(args.get("y", 0)), int(args.get("ms", 1500))
    if not -100 <= x <= 100 or not -100 <= y <= 100 or not 100 <= ms <= 10000:
        return {"ok": False, "error": "gaze values are out of range: use x and y from -100 to 100 and ms from 100 to 10000"}
    face = _face(u)
    _expire_gaze(face, u.now_ms)
    if not face.get("ready", True):
        return {"ok": False, "error": NOT_READY_ERROR}
    face.update(gaze={"x": x, "y": y}, gaze_until=u.now_ms + ms)
    return {"ok": True}
