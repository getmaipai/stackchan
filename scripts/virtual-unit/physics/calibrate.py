#!/usr/bin/env python3
"""Fit the assumed servo parameters of a robot description from a bench recording of real head moves.

A recording is JSON ({"joint": "pitch", "samples": [{"t_ms": 0, "cmd_deg": 0, "meas_deg": 0.1}, ...]}) or the CSV that scripts/fw-head-record.py writes
(columns joint, move_id, t_ms, cmd_deg, meas_deg, rtt_ms; both joints may share one file). Angle against time over serial, steps or ramps.
The model is the one the physics engine integrates for a position servo on a hinge with damping and dry friction and a torque limit:
    I q'' = clip(kp (cmd - q) - kv q', -T, T) - b q' - f sign(q') + G sin(q)
with G the gravity torque of the head about the pitch axis (zero for yaw).
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


def head_inertia_yaw(desc: dict) -> float:
    """Inertia about the vertical axis: the head box, the nod servo box and the pan housing (box and cylinder formulas)."""
    v = lambda k: mjcf.value(desc, k)  # noqa: E731
    head = v("mass_head") * (v("head_w") ** 2 + v("head_d") ** 2) / 12 + v("mass_head") * v("head_com_x") ** 2
    servo = v("mass_tilt_servo") * (v("tilt_servo_w") ** 2 + v("tilt_servo_d") ** 2) / 12 + v("mass_tilt_servo") * v("tilt_servo_x") ** 2
    housing = 0.5 * v("mass_yaw_housing") * v("yaw_housing_r") ** 2
    return head + servo + housing + v("joint_armature")


def gravity_coefficient(desc: dict, joint: str) -> float:
    """G in the model's equation: the head's weight times the height of its center above the pitch axis (it pushes the head further the way it leans)."""
    if joint != "pitch":
        return 0.0
    v = lambda k: mjcf.value(desc, k)  # noqa: E731
    return v("mass_head") * 9.81 * (v("total_h") - v("head_h") / 2 - v("pitch_axis_z"))


def simulate(times_ms: list[int], cmd_deg: list[float], q0_deg: float, inertia: float, kp: float, kv: float, damping: float, torque: float, friction: float, gravity: float = 0.0, delay_ms: float = 0.0) -> list[float]:
    """Semi-implicit Euler at 0.5 ms steps; returns the angle in degrees at each sample time.
    The command is a staircase (it holds its value from the sample where it changed) and reaches the servo `delay_ms` after that sample (the cable and the tool call)."""
    import bisect

    q, dq, t = math.radians(q0_deg), 0.0, times_ms[0] / 1000.0
    out, dt = [], 0.0005
    stamps = [x / 1000.0 + delay_ms / 1000.0 for x in times_ms]
    for tm in times_ms:
        while t < tm / 1000.0 - 1e-9:
            i = max(0, bisect.bisect_right(stamps, t + 1e-9) - 1)
            target = math.radians(cmd_deg[i])
            u = max(-torque, min(torque, kp * (target - q) - kv * dq))
            fr = friction * (1 if dq > 0 else -1 if dq < 0 else 0)
            ddq = (u - damping * dq - fr + gravity * math.sin(q)) / inertia
            dq += ddq * dt
            q += dq * dt
            t += dt
        out.append(math.degrees(q))
    return out


def error(rec: dict, inertia: float, theta: list[float], friction: float, gravity: float = 0.0, delay_ms: float = 0.0) -> float:
    t = [s["t_ms"] for s in rec["samples"]]
    cmd = [s["cmd_deg"] for s in rec["samples"]]
    meas = [s["meas_deg"] for s in rec["samples"]]
    kp, kv, damping, torque = theta
    sim = simulate(t, cmd, meas[0], inertia, kp, kv, damping, torque, friction, gravity, delay_ms)
    return sum((a - b) ** 2 for a, b in zip(sim, meas)) / len(meas)


def load_recording(path: Path) -> dict[str, dict]:
    """joint -> {"joint", "samples"}; a JSON file holds one joint, a CSV may hold several."""
    if path.suffix == ".json":
        rec = json.loads(path.read_text())
        return {rec["joint"]: rec}
    import csv

    out: dict[str, dict] = {}
    for row in csv.DictReader(path.read_text().splitlines()):
        out.setdefault(row["joint"], {"joint": row["joint"], "samples": []})["samples"].append(
            {"t_ms": int(float(row["t_ms"])), "cmd_deg": float(row["cmd_deg"]), "meas_deg": float(row["meas_deg"])}
        )
    return out


def fit_joints(recs: dict[str, dict], desc: dict, seed: int = 1, rounds: int = 60) -> tuple[dict[str, float], float]:
    """One fit over every joint present: a gain and a velocity gain per joint, and the damping and torque limit shared by both (as in the description)."""
    v = lambda k: mjcf.value(desc, k)  # noqa: E731
    joints = [j for j in ("yaw", "pitch") if j in recs]
    inertia = {"yaw": head_inertia_yaw(desc), "pitch": head_inertia_pitch(desc)}
    names = [f"{j}_{k}" for j in joints for k in ("kp", "kv")] + ["joint_damping", "torque_limit", "command_delay_ms"]
    theta = [v(n) for n in names]
    friction = v("joint_friction")

    def total(th: list[float]) -> float:
        damping, torque, delay = th[-3], th[-2], th[-1]
        return sum(error(recs[j], inertia[j], [th[2 * i], th[2 * i + 1], damping, torque], friction, gravity_coefficient(desc, j), delay) for i, j in enumerate(joints)) / len(joints)

    rng, best, step = random.Random(seed), total(theta), 0.5
    for _ in range(rounds):
        improved = False
        for i in rng.sample(range(len(theta)), len(theta)):
            for factor in (1 + step, 1 / (1 + step)):
                trial = list(theta)
                trial[i] *= factor
                e = total(trial)
                if e < best:
                    theta, best, improved = trial, e, True
        if not improved:
            step *= 0.6
            if step < 0.004:
                break
    return dict(zip(names, theta)), best


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
    args = ap.parse_args(argv)
    recs = load_recording(args.recording)
    unknown = set(recs) - {"yaw", "pitch"}
    if unknown:
        print(f"calibrate: no inertia for {sorted(unknown)}; this fit knows yaw and pitch.", file=sys.stderr)
        return 2
    desc = mjcf.load(args.robot)
    fitted, err = fit_joints(recs, desc)
    print(json.dumps({"joints": sorted(recs), "rms_deg": round(math.sqrt(err), 3), "fitted": {k: round(x, 6) for k, x in fitted.items()}}, indent=1))
    if args.write:
        path = HERE / "robots" / f"{args.robot}.robot.json"
        for name, val in fitted.items():
            desc["params"][name].update(v=round(val, 6), src="measured", note=f"fitted from {args.recording.name}")
        path.write_text(json.dumps(desc, indent=2) + "\n")
        print(f"calibrate: wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
