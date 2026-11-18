"""Audio, listening, music and unit utility tools for the virtual unit."""
import json

from tools import tool


def _state(u):
    return u.state.setdefault("audio", {
        "policy": {"enabled": True, "night_ok": False, "muted": False, "dark": False,
                   "quiet_from": -1, "quiet_to": -1},
        "plays": 0, "refused": 0, "chime_enabled": False, "music_enabled": False,
        "stage": 0, "privacy": {"muted": 0, "vision_off": 0, "quiet": 0,
                                  "mic_off": 0, "mic_off_verified": 0,
                                  "mute_source": "none", "local_unmute": 1, "mic_regs": "unavailable"},
        "prefs": {}, "bench": {}, "offline": {"clips_played": 0, "clips_missing": 0},
    })


def _quiet(s):
    p = s["policy"]
    if p["dark"]:
        return True
    minute = (u_minute := s.get("minute", 720))
    start, end = p["quiet_from"], p["quiet_to"]
    if start < 0 or end < 0 or start == end:
        start, end = 1320, 420
    return start <= minute < end if start < end else minute >= start or minute < end


def _play(s, name, urgent=False, test=False):
    sounds = {"success", "popup", "vibration", "exclamation", "low_battery"}
    if name not in sounds:
        return False, "unknown_sound"
    p = s["policy"]
    if p["muted"]:
        return False, "muted"
    if not p["enabled"] and not test:
        return False, "disabled"
    if _quiet(s) and not p["night_ok"] and not urgent and not test:
        return False, "night"
    s["plays"] += 1
    return True, ""


@tool("self.audio.hourly_chime")
def hourly_chime(u, args):
    s = _state(u)
    enabled = args.get("enabled", -1)
    if enabled >= 0:
        s["chime_enabled"] = bool(enabled)
    result = "none"
    if args.get("test", False):
        if not s["chime_enabled"]:
            result = "off"
        elif _quiet(s):
            result = "quiet"
        elif s["policy"]["muted"] or not s["policy"]["enabled"]:
            s["refused"] += 1
            result = "disabled"
        else:
            s["plays"] += 1
            result = "chime"
    return {"ok": True, "enabled": s["chime_enabled"], "result": result}


@tool("self.audio.notify")
def notify(u, args):
    ok, why = _play(_state(u), "exclamation" if args.get("urgent", False) else "popup", args.get("urgent", False))
    return {"ok": ok, "spoken": False} if ok else {"ok": False, "error": why}


@tool("self.audio.offline_phrase")
def offline_phrase(u, args):
    s = _state(u)
    group = args.get("group", "")
    groups = {"no_wifi", "no_host", "refused", "connecting", "back"}
    if group and group not in groups:
        return {"ok": False, "error": "unknown_group"}
    dry = args.get("dry", True)
    picked = group or "no_host"
    result = {"ok": True, "kind": "clip", "group": picked, "variant": 0, "bytes": 0, "dry": dry}
    if not dry and (s["policy"]["muted"] or not s["policy"]["enabled"] or _quiet(s)):
        result.update(kind="none", group=picked, variant=-1, bytes=0)
    return result


@tool("self.audio.play_sound")
def play_sound(u, args):
    ok, why = _play(_state(u), args.get("name", "success"), args.get("urgent", False), args.get("test", False))
    return {"ok": True} if ok else {"ok": False, "error": why}


@tool("self.audio.set_sound_policy")
def set_sound_policy(u, args):
    s = _state(u)
    p = s["policy"]
    old = {k: p[k] for k in ("enabled", "night_ok", "muted", "quiet_from", "quiet_to")}
    for key in ("enabled", "night_ok", "muted", "dark", "quiet_from", "quiet_to"):
        if key in args:
            p[key] = args[key]
    p["quiet_from"] = max(-1, min(1439, p["quiet_from"]))
    p["quiet_to"] = max(-1, min(1439, p["quiet_to"]))
    changed = any(old[k] != p[k] for k in old)
    return {"ok": True, "changed": changed}


@tool("self.audio.sound_info")
def sound_info(u, args):
    s = _state(u)
    p = s["policy"]
    return {"enabled": int(p["enabled"]), "night_ok": int(p["night_ok"]), "muted": int(p["muted"]),
            "mute_hook": int(p["muted"]), "quiet_from": p["quiet_from"], "quiet_to": p["quiet_to"],
            "night": _quiet(s), "clips_present": 16, "clips_total": 16, "played": s["plays"],
            "refused": s["refused"], "clips_played": s["offline"]["clips_played"],
            "clips_missing": s["offline"]["clips_missing"]}


@tool("self.bench.inject")
def bench_inject(u, args):
    s = _state(u)
    if s["bench"].get("inject_until", 0) > u.now_ms:
        return {"ok": False, "error": "running"}
    s["bench"].update(args)
    s["bench"]["inject_until"] = u.now_ms + args.get("gap_ms", 1800) + args.get("tail_ms", 9000)
    return {"ok": True}


