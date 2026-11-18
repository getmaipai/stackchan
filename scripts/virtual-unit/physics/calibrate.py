#!/usr/bin/env python3
"""Fit the assumed servo parameters of a robot description from a bench recording of real head moves.

A recording is JSON: {"joint": "pitch", "samples": [{"t_ms": 0, "cmd_deg": 0, "meas_deg": 0.1}, ...]} (angle against time over serial, a step or a ramp command).
The model is the one the physics engine integrates for a position servo on a hinge with damping and dry friction and a torque limit:
    I q'' = clip(kp (cmd - q) - kv q', -T, T) - b q' - f sign(q')
The fit searches kp, kv, b and T (not the inertia, which follows from the measured mass and the box shape; and not the friction f unless --fit-friction) to
minimize the squared angle error. It prints the parameters and, with --write, puts the fitted values in the description file, changing their src from assumed
to measured with a note naming the recording. Pure Python (no numpy): a few hundred samples fit in seconds.
Usage: calibrate.py RECORDING.json [--robot stackchan] [--write] [--fit-friction]
Placement: host-side development tool; no firmware change. Upstream: none."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("mjcf", HERE / "mjcf.py")
mjcf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mjcf)


def head_inertia_pitch(desc: dict) -> float:
    """Inertia of the head and the nod servo about the pitch axis (box formulas and the parallel axis theorem)."""
    v = lambda k: mjcf.value(desc, k)  # noqa: E731
    m, w, h, d = v("mass_head"), v("head_w"), v("head_h"), v("head_d")
    center = v("total_h") - h / 2 - v("pitch_axis_z")
    head = m * (d * d + h * h) / 12 + m * (center * center + v("head_com_x") ** 2)
    ms, sw, sh, sd = v("mass_tilt_servo"), v("tilt_servo_w"), v("tilt_servo_h"), v("tilt_servo_d")
    servo = ms * (sd * sd + sh * sh) / 12 + ms * v("tilt_servo_x") ** 2
    return head + servo + v("joint_armature")


def simulate(times_ms: list[int], cmd_deg: list[float], q0_deg: float, inertia: float, kp: float, kv: float, damping: float, torque: float, friction: float) -> list[float]:
    """Semi-implicit Euler at 0.5 ms steps; returns the angle in degrees at each sample time."""
    q, dq, t, out = math.radians(q0_deg), 0.0, times_ms[0] / 1000.0, []
    dt = 0.0005
    for i, tm in enumerate(times_ms):
        target = math.radians(cmd_deg[i])
        while t < tm / 1000.0 - 1e-9:
            u = max(-torque, min(torque, kp * (target - q) - kv * dq))
            fr = friction * (1 if dq > 0 else -1 if dq < 0 else 0)
            ddq = (u - damping * dq - fr) / inertia
            dq += ddq * dt
            q += dq * dt
            t += dt
        out.append(math.degrees(q))
    return out


def error(rec: dict, inertia: float, theta: list[float], friction: float) -> float:
    t = [s["t_ms"] for s in rec["samples"]]
    cmd = [s["cmd_deg"] for s in rec["samples"]]
    meas = [s["meas_deg"] for s in rec["samples"]]
    kp, kv, damping, torque = theta
    sim = simulate(t, cmd, meas[0], inertia, kp, kv, damping, torque, friction)
    return sum((a - b) ** 2 for a, b in zip(sim, meas)) / len(meas)


def fit(rec: dict, inertia: float, start: list[float], friction: float, seed: int = 1, rounds: int = 60) -> tuple[list[float], float]:
    """Coordinate search with shrinking multiplicative steps on log-scale parameters (positive by construction)."""
    rng = random.Random(seed)
    theta, best = list(start), error(rec, inertia, start, friction)
    step = 0.5
    for _ in range(rounds):
        improved = False
        for i in rng.sample(range(len(theta)), len(theta)):
            for factor in (1 + step, 1 / (1 + step)):
                trial = list(theta)
                trial[i] *= factor
                e = error(rec, inertia, trial, friction)
                if e < best:
                    theta, best, improved = trial, e, True
        if not improved:
            step *= 0.6
            if step < 0.004:
                break
    return theta, best


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("recording", type=Path)
    ap.add_argument("--robot", default="stackchan")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--fit-friction", action="store_true")
    args = ap.parse_args(argv)
    rec = json.loads(args.recording.read_text())
    joint = rec["joint"]
    if joint != "pitch":
        print("calibrate: this fit knows the pitch joint (its inertia is computed from the head's mass); record the pitch moves, or add the yaw inertia first.", file=sys.stderr)
        return 2
    desc = mjcf.load(args.robot)
    v = lambda k: mjcf.value(desc, k)  # noqa: E731
    inertia = head_inertia_pitch(desc)
    start = [v("pitch_kp"), v("pitch_kv"), v("joint_damping"), v("torque_limit")]
    friction = v("joint_friction")
    theta, err = fit(rec, inertia, start, friction)
    names = ("pitch_kp", "pitch_kv", "joint_damping", "torque_limit")
    print(json.dumps({"joint": joint, "rms_deg": round(math.sqrt(err), 3), "fitted": dict(zip(names, (round(x, 6) for x in theta)))}, indent=1))
    if args.write:
        path = HERE / "robots" / f"{args.robot}.robot.json"
        for name, val in zip(names, theta):
            desc["params"][name].update(v=round(val, 6), src="measured", note=f"fitted from {args.recording.name}")
        path.write_text(json.dumps(desc, indent=2) + "\n")
        print(f"calibrate: wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
