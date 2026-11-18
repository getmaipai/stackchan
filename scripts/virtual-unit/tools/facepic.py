"""Virtual picture-face pack tools."""
from __future__ import annotations

import base64
import binascii
import json
import zlib

from tools import tool

MAX_STORE = 512 * 1024
MAX_FRAMES = 42
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
        return isinstance(ov, dict) and all(k in ov for k in ("left_eye", "right_eye", "mouth", "color"))
    except (ValueError, TypeError):
        return False


@tool("self.facepic.begin")
def begin(u, args):
    mode, fps, overlay = args.get("mode", "picture"), args.get("fps", 6), args.get("overlay", "")
    if mode not in MODES:
        return _err("mode", "Unknown picture face mode")
    if fps < 1 or fps > 12:
        return _err("fps", "FPS must be from 1 to 12")
    if mode == "overlay" and not _overlay_ok(overlay):
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
    if idx < 0 or idx >= 6 or (p["mode"] != "sequence" and idx != 0):
        return _err("index", "Frame index is outside the mode limit")
    if size <= 0 or size > FRAME_BYTES:
        return _err("size", "Frame size is invalid")
    try:
        expected_crc = int(crc, 16)
    except (ValueError, TypeError):
        return _err("crc", "CRC must contain eight hexadecimal digits")
    old = p["frames"].get((slot, idx))
    total = p["bytes"] - (old["bytes"] if old else 0) + size
    if total > MAX_STORE or len(p["frames"]) >= MAX_FRAMES and old is None:
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
    if p is None:
        return {"ok": True, "held": False, "mode": "", "frames": 0, "bytes": 0, "shown": "", "free_bytes": MAX_STORE}
    return {"ok": True, "held": True, "mode": p["mode"], "frames": len(p["frames"]), "bytes": p["bytes"], "shown": s["shown"] or "", "free_bytes": MAX_STORE - p["bytes"]}


@tool("self.facepic.bench_force")
def bench_force(u, args):
    s = _state(u); slot = args.get("slot", "neutral"); secs = args.get("seconds", 30)
    if _slot(slot) < 0:
        return _err("slot", "Unknown frame slot")
    if secs < 0 or secs > 600:
        return _err("seconds", "Seconds must be from 0 to 600")
    if secs and (s["pack"] is None or not s["pack"]["committed"]):
        return _err("not_ready", "No committed picture pack is available")
    s["force_slot"] = slot if secs else None
    s["force_until"] = u.now_ms + secs * 1000
    s["shown"] = slot if secs else None
    return {"ok": True}
