#!/usr/bin/env python3
"""Fit the assumed servo parameters of a robot description from a bench recording of real head moves.

A recording is JSON ({"joint": "pitch", "samples": [{"t_ms": 0, "cmd_deg": 0, "meas_deg": 0.1}, ...]}) or the CSV that scripts/fw-head-record.py writes
(columns joint, move_id, t_ms, cmd_deg, meas_deg, rtt_ms; both joints may share one file). Angle against time over serial, steps or ramps.
The model is the one the physics engine integrates for a position servo on a hinge with damping and dry friction and a torque limit:
    I q'' = clip(kp (cmd - q) - kv q', -T, T) - b q' - f sign(q') 
with the gravity torque of the head about the pitch axis G_sin sin(q) + G_cos cos(q) (a head center ahead of the axis pulls the face down; zero for yaw).
The fit searches kp, kv, b and T (not the inertia, which follows from the measured mass and the box shape; and not the friction f unless --fit-friction) to
minimize the squared angle error. It prints the parameters and, with --write, puts the fitted values in the description file, changing their src from assumed
to measured with a note naming the recording. Pure Python (no numpy): a few hundred samples fit in seconds.
With --measured-on DATE and --label NAME the written values are marked measured (the spec allows measured or assumed), their note starting "Fitted, measured on the unit" with the date and the recording's file name, and the whole fit is also kept under
"fits" in the description (NAME is for example before_servo_fix or after_servo_fix), so two fits of the same unit can sit side by side.
Usage: calibrate.py RECORDING.json [--robot stackchan] [--write] [--fit-friction] [--measured-on YYYY-MM-DD --label NAME]
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
    """Inertia of the head box about the nod axis (the axis runs through the box's vertical center): box formula plus the parallel axis term for its forward offset."""
    v = lambda k: mjcf.value(desc, k)  # noqa: E731
    m = v("mass_head")
    return m * (v("head_d") ** 2 + v("head_h") ** 2) / 12 + m * v("head_center_x") ** 2 + v("joint_armature")


def head_inertia_yaw(desc: dict) -> float:
    """Inertia about the vertical axis: the head box and the neck box (box formulas, the head's forward offset)."""
    v = lambda k: mjcf.value(desc, k)  # noqa: E731
    head = v("mass_head") * (v("head_w") ** 2 + v("head_d") ** 2) / 12 + v("mass_head") * v("head_center_x") ** 2
    neck = v("mass_neck") * (v("neck_w") ** 2 + v("neck_d") ** 2) / 12
    return head + neck + v("joint_armature")


def gravity_coefficient(desc: dict, joint: str) -> tuple[float, float]:
    """(G_sin, G_cos) in the model's equation: the head's weight acting at its center, which is 2.5 mm ahead of the nod axis and level with it.
    A forward center pulls the face down by a constant torque (cos term); none for yaw."""
    if joint != "pitch":
        return (0.0, 0.0)
    v = lambda k: mjcf.value(desc, k)  # noqa: E731
    return (0.0, -v("mass_head") * 9.81 * v("head_center_x"))


def simulate(times_ms: list[int], cmd_deg: list[float], q0_deg: float, inertia: float, kp: float, kv: float, damping: float, torque: float, friction: float, gravity: tuple[float, float] | float = (0.0, 0.0), delay_ms: float = 0.0, speed_cap: float | None = None, accel_cap: float | None = None) -> list[float]:
    """Semi-implicit Euler at 0.5 ms steps; returns the angle in degrees at each sample time.
    The command is a staircase (it holds its value from the sample where it changed) and reaches the servo `delay_ms` after that sample (the cable and the tool call).
    The servo does not chase a step at once: its own setpoint follows the command at no more than `speed_cap` degrees a second and `accel_cap` degrees a second squared
    (a trapezoid: it brakes in time to arrive), and the position loop tracks that setpoint. Without caps the setpoint is the command itself."""
    import bisect

    gs, gc = (gravity, 0.0) if isinstance(gravity, (int, float)) else gravity

    q, dq, t = math.radians(q0_deg), 0.0, times_ms[0] / 1000.0
    out, dt = [], 0.0005
    stamps = [x / 1000.0 + delay_ms / 1000.0 for x in times_ms]
    ref, ref_v = q0_deg, 0.0  # the servo's own setpoint, degrees and degrees a second
    for tm in times_ms:
        while t < tm / 1000.0 - 1e-9:
            i = max(0, bisect.bisect_right(stamps, t + 1e-9) - 1)
            goal = cmd_deg[i]
            if speed_cap is None or accel_cap is None:
                ref = goal
            else:
                err = goal - ref
                want = math.copysign(min(speed_cap, math.sqrt(2.0 * accel_cap * abs(err))), err) if err else 0.0
                ref_v += max(-accel_cap * dt, min(accel_cap * dt, want - ref_v))
                ref += ref_v * dt
            target = math.radians(ref)
            u = max(-torque, min(torque, kp * (target - q) - kv * dq))
            fr = friction * (1 if dq > 0 else -1 if dq < 0 else 0)
            ddq = (u - damping * dq - fr + gs * math.sin(q) + gc * math.cos(q)) / inertia
            dq += ddq * dt
            q += dq * dt
            t += dt
        out.append(math.degrees(q))
    return out


def error(rec: dict, inertia: float, theta: list[float], friction: float, gravity: tuple[float, float] | float = (0.0, 0.0), delay_ms: float = 0.0) -> float:
    t = [s["t_ms"] for s in rec["samples"]]
    cmd = [s["cmd_deg"] for s in rec["samples"]]
    meas = [s["meas_deg"] for s in rec["samples"]]
    kp, kv, damping, torque, *caps = theta
    sim = simulate(t, cmd, meas[0], inertia, kp, kv, damping, torque, friction, gravity, delay_ms, *(caps if len(caps) == 2 else (None, None)))
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
    """One fit over every joint present: a gain, a velocity gain and the servo's own speed and acceleration caps per joint (the caps are separate from the gain: the
    position loop is stiff, but the servo walks its setpoint toward a step at a limited rate), and the damping, torque limit and command delay shared by all."""
    v = lambda k: mjcf.value(desc, k)  # noqa: E731
    joints = [j for j in ("yaw", "pitch") if j in recs]
    inertia = {"yaw": head_inertia_yaw(desc), "pitch": head_inertia_pitch(desc)}
    names = [f"{j}_{k}" for j in joints for k in ("kp", "kv", "speed_cap_deg_s", "accel_cap_deg_s2")] + ["joint_damping", "torque_limit", "command_delay_ms"]
    theta = [v(n) for n in names]
    friction = v("joint_friction")

    def total(th: list[float]) -> float:
        damping, torque, delay = th[-3], th[-2], th[-1]
        return sum(error(recs[j], inertia[j], th[4 * i : 4 * i + 2] + [damping, torque, th[4 * i + 2], th[4 * i + 3]], friction, gravity_coefficient(desc, j), delay) for i, j in enumerate(joints)) / len(joints)

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


def quality(recs: dict[str, dict], desc: dict, fitted: dict[str, float]) -> dict[str, dict]:
    """How well the fitted servo reproduces each recording: rms error in degrees, the largest commanded step, the error as a share of it, and how much of the
    biggest step the head had covered half a second after it (the bench saw 40 to 46 percent)."""
    inertia = {"yaw": head_inertia_yaw(desc), "pitch": head_inertia_pitch(desc)}
    out = {}
    friction = mjcf.value(desc, "joint_friction")
    for j, rec in recs.items():
        th = [fitted[f"{j}_kp"], fitted[f"{j}_kv"], fitted["joint_damping"], fitted["torque_limit"], fitted[f"{j}_speed_cap_deg_s"], fitted[f"{j}_accel_cap_deg_s2"]]
        rms = math.sqrt(error(rec, inertia[j], th, friction, gravity_coefficient(desc, j), fitted["command_delay_ms"]))
        cmds = [x["cmd_deg"] for x in rec["samples"]]
        step = max((abs(b - a) for a, b in zip(cmds, cmds[1:]) if abs(b - a) > 0), default=0.0)
        out[j] = {"rms_deg": round(rms, 3), "step_deg": round(step, 1), "rms_pct_of_step": round(100 * rms / step, 1) if step else None}
    return out


MAX_RMS_PCT = 5.0


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
    ap.add_argument("--measured-on", help="date of the bench recording; marks the fit as measured on the unit")
    ap.add_argument("--label", help="name of this fit in the description's fits (needs --measured-on)")
    args = ap.parse_args(argv)
    recs = load_recording(args.recording)
    unknown = set(recs) - {"yaw", "pitch"}
    if unknown:
        print(f"calibrate: no inertia for {sorted(unknown)}; this fit knows yaw and pitch.", file=sys.stderr)
        return 2
    for joint, rec in recs.items():
        meas = [x["meas_deg"] for x in rec["samples"]]
        cmd = [x["cmd_deg"] for x in rec["samples"]]
        if len(meas) < 10 or (max(cmd) - min(cmd) >= 5 and max(meas) - min(meas) < 1.0):
            print(f"calibrate: no movement in the recording: the {joint} head did not follow its commands (readings moved {max(meas) - min(meas):.1f} degrees, commands {max(cmd) - min(cmd):.0f}). "
                  "Record again with the head able to move (idle movement on, or the bench head command).", file=sys.stderr)
            return 3
    desc = mjcf.load(args.robot)
    try:
        fitted, err = fit_joints(recs, desc)
    except (ValueError, OverflowError, ZeroDivisionError) as error_:
        print(f"calibrate: the fit failed ({error_}); the recording does not look like a servo following commands. Record again, or check the CSV.", file=sys.stderr)
        return 3
    quals = quality(recs, desc, fitted)
    poor = [j for j, q in quals.items() if q["rms_pct_of_step"] is None or q["rms_pct_of_step"] > MAX_RMS_PCT]
    verdict = "poor: the fitted servo does not reproduce the recording" if poor else "ok"
    print(json.dumps({"joints": sorted(recs), "rms_deg": round(math.sqrt(err), 3), "quality": quals, "verdict": verdict, "fitted": {k: round(x, 6) for k, x in fitted.items()}}, indent=1))
    if args.write:
        if poor:
            print(f"calibrate: not written. The fit leaves an error above {MAX_RMS_PCT:.0f} percent of the step for {', '.join(poor)}; a model that misses that much would make the physics worse, not better. "
                  "Record again with a step and a ramp, a faster reading rate, or readings finer than whole degrees.", file=sys.stderr)
            return 4
        path = HERE / "robots" / f"{args.robot}.robot.json"
        shown = ", ".join("%s %s deg" % (j, q["rms_deg"]) for j, q in quals.items())
        if args.measured_on:
            if not args.label:
                print("calibrate: --measured-on needs --label (the name of this fit, for example before_servo_fix).", file=sys.stderr)
                return 2
            for name, val in fitted.items():
                desc["params"][name].update(v=round(val, 6), src="measured", note="Fitted, measured on the unit: fitted from %s on %s (rms %s), fit %s" % (args.recording.name, args.measured_on, shown, args.label))
            desc.setdefault("fits", {})[args.label] = {"measured_on": args.measured_on, "recording": args.recording.name, "rms_deg": round(math.sqrt(err), 3),
                                                       "quality": quals, "params": {k: round(x, 6) for k, x in fitted.items()}}
        else:
            for name, val in fitted.items():
                desc["params"][name].update(v=round(val, 6), src="fitted, low confidence", note="fitted from %s (rms %s); low confidence until a faster, finer recording" % (args.recording.name, shown))
        path.write_text(json.dumps(desc, indent=2) + "\n")
        print(f"calibrate: wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
