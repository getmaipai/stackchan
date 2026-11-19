#!/usr/bin/env python3
"""The frame budget of the four tilt games before any of them has a screen (docs/design/accelerometer-games.md): each game is described by what moves and how, and the script plays 20 seconds of
a plausible run at 30 ticks a second, computing the rectangles a game would invalidate each tick (the old and the new place of every moving thing, thin edge columns for a flat shape that scrolls
a few pixels) and their pixel area. Flush ms is the measured 30 ms for a full screen (0.39 ms per 1,000 pixels); drawing time is not in it. The geometry is the design, so these numbers are
estimates of the design, to be replaced by `games_cost.py` once the screens exist. Usage: tilt_games_budget.py [--json]. Placement: host-side development tool. Upstream: none."""
import json
import math
import sys

W, H = 320, 240
MS_PER_PX = 30.0 / (W * H)
TICKS = 20 * 30


def area(rects):
    """Pixels covered by the union of rectangles (x, y, w, h), clipped to the glass."""
    rows = [bytearray(W) for _ in range(H)]
    for x, y, w, h in rects:
        x, y, w, h = int(x), int(y), int(w), int(h)
        x0, x1, y0, y1 = max(0, x), min(W, x + w), max(0, y), min(H, y + h)
        if x1 <= x0:
            continue
        for yy in range(y0, y1):
            rows[yy][x0:x1] = b"\x01" * (x1 - x0)
    return sum(sum(r) for r in rows)


def box(cx, cy, w, h, m=2):
    return (int(cx - w / 2) - m, int(cy - h / 2) - m, int(w) + 2 * m, int(h) + 2 * m)


def balance(t):
    """A ball of 18 px on a round plate (radius 88), pulled by the tilt: speed up to 5 px a tick. Moves: the ball, its shadow (offset 3), and a tilt marker (a 6 px dot on the plate's rim)."""
    a = t / 30.0
    now = (160 + 70 * math.sin(a * 0.9), 120 + 60 * math.sin(a * 1.3 + 1))
    prev = (160 + 70 * math.sin((t - 1) / 30.0 * 0.9), 120 + 60 * math.sin((t - 1) / 30.0 * 1.3 + 1))
    ang = a * 0.9
    marker = [box(160 + 86 * math.cos(ang), 120 + 86 * math.sin(ang), 6, 6)] if int(a * 2) != int((t - 1) / 30.0 * 2) else []
    return [box(*prev, 24, 24), box(*now, 24, 24)] + marker


def maze(t):
    """An 8 by 8 maze of 24 px cells (192 by 192): a marble of 12 px moves up to 3 px a tick along the corridors, a light trail dot is left every 12 px, the goal pulses once a second."""
    a = t / 30.0
    now = (40 + 100 * abs(math.sin(a * 0.35)), 40 + 100 * abs(math.sin(a * 0.5 + 0.5)))
    prev = (40 + 100 * abs(math.sin((t - 1) / 30.0 * 0.35)), 40 + 100 * abs(math.sin((t - 1) / 30.0 * 0.5 + 0.5)))
    r = [box(*prev, 12, 12), box(*now, 12, 12)]
    if t % 30 == 0:
        r.append(box(40 + 7 * 24, 40 + 7 * 24, 20, 20))
    return r


def racing(t):
    """Three lanes of 64 px (192 wide) seen from above, the road scrolls 6 px a tick: lane dashes (6 by 24, every 48 px, two lines) change at their edges only; the player's car (28 by 44) changes lane with a 90 ms slide; up to 2 obstacles (28 by 36) scroll."""
    r = []
    for line in (0, 1):   # the two lane lines: thin edge columns, the dash edges move along
        x = 64 * (line + 1) + 64 - 3
        for k in range(6):
            y = (t * 6 + k * 48) % (H + 48) - 24
            r.append((x - 1, y - 6, 8, 12))      # the leading edge of the dash
            r.append((x - 1, y + 18, 8, 12))     # and the trailing one
    for o in range(2):
        y = (t * 6 + o * 130) % (H + 80) - 40
        x = 64 * (1 + (o * 2 + t // 90) % 3) + 32
        r.append((x - 16, y - 24, 32, 12 + 12))  # an obstacle: its leading and trailing 12 px rows
        r.append((x - 16, y + 12, 32, 12))
    lane_x = 160 + 64 * math.sin(t / 45.0)
    prev_x = 160 + 64 * math.sin((t - 1) / 45.0)
    r.append(box(min(lane_x, prev_x) + abs(lane_x - prev_x) / 2, 200, 28 + abs(lane_x - prev_x), 44))
    return r


def flying(t):
    """The plane (36 by 24) follows the tilt; rings of 70 px growing from 10 to 110 px over 2 s come at it: each ring is redrawn as its old and new outer box ring (a ring of 4 px width changes in a band round its outside and inside); a distant ground strip scrolls."""
    r = [box(160 + 70 * math.sin(t / 50.0), 130 + 50 * math.sin(t / 37.0), 36, 24), box(160 + 70 * math.sin((t - 1) / 50.0), 130 + 50 * math.sin((t - 1) / 37.0), 36, 24)]
    for o in range(2):
        age = (t + o * 60) % 120
        d0, d1 = 10 + age * 100 / 120, 10 + (age + 1) * 100 / 120
        cx, cy = 160 + 40 * (o * 2 - 1), 110
        for d in (d0, d1):                       # the band: four thin strips round the ring's outside at each size
            n = int(d)
            r += [(int(cx - n / 2) - 3, int(cy - n / 2) - 3, n + 6, 7), (int(cx - n / 2) - 3, int(cy + n / 2) - 3, n + 6, 7), (int(cx - n / 2) - 3, int(cy - n / 2) - 3, 7, n + 6), (int(cx + n / 2) - 3, int(cy - n / 2) - 3, 7, n + 6)]
    r.append((0, 190, W, 6))   # the horizon line of the ground strip, the part that scrolls
    return r


GAMES = {"Balance": balance, "Maze": maze, "Racing": racing, "Flying": flying}


def main() -> int:
    out = {}
    for name, fn in GAMES.items():
        areas = [area(fn(t)) for t in range(1, TICKS)]
        out[name] = {"mean_px": round(sum(areas) / len(areas)), "worst_px": max(areas), "flush_ms_mean": round(sum(areas) / len(areas) * MS_PER_PX, 1), "flush_ms_worst": round(max(areas) * MS_PER_PX, 1)}
    if "--json" in sys.argv:
        print(json.dumps(out, indent=1))
        return 0
    print("| Game | Dirty pixels per tick (mean) | Worst tick | Flush ms (mean) | Flush ms (worst) |\n|---|---:|---:|---:|---:|")
    for n, r in out.items():
        print(f"| {n} | {r['mean_px']:,} | {r['worst_px']:,} | {r['flush_ms_mean']} | {r['flush_ms_worst']} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
