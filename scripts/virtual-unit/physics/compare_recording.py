#!/usr/bin/env python3
"""Draw the recorded head curve against the simulated one for the same steps, both axes, as an SVG (no libraries).

For each joint it takes the largest and the smallest step of the recording, starts the simulated servo (the robot description's parameters, or one of its saved fits
with --fit NAME) at the measured angle where the step began, sends it the same command after the same time, and plots recorded readings (dots) and the simulation (line)
against the time since the step. The title of each panel names the step and the rms difference over the window.
Usage: compare_recording.py RECORDING.csv OUT.svg [--robot stackchan] [--fit NAME] [--title TEXT]
Placement: host-side development tool; no firmware change. Upstream: none."""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("calibrate", HERE / "calibrate.py")
cal = importlib.util.module_from_spec(_spec)
sys.modules["calibrate"] = cal
_spec.loader.exec_module(cal)
mjcf = cal.mjcf

WINDOW_MS = 1700


def steps_of(samples: list[dict]) -> list[dict]:
    """The commanded steps of one joint: where the command changed, the angle read just before, and the readings until the next change (or WINDOW_MS)."""
    out = []
    for i in range(1, len(samples)):
        a, b = samples[i - 1], samples[i]
        if b["cmd_deg"] != a["cmd_deg"]:
            t0 = b["t_ms"]
            window = []
            for s in samples[i:]:
                if s["t_ms"] - t0 > WINDOW_MS or (s["cmd_deg"] != b["cmd_deg"]):
                    break
                window.append(s)
            out.append({"t0": t0, "from_cmd": a["cmd_deg"], "to_cmd": b["cmd_deg"], "start": a["meas_deg"], "readings": window})
    return [s for s in out if len(s["readings"]) >= 3]


def params(desc: dict, fit: str | None) -> dict[str, float]:
    if fit:
        return dict(desc["fits"][fit]["params"])
    return {k: float(e["v"]) for k, e in desc["params"].items()}


def simulate_step(desc: dict, p: dict[str, float], joint: str, step: dict) -> tuple[list[float], list[float]]:
    inertia = cal.head_inertia_yaw(desc) if joint == "yaw" else cal.head_inertia_pitch(desc)
    grid = list(range(0, WINDOW_MS + 1, 10))
    times = [step["t0"] + g for g in grid]
    cmd = [step["to_cmd"]] * len(times)
    sim = cal.simulate([step["t0"] - 200] + times, [step["from_cmd"]] + cmd, step["start"], inertia, p[f"{joint}_kp"], p[f"{joint}_kv"], p["joint_damping"], p["torque_limit"],
                       mjcf.value(desc, "joint_friction"), cal.gravity_coefficient(desc, joint), p["command_delay_ms"], p[f"{joint}_speed_cap_deg_s"], p[f"{joint}_accel_cap_deg_s2"])
    return grid, sim[1:]


def rms_over(step: dict, grid: list[int], sim: list[float]) -> float:
    errs = []
    for r in step["readings"]:
        k = min(len(grid) - 1, max(0, round((r["t_ms"] - step["t0"]) / 10)))
        errs.append((sim[k] - r["meas_deg"]) ** 2)
    return math.sqrt(sum(errs) / len(errs))


