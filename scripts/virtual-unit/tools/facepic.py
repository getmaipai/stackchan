"""Virtual picture-face pack tools."""
from __future__ import annotations

import base64
import binascii
import json
import zlib

from tools import tool

MAX_STORE = 1_000_000
MAX_FRAMES = 14
MAX_FRAMES_PER_SLOT = 6
FRAME_BYTES = 320 * 240 * 2
MODES = {"picture", "overlay", "sequence"}
SLOTS = ("neutral", "happy", "sad", "angry", "doubt", "sleepy", "speaking")


def _err(code: str, error: str) -> dict:
    return {"ok": False, "code": code, "error": error, "error_es": error}


def _state(u):
    return u.state.setdefault("facepic", {"pack": None, "shown": None, "force_until": 0, "force_slot": None})


def _slot(name):
    return SLOTS.index(name) if name in SLOTS else -1


def _overlay_ok(raw):
    if not raw:
        return True
    try:
        ov = json.loads(raw)
        defaults = {"lx": 112, "ly": 100, "rx": 208, "ry": 100, "eye_w": 28, "eye_h": 36,
                    "mx": 160, "my": 170, "mouth_w": 70, "mouth_h": 40}
        if not isinstance(ov, dict) or not ov or any(key not in {*defaults, "color"} for key in ov):
            return False
        values = defaults.copy()
        for key in defaults:
            if key in ov:
                value = ov[key]
                if not isinstance(value, (int, float)) or not -1000 <= int(value) <= 1000:
                    return False
                values[key] = int(value)
        if "color" in ov:
            color = ov["color"]
            if not isinstance(color, str) or len(color) != 7 or color[0] != "#":
                return False
            try:
                int(color[1:], 16)
            except ValueError:
                return False
        return (4 <= values["eye_w"] <= 160 and 4 <= values["eye_h"] <= 160
                and 4 <= values["mouth_w"] <= 200 and 4 <= values["mouth_h"] <= 120
                and all(0 <= values[k] < 320 for k in ("lx", "rx", "mx"))
                and all(0 <= values[k] < 240 for k in ("ly", "ry", "my")))
    except (ValueError, TypeError):
        return False


@tool("self.facepic.begin")
def begin(u, args):
    mode, fps, overlay = args.get("mode", "picture"), args.get("fps", 6), args.get("overlay", "")
    if mode not in MODES:
        return _err("mode", "Unknown picture face mode")
    if fps < 1 or fps > 12:
        return _err("fps", "FPS must be from 1 to 12")
    if overlay and not _overlay_ok(overlay):
        return _err("overlay", "Overlay is invalid; provide valid eye, mouth, and color fields")
    _state(u).update(pack={"mode": mode, "fps": fps, "bytes": 0, "frames": {}, "overlay": overlay, "committed": False}, shown=None)
    return {"ok": True, "max_bytes": MAX_STORE, "max_frames": MAX_FRAMES, "frame_bytes": FRAME_BYTES}


@tool("self.facepic.frame")
def frame(u, args):
    s = _state(u); p = s["pack"]
    if p is None:
        return _err("not_started", "No picture pack has started; call self.facepic.begin first")
    slot, idx, size, crc = args.get("slot", "neutral"), args.get("index", 0), args.get("bytes", 0), args.get("crc", "00000000")
    si = _slot(slot)
    if si < 0:
        return _err("slot", "Unknown frame slot")
    if idx < 0 or idx >= (MAX_FRAMES_PER_SLOT if p["mode"] == "sequence" else 1):
        return _err("index", "Frame index is outside the mode limit")
    if size <= 0 or size > FRAME_BYTES:
        return _err("size", "Frame size is invalid")
    # Firmware calls strtoul(..., 16) without checking the documented eight-digit shape.
    try:
        expected_crc = int(str(crc).strip() or "0", 16)
    except (ValueError, TypeError):
        expected_crc = 0
    old = p["frames"].get((slot, idx))
    total = p["bytes"] - (old["bytes"] if old else 0) + size
    counts = {name: max((i for (slot_name, i) in p["frames"] if slot_name == name), default=-1) + 1 for name in SLOTS}
    adds = max(0, idx + 1 - counts[slot])
    if idx >= counts[slot] and idx > counts[slot]:
        return _err("index", "Frame indices must be declared in order; send the next index for this slot")
    if total > MAX_STORE or sum(counts.values()) + adds > MAX_FRAMES:
        return _err("limit", "Picture pack exceeds its storage or frame limit")
    p["bytes"] = total
    p["frames"][(slot, idx)] = {"bytes": size, "crc": expected_crc, "raw": args.get("raw", False), "data": bytearray(), "done": False}
    return {"ok": True}


