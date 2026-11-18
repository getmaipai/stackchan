#!/usr/bin/env python3
"""Browser view of the virtual unit: the real LVGL face on a 3D head. Usage: view.py [port]  then open http://127.0.0.1:PORT/
The server runs the fake clock at real speed (about 10 frames a second) and serves /frame.png, POST /call and /state.
Face first: the head turn sliders move the model only; real head motion comes with the motion step.
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
            self._send(json.dumps({"now_ms": UNIT.now_ms, "emotion": UNIT.emotion, "tools": len(UNIT.tool_names)}).encode(), "application/json")
        elif self.path == "/":
            self._send((HERE / "view.html").read_bytes(), "text/html; charset=utf-8")
        else:
            self._send(b"not found: this view serves / and /frame.png", "text/plain", 404)

    def do_POST(self):
        if self.path != "/call":
            return self._send(b"not found: POST /call only", "text/plain", 404)
        req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        with LOCK:
            out = UNIT.call(req.get("name", ""), req.get("arguments", {}))
        out.pop("png_base64", None)
        self._send(json.dumps(out).encode(), "application/json")


def main():
    global UNIT, FRAME
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8780
    UNIT = vunit.VirtualUnit().__enter__()
    FRAME = UNIT.snapshot()
    threading.Thread(target=pump, daemon=True).start()
    print(f"virtual unit view on http://127.0.0.1:{port}/", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
