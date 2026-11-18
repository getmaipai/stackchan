#!/usr/bin/env python3
"""Browser view of the virtual unit: the unit's real LVGL screen on a 3D head, with touch, a tool panel and scripted scenarios.
Usage: view.py [port]  then open http://127.0.0.1:PORT/   (the screens renderer is used when built, else the bare face: no touch then)
Click the screen to tap, drag across it to swipe; the side panel calls any tool by name, shows the call log and plays scenarios in real time.
The server runs the fake clock at real speed (20 frames a second) and serves /frame.png, POST /call and /state.
The head follows self.robot.set_head_angles on the fake clock and the 12 ring lights show self.robot.set_led_colors.
Dev tool, loopback only. The page loads three.js (pinned) from cdnjs for the 3D drawing; nothing from the unit leaves this Mac.
Placement: host-side development tool; no firmware change. Upstream: none."""
import importlib.util
import json
import re
import struct
import subprocess
import sys
import tempfile
import threading
import time
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("vunit", HERE / "vunit.py")
vunit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vunit)

SCEN = importlib.util.spec_from_file_location("scenarios", HERE / "scenarios.py")
scenarios = importlib.util.module_from_spec(SCEN)
SCEN.loader.exec_module(scenarios)
HWSPEC = importlib.util.spec_from_file_location("hw", HERE / "hw.py")
hw = importlib.util.module_from_spec(HWSPEC)
HWSPEC.loader.exec_module(hw)
HW = hw.Hardware()
PHYS = HERE / "physics"
_ms = importlib.util.spec_from_file_location("mjcf", PHYS / "mjcf.py")
mjcf = importlib.util.module_from_spec(_ms)
_ms.loader.exec_module(mjcf)
_is = importlib.util.spec_from_file_location("imu", PHYS / "imu.py")
imu = importlib.util.module_from_spec(_is)
_is.loader.exec_module(imu)
PICKUP = imu.PickupRule()
PHYSICS = {"driven": False, "imu": None}
PLAYING = {"name": None}
STEP_MS = 50  # the fake clock and the screen advance 20 times a second, the rate of the dances' light shows
COVER_RENDER = HERE.parents[1] / ".runs" / "vu-screens" / "cover" / "cover_render"
APPLIED = {"status": None, "tired": 0, "cover_ring": []}


def _png(w, h, rgb=(0, 0, 0)):
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))
    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


BLACK = _png(320, 240)


def cover_frame(text, ring, glyph, elapsed_ms):
    """One frame of a boot cover, drawn by the unit's own cover code (a fresh run replayed to elapsed_ms; the cover renderer is a separate program)."""
    if not COVER_RENDER.exists():
        return None, []
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "c.png"
        script = f"show {ring} {glyph} {text}\nadvance {max(0, elapsed_ms)}\nring\nsnap {out}\n"
        done = subprocess.run([str(COVER_RENDER)], input=script, text=True, capture_output=True, timeout=20)
        leds = []
        for line in done.stdout.splitlines():
            if line.startswith("ring "):
                leds = [[int(v) for v in line.split()[1:4]]] * 12
        return (out.read_bytes() if out.exists() else None), leds

REC_DIR = HERE / "recordings"
REC = {"on": False, "t0": 0, "last": 0, "steps": []}  # a recording of what a person did: waits, touches and tool calls


def rec_step(kind, data):
    """While recording, keep one step with the wait since the previous one (fake clock milliseconds)."""
    if REC["on"]:
        REC["steps"].append({"wait_ms": UNIT.now_ms - REC["last"], kind: data})
        REC["last"] = UNIT.now_ms


def recordings():
    return sorted(p.stem for p in REC_DIR.glob("*.json")) if REC_DIR.exists() else []
LOCK = threading.Lock()
UNIT = None
FRAME = b""


def apply_body():
    """Send what the body implies to the renderer and the tools: status bar fields, the tired look on a low battery, the motion limiter inputs."""
    if UNIT.profile == "screens" and HW.on and HW.boot_started is None:
        args = HW.status_args()
        if APPLIED["status"] != args:
            UNIT.raw("bstatus " + " ".join(str(a) for a in args))
            APPLIED["status"] = args
    if HW.on and HW.boot_started is None and APPLIED["tired"] != HW.tired_level():
        APPLIED["tired"] = HW.tired_level()
        if HW.tired_level():
            UNIT.call("self.face.bench_emotion", {"emotion": "tired", "tired_level": HW.tired_level()})
        else:
            UNIT.call("self.face.bench_emotion", {"emotion": "neutral"})
    sync_motion()