@tool("self.bench.noise")
def bench_noise(u, args):
    s = _state(u)
    s["bench"].update(args)
    s["bench"]["noise_until"] = u.now_ms + args.get("seconds", 60) * 1000
    return {"ok": True}


@tool("self.camera.cue_test")
def camera_cue_test(u, args):
    s = _state(u)
    s["camera_cue_until"] = u.now_ms + 3000
    # The virtual unit does not draw the camera glyph; its fixed cue deadline is modeled.
    return {"ok": True}


@tool("self.listen.test")
def listen_test(u, args):
    p = _state(u)["prefs"]
    sound = p.get("listen_sound", "chime")
    light = p.get("listen_light", "normal")
    face = p.get("listen_face", True)
    return {"ok": True, "sound": sound, "light": light, "face": face,
            "sound_chosen": sound, "all_off": sound == "off" and light == "off" and not face,
            "ring_frames": 0, "ring_slow": 0, "ring_max_us": 0}


@tool("self.music.get_status")
def music_status(u, args):
    s = _state(u)
    return {"ok": True, "enabled": s["music_enabled"], "state": "idle", "bpm": 0, "beat_ms": 0,
            "dances": 0, "dropped": 0, "suppressed": 0, "link": False, "stage": s["stage"]}


@tool("self.music.set")
def music_set(u, args):
    s = _state(u)
    s["music_enabled"] = args.get("enabled", False)
    return {"ok": True, "enabled": s["music_enabled"]}


@tool("self.music.stage")
def music_stage(u, args):
    s = _state(u)
    stage = max(0, min(4, args.get("stage", 0)))
    if stage and not s["music_enabled"]:
        return {"ok": False, "error": "the music features are off: turn them on with self.music.set first"}
    if s["privacy"]["muted"] or s["privacy"]["quiet"]:
        s["stage"] = 0
        return {"ok": False, "stage": 0, "beat": False}
    s["stage"] = stage
    return {"ok": True, "stage": stage, "beat": False}


@tool("self.power.keep_awake")
def keep_awake(u, args):
    _state(u)["keep_awake_ms"] = u.now_ms
    return {"ok": True}


@tool("self.prefs.get")
def prefs_get(u, args):
    s = _state(u)
    defaults = {"emotion_faces": False, "overlays_enabled": False, "filler_mode": "tone", "filler_wait_s": 0.4,
                "listen_sound": "chime", "listen_light": "normal", "listen_light_colour": "#40c0ff",
                "listen_face": True, "fx_crt": False, "fx_colour_mode": "normal", "fx_night_dim": False,
                "fx_glow": False, "speech_bubble": False, "thinking_dots": True, "pickup_reaction": "face"}
    chosen = sorted(s["prefs"])
    return {"ok": True, "values": {**defaults, **s["prefs"]}, "chosen": chosen,
            "unit_keys": ["listen_sound", "listen_light", "listen_light_colour", "listen_face", "fx_crt",
                          "fx_colour_mode", "fx_night_dim", "fx_glow", "speech_bubble", "thinking_dots"]}


@tool("self.prefs.set")
def prefs_set(u, args):
    s = _state(u)
    try:
        values = json.loads(args.get("json", "{}"))
        if not isinstance(values, dict):
            raise ValueError("send a JSON object")
    except (ValueError, TypeError):
        return {"ok": False, "error": "json must be a valid JSON object: send fields in an object"}
    allowed = {"emotion_faces", "overlays_enabled", "filler_mode", "filler_wait_s", "listen_sound", "listen_light",
               "listen_light_colour", "listen_face", "fx_crt", "fx_colour_mode", "fx_night_dim", "fx_glow",
               "speech_bubble", "thinking_dots", "pickup_reaction"}
    if set(values) - allowed:
        key = sorted(set(values) - allowed)[0]
        return {"ok": False, "error": f"unknown preference {key}: remove it or use a supported preference"}
    updated = dict(s["prefs"])
    for key, value in values.items():
        if key.endswith(("_faces", "_enabled", "_dim", "_glow", "_bubble", "_dots", "listen_face", "fx_crt")) and not isinstance(value, bool):
            return {"ok": False, "error": f"{key} must be true or false: send a boolean"}
        updated[key] = value
    changed = [k for k in values if s["prefs"].get(k) != values[k]]
    s["prefs"] = updated
    return {"ok": True, "changed": changed}


@tool("self.privacy.get")
def privacy_get(u, args):
    return dict(_state(u)["privacy"])


@tool("self.privacy.set")
def privacy_set(u, args):
    s = _state(u)
    p = s["privacy"]
    for field in ("mute", "vision_off", "quiet"):
        value = args.get(field, -1)
        if value >= 0:
            key = "muted" if field == "mute" else field
            p[key] = int(value != 0)
    p["mic_off"] = int(bool(p["muted"] or p["quiet"]))
    p["mic_off_verified"] = p["mic_off"]
    p["mute_source"] = "home"
    return dict(p)


@tool("self.privacy.set_policy")
def privacy_set_policy(u, args):
    p = _state(u)["privacy"]
    p["local_unmute"] = int(args.get("local_unmute", True))
    return {"ok": True}
