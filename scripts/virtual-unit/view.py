#!/usr/bin/env python3
"""Browser view of the virtual unit: the unit's real LVGL screen on a 3D head, with touch, a tool panel and scripted scenarios.
Usage: view.py [port]  then open http://127.0.0.1:PORT/   (the screens renderer is used when built, else the bare face: no touch then)
Click the screen to tap, drag across it to swipe; the side panel calls any tool by name, shows the call log and plays scenarios in real time.
The server runs the fake clock at real speed (about 10 frames a second) and serves /frame.png, POST /call and /state.
The head follows self.robot.set_head_angles on the fake clock and the 12 ring lights show self.robot.set_led_colors.
Dev tool, loopback only. The page loads three.js (pinned) from cdnjs for the 3D drawing; nothing from the unit leaves this Mac.
Placement: host-side development tool; no firmware change. Upstream: none."""
import importlib.util
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("vunit", HERE / "vunit.py")
vunit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vunit)

SCEN = importlib.util.spec_from_file_location("scenarios", HERE / "scenarios.py")
scenarios = importlib.util.module_from_spec(SCEN)
SCEN.loader.exec_module(scenarios)
PLAYING = {"name": None}
LOCK = threading.Lock()
UNIT = None
FRAME = b""


def pump():
    global FRAME
    while True:
        with LOCK:
            UNIT.advance(100)
            FRAME = UNIT.snapshot()
        time.sleep(0.1)


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
            self._send(json.dumps({"now_ms": UNIT.now_ms, "emotion": UNIT.emotion, "tools": len(UNIT.tool_names), "head": UNIT.head(), "leds": UNIT.leds, "battery": UNIT.battery}).encode(), "application/json")
        elif self.path == "/tools":
            tools = [{"name": n, "args": UNIT.tool_args.get(n, {}), "user_only": n in UNIT.user_only} for n in UNIT.tool_names]
            self._send(json.dumps({"tools": tools, "touch": UNIT.profile == "screens"}).encode(), "application/json")
        elif self.path == "/log":
            self._send(json.dumps({"log": UNIT.log[-60:], "playing": PLAYING["name"]}).encode(), "application/json")
        elif self.path == "/scenarios":
            names = [n for n in list(scenarios.SCENARIOS) + list(scenarios.SCREENS) if UNIT.profile == "screens" or n in scenarios.SCENARIOS]
            self._send(json.dumps({"scenarios": names}).encode(), "application/json")
        elif self.path == "/":
            self._send((HERE / "view.html").read_bytes(), "text/html; charset=utf-8")
        else:
            self._send(b"not found: this view serves / and /frame.png", "text/plain", 404)

    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if self.path == "/call":
            with LOCK:
                out = UNIT.call(req.get("name", ""), req.get("arguments", {}))
            out.pop("png_base64", None)
            return self._send(json.dumps(out).encode(), "application/json")
        if self.path == "/touch":
            if UNIT.profile != "screens":
                return self._send(json.dumps({"isError": True, "text": "touch needs the screens renderer: run bash scripts/virtual-unit/build-screens.sh"}).encode(), "application/json")
            with LOCK:
                if req.get("kind") == "swipe":
                    said = UNIT.swipe(int(req["x"]), int(req["y"]), int(req["x2"]), int(req["y2"]), int(req.get("ms", 250)))
                else:
                    said = UNIT.tap(int(req["x"]), int(req["y"]))
            return self._send(json.dumps({"ok": True, "renderer": said}).encode(), "application/json")
        if self.path == "/scenario":
            name = req.get("name", "")
            steps = scenarios.SCENARIOS.get(name) or scenarios.SCREENS.get(name)
            if steps is None or PLAYING["name"]:
                return self._send(json.dumps({"isError": True, "text": "unknown scenario, or one is already playing: wait for it to end"}).encode(), "application/json")
            threading.Thread(target=play, args=(name, steps), daemon=True).start()
            return self._send(json.dumps({"ok": True, "playing": name}).encode(), "application/json")
        self._send(b"not found: POST /call, /touch or /scenario", "text/plain", 404)


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
                    UNIT.call(step[1], step[2])
                elif step[0] == "raw":
                    UNIT.raw(step[1])
                elif step[0] == "touch":
                    UNIT.touch(*step[1:])
    finally:
        PLAYING["name"] = None


def main():
    global UNIT, FRAME
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8780
    screens = (HERE.parents[1] / ".runs" / "vu-screens" / "render").exists()
    UNIT = vunit.VirtualUnit(profile="screens" if screens else "face").__enter__()
    FRAME = UNIT.snapshot()
    threading.Thread(target=pump, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"virtual unit view on http://127.0.0.1:{server.server_port}/", flush=True)  # port 0 picks a free one
    server.serve_forever()


if __name__ == "__main__":
    main()