@tool("self.facepic.data")
def data(u, args):
    s = _state(u); p = s["pack"]
    if p is None:
        return _err("not_started", "No picture pack has started; call self.facepic.begin first")
    slot, idx = args.get("slot", "neutral"), args.get("index", 0)
    if _slot(slot) < 0:
        return _err("slot", "Unknown frame slot")
    f = p["frames"].get((slot, idx))
    if f is None:
        return _err("index", "Frame was not declared; call self.facepic.frame first")
    try:
        chunk = base64.b64decode(args.get("b64", ""), validate=True)
    except (ValueError, binascii.Error):
        return _err("order", "Frame data is not valid base64; send a valid base64 chunk")
    at = args.get("at", 0)
    if at != len(f["data"]) or at + len(chunk) > f["bytes"]:
        return _err("order", "Frame chunk offset or size is out of order; send the next chunk at the reported offset")
    f["data"].extend(chunk)
    done = len(f["data"]) == f["bytes"]
    if done and (zlib.crc32(f["data"]) & 0xffffffff) != f["crc"]:
        # Firmware resets got and the running CRC while retaining bytes in the allocated buffer.
        f["data"].clear()
        return _err("crc", "Frame CRC did not match; resend the frame data")
    f["done"] = done
    return {"ok": True, "got": len(f["data"]), "done": done}


@tool("self.facepic.commit")
def commit(u, args):
    s = _state(u); p = s["pack"]
    if p is None:
        return _err("not_started", "No picture pack has started; call self.facepic.begin first")
    if not any(slot == "neutral" and f["done"] for (slot, _), f in p["frames"].items()) or any(not f["done"] for f in p["frames"].values()):
        return _err("incomplete", "Pack needs a complete neutral frame and every declared frame")
    # Decode, worker startup and allocation failures require hardware state unavailable here.
    p["committed"] = True
    s["shown"] = "neutral"
    return {"ok": True, "frames": len(p["frames"]), "bytes": p["bytes"]}


@tool("self.facepic.clear")
def clear(u, args):
    s = _state(u); s.update(pack=None, shown=None, force_slot=None, force_until=0)
    return {"ok": True}


@tool("self.facepic.status")
def status(u, args):
    s = _state(u); p = s["pack"]
    # Heap and decode counters have no virtual hardware source, so document them as fixed zeroes.
    common = {"showing": bool(p and p.get("committed")), "shown": SLOTS.index(s["shown"]) if s["shown"] in SLOTS else -1,
              "cache": [-1, -1, -1], "decode_ms": 0, "decode_ms_max": 0, "psram_free": 0, "internal_free": 0}
    if p is None:
        return {"ok": True, "held": False, **common}
    counts = {slot: max((i for (name, i) in p["frames"] if name == slot), default=-1) + 1
              for slot in SLOTS if any(name == slot for name, _ in p["frames"])}
    return {"ok": True, "held": True, "mode": p["mode"], "fps": p["fps"], "bytes": p["bytes"],
            "frames": sum(counts.values()), "slots": counts, **common}


@tool("self.facepic.bench_force")
def bench_force(u, args):
    s = _state(u); slot = args.get("slot", "neutral"); secs = args.get("seconds", 30)
    if _slot(slot) < 0:
        return _err("slot", "Unknown frame slot")
    if secs < 0 or secs > 600:
        return _err("seconds", "Seconds must be from 0 to 600")
    ignore = args.get("ignore_privacy", False)
    s["bench_ignore_privacy"] = ignore
    if ignore:
        # The virtual unit tracks the display override; it has no face widgets to mutate.
        s["privacy_display_overridden"] = True
    s["force_slot"] = slot if secs else None
    s["force_until"] = u.now_ms + secs * 1000
    s["shown"] = slot if secs else None
    return {"ok": True}