def sync_motion():
    """The unit's own limiter (patch ML01) answers for this body: carried, USB, battery and orientation are its inputs."""
    UNIT.battery.update(percent=HW.battery, charging=HW.charging)
    carried, usb, level, orient = HW.motion_force()
    hw_force = UNIT.state["motion"].get("force")
    if hw_force != [carried, usb, level, orient]:
        UNIT.call("self.motion.force", {"carried": carried, "usb": usb, "level": level, "orient": orient})


def head_now():
    """The head including a running dance, kept inside the servo ranges."""
    base = UNIT.head()
    yaw, pitch = float(base["yaw"]), float(base["pitch"])
    if HW.on and HW.dance:
        lim = motion_state()
        dy, dp = hw.dance_offset(HW.dance, UNIT.now_ms - HW.dance_started, lim.get("scale", 100), lim.get("speed_cap", 1000))
        yaw, pitch = yaw + dy, pitch + dp
    yaw = max(vunit.YAW_RANGE[0], min(vunit.YAW_RANGE[1], yaw))
    pitch = max(vunit.PITCH_RANGE[0], min(vunit.PITCH_RANGE[1], pitch))
    return {"yaw": round(yaw, 1), "pitch": round(pitch, 1)}


DANCE = {"name": ""}  # the dance last asked for by name: the unit's dance session keeps the beat, not the name


def note_dance(name, args, out):
    if name == "self.robot.dance" and out.get("ok"):
        DANCE["name"] = str(args.get("name", "happy"))
    elif name == "self.robot.stop_dance":
        DANCE["name"] = ""


def dance_now():
    """(name of the dance running now or "", the dance simulation's own status or None). A dance runs either as the old keyframe
    shape (HW.dance) or as a session of the unit's dance simulation (dance_sim.py), which moves the head, the eyes and the lights itself."""
    sim = UNIT.dance.status() if getattr(UNIT, "_dance", None) is not None else None
    if HW.dance:
        return HW.dance, sim
    live = bool(sim and HW.on and (sim["running"] or UNIT.dance.session))
    if not live:
        DANCE["name"] = ""
    return (DANCE["name"] or (sim["step_name"] if live else "")) if live else "", sim


def motion_state():
    return vunit._tools.REGISTRY["self.motion.status"](UNIT, {})


