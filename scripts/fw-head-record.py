#!/usr/bin/env python3
"""Record head moves on the unit for the physics calibration: send scripted steps through the tool path, sample the real servo angle against time, write a CSV.

Bench builds only (the serial tool call of scripts/fw-serial.py). The unit must be upright on the table, powered, and its movement limiter free: on a cable the limiter
halves every move, so the script checks `self.motion.status` first and stops with the way out (or lifts the USB limit for the run with --usb-limit-off and puts it
back at the end).

  fw-head-record.py OUT.csv                       both axes, the full move set (about 45 seconds)
  fw-head-record.py OUT.csv --axes pitch          one axis
  fw-head-record.py OUT.csv --link http://127.0.0.1:PORT/   against the virtual unit's browser view instead of the cable (a dry run)
  fw-head-record.py OUT.csv --dry-run             print the move list and the time it needs, send nothing

The moves (steps at the tool's top speed, so the commanded path is a step as far as the firmware's own slew allows): small and large, up and down, in both directions
of each axis, each held 1.8 s so the servo settles; the large pitch steps stay inside the maker's 5 to 85 degrees. Small steps (10 to 20 degrees) show the linear
gain and the damping, large steps (60 degrees) reach the torque limit, going back shows the gravity offset. At most 30 head moves a minute, under the unit's cap of 40.
Sampling: `self.robot.get_head_angles` back to back, as fast as the cable allows (each sample keeps its round trip time; its time stamp is the middle of it).
Output columns: joint, move_id, t_ms, cmd_deg, meas_deg, rtt_ms. Fit it with scripts/virtual-unit/physics/calibrate.py OUT.csv.
Whether get_head_angles reports the servo's feedback or the last target is not recorded in this repo; the first run prints the first samples after a step so the bench agent can see which.
Placement: Mac that holds the cable (development only). Upstream: none.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOLD_S = 1.8
SPEED = 1000
YAW_MOVES = [0, 15, 0, 60, 0, -60, 0, -15, 0, 120, 0, -120, 0]
PITCH_MOVES = [10, 30, 10, 70, 10, 80, 10, 25, 10, 60, 10]  # between 5 and 85, rest at 10
MAX_PER_MINUTE = 30


def move_list(axes: list[str]) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    if "pitch" in axes:
        out += [("pitch", a) for a in PITCH_MOVES]
    if "yaw" in axes:
        out += [("yaw", a) for a in YAW_MOVES]
    return out


class SerialLink:
    """The unit on the cable (bench build). Two things the real unit does: the first call after the port opens is answered "Unknown tool" (so one throwaway call
    warms it up), and a tool may answer a bare true or false instead of an object (read here as {"ok": value})."""

    def __init__(self, mod=None, port=None) -> None:
        if mod is None:
            spec = importlib.util.spec_from_file_location("fw_serial", HERE / "fw-serial.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        self.mod = mod
        self.port = port if port is not None else mod.open_port()
        try:
            self.mod.call(self.port, "self.robot.get_head_angles", {}, wait=3.0)  # warm-up; its answer (often Unknown tool) is not used
        except (TimeoutError, OSError, ValueError):
            pass

    def call(self, name: str, args: dict | None = None) -> dict:
        reply = self.mod.call(self.port, name, args or {}, wait=5.0)
        return reply if isinstance(reply, dict) else {"ok": reply}

    has_bench_head: bool | None = None

    def move(self, axis: str, angle: int, speed: int = SPEED) -> dict:
        """One head step. Bench builds have self.bench.set_head, which moves the head whatever the idle rule says (the unit ignores set_head_angles while idle);
        it is used when the build has it, else the ordinary head move."""
        if self.has_bench_head is not False:
            reply = self.call("self.bench.set_head", {axis: angle, "speed": max(100, min(1000, speed)), "hold_ms": 0})
            text = str(reply.get("text", "")) + str(reply.get("error", ""))
            if "Unknown tool" not in text:
                self.has_bench_head = True
                return reply
            self.has_bench_head = False
        return self.call("self.robot.set_head_angles", {axis: angle, "speed": speed})

    def close(self) -> None:
        self.port.close()


class HttpLink:
    """The virtual unit's browser view (scripts/virtual-unit/view.py): same tool names, same answers."""

    def __init__(self, base: str) -> None:
        self.base = base if base.endswith("/") else base + "/"

    def call(self, name: str, args: dict | None = None) -> dict:
        req = urllib.request.Request(self.base + "call", json.dumps({"name": name, "arguments": args or {}}).encode())
        return json.loads(urllib.request.urlopen(req, timeout=5).read())

    def move(self, axis: str, angle: int, speed: int = SPEED) -> dict:
        return self.call("self.bench.set_head", {axis: angle, "speed": max(100, min(1000, speed)), "hold_ms": 0})

    def close(self) -> None:
        pass


def check_limiter(link, allow_usb_limit_off: bool) -> str | None:
    """None when moves will be unlimited, else the plain message. With --usb-limit-off the USB limit is lifted (returns "restore" to put it back)."""
    status = link.call("self.motion.status")
    state = status.get("state", "")
    if state == "free":
        return None
    if state == "usb_limited" and allow_usb_limit_off:
        link.call("self.motion.set", {"usb_limit": "off"})
        return "restore"
    return (f"The movement limiter is {state} ({status.get('reasons', 'no reason given')}), so every move would be shortened. "
            "Put the unit upright and charged, take it off the cable, or on a cable run again with --usb-limit-off.")


