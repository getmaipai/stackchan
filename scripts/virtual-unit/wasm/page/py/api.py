"""The playground's API: what the native viewer server (view.py) answers over HTTP, answered in the page. The real Handler class of view.py is used as it is: a request is made into the
object the HTTP server would have made, so /state, /tools, /log, /scenarios, /call, /touch, /hw, /imu and the rest are view.py's own code. Only three things are replaced from outside:
the pump loop (one iteration per call, view.py's own pump with its sleep turned into a stop), the scenario thread (a stepper on the same wall clock), and the cover frame (one running
cover instance, not a replay per frame). Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import base64
import importlib.util
import io
import json
import sys
import time
import types
from pathlib import Path

import wasm_shim

VU = Path("/vu/scripts/virtual-unit")
view = None
_player = None
_last_frame = None
_frame_id = 0
_cover = {"key": None, "id": None, "t": 0}


class _Stop(Exception):
    pass


def _stop(_s):
    raise _Stop()


class _Thread:
    """threading.Thread for view.py's /scenario: the page has no threads, so start() hands the scenario to the stepper."""

    def __init__(self, target=None, args=(), daemon=None, **_kw) -> None:
        self.target, self.args = target, args

    def start(self) -> None:
        global _player
        _player = _Player(*self.args)


class _Player:
    """view.play on the page's clock: the same steps, the same locks, the waits taken from wall time between pump iterations."""

    def __init__(self, name, steps) -> None:
        view.PLAYING["name"] = name
        self.steps, self.wait_until = iter(steps), None

    def tick(self) -> None:
        while view.PLAYING["name"]:
            if self.wait_until is not None:
                if time.monotonic() < self.wait_until:
                    return
                self.wait_until = None
            step = next(self.steps, None)
            if step is None:
                view.PLAYING["name"] = None
                return
            if step[0] == "advance":
                self.wait_until = time.monotonic() + step[1] / 1000
                continue
            with view.LOCK:
                if step[0] == "call":
                    view.note_dance(step[1], step[2], view.UNIT.call(step[1], step[2]))
                elif step[0] == "raw":
                    view.UNIT.raw(step[1])
                elif step[0] == "touch":
                    view.UNIT.touch(*step[1:])
                elif step[0] == "hw":
                    view.HW.set(step[1], step[2], view.UNIT.now_ms)
                    view.sync_motion()


def init(live: bool = True) -> dict:
    """Load view.py, take a renderer, make the unit. live=True answers snapshots with nothing (the page reads the screen's frame buffer) so a pump iteration stays cheap."""
    global view
    spec = importlib.util.spec_from_file_location("view", VU / "view.py")
    view = importlib.util.module_from_spec(spec)
    sys.modules["view"] = view
    spec.loader.exec_module(view)
    view.threading = types.SimpleNamespace(Thread=_Thread, Lock=view.threading.Lock)
    view.cover_frame = _cover_frame
    view.UNIT = view.vunit.VirtualUnit(profile="screens").__enter__()
    if live:
        view.UNIT.snapshot = lambda: b""
    view.motion_state()
    view.FRAME = b"" if live else view.UNIT.snapshot()
    return {"tools": len(view.UNIT.tool_names)}


def _cover_frame(text, ring, glyph, elapsed_ms):
    """One frame of a boot cover from one running cover renderer: started on the first frame of a cover, advanced by the time since the last frame."""
    key = (text, ring, glyph)
    b = wasm_shim.BRIDGE
    if _cover["key"] != key or elapsed_ms < _cover["t"]:
        if _cover["id"] is not None:
            b.release(_cover["id"])
        _cover["id"] = b.take("cover")
        b.cmd(_cover["id"], f"show {ring} {glyph} {text}")
        _cover["t"] = 0
        _cover["key"] = key
    cid = _cover["id"]
    b.cmd(cid, f"advance {max(0, elapsed_ms - _cover['t'])}")
    _cover["t"] = elapsed_ms
    leds = []
    for line in b.cmd(cid, "ring").split("\n"):
        if line.startswith("ring "):
            leds = [[int(v) for v in line.split()[1:4]]] * 12
    b.cmd(cid, "snap /c.png")
    png = bytes(b.file(cid, "/c.png").to_py())
    b.drop(cid, "/c.png")
    return png, leds


def tick() -> dict:
    """One pump iteration (50 ms of the unit's clock times the time scale) and one step of the scenario player. Returns what the page needs next."""
    global _last_frame, _frame_id
    real = view.time
    view.time = types.SimpleNamespace(monotonic=real.monotonic, sleep=_stop)
    try:
        view.pump()
    except _Stop:
        pass
    finally:
        view.time = real
    if _player is not None:
        _player.tick()
    if view.FRAME is not _last_frame:
        _last_frame = view.FRAME
        _frame_id += 1
    return {"frame_id": _frame_id, "png": len(view.FRAME) > 0, "playing": view.PLAYING["name"]}


def frame_png() -> bytes:
    return view.FRAME


def handle(method: str, path: str, body: str = "") -> str:
    """One request, answered by view.py's Handler. Returns JSON {code, type, body}: text bodies as they are, binary ones base64 in body_b64."""
    h = view.Handler.__new__(view.Handler)
    raw = body.encode()
    h.path, h.command, h.request_version, h.requestline = path, method, "HTTP/1.1", f"{method} {path} HTTP/1.1"
    h.client_address, h.server, h.close_connection = ("127.0.0.1", 0), None, True
    h.rfile, h.wfile = io.BytesIO(raw), io.BytesIO()
    h.headers = {"Content-Length": str(len(raw))}
    getattr(h, "do_" + method)()
    head, _, payload = h.wfile.getvalue().partition(b"\r\n\r\n")
    lines = head.decode().split("\r\n")
    code = int(lines[0].split()[1])
    ctype = next((l.split(":", 1)[1].strip() for l in lines if l.lower().startswith("content-type")), "")
    out = {"code": code, "type": ctype}
    if ctype.startswith(("application/json", "text/")):
        out["body"] = payload.decode()
    else:
        out["body_b64"] = base64.b64encode(payload).decode()
    return json.dumps(out)
