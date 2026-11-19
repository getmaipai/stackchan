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
import threading
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tools as _tools  # noqa: E402

for _mod in sorted((Path(__file__).resolve().parent / "tools").glob("[a-z]*.py")):
    __import__(f"tools.{_mod.stem}")
EMOTIONS = {"neutral", "happy", "sad", "angry", "doubt", "surprised", "sleepy", "tired", "closing", "sleeping", "love", "content", "thinking"}
ALIASES = {"doubtful": "doubt"}


# Tools with real behavior here. The parity suite (host/tests/test_virtual_unit_parity.py) expects every other firmware tool to be a known gap;
# when you simulate one, add it here and the suite tells you to drop its gap entry.
SIMULATED = {"self.face.bench_emotion", "self.face.bench_speak", "self.face.snapshot", "self.screen.bench_touch",
             "self.robot.get_head_angles", "self.robot.set_head_angles", "self.robot.set_led_colors", "self.battery.get_status", "self.battery.simulate"}
SIMULATED |= {n for n in _tools.REGISTRY if not n.startswith("sim.")}   # sim.* are controls of the rig, not firmware tools (sim.music, dance_sim.py)
YAW_RANGE, PITCH_RANGE, KEEP = (-128, 128), (3, 87), -9999  # the servo limits in hal_servo.cpp (the maker advises 5 to 85)
MOVES_PER_MINUTE = 40  # patch 038
JSON_TYPES = {"string": str, "integer": int, "boolean": bool}


class RendererMissing(RuntimeError):
    pass


READ_TIMEOUT_S = 180.0  # generous: a loaded machine runs four test processes at once


