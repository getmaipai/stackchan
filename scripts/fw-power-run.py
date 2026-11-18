#!/usr/bin/env python3
"""Chain self.bench.power_log calls into one battery run and write a CSV (bench images only; owner steps in docs/dev/battery-and-power.md).

  fw-power-run.py --load "face only" --minutes 120 --out .runs/drain-face.csv [--seconds 300 --interval 30]
                  [--call 'python3 scripts/fw-serial.py tool {name} {json}']

Intent: a drain or charge curve is a long chain of power_log calls. This runs the chain, adds the wall-clock time and the load name to every
row, stops by itself when the unit is unsafe (a servo too hot, the battery voltage too low, the level under the floor) and prints the numbers
the power tables need: first and last level, the slope in percent per hour, and the minutes from 100 to 20 percent when the run crosses them.
The call command is a template ({name} and {json}) so the same script works over the cable, over the host link or in a test.
Placement: the machine that reaches the unit (development only). Upstream: none.
"""

from __future__ import annotations

import argparse
import csv
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path

COLUMNS = ["t_s", "level_pct", "charging", "on_cable", "vbat_mv", "vbus_mv", "vsys_mv", "direction", "charge_state", "servo1_tenths", "servo2_tenths", "servo1_temp", "servo2_temp", "heap_free"]
DEFAULT_CALL = "python3 scripts/fw-serial.py tool {name} {json}"


def call_tool(template: str, name: str, args: dict) -> dict:
    command = template.format(name=shlex.quote(name), json=shlex.quote(json.dumps(args)))
    out = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=600)
    text = out.stdout.strip()
    start = text.find("{")
    if out.returncode != 0 or start < 0:
        raise RuntimeError(f"the tool call failed ({out.returncode}): {(out.stderr or text)[-300:]}. Check the unit is on and reachable, then run again.")
    return json.loads(text[start:])


def unsafe(row: dict, floor: int, max_temp: int, min_vbat: int) -> str:
    """The reason to stop, or an empty string. A reading that failed (-1) never stops a run on its own."""
    if 0 <= row["level_pct"] < floor and not row["on_cable"]:
        return f"the level is {row['level_pct']} percent, under the floor of {floor}"
    for key in ("servo1_temp", "servo2_temp"):
        if row[key] >= max_temp:
            return f"{key} is {row[key]}, at or over {max_temp}"
    if 0 < row["vbat_mv"] < min_vbat and not row["on_cable"]:
        return f"the battery voltage is {row['vbat_mv']} mV, under {min_vbat}"
    return ""


def slope_per_hour(points: list[tuple[float, int]]) -> float | None:
    """Least squares slope of level against time, in percent per hour."""
    pts = [(t, v) for t, v in points if v >= 0]
    if len(pts) < 2:
        return None
    n = len(pts)
    mt = sum(t for t, _ in pts) / n
    mv = sum(v for _, v in pts) / n
    den = sum((t - mt) ** 2 for t, _ in pts)
    return None if den == 0 else sum((t - mt) * (v - mv) for t, v in pts) / den * 3600.0


def minutes_between(points: list[tuple[float, int]], high: int, low: int) -> float | None:
    """Minutes from the first reading at or under `high` to the first at or under `low` (drain); None if the run did not cross both."""
    start = next((t for t, v in points if 0 <= v <= high), None)
    end = next((t for t, v in points if 0 <= v <= low), None)
    return None if start is None or end is None or end < start else (end - start) / 60.0


def run(args: argparse.Namespace, sleep=time.sleep, clock=time.time) -> int:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    began = clock()
    points: list[tuple[float, int]] = []
    stop = ""
    with out.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["wall_s", "load"] + COLUMNS)
        while clock() - began < args.minutes * 60 and not stop:
            reply = call_tool(args.call, "self.bench.power_log", {"seconds": args.seconds, "interval_s": args.interval})
            if not reply.get("ok"):
                raise RuntimeError(f"power_log refused: {reply.get('error', reply)}. Use a bench image.")
            base = clock() - args.seconds
            for raw in reply["rows"]:
                row = dict(zip(COLUMNS, raw))
                wall = base + row["t_s"] - began
                writer.writerow([f"{wall:.0f}", args.load] + raw)
                points.append((wall, row["level_pct"]))
                stop = unsafe(row, args.floor, args.max_temp, args.min_vbat)
                if stop:
                    break
            fh.flush()
    slope = slope_per_hour(points)
    drain = minutes_between(points, 100, 20)
    levels = [v for _, v in points if v >= 0]
    print(f"load: {args.load}; rows: {len(points)}; first level: {levels[0] if levels else 'n/a'}; last level: {levels[-1] if levels else 'n/a'}")
    print(f"slope: {'n/a' if slope is None else f'{slope:+.1f} percent per hour'}; minutes 100 to 20: {'not crossed' if drain is None else f'{drain:.0f}'}")
    if stop:
        print(f"stopped early: {stop}.")
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--load", required=True, help="the load this run measures, for the CSV")
    ap.add_argument("--minutes", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=int, default=300)
    ap.add_argument("--interval", type=int, default=30)
    ap.add_argument("--call", default=DEFAULT_CALL, help="command template with {name} and {json}")
    ap.add_argument("--floor", type=int, default=10, help="stop under this level on the battery")
    ap.add_argument("--max-temp", type=int, default=55)
    ap.add_argument("--min-vbat", type=int, default=3300)
    args = ap.parse_args(argv)
    if not 1 <= args.seconds <= 300 or not 1 <= args.interval <= 60 or args.seconds // args.interval > 40:
        print("seconds must be 1 to 300, interval 1 to 60, and at most 40 rows a call (seconds divided by interval).", file=sys.stderr)
        return 1
    try:
        return run(args)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
