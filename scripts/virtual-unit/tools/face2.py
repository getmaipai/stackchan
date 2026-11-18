"""Face configuration, clock, notes, and thinking tools."""
import json
import re

from tools import tool


DEFAULT_CONFIG = {
    "style": "classic", "colour": "none", "captions": True, "tod": True,
    "tod_hours": [6, 12, 18, 22], "thinking_tone": True, "lang": "en",
    "clock24": False, "clock_style": "digits", "clock_idle_s": 0,
}


def _face(u):
    return u.state.setdefault("face2", {"config": dict(DEFAULT_CONFIG), "music_notes": 0,
                                          "notes_until_ms": 0, "clock_until_ms": 0,
                                          "thinking_until_ms": 0, "thinking": False})


def _config_result(config):
    return dict(config)


@tool("self.face.get_config")
def get_config(u, args):
    return _config_result(_face(u)["config"])


@tool("self.face.set_config")
def set_config(u, args):
    try:
        value = json.loads(args.get("config", "{}"))
    except (TypeError, json.JSONDecodeError):
        return {"isError": True, "text": 'config is not a JSON object: send something like {"style":"minimal"}'}
    if not isinstance(value, dict):
        return {"isError": True, "text": 'config is not a JSON object: send something like {"style":"minimal"}'}
    current = dict(_face(u)["config"])
    next_config = dict(current)
    next_config.update(value)
    enums = {"style": {"classic", "big_eyes", "minimal"},
             "colour": {"none", "mint", "sky", "amber", "rose", "lilac", "lime", "coral"},
             "lang": {"en", "es"}, "clock_style": {"digits", "ring"}}
    known = set(DEFAULT_CONFIG)
    for key, val in value.items():
        if key not in known:
            return {"isError": True, "text": f"{key}: unknown setting; remove it and try again"}
        if key in enums and not (val in enums[key] or key == "colour" and isinstance(val, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", val)):
            return {"isError": True, "text": f"{key}: invalid value; choose a supported setting and try again"}
        if key in {"captions", "tod", "thinking_tone", "clock24"} and not isinstance(val, bool):
            return {"isError": True, "text": f"{key}: must be a boolean; send true or false"}
        if key == "tod_hours" and (not isinstance(val, list) or len(val) != 4 or any(type(x) is not int or x < 0 or x > 23 for x in val)):
            return {"isError": True, "text": "tod_hours: invalid hours; send four integers from 0 to 23"}
        if key == "clock_idle_s" and (type(val) is not int or not 0 <= val <= 3600):
            return {"isError": True, "text": "clock_idle_s: must be from 0 to 3600; send a valid integer"}
    if "colour" in value and isinstance(value["colour"], str):
        next_config["colour"] = value["colour"].lower()
    _face(u)["config"] = next_config
    return _config_result(next_config)


@tool("self.face.music_notes")
def music_notes(u, args):
    count = int(args.get("count", 0))
    face = _face(u)
    if count < 0 or count > 3:
        return {"ok": False, "error": "count must be from 0 to 3: choose a supported note count"}
    face["music_notes"] = count
    face["notes_until_ms"] = u.now_ms + 30000 if count else 0
    return {"ok": True}


@tool("self.face.show_clock")
def show_clock(u, args):
    seconds = int(args.get("seconds", 30))
    face = _face(u)
    if seconds < 0 or seconds > 3600:
        return {"ok": False, "error": "seconds must be from 0 to 3600: choose a supported duration"}
    if seconds == 0:
        face["clock_until_ms"] = 0
        return {"ok": True}
    if not face.get("time_set", False):
        return {"ok": False, "error": "the clock is not set yet: wait for the unit to get the time, then ask again"}
    if face.get("privacy_bits", 0) or face.get("timers_ringing", False):
        return {"ok": False, "error": "the clock does not cover a mute, vision-off or quiet look or a ringing timer: end that first"}
    face["clock_until_ms"] = u.now_ms + seconds * 1000
    return {"ok": True}


@tool("self.face.thinking")
def thinking(u, args):
    face = _face(u)
    on = args.get("on", True)
    face["thinking"] = on
    face["thinking_until_ms"] = u.now_ms + 45000 if on else 0
    return {"ok": True}