class VirtualUnit:
    def __init__(self, render: str | None = None, profile: str = "face") -> None:
        """profile "face": the bare face renderer; "screens": also the status bar, pages, control sheet and Apps (build-screens.sh)."""
        default = ROOT / ".runs" / ("vu-screens" if profile == "screens" else "vu-build") / "render"
        self.render = Path(render or os.environ.get("MAIPAI_VUNIT_RENDER") or default)
        self.profile = profile
        schema = json.loads((ROOT / "schema" / "tools.json").read_text())
        self.tool_names = sorted(schema["tools"])
        self.tool_args: dict[str, dict[str, str]] = schema.get("arguments", {})
        self.user_only: list[str] = schema.get("user_only", [])
        self.now_ms = 0
        self.output: list[str] = []
        self.log: list[dict] = []  # tool calls and touches with the fake time, newest last
        self.state: dict = {}  # per group state for tools/*.py handlers
        self.touches: list[tuple[int, int, int, int]] = []  # (at_ms, x, y, duration_ms)
        self.calls: list[tuple[str, dict]] = []
        self.emotion = "neutral"
        self._speak_until = 0
        self.yaw0 = self.pitch0 = 0.0
        self.yaw1 = self.pitch1 = 0.0
        self.move_start_ms = 0
        self.move_ms = 0
        self.move_times: list[int] = []
        self.tickers: list = []  # called with the fake clock after every slice of at most 66 ms (two renderer frames) of advance (the music dance, patch MD01, dance_sim.py)
        self._dance = None
        self._memory = None
        self.leds = [(0, 0, 0)] * 12
        self.battery = {"percent": 75, "charging": False}
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

    def _read_until(self, prefix: str) -> str:
        """The renderer prints a line for some commands (pshow, pstate): skip them and keep them in self.output."""
        # A renderer built from older sources can wait for a command it does not know and never answer: a watchdog kills it after READ_TIMEOUT_S
        # so the test fails with a clear message instead of hanging the whole suite.
        watchdog = threading.Timer(READ_TIMEOUT_S, self._proc.kill)
        watchdog.daemon = True
        watchdog.start()
        try:
            while True:
                line = self._proc.stdout.readline()
                if not line:
                    raise RuntimeError(f"the renderer stopped or did not answer in {READ_TIMEOUT_S:.0f} s: rebuild it (scripts/virtual-unit/build-screens.sh) and run again")
                if line.startswith(prefix):
                    return line.strip()
                self.output.append(line.strip())
        finally:
            watchdog.cancel()

    def _sync(self) -> str:
        self._send("count 0 0 1 1")  # the renderer answers on stdout: a barrier after earlier commands
        return self._read_until("count")

    def raw(self, command: str) -> None:
        """One renderer command (screens profile: pshow, bstatus, bst, bwifiscreen, ...). A bench aid, not a firmware tool."""
        self._send(command)
        if self._memory is not None:
            self._memory.on_raw(command)
        self.log.append({"at_ms": self.now_ms, "name": "renderer", "args": {"command": command}, "ok": True, "result": {}})

    @property
    def assets(self):
        """The installed set (assets_sim.py): slots per kind, the pool, signed installs, swap and remove. Made on first use."""
        if getattr(self, "_assets", None) is None:
            import assets_sim

            self._assets = assets_sim.AssetStore(self)
        return self._assets

    @property
    def host_away(self):
        """What the unit does while its host is away (host_away.py: the Offline label after 45 s, the notice after 10 minutes, the reconnect backoff). Made on first use."""
        if getattr(self, "_host_away", None) is None:
            import host_away

            self._host_away = host_away.HostAway(self)
        return self._host_away

    @property
    def memory(self):
        """The memory model (memory_model.py, decision 15): declared costs from schema/memory-budget.json, what is loaded now, the budget check and the leak canary. Made on first use;
        from then on every renderer command and tool call reports to it."""
        if self._memory is None:
            import memory_model

            self._memory = memory_model.MemoryModel(self)
            self.tickers.append(self._memory.sweep)
        return self._memory

    @property
    def dance(self):
        """The music dance and keyframe dance simulation (dance_sim.py), made on first use."""
        if self._dance is None:
            import dance_sim

            self._dance = dance_sim.DanceSim(self)
        return self._dance

    def move_head(self, yaw: float, pitch: float, speed: int) -> None:
        """A head move the unit's own modifiers make (stackchan.motion().moveWithSpeed): no 40 a minute tool limit (patch 038 guards the tool), the limiter's excursion and speed cap still apply."""
        lim = _tools.REGISTRY["self.motion.status"](self, {})
        if lim["state"] == "carried":
            return
        cur = self.head()
        yaw1 = max(YAW_RANGE[0], min(YAW_RANGE[1], yaw))
        pitch1 = max(PITCH_RANGE[0], min(PITCH_RANGE[1], pitch))
        if lim["scale"] < 100:
            yaw1, pitch1 = yaw1 * lim["scale"] / 100, pitch1 * lim["scale"] / 100
        speed = max(1, min(lim["speed_cap"] or 1000, 1000, int(speed)))
        self.yaw0, self.pitch0, self.yaw1, self.pitch1 = cur["yaw"], cur["pitch"], yaw1, pitch1
        self.move_start_ms = self.now_ms
        self.move_ms = int(1000 * max(abs(yaw1 - cur["yaw"]), abs(pitch1 - cur["pitch"])) / (speed * 0.4)) if speed else 0

    def advance(self, ms: int) -> None:
        """Move the fake clock; the face animates for that long. With tickers (the music dance) the time goes in slices of at most 66 ms and each ticker runs after every slice."""
        if self.tickers and ms > 66:
            left = ms
            while left > 0:
                step = min(66, left)
                self._advance(step)
                for t in list(self.tickers):
                    t(self.now_ms)
                left -= step
            return
        self._advance(ms)
        for t in list(self.tickers):
            t(self.now_ms)

    def _advance(self, ms: int) -> None:
        end = self.now_ms + ms
        if self._speak_until and self._speak_until <= end:
            self._send(f"advance {max(0, self._speak_until - self.now_ms)}")
            self._send("speak 0")
            self._send(f"advance {end - self._speak_until}")
            self._speak_until = 0
        else:
            self._send(f"advance {ms}")
        self.now_ms = end

    def jump(self, ms: int) -> None:
        """A unit that has been left on for a long time: the fake clock (the renderer's tick and the tools' time) jumps ahead by `ms` at once, with no frames between.
        Timers due in between are due on the next advance; the renderer's 32 bit tick wraps at 2^32 ms (49.7 days) as the unit's does."""
        self._send(f"clock {self.now_ms + ms}")
        self.now_ms += ms

    def head(self) -> dict:
        """Head angles now, moving at `speed` degrees per second (the unit of speed is an assumption, as in the old simulated unit)."""
        f = 1.0 if self.move_ms <= 0 else min(1.0, max(0.0, (self.now_ms - self.move_start_ms) / self.move_ms))
        return {"yaw": round(self.yaw0 + (self.yaw1 - self.yaw0) * f), "pitch": round(self.pitch0 + (self.pitch1 - self.pitch0) * f)}

    def snapshot(self) -> bytes:
        """The 320x240 screen as PNG bytes, as LVGL drew it."""
        path = Path(self._tmp.name) / "snap.png"
        self._send(f"snap {path}")
        self._sync()
        return path.read_bytes()

    def snapshot_now(self) -> bytes:
        """The screen as it is now: no frame runs and no time passes (snapshot() runs two frames, 66 ms)."""
        path = Path(self._tmp.name) / "snapnow.png"
        self._send(f"snapnow {path}")
        self._read_until("snapnow")
        return path.read_bytes()

    def count(self, x0: int, y0: int, x1: int, y1: int) -> dict:
        self._send(f"count {x0} {y0} {x1} {y1}")
        parts = self._read_until("count").split()
        return {"lit": int(parts[1]), "bbox": tuple(int(p) for p in parts[3:7])}

    def touch(self, x: int, y: int, ms: int = 200) -> None:
        self.touches.append((self.now_ms, x, y, ms))
        self.advance(ms)

    def call(self, name: str, args: dict | None = None) -> dict:
        """Run a tool by name (user-only tools included) and keep it in the log with the fake time."""
        out = self._call(name, args)
        if self._memory is not None:
            self._memory.on_call(name, dict(args or {}), out)
        self.log.append({"at_ms": self.now_ms, "name": name, "args": dict(args or {}), "ok": not out.get("isError") and out.get("ok") is not False,
                         "result": {k: v for k, v in out.items() if k != "png_base64"}})
        del self.log[:-200]
        return out

    def tap(self, x: int, y: int) -> str:
        """A finger tap at panel x, y on the clickable object under it (screens profile). Returns what the renderer said."""
        mark = len(self.output)
        self._send(f"pclick {x} {y}")
        self._sync()
        said = " ".join(self.output[mark:]) or "no output"
        self.log.append({"at_ms": self.now_ms, "name": "touch.tap", "args": {"x": x, "y": y}, "ok": True, "result": {"renderer": said}})
        return said

    def head_touch(self, zone: int = 1) -> str:
        """A touch on the head strip (zone 0 front, 1 middle, 2 back): the unit's head tap event, which brings the face back from a page."""
        zone = max(0, min(2, int(zone)))
        self._send("pevent head")
        self._sync()
        self.log.append({"at_ms": self.now_ms, "name": "touch.head", "args": {"zone": zone}, "ok": True, "result": {"event": "head tap"}})
        return "head tap"

    def swipe(self, x0: int, y0: int, x1: int, y1: int, ms: int = 250) -> str:
        """A one-finger drag through the unit's gesture code (screens profile)."""
        mark = len(self.output)
        self._send(f"pswipe {x0} {y0} {x1} {y1} {ms}")
        self._sync()
        said = " ".join(self.output[mark:]) or "no output"
        self.log.append({"at_ms": self.now_ms, "name": "touch.swipe", "args": {"from": [x0, y0], "to": [x1, y1], "ms": ms}, "ok": True, "result": {"renderer": said}})
        return said

    def _call(self, name: str, args: dict | None = None) -> dict:
        args = args or {}
        self.calls.append((name, dict(args)))
        if name.startswith("sim.") and name in _tools.REGISTRY:   # virtual only controls of the rig (not firmware tools): sim.music
            return _tools.REGISTRY[name](self, args)
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
        if name in _tools.REGISTRY:
            result = _tools.REGISTRY[name](self, args)
            return result if isinstance(result, dict) else ({"ok": result} if isinstance(result, bool) else {"result": result})  # a bare bool or a JSON array
        if name == "self.robot.get_head_angles":
            return self.head()
        if name == "self.robot.set_head_angles":
            lim = _tools.REGISTRY["self.motion.status"](self, {})  # the unit's own limiter (patch ML01) for this body: carried, USB, battery, orientation
            if lim["state"] == "carried":
                return {"ok": False, "text": "refused: the unit is held or tilted too far; put it upright (patch ML01)"}
            self.move_times = [t for t in self.move_times if self.now_ms - t < 60000]
            if len(self.move_times) >= MOVES_PER_MINUTE:
                return {"ok": False, "text": "refused: more than 40 head moves in a minute (patch 038)"}
            self.move_times.append(self.now_ms)
            cur = self.head()
            yaw, pitch = int(args.get("yaw", KEEP)), int(args.get("pitch", KEEP))
            yaw1 = cur["yaw"] if yaw == KEEP else max(YAW_RANGE[0], min(YAW_RANGE[1], yaw))
            pitch1 = cur["pitch"] if pitch == KEEP else max(PITCH_RANGE[0], min(PITCH_RANGE[1], pitch))
            if lim["scale"] < 100:  # the limiter shrinks the excursion around the rest pose and caps the speed
                yaw1, pitch1 = round(yaw1 * lim["scale"] / 100), round(pitch1 * lim["scale"] / 100)
            speed = max(100, min(lim["speed_cap"] or 1000, 1000, int(args.get("speed", 150))))
            self.yaw0, self.pitch0, self.yaw1, self.pitch1 = cur["yaw"], cur["pitch"], yaw1, pitch1
            self.move_start_ms = self.now_ms
            self.move_ms = int(1000 * max(abs(yaw1 - cur["yaw"]), abs(pitch1 - cur["pitch"])) / speed)
            return {"ok": True, "yaw": yaw1, "pitch": pitch1}
        if name == "self.robot.set_led_colors":
            try:
                self.leds = [tuple(max(0, min(255, int(args[f"led_{i}_{c}"]))) for c in ("red", "green", "blue")) for i in range(12)]
            except KeyError as missing:
                return {"isError": True, "text": f"set_led_colors needs led_0_red to led_11_blue: {missing} is missing"}
            return {"ok": True}
        if name == "self.battery.get_status":
            return dict(self.battery)
        if name == "self.battery.simulate":
            self.battery["percent"] = max(0, min(100, int(args.get("level", 75))))
            return {"ok": True}
        if name == "self.face.snapshot":
            return {"ok": True, "png_base64": base64.b64encode(self.snapshot()).decode()}
        if name == "self.screen.bench_touch":
            self.touch(160, 4, 200)
            return {"ok": True}
        return {"isError": True, "text": f"{name} is not simulated yet; the tool exists in the firmware, the virtual unit has no behavior for it"}

    def tools_list(self, for_model: bool = False) -> list[dict]:
        """for_model=True hides the user-only tools, as the unit's list does for the model; a call by name still answers."""
        hidden = set(self.user_only) if for_model else set()
        return [{"name": n, "inputSchema": {"type": "object", "properties": {k: {"type": t} for k, t in self.tool_args.get(n, {}).items()}}} for n in self.tool_names if n not in hidden]


def serve() -> int:
    with VirtualUnit() as u:
        for line in sys.stdin:
            req = json.loads(line)
            method, params, rid = req.get("method"), req.get("params", {}), req.get("id")
            if method == "initialize":
                result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": "StackChan", "version": "virtual"}}
            elif method == "tools/list":
                result = {"tools": u.tools_list(for_model=True)}  # as the unit lists them for the model
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