def panel(x0: float, y0: float, w: float, h: float, joint: str, step: dict, grid: list[int], sim: list[float]) -> list[str]:
    lo = min([step["start"], step["to_cmd"]] + [r["meas_deg"] for r in step["readings"]] + sim)
    hi = max([step["start"], step["to_cmd"]] + [r["meas_deg"] for r in step["readings"]] + sim)
    pad = max(2.0, (hi - lo) * 0.08)
    lo, hi = lo - pad, hi + pad
    px = lambda ms: x0 + 44 + (w - 56) * ms / WINDOW_MS  # noqa: E731
    py = lambda deg: y0 + 26 + (h - 58) * (1 - (deg - lo) / (hi - lo))  # noqa: E731
    out = [f'<text x="{x0 + 44:.0f}" y="{y0 + 16:.0f}" class="t">{joint}: {step["from_cmd"]:g} to {step["to_cmd"]:g} deg, rms {rms_over(step, grid, sim):.1f} deg</text>',
           f'<rect x="{x0 + 44:.0f}" y="{py(hi):.0f}" width="{w - 56:.0f}" height="{py(lo) - py(hi):.0f}" class="box"/>']
    for ms in (0, 500, 1000, 1500):
        out.append(f'<line x1="{px(ms):.1f}" y1="{py(hi):.0f}" x2="{px(ms):.1f}" y2="{py(lo):.0f}" class="grid"/><text x="{px(ms):.1f}" y="{py(lo) + 14:.0f}" class="a" text-anchor="middle">{ms}</text>')
    for k in range(5):
        deg = lo + (hi - lo) * k / 4
        out.append(f'<line x1="{x0 + 44:.0f}" y1="{py(deg):.1f}" x2="{x0 + w - 12:.0f}" y2="{py(deg):.1f}" class="grid"/><text x="{x0 + 38:.0f}" y="{py(deg) + 4:.1f}" class="a" text-anchor="end">{deg:.0f}</text>')
    out.append(f'<line x1="{x0 + 44:.0f}" y1="{py(step["to_cmd"]):.1f}" x2="{x0 + w - 12:.0f}" y2="{py(step["to_cmd"]):.1f}" class="cmd"/>')
    out.append('<polyline class="sim" fill="none" points="' + " ".join(f"{px(g):.1f},{py(v):.1f}" for g, v in zip(grid, sim)) + '"/>')
    for r in step["readings"]:
        out.append(f'<circle cx="{px(r["t_ms"] - step["t0"]):.1f}" cy="{py(r["meas_deg"]):.1f}" r="3.2" class="rec"/>')
    out.append(f'<text x="{x0 + 44 + (w - 56) / 2:.0f}" y="{y0 + h - 6:.0f}" class="a" text-anchor="middle">ms since the step</text>')
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("recording", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--robot", default="stackchan")
    ap.add_argument("--fit")
    ap.add_argument("--title", default="Recorded head against the simulated head")
    args = ap.parse_args(argv)
    desc = mjcf.load(args.robot)
    p = params(desc, args.fit)
    recs = cal.load_recording(args.recording)
    W, H = 920, 640
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{args.title}">',
           "<style>.t{font:600 14px sans-serif;fill:#1f2933}.a{font:12px sans-serif;fill:#52606d}.box{fill:#fff;stroke:#9aa5b1}.grid{stroke:#e4e7eb}.cmd{stroke:#9aa5b1;stroke-dasharray:5 4}"
           ".sim{stroke:#1d6fd6;stroke-width:2.4}.rec{fill:#e8590c}.k{font:13px sans-serif;fill:#1f2933}</style>",
           f'<rect width="{W}" height="{H}" fill="#f5f7fa"/><text x="20" y="28" style="font:700 17px sans-serif;fill:#1f2933">{args.title}</text>',
           '<circle cx="24" cy="50" r="4" class="rec"/><text x="34" y="54" class="k">recorded on the unit</text>',
           '<line x1="190" y1="50" x2="216" y2="50" class="sim"/><text x="222" y="54" class="k">simulated, same step</text>',
           '<line x1="380" y1="50" x2="406" y2="50" class="cmd"/><text x="412" y="54" class="k">the command</text>']
    row = 0
    for joint in ("pitch", "yaw"):
        steps = steps_of(recs[joint]["samples"])
        if not steps:
            continue
        by_size = sorted(steps, key=lambda s: abs(s["to_cmd"] - s["from_cmd"]))
        chosen = [by_size[-1], by_size[0]]
        for col, st in enumerate(chosen):
            grid, sim = simulate_step(desc, p, joint, st)
            svg += panel(10 + col * 455, 70 + row * 280, 445, 270, joint, st, grid, sim)
        row += 1
    svg.append("</svg>")
    args.out.write_text("\n".join(svg) + "\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