def pump():
    global FRAME
    while True:
        began = time.monotonic()
        with LOCK:
            UNIT.advance(STEP_MS)
            was_dancing = HW.dance
            HW.tick(UNIT.now_ms)
            if was_dancing and not HW.dance:
                UNIT.state["motion"]["dance"] = ""  # the dance ended or the unit went off
            if HW.dance and motion_state()["state"] == "carried":
                UNIT.state["motion"]["dance"] = ""  # held or on its side: the limiter allows no movement, so a dance ends (patch ML01)
                HW.dance = ""
            if HW.dance and not UNIT.state.get("motion", {}).get("dance"):
                HW.dance = ""  # self.robot.stop_dance
            elif not HW.dance and UNIT.state.get("motion", {}).get("dance") and HW.on:
                HW.dance, HW.dance_started = UNIT.state["motion"]["dance"], UNIT.now_ms
            if not HW.on:
                UNIT.state["motion"]["dance"] = ""
                FRAME = BLACK
                APPLIED["status"] = None
                APPLIED["tired"] = 0
            else:
                cover = HW.boot_cover(UNIT.now_ms)
                if cover is not None:
                    png, leds = cover_frame(*cover)
                    FRAME = png or BLACK
                    APPLIED["cover_ring"] = leds
                else:
                    APPLIED["cover_ring"] = []
                    apply_body()
                    FRAME = UNIT.snapshot()
        time.sleep(max(0.0, STEP_MS / 1000 - (time.monotonic() - began)))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body: bytes, ctype: str, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.path = self.path.split("?")[0]
        if self.path == "/frame.png":
            self._send(FRAME, "image/png")
        elif self.path == "/state":
            with LOCK:
                mot = motion_state()
                recent = [t for t in UNIT.move_times if UNIT.now_ms - t < 60000]
                state = {"now_ms": UNIT.now_ms, "emotion": UNIT.emotion, "tools": len(UNIT.tool_names), "head": head_now(), "leds": APPLIED["cover_ring"] or UNIT.leds,
                         "battery": UNIT.battery, "hw": HW.view(), "motion": mot, "moves_last_minute": len(recent), "moves_cap": vunit.MOVES_PER_MINUTE,
                         "dance": dance_now()[0], "dance_sim": dance_now()[1], "physics": PHYSICS, "yaw_range": vunit.YAW_RANGE, "pitch_range": vunit.PITCH_RANGE, "pitch_safe": [5, 85]}
            self._send(json.dumps(state).encode(), "application/json")
        elif self.path == "/affiliation.json":   # the one place the affiliation wording lives (docs/plan/trademark-and-affiliation.md)
            self._send((HERE.parents[1] / "docs" / "legal" / "affiliation.json").read_bytes(), "application/json")
        elif self.path == "/about":
            words = json.loads((HERE.parents[1] / "docs" / "legal" / "affiliation.json").read_text())
            page = ("<!doctype html><html lang=en><meta charset=utf-8><title>About: " + words["project"] + "</title>"
                    "<body style='font:16px system-ui;max-width:640px;margin:48px auto;padding:0 16px;line-height:1.5'>"
                    "<h1 style='font-size:20px'>" + words["project"] + "</h1><p>" + words["full"] + "</p>"
                    "<p>The 3D model shows the real robot, with its own name and label. Those marks belong to their owners and are not this project's branding. "
                    "A compliance mark drawn on a label is a detail of the original hardware; this software is not certified by anyone.</p>"
                    "<p><a href='/'>Back to the viewer</a></p></body></html>")
            self._send(page.encode(), "text/html; charset=utf-8")
        elif self.path == "/tools":
            tools = [{"name": n, "args": UNIT.tool_args.get(n, {}), "user_only": n in UNIT.user_only} for n in UNIT.tool_names]
            self._send(json.dumps({"tools": tools, "touch": UNIT.profile == "screens"}).encode(), "application/json")
        elif self.path == "/log":
            self._send(json.dumps({"log": UNIT.log[-60:], "playing": PLAYING["name"]}).encode(), "application/json")
        elif self.path == "/scenarios":
            names = [n for n in list(scenarios.SCENARIOS) + list(scenarios.SCREENS) if UNIT.profile == "screens" or n in scenarios.SCENARIOS]
            names += list(scenarios.PORTS) + [f"rec:{n}" for n in recordings()]
            self._send(json.dumps({"scenarios": names}).encode(), "application/json")
        elif self.path == "/physics/model.xml":
            self._send(mjcf.mjcf(mjcf.load()).encode(), "application/xml")
        elif self.path == "/physics/robot.json":
            self._send((PHYS / "robots" / "stackchan.robot.json").read_bytes(), "application/json")
        elif self.path == "/physics/engine.json":
            self._send((PHYS / "THIRD-PARTY-physics-engine.json").read_bytes(), "application/json")
        elif self.path == "/physics.js":
            self._send((PHYS / "physics.js").read_bytes(), "text/javascript; charset=utf-8")
        elif self.path == "/view3d.js":
            self._send((HERE / "view3d.js").read_bytes(), "text/javascript; charset=utf-8")
        elif self.path == "/model/stackchan.glb":  # the rigged body model the 3D drawing loads (built by model/make_body.py)
            self._send((HERE / "model" / "stackchan.glb").read_bytes(), "model/gltf-binary")
        elif self.path == "/":
            self._send((HERE / "view.html").read_bytes(), "text/html; charset=utf-8")
        else:
            self._send(b"not found: this view serves / and /frame.png", "text/plain", 404)

    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if self.path == "/record":
            return self._send(json.dumps(record_action(req)).encode(), "application/json")
        if self.path == "/hw":
            with LOCK:
                refused = HW.set(req.get("key", ""), req.get("value"), UNIT.now_ms)
                if req.get("key") in ("power", "reset") and refused is None and HW.on:
                    APPLIED["status"] = None
                sync_motion()
            return self._send(json.dumps({"isError": True, "text": refused} if refused else {"ok": True, "hw": HW.view()}).encode(), "application/json")
        if self.path == "/imu":
            with LOCK:  # the physics model's accelerometer and tilt feed the same carried and orientation rule as the unit's pickup detector
                carried, orient = PICKUP.feed(UNIT.now_ms, tuple(req["accel"]), float(req["tilt_deg"]))
                PHYSICS.update(driven=True, imu={"accel": req["accel"], "tilt_deg": req["tilt_deg"], "carried": carried, "orient": orient})
                HW.carried, HW.orient = carried, orient
                sync_motion()
            return self._send(json.dumps({"ok": True, "carried": carried, "orient": orient}).encode(), "application/json")
        if self.path == "/imu/off":
            with LOCK:
                PHYSICS.update(driven=False, imu=None)
            return self._send(b'{"ok": true}', "application/json")
        if self.path in ("/call", "/touch", "/scenario") and not HW.on:
            return self._send(json.dumps({"isError": True, "text": "The unit is off. Press its power button (or the Power button in the panel)."}).encode(), "application/json")
        if self.path == "/call":
            with LOCK:
                out = UNIT.call(req.get("name", ""), req.get("arguments", {}))
                note_dance(req.get("name", ""), req.get("arguments", {}), out)
                rec_step("call", {"name": req.get("name", ""), "arguments": req.get("arguments", {})})
            out.pop("png_base64", None)
            return self._send(json.dumps(out).encode(), "application/json")
        if self.path == "/touch":
            if UNIT.profile != "screens":
                return self._send(json.dumps({"isError": True, "text": "touch needs the screens renderer: run bash scripts/virtual-unit/build-screens.sh"}).encode(), "application/json")
            with LOCK:
                if req.get("kind") == "head":
                    said = UNIT.head_touch(int(req.get("zone", 1)))
                    rec_step("touch", {"kind": "head", "zone": int(req.get("zone", 1))})
                elif req.get("kind") == "swipe":
                    said = UNIT.swipe(int(req["x"]), int(req["y"]), int(req["x2"]), int(req["y2"]), int(req.get("ms", 250)))
                    rec_step("touch", {"kind": "swipe", "x": int(req["x"]), "y": int(req["y"]), "x2": int(req["x2"]), "y2": int(req["y2"]), "ms": int(req.get("ms", 250))})
                else:
                    said = UNIT.tap(int(req["x"]), int(req["y"]))
                    rec_step("touch", {"kind": "tap", "x": int(req["x"]), "y": int(req["y"])})
            return self._send(json.dumps({"ok": True, "renderer": said}).encode(), "application/json")
        if self.path == "/scenario":
            name = req.get("name", "")
            steps = scenarios.SCENARIOS.get(name) or scenarios.SCREENS.get(name) or scenarios.PORTS.get(name, {}).get("steps")
            if steps is None and name.startswith("rec:") and (REC_DIR / f"{name[4:]}.json").exists():
                steps = scenarios.load_recording(REC_DIR / f"{name[4:]}.json")
            if steps is None or PLAYING["name"]:
                return self._send(json.dumps({"isError": True, "text": "unknown scenario, or one is already playing: wait for it to end"}).encode(), "application/json")
            threading.Thread(target=play, args=(name, steps), daemon=True).start()
            return self._send(json.dumps({"ok": True, "playing": name}).encode(), "application/json")
        self._send(b"not found: POST /call, /touch or /scenario", "text/plain", 404)


