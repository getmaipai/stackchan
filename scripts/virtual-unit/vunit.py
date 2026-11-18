#!/usr/bin/env python3
"""Headless virtual StackChan unit: the real LVGL face (scripts/fw-face-render) behind the unit's MCP tool protocol.
Usage as a library:  with VirtualUnit() as u: u.call("self.face.bench_emotion", {"emotion": "happy"}); u.advance(1200); png = u.snapshot()
Usage as a process:  vunit.py serve   (JSON lines on stdin and stdout: initialize, tools/list, tools/call, sim/advance, sim/touch, sim/snapshot)
Fake clock: time moves only when advance() is called. Scripted touch: touch(x, y, ms) is logged and fed to the tool layer.
Tools not simulated answer isError with the reason, so a caller sees a gap instead of a silent pass.
Renderer: MAIPAI_VUNIT_RENDER=<path to render binary> (default .runs/vu-build/render, built by build.sh from a firmware tree).
Placement: host-side development tool; no firmware change. Upstream: none."""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EMOTIONS = {"neutral", "happy", "sad", "angry", "doubt", "surprised", "sleepy", "tired", "closing", "sleeping", "love", "content", "thinking"}
ALIASES = {"doubtful": "doubt"}


# Tools with real behavior here. The parity suite (host/tests/test_virtual_unit_parity.py) expects every other firmware tool to be a known gap;
# when you simulate one, add it here and the suite tells you to drop its gap entry.
SIMULATED = {"self.face.bench_emotion", "self.face.bench_speak", "self.face.snapshot", "self.screen.bench_touch"}
JSON_TYPES = {"string": str, "integer": int, "boolean": bool}


class RendererMissing(RuntimeError):
    pass


class VirtualUnit:
    def __init__(self, render: str | None = None) -> None:
        self.render = Path(render or os.environ.get("MAIPAI_VUNIT_RENDER") or ROOT / ".runs" / "vu-build" / "render")
        schema = json.loads((ROOT / "schema" / "tools.json").read_text())
        self.tool_names = sorted(schema["tools"])
        self.tool_args: dict[str, dict[str, str]] = schema.get("arguments", {})
        self.now_ms = 0
        self.touches: list[tuple[int, int, int, int]] = []  # (at_ms, x, y, duration_ms)
        self.calls: list[tuple[str, dict]] = []
        self.emotion = "neutral"
        self._speak_until = 0
        self._proc: subprocess.Popen | None = None
        self._tmp = tempfile.TemporaryDirectory(prefix="vunit-")

    def __enter__(self) -> "VirtualUnit":
        if not self.render.exists():
            raise RendererMissing(f"no renderer at {self.render}: build it with MAIPAI_FW_TREE=<firmware tree> bash scripts/fw-face-render/build.sh {ROOT}/.runs/vu-build")
        self._proc = subprocess.Popen([str(self.render)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self._send("emotion neutral")
        self.advance(1500)
        return self

    def __exit__(self, *exc) -> None:
        if self._proc:
            self._proc.stdin.close()
            self._proc.wait(timeout=10)
        self._tmp.cleanup()

    def _send(self, line: str) -> None:
        self._proc.stdin.write(line + "\n")
        self._proc.stdin.flush()

    def _sync(self) -> str:
        self._send("count 0 0 1 1")  # the renderer answers on stdout: a barrier after earlier commands
        return self._proc.stdout.readline().strip()

    def advance(self, ms: int) -> None:
        """Move the fake clock; the face animates for that long."""
        end = self.now_ms + ms
        if self._speak_until and self._speak_until <= end:
            self._send(f"advance {max(0, self._speak_until - self.now_ms)}")
            self._send("speak 0")
            self._send(f"advance {end - self._speak_until}")
            self._speak_until = 0
        else:
            self._send(f"advance {ms}")
        self.now_ms = end

    def snapshot(self) -> bytes:
        """The 320x240 screen as PNG bytes, as LVGL drew it."""
        path = Path(self._tmp.name) / "snap.png"
        self._send(f"snap {path}")
        self._sync()
        return path.read_bytes()

    def count(self, x0: int, y0: int, x1: int, y1: int) -> dict:
        self._send(f"count {x0} {y0} {x1} {y1}")
        parts = self._proc.stdout.readline().split()
        return {"lit": int(parts[1]), "bbox": tuple(int(p) for p in parts[3:7])}

    def touch(self, x: int, y: int, ms: int = 200) -> None:
        self.touches.append((self.now_ms, x, y, ms))
        self.advance(ms)

    def call(self, name: str, args: dict | None = None) -> dict:
        args = args or {}
        self.calls.append((name, dict(args)))
        if name not in self.tool_names:
            return {"isError": True, "text": f"unknown tool {name}: it is not in schema/tools.json"}
        for key, value in args.items():
            kind = self.tool_args.get(name, {}).get(key)
            if kind is None and self.tool_args.get(name):
                return {"isError": True, "text": f"{name} has no argument {key}: it takes {sorted(self.tool_args[name])}"}
            if kind and not isinstance(value, JSON_TYPES[kind]):
                return {"isError": True, "text": f"{name} argument {key} must be {kind}"}
        if name == "self.face.bench_emotion":
            emo = ALIASES.get(str(args.get("emotion", "neutral")), str(args.get("emotion", "neutral")))
            if emo not in EMOTIONS:
                return {"isError": True, "text": f"unknown emotion {emo}: use one of {sorted(EMOTIONS)}"}
            self.emotion = emo
            self._send(f"emotion {emo}")
            return {"ok": True}
        if name == "self.face.bench_speak":
            level, seconds = int(args.get("level", 60)), int(args.get("seconds", 8))
            self._send(f"speak {level}")
            self._speak_until = self.now_ms + seconds * 1000
            return {"ok": True}
        if name == "self.face.snapshot":
            return {"ok": True, "png_base64": base64.b64encode(self.snapshot()).decode()}
        if name == "self.screen.bench_touch":
            self.touch(160, 4, 200)
            return {"ok": True}
        return {"isError": True, "text": f"{name} is not simulated yet; the tool exists in the firmware, the virtual unit has no behavior for it"}

    def tools_list(self) -> list[dict]:
        return [{"name": n, "inputSchema": {"type": "object", "properties": {k: {"type": t} for k, t in self.tool_args.get(n, {}).items()}}} for n in self.tool_names]


def serve() -> int:
    with VirtualUnit() as u:
        for line in sys.stdin:
            req = json.loads(line)
            method, params, rid = req.get("method"), req.get("params", {}), req.get("id")
            if method == "initialize":
                result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": "StackChan", "version": "virtual"}}
            elif method == "tools/list":
                result = {"tools": u.tools_list()}
            elif method == "tools/call":
                out = u.call(params.get("name", ""), params.get("arguments", {}))
                result = {"content": [{"type": "text", "text": json.dumps(out)}], **({"isError": True} if out.get("isError") else {})}
            elif method == "sim/advance":
                u.advance(int(params["ms"])); result = {"now_ms": u.now_ms}
            elif method == "sim/touch":
                u.touch(int(params["x"]), int(params["y"]), int(params.get("ms", 200))); result = {"now_ms": u.now_ms}
            elif method == "sim/snapshot":
                result = {"png_base64": base64.b64encode(u.snapshot()).decode()}
            else:
                print(json.dumps({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"unknown method {method}"}}), flush=True)
                continue
            print(json.dumps({"jsonrpc": "2.0", "id": rid, "result": result}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(serve() if sys.argv[1:] == ["serve"] else print(__doc__) or 0)