def link_move(link, axis: str, angle: int) -> dict:
    """The link's own head step when it has one (the bench tool), else the ordinary tool: a link written for a test may offer only call()."""
    mover = getattr(link, "move", None)
    return mover(axis, angle) if mover else link.call("self.robot.set_head_angles", {axis: angle, "speed": SPEED})


def record(link, axes: list[str], out: Path, usb_limit_off: bool = False, hold_s: float = HOLD_S, log=print, clock=time.perf_counter, sleep=time.sleep) -> int:
    moves = move_list(axes)
    verdict = check_limiter(link, usb_limit_off)
    if verdict not in (None, "restore"):
        log(verdict)
        return 2
    t0 = clock()
    rows: list[list] = []
    first_after_step: list[str] = []
    cmd = {"yaw": 0, "pitch": 0}
    last_meas: dict[str, float] = {}
    try:
        for axis in axes:  # start every axis at rest and let it settle
            link_move(link, axis, 10 if axis == "pitch" else 0)
            cmd[axis] = 10 if axis == "pitch" else 0
        sleep(hold_s)
        stamps: list[float] = []
        for move_id, (axis, angle) in enumerate(moves):
            stamps = [s for s in stamps if clock() - s < 60.0]
            if len(stamps) >= MAX_PER_MINUTE:
                sleep(max(0.0, 60.0 - (clock() - stamps[0])))
            sent = clock()
            reply = link_move(link, axis, angle)
            stamps.append(sent)
            if reply.get("ok") is False:
                log(f"move {move_id} ({axis} {angle}) was refused: {reply.get('text') or reply.get('error')}. Stopped; the CSV so far is kept.")
                break
            cmd[axis] = angle
            t_cmd = (sent - t0) * 1000
            rows.append([axis, move_id, f"{t_cmd:.1f}", angle, last_meas.get(axis, angle), "0"])   # the step itself, at the moment it was sent
            end = sent + hold_s
            while clock() < end:
                a = clock()
                got = link.call("self.robot.get_head_angles")
                b = clock()
                mid = ((a + b) / 2 - t0) * 1000
                for joint in axes:
                    if joint in got:
                        last_meas[joint] = got[joint]
                        rows.append([joint, move_id, f"{mid:.1f}", cmd[joint], got[joint], f"{(b - a) * 1000:.1f}"])
                if move_id == 0 and len(first_after_step) < 6:
                    first_after_step.append(f"{mid:.0f} ms: {json.dumps(got)}")
    finally:
        if verdict == "restore":
            link.call("self.motion.set", {"usb_limit": "limited"})
        for axis in axes:
            link_move(link, axis, 10 if axis == "pitch" else 0)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        w = csv.writer(handle)
        w.writerow(["joint", "move_id", "t_ms", "cmd_deg", "meas_deg", "rtt_ms"])
        w.writerows(rows)
    rtts = sorted(float(r[5]) for r in rows) or [0.0]
    log(f"wrote {len(rows)} samples of {len(moves)} moves to {out}; median round trip {rtts[len(rtts) // 2]:.0f} ms (about {1000 / max(1.0, rtts[len(rtts) // 2]):.0f} samples a second)")
    log("first samples after the first step (does get_head_angles report feedback or the last target?):")
    for line in first_after_step:
        log("  " + line)
    for axis in axes:
        meas = [float(r[4]) for r in rows if r[0] == axis and r[5] != "0"]      # real readings only: the step rows carry no reading of their own
        commands = [float(r[3]) for r in rows if r[0] == axis and r[5] != "0"]
        if meas and max(commands) - min(commands) >= 10 and max(meas) - min(meas) < 2.0:
            log(f"The {axis} reading stayed within {max(meas) - min(meas):.1f} degrees while it was commanded over {max(commands) - min(commands):.0f}: the head did not follow, so this recording cannot be fitted. "
                "The unit ignores head moves while it is idle unless idle movement is on (the serial log says 'set_head_angles ignored: idle'); turn idle movement on or use the bench head command, then record again.")
            return 3
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("--axes", default="pitch,yaw")
    ap.add_argument("--link", default="", help="the virtual unit's address instead of the cable")
    ap.add_argument("--usb-limit-off", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    axes = [a for a in args.axes.split(",") if a in ("yaw", "pitch")]
    if not axes:
        print("fw-head-record: --axes is yaw, pitch or yaw,pitch.", file=sys.stderr)
        return 2
    moves = move_list(axes)
    seconds = HOLD_S * (len(moves) + 1)
    if args.dry_run:
        print(f"{len(moves)} moves, about {seconds:.0f} s:")
        print(", ".join(f"{a} {v}" for a, v in moves))
        return 0
    link = HttpLink(args.link) if args.link else SerialLink()
    try:
        return record(link, axes, args.out, args.usb_limit_off)
    finally:
        link.close()


if __name__ == "__main__":
    sys.exit(main())