def record_action(req):
    """POST /record: start, stop (keeps the steps) or save (writes scripts/virtual-unit/recordings/NAME.json, replayable by Play and by scenarios.py)."""
    action = req.get("action")
    with LOCK:
        if action == "start":
            REC.update(on=True, t0=UNIT.now_ms, last=UNIT.now_ms, steps=[])
            return {"ok": True, "recording": True}
        if action == "stop":
            REC["on"] = False
            return {"ok": True, "recording": False, "steps": len(REC["steps"])}
        if action == "save":
            name = re.sub(r"[^A-Za-z0-9_-]", "-", str(req.get("name") or "recording")).strip("-")[:40] or "recording"
            if not REC["steps"]:
                return {"isError": True, "text": "Nothing is recorded yet: press Record, use the robot, then Save."}
            REC_DIR.mkdir(exist_ok=True)
            (REC_DIR / f"{name}.json").write_text(json.dumps({"version": 1, "name": name, "steps": REC["steps"]}, indent=1) + "\n")
            return {"ok": True, "saved": name, "steps": len(REC["steps"])}
    return {"isError": True, "text": "action must be start, stop or save"}


def play(name, steps):
    """A scenario in real time: calls and renderer commands at once, waits as long as the scenario says (the clock runs on the pump)."""
    PLAYING["name"] = name
    try:
        for step in steps:
            if step[0] == "advance":
                time.sleep(step[1] / 1000)
                continue
            with LOCK:
                if step[0] == "call":
                    note_dance(step[1], step[2], UNIT.call(step[1], step[2]))
                elif step[0] == "raw":
                    UNIT.raw(step[1])
                elif step[0] == "touch":
                    UNIT.touch(*step[1:])
                elif step[0] == "hw":   # the body: a cable, the battery, a hand
                    HW.set(step[1], step[2], UNIT.now_ms)
                    sync_motion()
    finally:
        PLAYING["name"] = None


def main():
    global UNIT, FRAME
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8780
    screens = (HERE.parents[1] / ".runs" / "vu-screens" / "render").exists()
    UNIT = vunit.VirtualUnit(profile="screens" if screens else "face").__enter__()
    motion_state()  # creates the motion tools' defaults before the pump touches them
    FRAME = UNIT.snapshot()
    threading.Thread(target=pump, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"virtual unit view on http://127.0.0.1:{server.server_port}/", flush=True)  # port 0 picks a free one
    server.serve_forever()


if __name__ == "__main__":
    main()
