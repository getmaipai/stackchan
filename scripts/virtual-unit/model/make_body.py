#!/usr/bin/env python3
"""Build the rigged body model of the unit from the official structure files in source/.

Writes stackchan.glb and stackchan.params.json next to this file. Deterministic: the same source files give the
same bytes. Standard library only. The source files are data: they are parsed, never executed.

Frame of the model: meters, Y up, the robot faces +Z, +X is the robot's left, the origin is the yaw axis on the table.
Run: python3 scripts/virtual-unit/model/make_body.py   (add --check to compare with the files on disk instead of writing)
"""
import hashlib
import json
import math
import os
import struct
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import softrender  # noqa: E402  (the STL reader lives beside the preview renderer)

# ---- assembly: each official part sits in its own export position; these offsets bring them into one frame (mm).
# The assembly frame is the one of the servo body part: X across, -Y to the front, Z up. Every number below was
# found by fitting circles to the parts' own holes and bosses (see MATCH.md, "How the parts were assembled").
YAW_X, YAW_Y = 229.73, -320.563      # the turn axis: center of the servo body's round flange and of the base's turntable
PITCH_Z = 9.3                        # the nod axis height: the servo body's side stub, the arm's spline, the head pocket
BASE_MID_Y = -324.565                # middle of the base footprint, front to back (4 mm ahead of the turn axis)
TABLE_Z = -34.2                      # the table: the head top (36.3) minus the published overall height (70.5)
BASE_DROP = 1.45                     # the base sits this much lower than its export position: closes the gap to the published height
COVER_LIFT = 10.04                   # the bottom cover seats on the base's four screw posts
WALL = 26.0                          # the head's inner pocket floors sit this far from the middle plane
CORNER = (YAW_X + 23.0, 32.3)        # center of the head shell's rounded top corner (radius 4), +X side
BAR_Y = -319.3                       # middle of the light bar slot along the head


def _bar(side):
    """Seat a light bar in the slanted slot of the head's top corner: the rounded stem tip flush with the corner."""
    def place(p):
        d = 4.0 - (p[0] - 0.18)
        k = 0.70710678
        if side > 0:
            return (CORNER[0] + d * k + p[2] * k, p[1] + BAR_Y, CORNER[1] + d * k - p[2] * k)
        return (2 * YAW_X - CORNER[0] - d * k + p[2] * k, p[1] + BAR_Y, CORNER[1] + d * k + p[2] * k)
    return place


# part name, node, material, offset function (raw mm -> assembly mm)
PARTS = [
    ('Base', 'base', 'base', lambda p: (p[0] + 123.0, p[1], p[2] - BASE_DROP)),
    ('BaseCover', 'base', 'base', lambda p: (p[0] + YAW_X, p[1] - 338.45, p[2] + COVER_LIFT - BASE_DROP)),
    ('ServoBody', 'neck', 'neck', lambda p: p),
    ('ServoCover', 'neck', 'neck', lambda p: (p[0], p[1], p[2] - 12.0)),  # its screw holes meet the servo body's
    ('ServoSideCover', 'neck', 'servo', lambda p: p),                     # the darker cover on the holder back
    ('MainBody', 'head', 'shell', lambda p: (p[0] - 246.0, p[1] + 13.0, p[2])),
    ('ServoArm', 'head', 'neck', lambda p: (YAW_X + WALL - (p[0] - 327.73), p[1] + 123.05, 2 * PITCH_Z - p[2])),
    ('BearingFixture', 'head', 'neck', lambda p: (YAW_X - WALL + (p[0] - 327.73), p[1] + 123.05, p[2])),
    ('LightGuideBar-A', 'bar_left', 'light_bar', _bar(+1)),   # each bar is its own node, so a view can light it along its length
    ('LightGuideBar-B', 'bar_right', 'light_bar', _bar(-1)),
]

MATERIALS = [  # name, base color (linear RGBA), metallic, roughness, emissive. Colors are judged from product photos.
    ('base', (0.090, 0.090, 0.105, 1.0), 0.0, 0.85, None),   # measured in the owner's photos against the white label paper: dark gray, slightly blue
    ('port', (0.012, 0.012, 0.014, 1.0), 0.0, 0.5, None),
    ('neck', (0.420, 0.440, 0.440, 1.0), 0.0, 0.85, None),   # measured: the holder is a shade darker than the shell
    ('servo', (0.085, 0.087, 0.100, 1.0), 0.0, 0.85, None),   # measured: the holder's back cover is the same dark gray as the base
    ('camera', (0.80, 0.27, 0.07, 1.0), 0.6, 0.35, None),            # the copper-orange ring round the lens (owner's front photo)
    ('core', (0.525, 0.540, 0.540, 1.0), 0.0, 0.85, None),   # measured: the controller is a neutral light gray, a little lighter than the shell
    ('glass', (0.004, 0.004, 0.005, 1.0), 0.0, 0.12, None),
    ('light_bar', (0.42, 0.70, 0.72, 1.0), 0.0, 0.35, None),
    ('pcb', (0.028, 0.030, 0.034, 1.0), 0.0, 0.5, None),     # the boards are matte black (owner's photo of the open back)
    ('shell', (0.480, 0.500, 0.505, 1.0), 0.0, 0.85, None),   # measured: neutral light gray, very slightly cool
    ('screen', (0.0, 0.0, 0.0, 1.0), 0.0, 0.4, (1.0, 1.0, 1.0)),
    ('button', (0.525, 0.540, 0.540, 1.0), 0.0, 0.85, None),   # the keys are the controller's own plastic
    ('port_metal', (0.42, 0.43, 0.46, 1.0), 0.6, 0.4, None),
    ('port_red', (0.45, 0.03, 0.02, 1.0), 0.0, 0.6, None),
    ('servo_case', (0.012, 0.014, 0.02, 1.0), 0.0, 0.5, None),
    ('battery', (0.02, 0.09, 0.42, 1.0), 0.0, 0.5, None),
    ('cable', (0.45, 0.45, 0.47, 1.0), 0.0, 0.6, None),
    ('touch_pad', (0.50, 0.53, 0.58, 1.0), 0.0, 0.5, None),
    ('port_teal', (0.22, 0.50, 0.80, 1.0), 0.0, 0.5, None),          # the second top connector is light blue (owner's top photos); the name is kept
    ('sticker', (0.80, 0.80, 0.79, 1.0), 0.0, 0.7, None),
    ('sticker_ink', (0.012, 0.012, 0.014, 1.0), 0.0, 0.7, None),
    ('led_charge', (0.10, 0.012, 0.01, 1.0), 0.0, 0.4, None),
    ('led_bottom', (0.10, 0.012, 0.01, 1.0), 0.0, 0.4, None),         # red when lit (owner's photo of the underside)
    ('print', (0.30, 0.30, 0.31, 1.0), 0.0, 0.7, None),
    ('tongue', (0.20, 0.20, 0.21, 1.0), 0.0, 0.5, None),
    ('screw', (0.55, 0.55, 0.57, 1.0), 0.8, 0.35, None),
    ('screw_dark', (0.02, 0.02, 0.022, 1.0), 0.6, 0.4, None),
    ('chip', (0.015, 0.015, 0.018, 1.0), 0.0, 0.45, None),
    ('conn', (0.74, 0.71, 0.62, 1.0), 0.0, 0.6, None),
    ('flex', (0.85, 0.86, 0.88, 1.0), 0.0, 0.5, None),
    ('wire_red', (0.50, 0.02, 0.02, 1.0), 0.0, 0.6, None),
    ('sticker_dark', (0.06, 0.06, 0.065, 1.0), 0.0, 0.7, None),
    ('sticker_orange', (0.75, 0.13, 0.02, 1.0), 0.0, 0.7, None),
    ('sticker_gray', (0.45, 0.45, 0.46, 1.0), 0.0, 0.7, None),
    ('emboss', (0.46, 0.48, 0.48, 1.0), 0.0, 0.85, None),          # the raised mark is the housing's own plastic, a shade darker so it reads
    ('pin_gold', (0.80, 0.58, 0.18, 1.0), 0.9, 0.3, None),
    ('silk', (0.80, 0.80, 0.78, 1.0), 0.0, 0.7, None),
    ('conn_green', (0.25, 0.55, 0.85, 1.0), 0.0, 0.5, None),         # light blue in daylight (it looked green under amber light); the name is kept
    ('flex_ink', (0.08, 0.22, 0.75, 1.0), 0.0, 0.6, None),           # the print on the flat cables is blue (owner's photos)
    ('ring_led', (0.75, 0.75, 0.72, 1.0), 0.0, 0.4, None),
    ('cap_tan', (0.42, 0.30, 0.20, 1.0), 0.0, 0.5, None),
    ('trace', (0.075, 0.08, 0.085, 1.0), 0.0, 0.5, None),            # copper under the board's black coat: a shade lighter than the board
    ('ribbon', (0.06, 0.06, 0.066, 1.0), 0.3, 0.22, None),          # the black cable's wires: glossy, so each wire catches the light
]
LIGHT_OFF = (0.42, 0.70, 0.72, 1.0)
LIGHTS = 12

# ---- figures that do not come from the structure files
PUBLISHED = {'width_mm': 54.0, 'height_mm': 70.5, 'depth_mm': 61.5, 'mass_g': 187.2}   # product page
PITCH_FREE_DEG = (0.0, 90.0)         # nothing touches between these angles in a sweep of the assembled model (official parts alone: 0 to 93)
YAW_LIMIT_DEG = (-128.0, 128.0)      # firmware limiter: yaw angleLimit (-1280, 1280) tenths of a degree
PITCH_LIMIT_DEG = (3.0, 87.0)        # firmware limiter: pitch angleLimit (30, 870) tenths of a degree
PITCH_RECOMMENDED_DEG = (5.0, 85.0)  # product page note
SCREEN_MM = (41.5, 31.6)             # the screen window on the published drawing (a 2.0 inch panel lights about 40.6 x 30.5 of it)
SCREEN_DROP_MM = 0.3                 # screen center below the head center, read off the published drawing
CORE_R_MM = 4.0
SERVO_MM = (23.2, 12.1, 25.25)       # servo data sheet: length, width, height
SERVO_SHAFT_R = 1.975                # servo data sheet: 20 tooth output, 3.95 mm across; the base and the arm have sockets of this size
SERVO_SHAFT_INSET = 6.0              # shaft center from the near end of the case (assumed)
BATTERY_MM = (30.0, 20.0, 8.0)       # a 550 mAh cell of a common size (assumed; only the capacity is published)


def world(p):
    """Assembly mm -> model mm (Y up, +Z front, origin on the turn axis at the table)."""
    return (p[0] - YAW_X, p[2] - TABLE_Z, -(p[1] - YAW_Y))


YAW_O = (0.0, -22.3 - TABLE_Z, 0.0)        # yaw joint origin: bottom of the servo body flange, on the axis
PITCH_O = (0.0, PITCH_Z - TABLE_Z, 0.0)    # pitch joint origin: the nod axis crosses the turn axis
ORIGIN = {'base': (0.0, 0.0, 0.0), 'neck': YAW_O, 'head': PITCH_O, 'bar_left': PITCH_O, 'bar_right': PITCH_O}


# ---- primitives (model mm, world position)
def obox(c, a, b, n):
    """Box centered at c with half-edge vectors a, b, n; faces wound outward."""
    def add(u, v, w):
        return (c[0] + u * a[0] + v * b[0] + w * n[0], c[1] + u * a[1] + v * b[1] + w * n[1], c[2] + u * a[2] + v * b[2] + w * n[2])
    tris = []
    for axis in range(3):
        for s in (-1, 1):
            q = []
            for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                uvw = [0, 0, 0]
                uvw[axis] = s
                uvw[(axis + 1) % 3] = u
                uvw[(axis + 2) % 3] = v
                q.append(add(*uvw))
            mid = add(*[s if i == axis else 0 for i in range(3)])
            for t in ((q[0], q[1], q[2]), (q[0], q[2], q[3])):
                e = [t[1][i] - t[0][i] for i in range(3)]
                g = [t[2][i] - t[0][i] for i in range(3)]
                nrm = (e[1] * g[2] - e[2] * g[1], e[2] * g[0] - e[0] * g[2], e[0] * g[1] - e[1] * g[0])
                out = sum(nrm[i] * (mid[i] - c[i]) for i in range(3))
                tris.append(t[0] + t[1] + t[2] if out > 0 else t[0] + t[2] + t[1])
    return tris


def box(c, size):
    return obox(c, (size[0] / 2.0, 0, 0), (0, size[1] / 2.0, 0), (0, 0, size[2] / 2.0))


def rounded_outline(w, h, r, seg=6):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90.0 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts  # counter-clockwise seen from +Z


def prism(outline, cx, cy, z0, z1):
    """Extrude a convex outline (XY, counter-clockwise from +Z) from z0 to z1."""
    tris = []
    n = len(outline)
    p = [(cx + x, cy + y) for x, y in outline]
    for i in range(n):
        a, b = p[i], p[(i + 1) % n]
        tris.append((a[0], a[1], z0, b[0], b[1], z0, b[0], b[1], z1))
        tris.append((a[0], a[1], z0, b[0], b[1], z1, a[0], a[1], z1))
    for i in range(1, n - 1):
        tris.append((p[0][0], p[0][1], z1, p[i][0], p[i][1], z1, p[i + 1][0], p[i + 1][1], z1))
        tris.append((p[0][0], p[0][1], z0, p[i + 1][0], p[i + 1][1], z0, p[i][0], p[i][1], z0))
    return tris


def disc_x(c, r, side, seg=10):
    """Flat disc facing +X (side 1) or -X (side -1)."""
    pts = [(c[0], c[1] + r * math.cos(2 * math.pi * i / seg), c[2] + side * r * math.sin(2 * math.pi * i / seg)) for i in range(seg)]
    return [c + pts[i] + pts[(i + 1) % seg] for i in range(seg)]


def quad_x(side, x, y0, y1, z0, z1):
    """Flat rectangle on a plane of constant X, facing +X (side 1) or -X (side -1)."""
    a, b, c, d = (x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)
    return [a + b + c, a + c + d] if side > 0 else [a + c + b, a + d + c]


def quad_y(side, y, x0, x1, z0, z1):
    """Flat rectangle on a plane of constant Y, facing up (side 1) or down (side -1)."""
    a, b, c, d = (x0, y, z0), (x0, y, z1), (x1, y, z1), (x1, y, z0)
    return [a + b + c, a + c + d] if side > 0 else [a + c + b, a + d + c]


LETTERS = {'S': (7, 4, 7, 1, 7), 'T': (7, 2, 2, 2, 2), 'A': (2, 5, 7, 5, 5), 'C': (7, 4, 4, 4, 7), 'K': (5, 6, 4, 6, 5), 'H': (5, 5, 7, 5, 5), 'N': (5, 7, 7, 5, 5)}


def dashes(rows, x0, x1, seed=5):
    """Stand-in print for a label: rows of short dark bars. Returns (row index, start, end) spans between x0 and x1; no real text."""
    out, state = [], seed
    for r in range(rows):
        x = x0
        while x < x1 - 1.0:
            state = (state * 73 + 41) % 199
            w = 1.2 + (state % 5) * 0.9
            out.append((r, x, min(x1, x + w)))
            x += w + 0.7 + (state % 3) * 0.4
    return out


def circle(r, seg=20):
    return [(r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg)) for i in range(seg)]


# ---- drawn details. A "frame" f(u, v, c) maps a flat drawing (u, v) and a height c above it to model mm; c < 0 is inside the part.
def both(tris):
    """The same triangles facing both ways: for thin parts and the inside of openings."""
    return tris + [t[0:3] + t[6:9] + t[3:6] for t in tris]


def moved(outline, du, dv):
    return [(u + du, v + dv) for u, v in outline]


def flat(f, outline, c=0.0):
    """A convex outline filled at height c."""
    p = [f(u, v, c) for u, v in outline]
    return both([p[0] + p[i] + p[i + 1] for i in range(1, len(p) - 1)])


def tube(f, outline, c0, c1):
    """The walls of an outline between two heights."""
    tris, n = [], len(outline)
    for i in range(n):
        (u0, v0), (u1, v1) = outline[i], outline[(i + 1) % n]
        a, b, c, d = f(u0, v0, c0), f(u1, v1, c0), f(u1, v1, c1), f(u0, v0, c1)
        tris += [a + b + c, a + c + d]
    return both(tris)


def band(f, outer, inner, c):
    """The flat ring between two outlines with the same number of points."""
    tris, n = [], len(outer)
    for i in range(n):
        a, b = f(outer[i][0], outer[i][1], c), f(outer[(i + 1) % n][0], outer[(i + 1) % n][1], c)
        p, q = f(inner[i][0], inner[i][1], c), f(inner[(i + 1) % n][0], inner[(i + 1) % n][1], c)
        tris += [a + b + q, a + q + p]
    return both(tris)


def slab(f, u0, u1, v0, v1, c0, c1):
    """A box in a frame."""
    o = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    return tube(f, o, c0, c1) + flat(f, o, c0) + flat(f, o, c1)


def _ray(cu, cv, a, poly):
    """Where the ray from (cu, cv) at angle a leaves a convex outline."""
    dx, dy = math.cos(a), math.sin(a)
    best = None
    for i in range(len(poly)):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % len(poly)]
        ex, ey = x1 - x0, y1 - y0
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        t = ((x0 - cu) * ey - (y0 - cv) * ex) / den
        s = ((x0 - cu) * dy - (y0 - cv) * dx) / den
        if t > 0 and -1e-9 <= s <= 1 + 1e-9 and (best is None or t < best):
            best = t
    return (cu + dx * best, cv + dy * best)


def holed(f, u0, u1, v0, v1, hole):
    """A flat rectangle with one convex opening cut through it: the face around a real hole."""
    cu, cv = sum(p[0] for p in hole) / len(hole), sum(p[1] for p in hole) / len(hole)
    rect = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    marks = [(math.atan2(p[1] - cv, p[0] - cu), p, None) for p in hole] + [(math.atan2(p[1] - cv, p[0] - cu), None, p) for p in rect]
    marks.sort(key=lambda m: m[0])
    ring = []
    for a, h, r in marks:
        if ring and abs(a - ring[-1][0]) < 1e-9:
            continue
        ring.append((a, h or _ray(cu, cv, a, hole), r or _ray(cu, cv, a, rect)))
    tris = []
    for i in range(len(ring)):
        (_, h0, r0), (_, h1, r1) = ring[i], ring[(i + 1) % len(ring)]
        a, b, c, d = f(h0[0], h0[1], 0.0), f(r0[0], r0[1], 0.0), f(r1[0], r1[1], 0.0), f(h1[0], h1[1], 0.0)
        tris += [a + b + c, a + c + d]
    return both(tris)


def clipped(outline, axis, at, keep_low):
    """A convex outline cut by a straight line: the part with coordinate `axis` below `at` (or above it)."""
    out = []
    for i in range(len(outline)):
        p, q = outline[i], outline[(i + 1) % len(outline)]
        pin, qin = (p[axis] <= at) == keep_low, (q[axis] <= at) == keep_low
        if pin:
            out.append(p)
        if pin != qin:
            t = (at - p[axis]) / (q[axis] - p[axis])
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def stroke(f, pts, w, c):
    """A thin line through the points, drawn flat at height c."""
    tris = []
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        ln = math.hypot(bx - ax, by - ay)
        dx, dy = (bx - ax) / ln * w / 2, (by - ay) / ln * w / 2
        tris += flat(f, [(ax - dx + dy, ay - dy - dx), (bx + dx + dy, by + dy - dx), (bx + dx - dy, by + dy + dx), (ax - dx - dy, ay - dy + dx)], c)
    return tris


def arc(cx, cy, rx, ry, a0, a1, n=10):
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


_ARCH = [(0.05, 0.5), (0.15, 0.63), (0.3, 0.68), (0.44, 0.62), (0.5, 0.48), (0.5, 0.0)]
STROKES = {  # letter: (advance, strokes) in a box one capital high; the product's own name on the side labels, and marks
    'S': (0.62, [[(0.55, 0.84), (0.42, 0.97), (0.22, 0.98), (0.07, 0.86), (0.08, 0.66), (0.29, 0.53), (0.47, 0.41), (0.56, 0.23), (0.46, 0.05), (0.26, 0.0), (0.09, 0.07), (0.0, 0.19)]]),
    't': (0.44, [[(0.18, 0.95), (0.18, 0.13), (0.27, 0.01), (0.4, 0.02)], [(0.0, 0.68), (0.4, 0.68)]]),
    'a': (0.62, [arc(0.27, 0.34, 0.27, 0.34, 0, 360, 14), [(0.54, 0.68), (0.54, 0.0)]]),
    'c': (0.56, [arc(0.3, 0.34, 0.3, 0.34, 50, 310, 12)]),
    'k': (0.54, [[(0.05, 1.0), (0.05, 0.0)], [(0.45, 0.68), (0.05, 0.28)], [(0.2, 0.43), (0.5, 0.0)]]),
    'C': (0.8, [arc(0.42, 0.5, 0.42, 0.5, 52, 308, 14)]),
    'h': (0.6, [[(0.05, 1.0), (0.05, 0.0)], _ARCH]),
    'n': (0.6, [[(0.05, 0.68), (0.05, 0.0)], _ARCH]),
    'E': (0.7, [arc(0.42, 0.5, 0.42, 0.5, 52, 308, 14), [(0.1, 0.5), (0.55, 0.5)]]),
    'o': (0.7, [arc(0.3, 0.5, 0.3, 0.3, 0, 360, 14)]),
    '7': (0.7, [[(0.05, 1.0), (0.62, 1.0), (0.25, 0.0)]]),
    'A': (0.8, [[(0.02, 0.0), (0.38, 1.0), (0.74, 0.0)], [(0.16, 0.36), (0.6, 0.36)]]),
    'W': (1.05, [[(0.0, 1.0), (0.24, 0.0), (0.5, 0.75), (0.76, 0.0), (1.0, 1.0)]]),
    'V': (0.8, [[(0.02, 1.0), (0.38, 0.0), (0.74, 1.0)]]),
    '0': (0.7, [arc(0.32, 0.5, 0.28, 0.5, 0, 360, 12)]),
    '1': (0.5, [[(0.08, 0.78), (0.3, 1.0), (0.3, 0.0)]]),
    '2': (0.7, [[(0.06, 0.78), (0.2, 0.97), (0.44, 0.97), (0.58, 0.78), (0.5, 0.52), (0.04, 0.0), (0.62, 0.0)]]),
    '4': (0.7, [[(0.5, 0.0), (0.5, 1.0), (0.04, 0.32), (0.64, 0.32)]]),
    '6': (0.7, [[(0.54, 0.92), (0.32, 1.0), (0.12, 0.8), (0.06, 0.4), (0.14, 0.1), (0.32, 0.0), (0.52, 0.1), (0.6, 0.32), (0.5, 0.54), (0.3, 0.6), (0.1, 0.46)]]),
    '8': (0.7, [arc(0.32, 0.76, 0.22, 0.24, 0, 360, 10), arc(0.32, 0.27, 0.27, 0.27, 0, 360, 10)]),
    'C': (0.75, [arc(0.4, 0.5, 0.36, 0.5, 55, 305, 10)]),
    '.': (0.3, [[(0.1, 0.0), (0.1, 0.12)]]),
    ' ': (0.45, []),
    'P': (0.7, [[(0.05, 0.0), (0.05, 1.0), (0.4, 1.0), (0.58, 0.86), (0.58, 0.64), (0.4, 0.5), (0.05, 0.5)]]),
    'M': (1.1, [[(0.05, 0.0), (0.05, 1.0), (0.52, 0.25), (1.0, 1.0), (1.0, 0.0)]]),
    '5': (0.75, [[(0.62, 1.0), (0.1, 1.0), (0.06, 0.55), (0.34, 0.62), (0.56, 0.52), (0.64, 0.3), (0.54, 0.08), (0.32, 0.0), (0.06, 0.1)]]),
}


def lettering(text, size, weight, gap=0.14):
    """Quads (four (along, up) points each) that draw `text` in strokes, and the length of the line."""
    quads, x = [], 0.0
    h = weight / 2.0
    for ch in text:
        adv, strokes = STROKES[ch]
        for line in strokes:
            for (ax, ay), (bx, by) in zip(line, line[1:]):
                ax, ay, bx, by = x + ax * size, ay * size, x + bx * size, by * size
                ln = math.hypot(bx - ax, by - ay)
                if ln == 0.0:
                    continue
                dx, dy = (bx - ax) / ln * h, (by - ay) / ln * h
                quads.append([(ax - dx + dy, ay - dy - dx), (bx + dx + dy, by + dy - dx), (bx + dx - dy, by + dy + dx), (ax - dx - dy, ay - dy + dx)])
        x += (adv + gap) * size
    return quads, x - gap * size


# ---- mesh packing
def index_mesh(tris, origin):
    """Weld triangles (model mm, world) into positions, normals and indices, local to `origin`, in meters.

    Corners at one position share a vertex when their face normals are within 30 degrees, so curved faces shade smooth
    and edges stay sharp."""
    cos_lim = math.cos(math.radians(30.0))
    groups, pos, nsum, idx = {}, [], [], []
    for t in tris:
        q = [(int(round((t[i] - origin[0]) * 1000.0)), int(round((t[i + 1] - origin[1]) * 1000.0)), int(round((t[i + 2] - origin[2]) * 1000.0)))
             for i in (0, 3, 6)]  # microns
        e = [q[1][i] - q[0][i] for i in range(3)]
        g = [q[2][i] - q[0][i] for i in range(3)]
        n = (e[1] * g[2] - e[2] * g[1], e[2] * g[0] - e[0] * g[2], e[0] * g[1] - e[1] * g[0])
        ln = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])
        if ln == 0.0:
            continue
        u = (n[0] / ln, n[1] / ln, n[2] / ln)
        for c in q:
            found = -1
            for seed, vi in groups.setdefault(c, []):
                if seed[0] * u[0] + seed[1] * u[1] + seed[2] * u[2] > cos_lim:
                    found = vi
                    break
            if found < 0:
                found = len(pos)
                groups[c].append((u, found))
                pos.append(c)
                nsum.append([0.0, 0.0, 0.0])
            s = nsum[found]
            s[0] += n[0]
            s[1] += n[1]
            s[2] += n[2]
            idx.append(found)
    normals = []
    for s in nsum:
        ln = math.sqrt(s[0] * s[0] + s[1] * s[1] + s[2] * s[2]) or 1.0
        normals.append((round(s[0] / ln, 4), round(s[1] / ln, 4), round(s[2] / ln, 4)))
    return [(c[0] / 1e6, c[1] / 1e6, c[2] / 1e6) for c in pos], normals, idx


class Glb:
    def __init__(self):
        self.bin = bytearray()
        self.views, self.accessors, self.meshes, self.nodes = [], [], [], []
        self.mat = {m[0]: i for i, m in enumerate(MATERIALS)}

    def _view(self, data, target):
        while len(self.bin) % 4:
            self.bin.append(0)
        self.views.append({'buffer': 0, 'byteOffset': len(self.bin), 'byteLength': len(data), 'target': target})
        self.bin += data
        return len(self.views) - 1

    def _acc(self, view, comp, count, kind, lo=None, hi=None):
        a = {'bufferView': view, 'componentType': comp, 'count': count, 'type': kind}
        if lo is not None:
            a['min'], a['max'] = lo, hi
        self.accessors.append(a)
        return len(self.accessors) - 1

    def primitive(self, tris, origin, material, uvs=None):
        pos, nrm, idx = index_mesh(tris, origin)
        if not idx:
            raise ValueError('a mesh for material %s is empty: check the source files against SOURCE.md' % material)
        f32 = struct.Struct('<3f')
        pv = self._view(b''.join(f32.pack(*p) for p in pos), 34962)
        lo = [min(struct.unpack('<f', struct.pack('<f', p[i]))[0] for p in pos) for i in range(3)]
        hi = [max(struct.unpack('<f', struct.pack('<f', p[i]))[0] for p in pos) for i in range(3)]
        attrs = {'POSITION': self._acc(pv, 5126, len(pos), 'VEC3', lo, hi)}
        attrs['NORMAL'] = self._acc(self._view(b''.join(f32.pack(*n) for n in nrm), 34962), 5126, len(nrm), 'VEC3')
        if uvs is not None:
            attrs['TEXCOORD_0'] = self._acc(self._view(b''.join(struct.pack('<2f', *uvs[p]) for p in pos), 34962), 5126, len(pos), 'VEC2')
        if len(pos) < 65536:
            iv, comp = self._view(struct.pack('<%dH' % len(idx), *idx), 34963), 5123
        else:
            iv, comp = self._view(struct.pack('<%dI' % len(idx), *idx), 34963), 5125
        return {'attributes': attrs, 'indices': self._acc(iv, comp, len(idx), 'SCALAR'), 'material': self.mat[material]}

    def mesh(self, name, primitives):
        self.meshes.append({'name': name, 'primitives': primitives})
        return len(self.meshes) - 1

    def node(self, name, parent=None, translation=None, mesh=None, extras=None):
        n = {'name': name}
        if translation is not None and any(abs(v) > 0 for v in translation):
            n['translation'] = [round(v / 1000.0, 6) for v in translation]
        if mesh is not None:
            n['mesh'] = mesh
        if extras:
            n['extras'] = extras
        self.nodes.append(n)
        i = len(self.nodes) - 1
        if parent is not None:
            self.nodes[parent].setdefault('children', []).append(i)
        return i

    def pack(self):
        doc = {'asset': {'version': '2.0', 'generator': 'make_body.py'},
               'scene': 0, 'scenes': [{'name': 'stackchan', 'nodes': [0]}], 'nodes': self.nodes, 'meshes': self.meshes,
               'materials': [], 'accessors': self.accessors, 'bufferViews': self.views}
        for name, col, metal, rough, emis in MATERIALS:
            m = {'name': name, 'pbrMetallicRoughness': {'baseColorFactor': list(col), 'metallicFactor': metal, 'roughnessFactor': rough}}
            if emis:
                m['emissiveFactor'] = list(emis)
            doc['materials'].append(m)
        for i in range(LIGHTS):
            doc['materials'].append({'name': 'ring_light_%d' % i, 'emissiveFactor': [0.0, 0.0, 0.0],
                                     'pbrMetallicRoughness': {'baseColorFactor': list(LIGHT_OFF), 'metallicFactor': 0.0, 'roughnessFactor': 0.35}})
            self.mat['ring_light_%d' % i] = len(MATERIALS) + i
        while len(self.bin) % 4:
            self.bin.append(0)
        doc['buffers'] = [{'byteLength': len(self.bin)}]
        js = json.dumps(doc, sort_keys=True, separators=(',', ':')).encode('ascii')
        js += b' ' * (-len(js) % 4)
        body = struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(self.bin), 0x004E4942) + bytes(self.bin)
        return b'glTF' + struct.pack('<II', 2, 12 + len(body)) + body


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def bounds(tris):
    return ([min(t[i + k] for t in tris for i in (0, 3, 6)) for k in range(3)], [max(t[i + k] for t in tris for i in (0, 3, 6)) for k in range(3)])


def assemble():
    """Returns (glb bytes, params dict)."""
    geo = {'base': {}, 'neck': {}, 'head': {}, 'bar_left': {}, 'bar_right': {}}
    hashes, tri_count = {}, 0
    for name, node, material, place in PARTS:
        path = os.path.join(HERE, 'source', 'StackChan-%s.stl' % name)
        hashes['StackChan-%s.stl' % name] = hashlib.sha256(open(path, 'rb').read()).hexdigest()
        raw = softrender.read_stl(path)
        tri_count += len(raw)
        out = geo[node].setdefault(material, [])
        for t in raw:
            out.append(world(place(t[0:3])) + world(place(t[3:6])) + world(place(t[6:9])))

    # ---- stand-ins for what the structure files do not hold (model mm)
    head_lo, head_hi = bounds(geo['head']['shell'])
    front = head_hi[2]                                        # front edge of the head shell
    shell_depth = head_hi[2] - head_lo[2]
    core_depth = PUBLISHED['depth_mm'] - shell_depth
    cy = (head_lo[1] + head_hi[1]) / 2.0                      # head center height (the nod axis height)
    top = head_hi[1]
    face = front + core_depth
    under = top - 54.0                                        # underside of the controller
    z0, z1 = front, face - 0.2                                # the controller's plastic, front to back
    core = [t for t in prism(rounded_outline(54.0, 54.0, CORE_R_MM), 0.0, cy, z0, z1)
            if not (max(abs(t[i] + 27.0) for i in (0, 3, 6)) < 1e-6 or max(abs(t[i] - under) for i in (1, 4, 7)) < 1e-6)]
    geo['head']['glass'] = prism(rounded_outline(51.6, 51.6, 3.0), 0.0, cy, face - 0.2, face)
    row = top - 54.0 + 5.9                                    # camera, microphones and light sensor sit in one row under the screen
    geo['head']['camera'] = prism(circle(2.1), 0.0, row, face, face + 0.03)
    dots = prism(circle(1.75), 0.0, row, face + 0.03, face + 0.05)    # the dark lens inside the ring
    geo['head']['button'] = prism(circle(0.5, 10), 0.0, row, face + 0.05, face + 0.06)   # the glint in the middle of the lens
    geo['head']['print'] = band(lambda u, v, c: (u, v, face + 0.055 + c), moved(circle(1.2, 16), 0.0, row), moved(circle(1.02, 16), 0.0, row), 0.0)   # a ring inside the lens: it is a small dome (owner's close-up)
    geo['head']['pin_gold'] = []
    for dx in (7.1, 9.6):                                     # two tiny gold dots beside the camera, on the robot's left (owner's front photo)
        geo['head']['pin_gold'] += prism(circle(0.3, 8), dx, row, face, face + 0.03)
    for dx in (-14.6, 14.9):                                  # the two microphone holes, dark with a thin rim (owner's front photo)
        dots += prism(circle(0.45, 10), dx, row, face + 0.03, face + 0.05)
        geo['head'].setdefault('print', [])
        geo['head']['print'] += prism(circle(0.65, 10), dx, row, face, face + 0.03)
    for c, behind in enumerate((5.6, 7.7, 9.7)):              # speaker grille on the robot's left side: 26 holes in three staggered columns (owner's side photo)
        for r in range(8 if c == 1 else 9):
            dots += disc_x((27.02, top - 8.4 - 3.2 * r - (1.6 if c == 1 else 0.0), face - behind), 0.43, 1, 10)
    dots += quad_x(1, 27.02, top - 45.0, top - 38.0, front + 0.1, front + 1.0)   # the dark notch at the seam under the grille
    geo['head']['port'] = dots
    prints = geo['head'].pop('print', [])                     # small gray marks printed on the controller

    # ---- the controller's right side (-X): real openings for the button, the USB-C socket and port A (sizes and places from the side photo)
    def side(u, v, c):                                        # u up, v toward the front, c out of the side
        return (-27.0 - c, u, v)
    button_c = (-27.0, top - 14.0, face - 8.0)
    otg_c = (-27.0, top - 27.5, face - 7.8)
    port_a_c = (-27.0, top - 41.7, face - 8.6)
    well = moved(rounded_outline(7.1, 9.7, 2.3), button_c[1], button_c[2])
    otg_hole = moved(rounded_outline(9.2, 3.3, 1.64), otg_c[1], otg_c[2])
    a_hole = moved(rounded_outline(10.5, 5.3, 0.5), port_a_c[1], port_a_c[2])
    a_room = moved(rounded_outline(8.9, 3.7, 0.3), port_a_c[1], port_a_c[2])
    cuts = [cy - 23.0, top - 34.3, top - 20.2, cy + 23.0]
    for (u0, u1), hole in zip(zip(cuts, cuts[1:]), (a_hole, otg_hole, well)):
        core += holed(side, u0, u1, z0, z1, hole)
    geo['head']['port'] += tube(side, well, 0.0, -0.8) + flat(side, well, -0.8)          # the dark gap round the button
    # The key (owner's close-ups): a tongue narrower than its opening, with a dark gap at the back and down both sides. Its back part sits
    # low in the opening; a step lifts the front part level with the housing, where the tongue joins it with no gap.
    key = moved(rounded_outline(5.3, 9.05, 1.8), button_c[1], button_c[2] + 0.33)
    split = button_c[2] + 1.6
    back_part, front_part = clipped(key, 1, split, True), clipped(key, 1, split, False)
    button_tris = tube(side, back_part, -0.8, -0.45) + flat(side, back_part, -0.45) + tube(side, front_part, -0.8, 0.0) + flat(side, front_part, 0.0)   # flush with the housing: nothing stands proud (owner)
    # the power mark above the key: a ring open toward the front, with a short line from its middle out through the opening
    pc = (top - 8.2, face - 8.0)
    prints += stroke(side, [(pc[0] + 0.8 * math.sin(math.radians(a)), pc[1] + 0.8 * math.cos(math.radians(a))) for a in range(40, 321, 20)], 0.22, 0.02)
    prints += stroke(side, [(pc[0], pc[1] + 0.1), (pc[0], pc[1] + 1.0)], 0.22, 0.02)
    for k in range(4):                                        # the pin marks beside port A
        prints += flat(side, [(top - 38.6 - 2.0 * k, face - 4.6), (top - 39.5 - 2.0 * k, face - 4.6), (top - 39.5 - 2.0 * k, face - 4.2), (top - 38.6 - 2.0 * k, face - 4.2)], 0.02)
    otg_in = moved(rounded_outline(8.6, 2.7, 1.34), otg_c[1], otg_c[2])
    otg = {'port_metal': band(side, otg_hole, otg_in, -0.15) + tube(side, otg_hole, 0.0, -0.15) + tube(side, otg_in, -0.15, -5.5), 'port': flat(side, otg_in, -5.5),
           'tongue': slab(side, otg_c[1] - 3.3, otg_c[1] + 3.3, otg_c[2] - 0.35, otg_c[2] + 0.35, -5.5, -1.2),
           'pin_gold': []}
    for k in range(8):                                        # the row of contacts on each face of the tongue
        u = otg_c[1] - 2.45 + 0.7 * k
        for sv in (-1, 1):
            otg['pin_gold'] += slab(side, u - 0.2, u + 0.2, otg_c[2] + sv * 0.35, otg_c[2] + sv * 0.41, -4.8, -1.5)
    port_a = {'port_red': tube(side, a_hole, 0.0, -0.25) + band(side, a_hole, a_room, -0.25) + tube(side, a_room, -0.25, -5.0) + flat(side, a_room, -5.0), 'pin_gold': []}
    for k in range(4):                                        # four square pins standing in the socket
        u = port_a_c[1] - 3.0 + 2.0 * k
        port_a['pin_gold'] += slab(side, u - 0.3, u + 0.3, port_a_c[2] - 0.3, port_a_c[2] + 0.3, -5.0, -1.6)
    for du in (-2.6, 2.6):                                    # the two plastic keys on the socket's back wall
        port_a['port_red'] += slab(side, port_a_c[1] + du - 0.5, port_a_c[1] + du + 0.5, port_a_c[2] - 1.85, port_a_c[2] - 1.25, -5.0, -0.25)

    # ---- under the controller: card slot, light hole, two short slots and the reset button (places from the underside photo, as shares of the depth)
    def below(u, v, c):                                       # u toward the robot's left, v toward the front, c down
        return (u, under - c, v)
    sd_c = (-6.8, under, face - 7.0)
    reset_c = (15.0, under, face - 6.6)
    led_bottom_c = (6.8, under - 0.02, face - 6.6)
    sd_hole = moved(rounded_outline(12.9, 1.3, 0.4), sd_c[0], sd_c[2])
    reset_well = moved(rounded_outline(8.6, 6.4, 3.19, 8), reset_c[0], reset_c[2])   # a pill-shaped opening (owner's close-up)
    slots = [moved(rounded_outline(0.8, 2.9, 0.38, 4), dx, face - 11.0) for dx in (5.6, 7.5)]
    cuts = [-23.0, 1.0, 6.55, 9.5, 23.0]
    for (u0, u1), hole in zip(zip(cuts, cuts[1:]), (sd_hole, slots[0], slots[1], reset_well)):
        core += holed(below, u0, u1, z0, z1, hole)
    slot_tris = [tube(below, sl, 0.0, -1.5) + flat(below, sl, -1.5) for sl in slots]
    prints_under = band(below, moved(circle(3.4, 24), sd_c[0], sd_c[2]), moved(circle(3.25, 24), sd_c[0], sd_c[2]), 0.02)   # the rim of the round finger recess behind the card slot
    geo['head']['port'] += tube(below, reset_well, 0.0, -0.8) + flat(below, reset_well, -0.8)
    sd_tris = tube(below, sd_hole, 0.0, -3.0) + flat(below, sd_hole, -3.0)
    sd_pins = []                                              # the row of card contacts inside the slot
    for k in range(8):
        sd_pins += slab(below, sd_c[0] - 3.85 + 1.1 * k, sd_c[0] - 3.35 + 1.1 * k, sd_c[2] + 0.45, sd_c[2] + 0.6, -2.8, -1.2)
    # the reset key has the same lift: a tongue in a pill-shaped opening, low at the end toward the light, stepped up level with the housing
    # at the end toward its mark, where it joins with no gap
    reset_cap = moved(rounded_outline(7.9, 4.6, 2.29, 8), reset_c[0] + 0.35, reset_c[2])
    low, high = clipped(reset_cap, 0, reset_c[0] + 0.8, True), clipped(reset_cap, 0, reset_c[0] + 0.8, False)
    reset_tris = tube(below, low, -0.8, -0.45) + flat(below, low, -0.45) + tube(below, high, -0.8, 0.0) + flat(below, high, 0.0)   # flush with the housing
    led_bottom_tris = flat(below, moved(circle(0.5, 12), led_bottom_c[0], led_bottom_c[2]), 0.02)
    rc = (21.0, face - 6.6)                                   # the restart mark beside the key: an open ring that ends in an arrowhead
    ring_pts = [(rc[0] + 0.85 * math.cos(math.radians(a)), rc[1] + 0.85 * math.sin(math.radians(a))) for a in range(70, 351, 20)]
    prints += stroke(below, ring_pts, 0.22, 0.02)
    tip_a = math.radians(70)
    prints += flat(below, [(rc[0] + 0.45 * math.cos(tip_a), rc[1] + 0.45 * math.sin(tip_a)), (rc[0] + 1.25 * math.cos(tip_a), rc[1] + 1.25 * math.sin(tip_a)),
                           (rc[0] + 0.85 * math.cos(tip_a) + 0.6 * math.sin(tip_a), rc[1] + 0.85 * math.sin(tip_a) - 0.6 * math.cos(tip_a))], 0.02)
    quads, length = lettering('M5', 6.0, 0.8)                  # the raised two-character mark on the speaker side, under the grille (side photo)
    geo['head']['emboss'] = []
    for quad in quads:
        geo['head']['emboss'] += flat(lambda u, v, c: (27.0 + c, u, v), [(top - 49.0 + a, face - 11.3 + b) for a, b in quad], 0.03)
    # The controller sits tight against the shell on the real unit: no gap and nothing seen through the seam. A plate just inside the shell's
    # front edge closes the joint all round (the shell file's front lip is rounded, which otherwise leaves a slit).
    core += prism(rounded_outline(53.2, 53.2, 3.7), 0.0, cy, front - 0.45, front + 0.05)
    geo['head']['core'] = core
    geo['head']['print'] = prints + prints_under

    # ---- the two connectors in the top openings: black on the robot's right, teal on its left; each an open socket with four pins
    def above(u, v, c):
        return (u, top - 0.3 + c, v)
    # Each connector, from the owner's two close-ups (seen from the front, looking back): thick side walls with a deep pocket inside each,
    # four square pins standing on the floor near the front, a low cross bar behind the pins, two inner posts with stepped tops, and
    # between the posts, behind the bar, a wide window with no floor: the inside of the head shows through it. The connector does not
    # reach the back of the shell's opening, so a ledge of the shell's own gray shows behind the window.
    for sx, material in ((-11.0, 'port'), (11.0, 'port_teal')):
        geo['head'].setdefault(material, [])
        part = geo['head'][material]
        zr, zf = front - 5.3, front - 0.7                              # back and front of the connector
        for sgn in (-1, 1):
            x_out, x_in = sorted((sx + sgn * 5.1, sx + sgn * 4.5))
            part += slab(above, x_out, x_in, zr, zf, -2.0, 0.0)                                         # outer side wall
            x0, x1 = sorted((sx + sgn * 4.5, sx + sgn * 2.4))
            part += slab(above, x0, x1, zr, zr + 0.45, -2.0, 0.0)                                       # back wall behind the pocket
            x0, x1 = sorted((sx + sgn * 3.4, sx + sgn * 2.4))
            part += slab(above, x0, x1, zr + 0.45, front - 3.5, -2.0, -0.25)                            # inner post, a step lower
            x0, x1 = sorted((sx + sgn * 5.1, sx + sgn * 3.0))
            part += slab(above, x0, x1, zf - 0.6, zf, -2.0, -0.35)                                      # low front stub
        part += slab(above, sx - 2.4, sx + 2.4, front - 3.9, front - 3.5, -2.0, -1.2)                   # the low cross bar behind the pins
        part += slab(above, sx - 4.5, sx + 4.5, front - 3.5, zf, -2.3, -2.0)                            # the floor under the pins
        for sgn in (-1, 1):
            x0, x1 = sorted((sx + sgn * 4.5, sx + sgn * 3.4))
            part += slab(above, x0, x1, zr + 0.45, front - 3.5, -2.3, -2.0)                             # the floor of each side pocket
        geo['head']['shell'] += both(quad_y(1, top - 1.0, sx - 5.1, sx + 5.1, front - 7.15, zr))        # the shell's gray ledge behind the connector
        for k in range(4):                                                                              # four square pins, bright at the tips
            geo['head'].setdefault('port_metal', [])
            geo['head']['port_metal'] += slab(above, sx - 3.3 + 2.0 * k, sx - 2.7 + 2.0 * k, front - 2.6, front - 2.0, -2.0, -0.7)
    geo['head']['port'] += slab(above, -2.2, 2.2, front - 7.6, front - 0.4, -2.2, -2.0)
    geo['head']['glass'] += slab(above, -0.5, 0.5, front - 1.9, front - 0.5, 0.28, 0.31)   # the small clear window beside the round hole (owner's top photo)   # dark behind the two small windows between the connectors

    # ---- the dark shapes between the three round side openings (through the shell wall; black in the photos)
    for sx in (-1, 1):
        for zc in (-5.35, 2.65):
            steps = [-3.6 + 0.45 * i for i in range(17)]
            half = [min(1.7, 4.0 - math.sqrt(max(0.0, 3.1 * 3.1 - dy * dy))) for dy in steps]
            for (d0, w0), (d1, w1) in zip(zip(steps, half), zip(steps[1:], half[1:])):
                geo['head']['port'] += both([(sx * 26.5, 60.5 + d0, zc - w0, sx * 26.5, 60.5 + d0, zc + w0, sx * 26.5, 60.5 + d1, zc + w1),
                                             (sx * 26.5, 60.5 + d0, zc - w0, sx * 26.5, 60.5 + d1, zc + w1, sx * 26.5, 60.5 + d1, zc - w1)])

    # ---- the boards in the head, seen through the open back (positions assumed; they clear the servo housing over the whole sweep)
    # The ring board: the dark plate under the head top that carries the 12 lights (owner's photo of the open back, lights on). Its small
    # lights sit in a row along each side edge, on the underside, and fire sideways into the frosted bar in that top corner.
    ring_z0, ring_z1 = head_lo[2] + 9.0, front - 1.5
    ring_c = (0.0, top - 3.1, (ring_z0 + ring_z1) / 2.0)
    ring_under = top - 3.7
    ring_board = {'pcb': box(ring_c, (45.0, 1.2, ring_z1 - ring_z0)), 'chip': [], 'conn': [], 'port': [], 'conn_green': []}
    for x, z, w, d, t, material in ((-6.0, 2.0, 3.0, 3.0, 0.8, 'chip'), (4.0, -6.0, 2.0, 4.0, 0.7, 'chip'), (-12.0, -9.0, 1.2, 2.0, 0.6, 'conn'), (9.0, 6.0, 1.0, 2.0, 0.6, 'conn')):
        ring_board[material] += box((x, ring_under - t / 2, z), (w, t, d))
    for dz in (4.6, 9.2, 13.3):                                                                  # three small square parts in a row down the middle (owner's photo of the board)
        ring_board['chip'] += box((0.0, ring_under - 0.3, ring_z0 + dz), (1.0, 0.6, 1.0))
    ring_board['port'] += box((-10.2, ring_under - 2.2, front - 4.6), (8.6, 4.4, 5.6))            # the body of the black top connector, under the board
    green_c = (11.0, ring_under - 2.2, front - 4.6)                                              # the mint green body of the other top connector (owner's photo)
    green_tris = box(green_c, (10.2, 4.4, 5.6))
    for k4 in range(4):                                                                          # its four solder tails
        green_tris += box((11.0 - 3.0 + 2.0 * k4, ring_under - 4.9, front - 5.6), (0.6, 1.0, 0.6))
    ring_leds = []                                                                               # (center, triangles) for lights 0..11, in the order of ring_light_N
    for i in range(LIGHTS):
        side_x = 1 if i < 6 else -1
        along = (-12.5 + 5.0 * i) if i < 6 else (12.5 - 5.0 * (i - 6))
        c = (side_x * 21.3, ring_under - 0.45, -(BAR_Y + along - YAW_Y))
        ring_leds.append((c, box(c, (1.4, 0.9, 2.2))))
    zb = front - 1.7                                          # the back of the upright board
    # The upright board and what is on it, laid out from the owner's close photo of the open back (board-7p-flex-ribbon-lit). Places are
    # read off the photo at about 30 pixels per millimeter: `left` is millimeters toward the robot's left of the middle, `down` is
    # millimeters below the underside of the ring board. Sizes are to about half a millimeter; heights off the board are assumed.
    board_7p = {'pcb': box((0.0, cy + 1.0, front - 1.1), (48.0, 46.0, 1.2)), 'silk': [], 'trace': []}

    def onboard(u, v, c):                                     # u toward the robot's left, v up, c out of the board toward the back
        return (u, v, zb - c)

    # Everything below is placed in millimeters measured in the owner's close photo of the open back (board-7p-flex-ribbon-lit): `left`
    # is toward the robot's left of the cable socket's middle, `down` is below the underside of the ring board. The photo gives about
    # 24 pixels per millimeter (the four-pin connector is 10 mm wide), so places are good to about 0.3 mm. Heights off the board are assumed.
    def at(left, down, w, h, c0, c1):                         # a block on the board: centered `left` and `down`, w across, h tall
        return slab(onboard, left - w / 2, left + w / 2, ring_under - down - h / 2, ring_under - down + h / 2, c0, c1)

    def mark(left, down, w, h, c=0.02):                       # a flat mark printed or etched on the board
        return flat(onboard, [(left - w / 2, ring_under - down - h / 2), (left + w / 2, ring_under - down - h / 2), (left + w / 2, ring_under - down + h / 2), (left - w / 2, ring_under - down + h / 2)], c)

    def line(pts, w, c=0.015):                                # a thin line through (left, down) points
        return stroke(onboard, [(a, ring_under - b) for a, b in pts], w, c)

    def frame(left, down, w, h, m=0.25, t=0.1):               # the thin white frame printed round a part
        return (mark(left, down - h / 2 - m, w + 2 * m + t, t) + mark(left, down + h / 2 + m, w + 2 * m + t, t)
                + mark(left - w / 2 - m, down, t, h + 2 * m) + mark(left + w / 2 + m, down, t, h + 2 * m))

    def text(word, left, down, size, weight, c=0.025, upward=False):
        """Print on the board, read from behind: left to right, or (upward) bottom to top with the letter tops toward the robot's left."""
        quads, length = lettering(word, size, weight)
        out = []
        for quad in quads:
            pts = [(left + b, ring_under - down + a) for a, b in quad] if upward else [(left - a, ring_under - down + b) for a, b in quad]
            out += flat(onboard, pts, c)
        return out

    def part(kind, left, down, w, h, t, ends=0.0, framed=False):
        """A small surface part: a body of `kind`, bright solder ends when `ends` is given, a printed frame when asked."""
        board_parts[kind] += at(left, down, w, h, 0.0, t)
        if ends:
            horizontal = w >= h
            for sg in (-1, 1):
                if horizontal:
                    board_parts['port_metal'] += at(left + sg * (w / 2 - ends / 2), down, ends, h, 0.0, t + 0.02)
                else:
                    board_parts['port_metal'] += at(left, down + sg * (h / 2 - ends / 2), w, ends, 0.0, t + 0.02)
        if framed:
            board_7p['silk'] += frame(left, down, w, h)
    board_parts = {'chip': [], 'conn': [], 'cap_tan': [], 'pin_gold': [], 'port_metal': [], 'ribbon': []}
    # sockets along the top edge, under the ring board
    board_parts['chip'] += at(0.8, 2.1, 10.0, 4.2, 0.0, 3.0)                    # the black housing the eight-wire cable plugs into
    for k4 in range(4):                                                        # the pins of the black top connector beside it
        board_parts['port_metal'] += at(-7.2 - 2.0 * k4, 4.9, 0.7, 1.3, 0.0, 0.6)
    board_parts['conn'] += at(-15.9, 0.9, 5.0, 1.8, 0.0, 1.4)                   # the flat cable's socket: a pale body with a dark latch
    board_parts['chip'] += at(-15.9, 1.9, 5.0, 0.4, 0.0, 1.5)
    for k4 in range(4):                                                        # the four tails of the blue connector, soldered to the board
        board_parts['port_metal'] += at(8.0 + 2.0 * k4, 4.9, 0.7, 1.3, 0.0, 0.6)
        board_7p['trace'] += mark(8.0 + 2.0 * k4, 5.2, 1.2, 1.7, 0.012)
    post = moved(circle(1.35, 16), 18.1, ring_under - 0.9)                      # a cream standoff with a hole, beside the blue connector
    board_parts['conn'] += tube(onboard, post, 0.0, 2.6) + band(onboard, post, moved(circle(0.6, 16), 18.1, ring_under - 0.9), 2.6)
    board_parts['chip'] += flat(onboard, moved(circle(0.6, 16), 18.1, ring_under - 0.9), 2.55)
    # left of the cable: the print 7P, a square chip, two capacitors, a row of tiny parts, a three-legged part
    board_7p['silk'] += text('7P', 8.4, 8.4, 0.95, 0.14)
    board_parts['cap_tan'] += at(5.0, 7.9, 1.3, 2.2, 0.0, 0.25)                 # a strip of tan tape at the cable's side
    part('chip', 11.5, 12.0, 3.4, 3.2, 0.75, framed=True)
    for sg in (-1, 1):                                                          # the chip's legs: a row of bright dashes on two sides
        for k5 in range(5):
            board_parts['port_metal'] += at(11.5 + sg * 1.75, 10.8 + 0.6 * k5, 0.22, 0.3, 0.0, 0.2)
    part('cap_tan', 8.2, 11.5, 1.5, 3.0, 0.8, ends=0.55, framed=True)
    part('cap_tan', 6.5, 11.5, 1.5, 3.0, 0.8, ends=0.55, framed=True)
    for k4 in range(4):
        part('chip', 8.9 - 1.15 * k4, 14.4, 0.7, 0.95, 0.35, ends=0.22)
    part('chip', 10.9, 15.8, 1.4, 2.2, 0.8)
    for dl, dd in ((-0.45, -1.35), (0.45, -1.35), (0.0, 1.35)):                 # its three legs
        board_parts['port_metal'] += at(10.9 + dl, 15.8 + dd, 0.4, 0.5, 0.0, 0.25)
    part('chip', 13.6, 15.2, 0.8, 1.2, 0.35, ends=0.25, framed=True)
    part('chip', 12.6, 16.6, 1.1, 0.7, 0.35, ends=0.25)
    # right of the cable: one capacitor above three, a pale part, small ones
    part('cap_tan', -8.6, 8.8, 1.4, 2.6, 0.8, ends=0.5, framed=True)
    for dn in (11.2, 12.75, 14.3):
        part('cap_tan', -8.6, dn, 2.3, 1.15, 0.8, ends=0.5, framed=True)
    part('conn', -4.8, 12.7, 1.5, 1.5, 0.5)
    part('chip', -5.6, 9.2, 0.7, 1.0, 0.35, ends=0.22)
    part('chip', -6.7, 15.6, 1.0, 0.6, 0.35, ends=0.25)
    # the left edge: two rows of paired holes with rings, and two lone holes above them
    for row_left in (20.4, 17.9):
        for dn in (11.0, 12.9, 14.8, 16.7):
            for off in (-0.42, 0.42):
                c2 = (row_left + off, ring_under - dn)
                board_7p['trace'] += band(onboard, moved(circle(0.5, 12), *c2), moved(circle(0.26, 12), *c2), 0.012)
                board_parts['chip'] += flat(onboard, moved(circle(0.26, 12), *c2), 0.014)
    for dn in (7.3, 8.8):
        c2 = (18.8, ring_under - dn)
        board_7p['trace'] += band(onboard, moved(circle(0.62, 14), *c2), moved(circle(0.3, 14), *c2), 0.012)
        board_parts['chip'] += flat(onboard, moved(circle(0.3, 14), *c2), 0.014)
    board_7p['trace'] += line([(21.6, 6.0), (21.6, 18.5)], 0.12) + line([(16.4, 6.0), (16.4, 18.5)], 0.12)   # the frame lines round the hole rows
    # the board's own lines: traces fanning from the cable socket and the chip, drawn a shade lighter than the board
    for k6 in range(6):
        board_7p['trace'] += line([(3.6 - 0.32 * k6, 4.6), (3.6 - 0.32 * k6, 5.4), (9.6 + 0.35 * k6, 7.2 - 0.25 * k6), (14.5, 7.2 - 0.25 * k6)], 0.11)
    for k5 in range(5):
        board_7p['trace'] += line([(-4.4 - 0.3 * k5, 4.9), (-4.4 - 0.3 * k5, 6.2 + 0.2 * k5), (-6.6 - 0.3 * k5, 7.6 + 0.2 * k5), (-11.5, 7.6 + 0.2 * k5)], 0.11)
    board_7p['trace'] += line([(13.2, 13.6), (14.6, 13.6), (15.4, 12.8), (15.4, 9.6)], 0.14) + line([(9.8, 12.9), (9.1, 12.9)], 0.3)
    board_7p['trace'] += line([(5.6, 13.2), (4.6, 14.2), (4.6, 17.5)], 0.14) + line([(-7.4, 15.0), (-5.2, 15.0), (-4.6, 15.6), (-4.6, 18.0)], 0.14)
    board_7p['trace'] += line([(-10.0, 11.2), (-11.6, 11.2), (-12.2, 11.8), (-12.2, 18.0)], 0.14) + line([(11.5, 13.7), (11.5, 14.6)], 0.3)
    for left, dn in ((2.5, 6.3), (-3.2, 7.0), (14.9, 8.6), (-11.0, 9.6), (7.4, 16.6), (-3.4, 16.4), (15.6, 17.4), (-10.6, 16.9)):   # vias
        board_7p['trace'] += flat(onboard, moved(circle(0.24, 8), left, ring_under - dn), 0.013)
    board_7p['silk'] += text('V1.0', -18.9, 5.2, 0.75, 0.11, upward=True) + text('4825', -20.1, 5.2, 0.75, 0.11, upward=True)
    # the white flat cable to the ring board: 4.1 mm wide, with its blue print reading upward, and bare contacts where it enters its socket
    flex = {'flex': [], 'flex_ink': [], 'port_metal': []}
    flex_x = -15.9
    flex['flex'] += at(flex_x, 9.4, 4.1, 15.4, 0.3, 0.42)
    flex['flex'] += slab(onboard, flex_x - 2.05, flex_x + 2.05, ring_under - 1.9, ring_under - 0.2, 0.42, 1.2)
    for k8 in range(8):
        flex['port_metal'] += at(flex_x - 1.75 + 0.5 * k8, 2.5, 0.22, 1.0, 0.42, 0.44)
    flex['flex_ink'] += text('AWM', flex_x - 1.1, 16.7, 1.35, 0.27, c=0.44, upward=True) + text('2062', flex_x - 1.1, 11.4, 1.35, 0.27, c=0.44, upward=True) + text('80C', flex_x - 1.0, 5.9, 1.0, 0.22, c=0.44, upward=True)
    # ---- inside the servo holder (assembly mm): two servos of the published size, stacked, and the battery behind the back cover
    L, W, H = SERVO_MM
    ax, ay = YAW_X, YAW_Y

    def abox(x0, x1, y0, y1, z0, z1):
        lo, hi = world((x0, y1, z0)), world((x1, y0, z1))
        return box([(lo[i] + hi[i]) / 2.0 for i in range(3)], [abs(hi[i] - lo[i]) for i in range(3)])

    def rod(axis, a0, a1, r, seg=16):
        """A round shaft along assembly X through the nod axis, or along assembly Z through the turn axis."""
        tris = []
        for i in range(seg):
            t0, t1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
            c0, s0, c1, s1 = r * math.cos(t0), r * math.sin(t0), r * math.cos(t1), r * math.sin(t1)
            if axis == 'x':
                q = [(a0, ay + c0, PITCH_Z + s0), (a1, ay + c0, PITCH_Z + s0), (a1, ay + c1, PITCH_Z + s1), (a0, ay + c1, PITCH_Z + s1)]
            else:
                q = [(ax + c0, ay + s0, a0), (ax + c1, ay + s1, a0), (ax + c1, ay + s1, a1), (ax + c0, ay + s0, a1)]
            w = [world(v) for v in q]
            tris += [w[0] + w[1] + w[2], w[0] + w[2] + w[3], w[0] + w[2] + w[1], w[0] + w[3] + w[2]]   # both sides: thin and half hidden
        return tris
    pitch_face = 19.5                                         # the tilt servo's output face, just inside the arm's spline boss
    servo_pitch = abox(ax + pitch_face - H, ax + pitch_face, ay - SERVO_SHAFT_INSET, ay - SERVO_SHAFT_INSET + L, PITCH_Z - W / 2, PITCH_Z + W / 2)
    servo_pitch += rod('x', ax + pitch_face, ax + pitch_face + 3.5, SERVO_SHAFT_R)
    yaw_top = PITCH_Z - W / 2                                 # the pan servo stands under the tilt servo, shaft down into the base socket
    servo_yaw = abox(ax + SERVO_SHAFT_INSET - L, ax + SERVO_SHAFT_INSET, ay - W / 2, ay + W / 2, yaw_top - H, yaw_top)
    servo_yaw += rod('z', -26.8 - BASE_DROP + 0.6, yaw_top - H, SERVO_SHAFT_R)
    bw, bh, bd = BATTERY_MM
    battery = abox(ax - bw / 2, ax + bw / 2, -301.8 - bd, -301.8, -19.5, -19.5 + bh)
    # the battery lead (red and black to a small plug) and the two servo leads (three wires each); paths assumed
    battery_lead = {'wire_red': abox(ax - 10.4, ax - 9.7, -306.2, -305.5, 0.5, 4.6), 'chip': abox(ax - 9.4, ax - 8.7, -306.2, -305.5, 0.5, 4.6),
                    'conn': abox(ax - 10.9, ax - 8.2, -306.9, -304.8, 4.6, 6.2)}
    servo_wires = {'chip': [], 'wire_red': [], 'conn': []}
    for k, material in enumerate(('chip', 'wire_red', 'conn')):
        servo_wires[material] += abox(ax - 18.0, ax - 17.3, ay - 1.5 + k, ay - 0.6 + k, -10.0, 3.0)             # beside the pan servo
        servo_wires[material] += abox(ax + 1.0 + k, ax + 1.9 + k, ay + 17.2, ay + 17.9, 3.3, 14.0)              # behind the tilt servo
    cable = []                                                # the same ribbon of eight black wires where it runs over the back of the holder (path assumed)
    path = [(-300.4, 9.0), (-299.6, 12.5), (-299.4, 15.5), (-300.4, 18.0), (-302.5, 19.6), (-305.4, 20.4), (-308.5, 20.7)]   # (assembly y, z)
    for wire in range(8):
        wx = ax - 0.3 + 3.71 - 1.06 * wire
        rings = []
        for n, (py, pz) in enumerate(path):
            a0, a1 = path[max(0, n - 1)], path[min(len(path) - 1, n + 1)]
            ty, tz = a1[0] - a0[0], a1[1] - a0[1]
            tl = math.hypot(ty, tz)
            ny, nz = -tz / tl, ty / tl
            rings.append([world((wx + 0.4 * math.cos(2 * math.pi * q / 12), py + 0.4 * math.sin(2 * math.pi * q / 12) * ny, pz + 0.4 * math.sin(2 * math.pi * q / 12) * nz)) for q in range(12)])
        for r0, r1 in zip(rings, rings[1:]):
            for q in range(12):
                a, b, c2, d = r0[q], r0[(q + 1) % 12], r1[(q + 1) % 12], r1[q]
                cable += both([a + b + c2, a + c2 + d])
    screen_c = (0.0, cy - SCREEN_DROP_MM, face + 0.03)

    def screw(f, u, v, r, c0, c1, socket=False):
        """A screw head in a frame: a round head from c0 to c1 with a cross on top, or a hex socket. Returns (head, mark)."""
        o = moved(circle(r, 14), u, v)
        if socket:
            return tube(f, o, c0, c1) + flat(f, o, c1), flat(f, moved(circle(r * 0.5, 6), u, v), c1 + 0.03)
        cross = slab(f, u - r * 0.62, u + r * 0.62, v - r * 0.13, v + r * 0.13, c1, c1 + 0.03) + slab(f, u - r * 0.13, u + r * 0.13, v - r * 0.62, v + r * 0.62, c1, c1 + 0.03)
        return tube(f, o, c0, c1) + flat(f, o, c1), cross

    # ---- labels: the unit's own name, marks and label artwork, drawn here in simple strokes so the model shows the real robot (owner's policy of
    # 2026-11-18, docs/plan/trademark-and-affiliation.md). They depict the hardware; they are not this project's branding. The small print is stand-in bars.
    stickers = {}
    lw, lh = 6.3, 43.0                                           # side labels: width, length (owner's side photo)
    for side_x, name in ((-1, 'sticker_side_right'), (1, 'sticker_side_left')):
        x = side_x * 27.04
        zc, yc = front - 1.2 - lw / 2, top - 5.6 - lh / 2

        def lab(p, q, c=0.0, x=x, zc=zc, yc=yc, side_x=side_x):   # p toward the front, q up
            return (x + side_x * c, yc + q, zc + p)
        o = rounded_outline(lw, lh, 1.0)
        n = len(o) // 2
        parts = {'sticker': flat(lab, o), 'sticker_dark': [], 'sticker_ink': []}
        if side_x < 0:                                            # dark end at the bottom on the button side, at the top on the other
            parts['sticker_dark'] = flat(lab, o[n:] + [(lw / 2, -lh / 2 + 12.4), (-lw / 2, -lh / 2 + 13.8)], 0.01)
            fq = -lh / 2 + 6.4
        else:
            parts['sticker_dark'] = flat(lab, o[:n] + [(-lw / 2, lh / 2 - 13.8), (lw / 2, lh / 2 - 12.4)], 0.01)
            fq = lh / 2 - 6.4
        for dq in (-2.85, 2.85):                                  # the little face in the dark end: two dots and a line
            parts['sticker'] += flat(lab, moved(circle(0.5, 10), 1.2, fq + dq), 0.02)
        parts['sticker'] += flat(lab, [(-1.1, fq - 1.85), (-0.75, fq - 1.85), (-0.75, fq + 1.85), (-1.1, fq + 1.85)], 0.02)
        quads, length = lettering('StackChan', 3.6, 0.52)
        for quad in quads:                                        # the name runs along the label with the letter tops toward the front
            if side_x < 0:
                pts = [(-lw / 2 + 1.4 + b, lh / 2 - 2.4 - a) for a, b in quad]
            else:
                pts = [(-lw / 2 + 1.4 + b, -lh / 2 + 2.4 + a) for a, b in quad]
            parts['sticker_ink'] += flat(lab, pts, 0.02)
        stickers[name] = (parts, (x, yc, zc))
    tx0, tx1, tz0, tz1 = -15.8, 0.5, front + 1.6, front + 13.9      # the rating label on top of the controller (top photo)

    def onlabel(u, v, c=0.0):
        return (u, top + 0.03 + c, v)
    parts = {'sticker': flat(onlabel, [(tx0, tz0), (tx0, tz1), (tx1, tz1), (tx1, tz0)]),
             'sticker_gray': flat(onlabel, [(tx0, tz0), (tx0, tz1), (tx0 + 2.3, tz1), (tx0 + 2.3, tz0)], 0.01), 'sticker_ink': []}
    for r, a0, a1 in dashes(2, tx0 + 3.2, tx1 - 0.8):
        parts['sticker_ink'] += flat(onlabel, [(a0, tz0 + 0.8 + r * 1.5), (a0, tz0 + 1.6 + r * 1.5), (a1, tz0 + 1.6 + r * 1.5), (a1, tz0 + 0.8 + r * 1.5)], 0.02)
    parts['sticker_ink'] += band(onlabel, moved(rounded_outline(3.6, 4.2, 0.2), tx0 + 5.0, tz1 - 3.2), moved(rounded_outline(3.0, 3.6, 0.2), tx0 + 5.0, tz1 - 3.2), 0.02)
    parts['sticker_ink'] += flat(onlabel, [(tx0 + 3.2, tz0 + 4.4), (tx0 + 3.2, tz0 + 5.0), (tx0 + 7.0, tz0 + 5.0), (tx0 + 7.0, tz0 + 4.4)], 0.02)
    quads, length = lettering('CE', 4.4, 0.7)
    for quad in quads:                                           # letter tops toward the front, as on the unit
        parts['sticker_ink'] += flat(onlabel, [(tx1 - 0.9 - a, tz1 - 5.6 + b) for a, b in quad], 0.02)
    stickers['sticker_top'] = (parts, ((tx0 + tx1) / 2.0, top + 0.03, (tz0 + tz1) / 2.0))
    # on the head top: the three zones of the head touch strip, front to back (count and order from the firmware; outlines assumed)
    pad_w, pad_d, pad_gap = 16.0, 8.0, 1.2
    pad_first = front - 15.5
    pads = [(0.0, top - 0.8, pad_first - i * (pad_d + pad_gap)) for i in range(3)]   # under the shell top: nothing shows on the outside of the real unit

    g = Glb()
    for i in range(LIGHTS):
        g.mat['ring_light_%d' % i] = len(MATERIALS) + i

    def prims(node):
        return [g.primitive(geo[node][m[0]], ORIGIN[node], m[0]) for m in MATERIALS if geo[node].get(m[0])]

    def many(parts, c):
        """Primitives of a small part drawn in several materials, in the order of the material table."""
        return [g.primitive(parts[m[0]], c, m[0]) for m in MATERIALS if parts.get(m[0])]

    def mm(v):
        return round(v / 1000.0, 6)

    limiter = 'firmware/main/hal/hal_servo.cpp (upstream tree pinned in firmware/BASE), Hal::servo_init angleLimit, tenths of a degree'
    root = g.node('stackchan', extras={'units': 'meters', 'up': '+Y', 'front': '+Z', 'left': '+X',
                                       'origin': 'yaw axis (turntable center) on the table plane', 'params': 'stackchan.params.json'})
    mid = -(BASE_MID_Y - YAW_Y)
    for sx in (-19.5, 19.5):                                     # the two dark strips under the base (underside photo)
        geo['base'].setdefault('port', [])
        geo['base']['port'] += box((sx, 0.075, mid + 2.7), (4.0, 0.15, 33.6))
    quads, length = lettering('M5', 3.8, 0.6)                    # the same mark raised on the plate, behind the label (underside photo)
    geo['base'].setdefault('servo', [])
    for quad in quads:
        geo['base']['servo'] += flat(lambda u, v, c: (u, 0.135, v), [(-length / 2 + a, mid - 23.4 + b) for a, b in quad])
    base = g.node('base', root, mesh=g.mesh('base', prims('base')))
    base_bottom = -32.6 - BASE_DROP - TABLE_Z
    usb_c = (0.0, -24.65 - BASE_DROP - TABLE_Z, -(-296.58 - YAW_Y) + 0.8)

    def back(u, v, c):                                           # the back of the base: u toward the robot's left, v up, c out of the back
        return (u, usb_c[1] + v, -23.7 - c)
    shell_o, shell_i = rounded_outline(8.9, 3.2, 1.58), rounded_outline(8.3, 2.6, 1.28)
    usb = {'port': slab(back, -6.0, 6.0, 5.96 - usb_c[1], 10.95 - usb_c[1], -1.3, -1.1) + flat(back, shell_i, -5.0),   # dark round the socket and at its end
           'port_metal': band(back, shell_o, shell_i, 0.0) + tube(back, shell_o, 0.0, -1.1) + tube(back, shell_i, 0.0, -5.0),
           'tongue': slab(back, -3.3, 3.3, -0.35, 0.35, -5.0, -0.9), 'pin_gold': []}
    for k in range(8):                                           # the row of contacts on each face of the tongue
        for sv in (-1, 1):
            usb['pin_gold'] += slab(back, -2.65 + 0.7 * k, -2.25 + 0.7 * k, sv * 0.35, sv * 0.41, -4.4, -1.2)
    g.node('usb_c_port', base, usb_c, g.mesh('usb_c_port', many(usb, usb_c)),
           {'what': 'USB-C for charging and data on the back of the base: an open socket with its tongue and contacts', 'opening': {'size': [mm(8.3), mm(2.6)], 'depth': mm(5.0)}})
    bb = (0.0, usb_c[1] - 2.2, -14.5)                            # the small board the back socket sits on (assumed: no picture of the open base yet)
    base_board = {'pcb': box(bb, (24.0, 1.0, 14.0)), 'chip': box((6.0, bb[1] + 0.9, -12.0), (3.0, 0.8, 3.0)), 'conn': box((-7.0, bb[1] + 1.2, -10.0), (4.0, 1.4, 3.0))}
    g.node('base_board', base, bb, g.mesh('base_board', many(base_board, bb)),
           {'what': 'board in the base that carries the back USB-C socket', 'basis': 'assumed', 'note': 'no picture of the open base: size, place and parts are a guess until the owner photographs it'})
    for i, (fx, fz) in enumerate([(-16.0, 24.0), (16.0, 24.0), (16.0, -24.0), (-16.0, -24.0)]):
        g.node('foot_%d' % i, base, (fx, base_bottom, mid + fz),
               extras={'what': 'corner mounting hole on the base underside (the base has no separate feet; the bottom plate rests on the table)'})

    def under_base(u, v, c=0.0):                                 # u toward the robot's left, v toward the front, c down
        return (u, -0.03 - c, v)
    for i, (sx, sz) in enumerate([(-9.0, 26.02), (9.0, 26.02), (9.0, -17.99), (-9.0, -17.99)]):   # hole centers measured in the plate file
        head_t, cross = screw(lambda u, v, c: (u, 0.9 - c, v), sx, sz, 1.5, 0.0, 0.45, socket=True)   # socket heads (owner's photo of the underside)
        c = (sx, 0.45, sz)
        g.node('screw_base_%d' % i, base, c, g.mesh('screw_base_%d' % i, [g.primitive(head_t, c, 'screw'), g.primitive(cross, c, 'screw_dark')]),
               {'what': 'screw that holds the bottom plate', 'basis': 'measured', 'note': 'hole from the plate file; the head is a stand-in'})
    for sx in (-16.0, 16.0):                                     # the two rear corner holes have metal sleeves (owner's photo of the underside)
        geo_sleeve = band(lambda u, v, c: (u, 0.12 - c, v), moved(circle(3.0, 20), sx, mid - 24.0), moved(circle(2.43, 20), sx, mid - 24.0), 0.0)
        g.node('sleeve_%s' % ('right' if sx < 0 else 'left'), base, (sx, 0.12, mid - 24.0), g.mesh('sleeve', [g.primitive(geo_sleeve, (sx, 0.12, mid - 24.0), 'screw')]),
               {'what': 'metal sleeve in a rear corner mounting hole', 'basis': 'assumed', 'note': "seen in the owner's photo of the underside"})
    lx, lz0, lz1 = 16.25, mid - 17.3, mid + 18.1                 # the big label under the base (underside photo): white, a dark header band, marks
    paper = [(-lx, lz1), (lx, lz1), (lx, lz0 + 4.0), (lx - 4.0, lz0), (-lx + 4.0, lz0), (-lx, lz0 + 4.0)]
    label = {'sticker': flat(under_base, paper), 'sticker_dark': flat(under_base, [(-lx, lz1), (lx, lz1), (lx, lz1 - 3.5), (-lx, lz1 - 3.5)], 0.01),
             'sticker_orange': flat(under_base, [(-15.1, lz1 - 4.6), (-10.7, lz1 - 4.6), (-10.7, lz1 - 9.0), (-15.1, lz1 - 9.0)], 0.01),
             'sticker_gray': flat(under_base, [(-6.5, mid + 4.5), (0.5, mid + 9.5), (4.5, mid + 3.9), (-2.5, mid - 1.1)], 0.01)
             + flat(under_base, [(-4.2, mid + 2.2), (1.4, mid + 2.2), (1.4, mid - 5.2), (-4.2, mid - 5.2)], 0.012)
             + flat(under_base, [(-5.6, mid - 6.4), (7.0, mid - 6.4), (7.0, mid - 7.6), (-5.6, mid - 7.6)], 0.01), 'sticker_ink': []}
    for r, a0, a1 in dashes(6, -15.3, -8.0, 11):                 # two columns of stand-in print
        label['sticker_ink'] += flat(under_base, [(a0, mid + 7.4 - r * 2.5), (a1, mid + 7.4 - r * 2.5), (a1, mid + 6.6 - r * 2.5), (a0, mid + 6.6 - r * 2.5)], 0.02)
    for r, a0, a1 in dashes(5, 5.5, 15.3, 7):
        label['sticker_ink'] += flat(under_base, [(a0, mid + 13.0 - r * 1.9), (a1, mid + 13.0 - r * 1.9), (a1, mid + 12.3 - r * 1.9), (a0, mid + 12.3 - r * 1.9)], 0.02)
    quads, length = lettering('CE', 4.0, 0.7)
    for quad in quads:                                           # read with the front of the robot up, as on the unit
        label['sticker_ink'] += flat(under_base, [(8.6 + a, mid - 1.6 + b) for a, b in quad], 0.02)
    label['sticker_ink'] += band(under_base, moved(circle(2.0, 16), 11.5, mid - 5.6), moved(circle(1.6, 16), 11.5, mid - 5.6), 0.02)
    label['sticker_ink'] += band(under_base, moved(circle(2.6, 18), -9.0, mid - 11.0), moved(circle(2.3, 18), -9.0, mid - 11.0), 0.02)
    label['sticker_ink'] += flat(under_base, [(1.8, mid - 13.4), (5.6, mid - 13.4), (5.6, mid - 14.2), (1.8, mid - 14.2)], 0.02)
    label['sticker_ink'] += band(under_base, moved(rounded_outline(3.0, 3.6, 0.2), 0.0, mid - 10.6), moved(rounded_outline(2.5, 3.1, 0.2), 0.0, mid - 10.6), 0.02)
    sb = (0.0, -0.03, mid - 2.0)
    g.node('sticker_bottom', base, sb, g.mesh('sticker_bottom', many(label, sb)),
           {'what': "label under the base of the real unit, drawn for this model in simple shapes; the small print is a stand-in", 'basis': 'assumed'})
    b_lo, b_hi = bounds([t for m in geo['base'].values() for t in m])
    g.node('col_base', base, [(b_lo[k] + b_hi[k]) / 2.0 for k in range(3)],
           extras={'collider': {'shape': 'box', 'size': [mm(b_hi[k] - b_lo[k]) for k in range(3)]}})

    yaw = g.node('yaw_joint', base, YAW_O, extras={'joint': {
        'type': 'revolute', 'axis': [0.0, -1.0, 0.0], 'positive': "turns the head toward the robot's right", 'limit_deg': list(YAW_LIMIT_DEG), 'rest_deg': 0.0,
        'source': limiter + ': yaw (-1280, 1280)', 'published': '360 degree servo, no angle restriction (product page)'}})
    g.node('neck', yaw, mesh=g.mesh('neck', prims('neck')), extras={'what': 'servo holder that turns with yaw: holder and its two covers'})
    led_w = world((YAW_X, -298.75, -17.4))
    g.node('back_charge_led', yaw, sub(led_w, YAW_O), g.mesh('back_charge_led', [g.primitive(box(led_w, (1.4, 2.8, 0.5)), led_w, 'led_charge')]),
           {'what': 'small red light in the holder back, between the two screws; lit while the unit has USB power (observed by the owner 2026-11-18); the firmware does not drive it', 'basis': 'assumed'})

    def holder_back(u, v, c):                                    # u toward the robot's left, v up, c out of the back
        return (u, v, -20.05 - c)
    for i, sx in enumerate((-11.0, 11.0)):                       # the two screws of the back cover, in its 4 mm recesses (cover file)
        head_t, cross = screw(holder_back, sx, 15.1, 1.5, 0.0, 1.1)
        c = (sx, 15.1, -21.15)
        g.node('screw_back_%d' % i, yaw, sub(c, YAW_O), g.mesh('screw_back_%d' % i, [g.primitive(head_t, c, 'screw'), g.primitive(cross, c, 'screw_dark')]),
               {'what': 'screw of the holder back cover', 'basis': 'measured', 'note': 'recess from the cover file; the head is a stand-in'})
    bracket_c = (14.7, 41.7, -17.95)                             # the black bracket on the tilt servo's back end, with its socket-head screw (owner's photo)
    g.node('black_bracket', yaw, sub(bracket_c, YAW_O), g.mesh('black_bracket', [g.primitive(box(bracket_c, (9.0, 13.0, 1.4)), bracket_c, 'servo_case')]),
           {'what': "black bracket on the tilt servo's back end", 'basis': 'assumed', 'note': "seen in the owner's photo of the open back; size and place read off it"})
    head_t, cross = screw(lambda u, v, c: (u, v, -18.65 - c), 14.7, 41.7, 1.5, 0.0, 1.4, socket=True)
    c = (14.7, 41.7, -19.35)
    g.node('screw_servo', yaw, sub(c, YAW_O), g.mesh('screw_servo', [g.primitive(head_t, c, 'screw'), g.primitive(cross, c, 'screw_dark')]),
           {'what': "socket-head screw in the black bracket on the tilt servo's back end", 'basis': 'assumed'})
    # The black flat cable from the head's board into the holder (owner's photos): its last stretch stands in front of the tilt servo and
    # goes down into the holder; the folded stack above it rides on the head (node coil, below).
    lead_c = (0.0, PITCH_O[1] + 4.6, 7.2)
    g.node('ribbon_to_holder', yaw, sub(lead_c, YAW_O), g.mesh('ribbon_to_holder', [g.primitive(box(lead_c, (7.5, 6.0, 0.4)), lead_c, 'ribbon')]),
           {'what': 'the black flat cable where it goes down into the holder, in front of the tilt servo', 'basis': 'assumed', 'note': "seen in the owner's photos of the open back"})
    inside = [('servo_yaw', {'servo_case': servo_yaw}, 'pan servo: its case turns with the holder, its shaft sits in the base socket (size from the data sheet, position assumed)'),
              ('servo_pitch', {'servo_case': servo_pitch}, 'tilt servo: its shaft drives the arm on the nod axis (size from the data sheet, position assumed)'),
              ('battery', {'battery': battery}, '550 mAh battery behind the holder back cover (capacity published; size and position assumed)'),
              ('battery_lead', battery_lead, 'red and black lead from the battery to a small plug (assumed)'),
              ('servo_wires', servo_wires, 'the three-wire leads of the two servos (assumed path)'),
              ('cable', {'ribbon': cable}, "the black cable where it runs over the back of the holder toward the head (owner's photos; the path is assumed)")]
    for name, parts, what in inside:
        c = [round(v, 3) for v in [(a0 + b0) / 2.0 for a0, b0 in zip(*bounds([t for m in parts.values() for t in m]))]]
        g.node(name, yaw, sub(c, YAW_O), g.mesh(name, many(parts, c)), {'what': what, 'basis': 'assumed'})
    n_lo, n_hi = bounds([t for m in geo['neck'].values() for t in m])
    g.node('col_neck', yaw, (0.0, (n_lo[1] + n_hi[1]) / 2.0 - YAW_O[1], 0.0),
           extras={'collider': {'shape': 'cylinder', 'radius': 0.023, 'height': mm(n_hi[1] - n_lo[1])}})
    pitch = g.node('pitch_joint', yaw, sub(PITCH_O, YAW_O), extras={'joint': {
        'type': 'revolute', 'axis': [-1.0, 0.0, 0.0], 'positive': 'tilts the face up', 'limit_deg': list(PITCH_LIMIT_DEG), 'rest_deg': 0.0,
        'source': limiter + ': pitch (30, 870)', 'published_limit_deg': list(PITCH_RECOMMENDED_DEG), 'geometry_free_deg': list(PITCH_FREE_DEG)}})
    head = g.node('head', pitch, mesh=g.mesh('head', prims('head')), extras={'what': 'shell, controller unit, board, light bars, pitch arm and bearing plate'})
    sw, sh = SCREEN_MM[0] / 2.0, SCREEN_MM[1] / 2.0
    quad = [(-sw, sh, 0, -sw, -sh, 0, sw, -sh, 0), (-sw, sh, 0, sw, -sh, 0, sw, sh, 0)]
    uvs = {}
    for x, u in ((-sw, 0.0), (sw, 1.0)):
        for y, v in ((sh, 0.0), (-sh, 1.0)):
            uvs[(int(round(x * 1000)) / 1e6, int(round(y * 1000)) / 1e6, 0.0)] = (u, v)
    g.node('screen_plane', head, sub(screen_c, PITCH_O), g.mesh('screen_plane', [g.primitive(quad, (0, 0, 0), 'screen', uvs)]),
           {'screen': {'pixels': [320, 240], 'size_m': [mm(SCREEN_MM[0]), mm(SCREEN_MM[1])],
                       'uv': '0,0 top-left to 1,1 bottom-right as seen from the front; set the live 320x240 frame as the material texture'}})
    g.node('power_button', head, sub(button_c, PITCH_O), g.mesh('power_button', [g.primitive(button_tris, button_c, 'button')]),
           {'what': "power button on the controller's right side: a tongue in a dark gap, low at the back and stepped up level with the housing at the front (owner's close-ups)", 'size': [mm(9.05), mm(5.3)]})
    g.node('usb_c_otg', head, sub(otg_c, PITCH_O), g.mesh('usb_c_otg', many(otg, otg_c)),
           {'what': "USB-C (OTG) on the controller's right side: an open socket with its tongue", 'opening': {'size': [mm(3.3), mm(9.2)], 'depth': mm(5.5)}})
    g.node('port_a', head, sub(port_a_c, PITCH_O), g.mesh('port_a', many(port_a, port_a_c)),
           {'what': "I2C port A on the controller's right side: a red socket with four pins", 'opening': {'size': [mm(5.3), mm(10.5)], 'depth': mm(5.0)}})
    board_c = (0.0, top - 3.1, (front - 1.5 + head_lo[2] + 9.0) / 2.0)
    g.node('board', head, sub(board_c, PITCH_O), extras={'what': 'marks the boards in the head: ring_board flat under the top and board_7p upright behind the controller', 'basis': 'assumed'})
    for side_name in ('left', 'right'):
        g.node('light_bar_%s' % side_name, head, mesh=g.mesh('light_bar_%s' % side_name, prims('bar_%s' % side_name)),
               extras={'what': "frosted light guide in the head's top %s corner; the six lights of that side shine into it from the ring board" % side_name,
                'lights': [0, 1, 2, 3, 4, 5] if side_name == 'left' else [11, 10, 9, 8, 7, 6], 'lights_order': 'front to back along the bar'})
    g.node('ring_board', head, sub(ring_c, PITCH_O), g.mesh('ring_board', many(ring_board, ring_c)),
           {'what': 'the dark board under the head top that carries the 12 lights, with the body of the black top connector', 'basis': 'assumed',
            'note': "plate and lights along both side edges seen in the owner's photo of the open back; exact size assumed"})
    for i, (c, tris) in enumerate(ring_leds):
        g.node('ring_led_%d' % i, head, sub(c, PITCH_O), g.mesh('ring_led_%d' % i, [g.primitive(tris, c, 'ring_led')]),
               {'what': 'the small light of ring_light_%d on the underside of the ring board; it fires sideways into the light bar' % i, 'light': i, 'basis': 'assumed'})
    for side_name, gx, lights in (('left', 11.0, [0, 1]), ('right', -11.0, [11, 10])):   # the top connectors are not sealed: a slit behind each lets the ring's light out (owner's close-up)
        c = (gx, top - 2.42, front - 4.6)                        # the window between the two inner posts, behind the cross bar: no floor there
        g.node('top_gap_%s' % side_name, head, sub(c, PITCH_O), g.mesh('top_gap_%s' % side_name, [g.primitive(both(quad_y(1, c[1], gx - 2.4, gx + 2.4, front - 5.3, front - 3.9)), c, 'port')]),
               {'what': 'the window in a top connector, between its two inner posts and behind its cross bar: it has no floor, so light from inside shows through it and nowhere else on the connector', 'lights': lights, 'basis': 'assumed', 'note': "seen in the owner's close-up of the head top; width read off it"})
    g.node('green_connector', head, sub(green_c, PITCH_O), g.mesh('green_connector', [g.primitive(green_tris, green_c, 'conn_green')]),
           {'what': "mint green body of the four-pin top connector, under the ring board on the robot's left", 'basis': 'assumed', 'note': "seen in the owner's photo"})
    b7 = (0.0, cy + 1.0, front - 1.1)
    g.node('board_7p', head, sub(b7, PITCH_O), g.mesh('board_7p', many(board_7p, b7)),
           {'what': 'the upright board behind the controller, with its white print (7P beside the seven-pin socket)', 'basis': 'assumed', 'note': "print seen in the owner's photo and in the maker's back picture"})
    # The black cable (owner's close photo): eight round wires side by side, 8.5 mm across. They leave the socket, arch away from the
    # board, come back down to a taped band, and go on as a flat ribbon toward the holder. It rides on the head.
    coil, coil_c = [], (-0.3, ring_under - 11.0, zb - 2.0)
    arch = [(4.6, 0.9), (5.4, 1.8), (6.6, 2.6), (8.2, 3.1), (10.2, 3.3), (12.2, 3.1), (13.8, 2.6), (15.0, 2.0), (16.0, 1.6), (17.4, 1.5), (19.4, 1.5)]   # (down, out of the board): the arch, then on down as the same eight wires
    for wire in range(8):
        wx = coil_c[0] + 3.71 - 1.06 * wire
        rings = []
        for n, (dn, cc) in enumerate(arch):
            a0, a1 = arch[max(0, n - 1)], arch[min(len(arch) - 1, n + 1)]
            tv, tc = -(a1[0] - a0[0]), a1[1] - a0[1]
            tl = math.hypot(tv, tc)
            nv, nc = -tc / tl, tv / tl                                           # across the wire, in the plane it bends in
            rings.append([onboard(wx + 0.4 * math.cos(2 * math.pi * q / 12), ring_under - dn + 0.4 * math.sin(2 * math.pi * q / 12) * nv, cc + 0.4 * math.sin(2 * math.pi * q / 12) * nc) for q in range(12)])
        for r0, r1 in zip(rings, rings[1:]):
            for q in range(12):
                a, b, c2, d = r0[q], r0[(q + 1) % 12], r1[(q + 1) % 12], r1[q]
                coil += both([a + b + c2, a + c2 + d])
    coil += slab(onboard, coil_c[0] - 4.3, coil_c[0] + 4.3, ring_under - 16.5, ring_under - 15.7, 1.0, 2.14)      # the narrow band where the wires are bonded together
    g.node('coil', head, sub(coil_c, PITCH_O), g.mesh('coil', [g.primitive(coil, coil_c, 'ribbon')]),
           {'what': 'black cable of eight round wires from its socket on the upright board: a ribbon of eight black wires that arches away from the board, is bonded in a narrow band, and goes on down toward the holder', 'basis': 'assumed', 'note': "laid out from the owner's close photo of the open back; it flexes as the head nods, drawn at rest"})
    low = {'flex': [], 'flex_ink': []}                           # a second flat cable, white with blue print, low on the board (owner's photo from below)
    low['flex'] += slab(lambda u, v, c: (u, v, zb - c), -13.0, -2.0, cy - 16.0, cy - 12.6, 0.0, 0.2)
    for k7 in range(7):
        low['flex_ink'] += slab(lambda u, v, c: (u, v, zb - c), -12.2 + 1.5 * k7, -11.4 + 1.5 * k7, cy - 15.4, cy - 13.2, 0.2, 0.23)
    lc = (-7.5, cy - 14.3, zb)
    g.node('flex_cable_low', head, sub(lc, PITCH_O), g.mesh('flex_cable_low', many(low, lc)),
           {'what': 'flat cable with blue print low on the upright board', 'basis': 'assumed', 'note': "seen in the owner's photo of the underside; where it ends is not known"})
    fc = (flex_x, top - 12.0, zb - 3.0)
    g.node('flex_cable_ring', head, sub(fc, PITCH_O), g.mesh('flex_cable_ring', many(flex, fc)),
           {'what': 'flat cable with green print from the upright board up to the ring board', 'basis': 'assumed', 'note': "seen in the owner's photo; the exact path is assumed"})
    bp = (0.0, top - 16.0, zb)
    g.node('board_parts', head, sub(bp, PITCH_O), g.mesh('board_parts', many(board_parts, bp)),
           {'what': "parts on the back of the upright board, laid out from the owner's close photo: the cable socket, the flat cable's socket, chips, tan capacitors, gold test pads and a standoff", 'basis': 'assumed'})
    for i, sx in enumerate((-21.85, 21.85)):                     # dark screws in the shell's two lower front holes, heads toward the back (holes from the shell file)
        head_t, cross = screw(lambda u, v, c: (u, v, 15.75 - c), sx, 21.88, 1.5, 0.0, 0.8)
        c = (sx, 21.88, 15.35)
        g.node('screw_head_%d' % i, head, sub(c, PITCH_O), g.mesh('screw_head_%d' % i, [g.primitive(head_t, c, 'screw_dark'), g.primitive(cross, c, 'chip')]),
               {'what': 'screw that holds the controller mount to the shell', 'basis': 'measured', 'note': 'hole from the shell file; the head is a stand-in'})
    g.node('reset_button', head, sub(reset_c, PITCH_O), g.mesh('reset_button', [g.primitive(reset_tris, reset_c, 'button')]),
           {'what': "reset button under the controller, beside the card slot: a tongue in a pill-shaped gap with the same step as the power key; a press restarts the unit, a 3 second hold enters download mode", 'size': [mm(7.9), mm(4.6)]})
    g.node('sd_slot', head, sub(sd_c, PITCH_O), g.mesh('sd_slot', [g.primitive(sd_tris, sd_c, 'port'), g.primitive(sd_pins, sd_c, 'pin_gold')]),
           {'what': 'card slot under the controller: an open slot', 'opening': {'size': [mm(12.9), mm(1.3)], 'depth': mm(3.0)}})
    g.node('screen_bottom_led', head, sub(led_bottom_c, PITCH_O), g.mesh('screen_bottom_led', [g.primitive(led_bottom_tris, led_bottom_c, 'led_bottom')]),
           {'what': 'small light under the controller, between the card slot and the reset button; observed by the owner 2026-11-18: lit with USB power, same as the rear one, so it is a power light; red in his photo', 'basis': 'assumed'})
    for i, (sl, tris_s) in enumerate(zip(slots, slot_tris)):
        c = (sum(p[0] for p in sl) / len(sl), under, face - 11.0)
        g.node('ir_window_%d' % i, head, sub(c, PITCH_O), g.mesh('ir_window_%d' % i, [g.primitive(tris_s, c, 'port')]),
               {'what': 'one of the two short dark slots beside the small light under the controller', 'basis': 'assumed',
                'note': "seen in the owner's photo; named as infrared windows on the coordinator's word, purpose not confirmed (the maker's picture marks infrared on the head top)"})
    g.node('red_led_side', g.nodes.index(next(n for n in g.nodes if n['name'] == 'screen_bottom_led')),
           extras={'what': 'another name for screen_bottom_led: the small red light under the controller'})
    g.node('button_left_top', g.nodes.index(next(n for n in g.nodes if n['name'] == 'power_button')),
           extras={'what': 'another name for power_button: the button at the top of the side that is on the left when you face the screen'})
    for name in sorted(stickers):
        parts, c = stickers[name]
        g.node(name, head, sub(c, PITCH_O), g.mesh(name, many(parts, c)),
               {'what': "label of the real unit, drawn for this model in simple strokes; the small print is a stand-in", 'basis': 'assumed'})
    for i, c in enumerate(pads):
        g.node('touch_back_%d' % i, head, sub(c, PITCH_O), g.mesh('touch_back_%d' % i, [g.primitive(box(c, (pad_w, 0.06, pad_d)), c, 'touch_pad'),
                                             g.primitive(band(lambda u, v, h: (u, top - 0.76 + h, v), moved(rounded_outline(pad_w, pad_d, 1.2), c[0], c[2]), moved(rounded_outline(pad_w - 0.7, pad_d - 0.7, 0.9), c[0], c[2]), 0.0), c, 'print')]),
               {'touch': {'zone': i, 'of': 3, 'order': 'front to back'}, 'what': 'one zone of the head touch strip, under the shell top: the real unit shows nothing on the outside (owner, 2026-11-18); three zones in the firmware, position and outline assumed', 'basis': 'assumed'})
    k = 0.70710678
    light_pos = []
    for i in range(LIGHTS):
        side = 1 if i < 6 else -1
        along = (-12.5 + 5.0 * i) if i < 6 else (12.5 - 5.0 * (i - 6))        # 0..5 front to back on the left bar, 6..11 back to front on the right
        cx = CORNER[0] if side > 0 else 2 * YAW_X - CORNER[0]
        c = world((cx + side * 4.05 * k, BAR_Y + along, CORNER[1] + 4.05 * k))
        tris = obox(c, (0, 0, 2.4), (side * k * 1.0, -k * 1.0, 0), (side * k * 0.15, k * 0.15, 0))
        g.node('ring_light_%d' % i, head, sub(c, PITCH_O), g.mesh('ring_light_%d' % i, [g.primitive(tris, c, 'ring_light_%d' % i)]),
               {'light': {'bar': 'left' if side > 0 else 'right', 'index_in_bar': i % 6, 'set': 'emissiveFactor of material ring_light_%d' % i}})
        light_pos.append([mm(v) for v in sub(c, PITCH_O)])
    h_lo, h_hi = bounds([t for m in geo['head'].values() for t in m])
    g.node('col_head', head, sub([(h_lo[j] + h_hi[j]) / 2.0 for j in range(3)], PITCH_O),
           extras={'collider': {'shape': 'box', 'size': [mm(PUBLISHED['width_mm']), mm(h_hi[1] - h_lo[1]), mm(h_hi[2] - h_lo[2])]}})
    glb = g.pack()

    def val(value, basis, note=None):
        d = {'value': value, 'basis': basis}
        if note:
            d['note'] = note
        return d
    drawing = 'read off the published drawing, about 1 mm'
    params = {
        'units': 'meters and degrees',
        'frame': {'up': '+Y', 'front': '+Z', 'left': '+X', 'origin': 'yaw axis on the table plane'},
        'source': {'files': 'source/ (official structure files, see SOURCE.md)', 'sha256': hashes},
        'triangles': tri_count,
        'dimensions': {
            'overall_height': val(mm(max(b_hi[1], n_hi[1], h_hi[1])), 'measured', '70.5 mm published; the files stack to 69.05, see base_drop'),
            'overall_depth': val(mm(h_hi[2] - h_lo[2]), 'measured', '61.5 mm published'),
            'head_width': val(0.054, 'measured', 'shell file and published drawing'),
            'head_height': val(mm(head_hi[1] - head_lo[1]), 'measured'),
            'head_depth': val(mm(PUBLISHED['depth_mm']), 'measured', 'published drawing; shell file 46.7 mm plus the controller unit'),
            'shell_depth': val(mm(shell_depth), 'measured'),
            'controller_depth': val(mm(core_depth), 'assumed', '61.5 published depth minus the 46.7 shell; the controller is not in the files'),
            'base_width': val(0.048, 'measured'),
            'base_depth': val(0.056, 'measured'),
            'base_height': val(mm(b_hi[1]), 'measured', 'table to the top of the turntable ring: 0.15 mm plate, 8.0 mm body, 3.1 mm ring'),
            'base_drop': val(mm(BASE_DROP), 'assumed', 'the base sits this much lower than in the files so the height reaches the published 70.5 mm; the drawing shows the same gap'),
            'bottom_plate_below_base': val(mm(base_bottom), 'measured', 'the plate seats on the four screw posts'),
            'base_mount_holes': val([0.032, 0.048], 'measured', 'corner hole spacing across and front to back'),
            'base_mount_hole_diameter': val(0.00486, 'measured'),
            'head_front_from_axis': val(mm(face), 'measured', 'the head pockets center on the servo stub; the glass ends 1.26 mm ahead of the base front (drawing: about 1.3)'),
            'base_center_from_axis': val([0.0, 0.0, mm(mid)], 'measured', 'the turntable sits 4 mm behind the base footprint center'),
            'screen_active_area': val([mm(SCREEN_MM[0]), mm(SCREEN_MM[1])], 'measured', 'drawing front view; 2.0 inch 320x240'),
            'screen_center_from_pitch_axis': val([mm(v) for v in sub(screen_c, PITCH_O)], 'assumed', drawing),
            'power_button_from_pitch_axis': val([mm(v) for v in sub(button_c, PITCH_O)], 'assumed', drawing),
            'usb_c_otg_from_pitch_axis': val([mm(v) for v in sub(otg_c, PITCH_O)], 'assumed', drawing),
            'usb_c_port_position': val([mm(v) for v in usb_c], 'measured', 'the opening in the back of the base'),
            'light_bar': val([0.005, 0.031, 0.0053], 'measured', 'light guide file; each bar sits in the slanted slot of a top corner of the shell, stem tip flush'),
            'ring_light_spacing': val(0.005, 'assumed'),
            'sd_slot_from_pitch_axis': val([mm(v) for v in sub(sd_c, PITCH_O)], 'assumed', 'underside photo: 6.8 mm right of the middle, 7.0 mm behind the glass, 12.9 x 1.3 mm'),
            'screen_bottom_led_from_pitch_axis': val([mm(v) for v in sub(led_bottom_c, PITCH_O)], 'assumed', 'underside photo: the pinhole between the card slot and the reset button, 6.6 mm behind the glass'),
            'back_charge_led_position': val([mm(v) for v in led_w], 'assumed', 'product photo of the back: a red part between the two screws'),
            'labels': val(['sticker_side_left', 'sticker_side_right', 'sticker_top', 'sticker_bottom'], 'assumed', 'placed from the product photos; print is a stand-in'),
            'reset_button_from_pitch_axis': val([mm(v) for v in sub(reset_c, PITCH_O)], 'assumed', 'underside photo: 15.0 mm left of the middle, 6.6 mm behind the glass, a white key 7.6 x 5.4 mm in a dark gap; press restarts, hold 3 s enters download mode (product page)'),
            'side_openings': val({'power_button': [mm(8.7), mm(6.1)], 'usb_c_otg': [mm(3.3), mm(9.2)], 'port_a': [mm(5.3), mm(10.5)]}, 'assumed', 'side photo, about 0.3 mm: width front to back, then height; centers 14.0, 27.5 and 41.7 mm below the head top'),
            'port_a_from_pitch_axis': val([mm(v) for v in sub(port_a_c, PITCH_O)], 'assumed', 'side photo'),
            'usb_c_opening': val([mm(8.3), mm(2.6), mm(5.0)], 'assumed', 'a standard socket (8.3 x 2.6 mm inside) set in the 12 x 5 mm opening of the base file'),
            'side_label': val([mm(lw), mm(lh)], 'assumed', 'side photos: 0.9 mm behind the shell front edge, 7.2 mm below the head top'),
            'screws': val({'holder_back': [[-0.011, 0.0151], [0.011, 0.0151]], 'base_plate': [[-0.009, 0.02602], [0.009, 0.02602], [0.009, -0.01799], [-0.009, -0.01799]], 'head_lower': [[-0.02185, 0.02188], [0.02185, 0.02188]]},
                          'measured', 'hole centers fitted in the cover, plate and shell files (holder and head: across, height; plate: across, front to back); head sizes are stand-ins'),
            'head_touch_zones': val(3, 'measured', 'firmware head touch code reads three intensities in a row and reports press, release, swipe forward and swipe backward'),
            'head_touch_pad_size': val([mm(pad_w), mm(pad_d)], 'assumed', 'the pads are under the shell and cannot be seen; only the touch board schematic is published'),
            'head_touch_from_pitch_axis': val([[mm(v) for v in sub(c, PITCH_O)] for c in pads], 'assumed', 'in a row under the head top behind the two connector openings, zone 0 at the front; not visible from outside'),
            'servo_size': val([mm(v) for v in SERVO_MM], 'measured', 'servo data sheet: 23.2 x 12.1 x 25.25 mm, both servos'),
            'servo_shaft_diameter': val(mm(2 * SERVO_SHAFT_R), 'measured', 'servo data sheet: 20 teeth, 3.95 mm; the base socket and the arm socket measure the same'),
            'servo_positions': val('pan servo upright on the turn axis with its shaft in the base socket; tilt servo lying on top of it with its shaft on the nod axis', 'assumed', 'the shaft axes are measured; where each case ends is not published'),
            'battery_capacity_mah': val(550, 'measured', 'product page'),
            'battery_size': val([mm(v) for v in BATTERY_MM], 'assumed', 'no size is published; a common 550 mAh cell, placed behind the holder back cover'),
            'boards': val('flat plates', 'assumed', 'only the schematics of the adapter, power, ring and touch boards are published'),
            'cable': val('flat strip', 'assumed'),
            'ring_light_from_pitch_axis': val(light_pos, 'assumed', 'on the bars (measured); order and spacing along each bar assumed'),
        },
        'joints': {
            'yaw_joint': {'axis': [0, -1, 0], 'origin': [mm(v) for v in YAW_O], 'limit_deg': list(YAW_LIMIT_DEG), 'basis': 'measured', 'source': limiter,
                          'published_range': '360 degree servo, no angle restriction (product page)',
                          'direction_basis': 'assumed', 'direction_note': "positive turns toward the robot's right, as the virtual unit view draws it"},
            'pitch_joint': {'axis': [-1, 0, 0], 'origin': [mm(v) for v in PITCH_O], 'limit_deg': list(PITCH_LIMIT_DEG), 'basis': 'measured', 'source': limiter,
                            'published_limit_deg': [5, 85], 'published_basis': 'product page text, recommended range',
                            'geometry_free_range_deg': list(PITCH_FREE_DEG), 'geometry_basis': 'measured: collision sweep of the assembled files',
                            'direction_basis': 'assumed', 'direction_note': 'positive tilts the face up; 0 is the level pose in the drawing'},
            'pitch_axis_height': val(mm(PITCH_O[1]), 'measured', "servo holder stub, arm spline and head pocket centers; equals the head's vertical center"),
        },
        'mass_kg': {
            'total': val(0.1872, 'measured', 'product page: 187.2 g'),
            'head': val(0.105, 'assumed', 'shell, controller unit, board'),
            'neck': val(0.047, 'assumed', 'servo holder, two servos, battery'),
            'base': val(0.0352, 'assumed'),
        },
        'colors': {'value': dict([(m[0], list(m[1])) for m in MATERIALS] + [('light_off', list(LIGHT_OFF))]), 'basis': 'assumed', 'note': "the plastics (shell, core, neck, servo, base, button) were measured in the owner's daylight photos against the white label paper, good to about 15 percent; the rest is by eye"},
    }
    return glb, params


def quantized(glb):
    """The same model with its numbers stored small, for the web: positions as 16-bit and normals as 8-bit (KHR_mesh_quantization).

    Nothing is left out: the same nodes, names, marks and materials. Each node that had a mesh keeps its name and place and gets one
    child, "<name>.mesh", which carries the mesh and the scale that turns the stored integers back into meters. Deterministic."""
    n = struct.unpack_from('<I', glb, 12)[0]
    doc = json.loads(glb[20:20 + n])
    blob = glb[20 + n + 8:]

    def data(i):
        a = doc['accessors'][i]
        v = doc['bufferViews'][a['bufferView']]
        return blob[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']], a
    out = bytearray()
    views, accessors = [], []

    def put(raw, target, stride=None):
        while len(out) % 4:
            out.append(0)
        v = {'buffer': 0, 'byteOffset': len(out), 'byteLength': len(raw), 'target': target}
        if stride:
            v['byteStride'] = stride
        views.append(v)
        out.extend(raw)
        return len(views) - 1
    nodes = doc['nodes']
    for ni in range(len(nodes)):
        node = nodes[ni]
        if 'mesh' not in node:
            continue
        mesh = doc['meshes'][node['mesh']]
        los = [doc['accessors'][p['attributes']['POSITION']]['min'] for p in mesh['primitives']]
        his = [doc['accessors'][p['attributes']['POSITION']]['max'] for p in mesh['primitives']]
        lo = [min(v[k] for v in los) for k in range(3)]
        ext = [max(max(v[k] for v in his) - lo[k], 1e-6) for k in range(3)]
        for prim in mesh['primitives']:
            attrs = {}
            raw, a = data(prim['attributes']['POSITION'])
            f = struct.unpack('<%df' % (a['count'] * 3), raw)
            q = [int(round((f[i] - lo[i % 3]) / ext[i % 3] * 65535.0)) for i in range(len(f))]
            packed = b''.join(struct.pack('<4H', q[i], q[i + 1], q[i + 2], 0) for i in range(0, len(q), 3))
            accessors.append({'bufferView': put(packed, 34962, 8), 'componentType': 5123, 'normalized': True, 'count': a['count'], 'type': 'VEC3',
                              'min': [min(q[k::3]) for k in range(3)], 'max': [max(q[k::3]) for k in range(3)]})
            attrs['POSITION'] = len(accessors) - 1
            raw, a = data(prim['attributes']['NORMAL'])
            f = struct.unpack('<%df' % (a['count'] * 3), raw)
            packed = bytearray()
            for i in range(0, len(f), 3):
                x, y, z = (f[i] * ext[1] * ext[2], f[i + 1] * ext[0] * ext[2], f[i + 2] * ext[0] * ext[1])   # the child node's scale is undone on the normal
                ln = math.sqrt(x * x + y * y + z * z) or 1.0
                packed += struct.pack('<4b', int(round(x / ln * 127)), int(round(y / ln * 127)), int(round(z / ln * 127)), 0)
            accessors.append({'bufferView': put(bytes(packed), 34962, 4), 'componentType': 5120, 'normalized': True, 'count': a['count'], 'type': 'VEC3'})
            attrs['NORMAL'] = len(accessors) - 1
            if 'TEXCOORD_0' in prim['attributes']:
                raw, a = data(prim['attributes']['TEXCOORD_0'])
                accessors.append({'bufferView': put(raw, 34962), 'componentType': 5126, 'count': a['count'], 'type': 'VEC2'})
                attrs['TEXCOORD_0'] = len(accessors) - 1
            raw, a = data(prim['indices'])
            accessors.append({'bufferView': put(raw, 34963), 'componentType': a['componentType'], 'count': a['count'], 'type': 'SCALAR'})
            prim['attributes'], prim['indices'] = attrs, len(accessors) - 1
        nodes.append({'name': node['name'] + '.mesh', 'mesh': node.pop('mesh'), 'translation': [round(v, 9) for v in lo], 'scale': [round(v, 9) for v in ext]})
        node.setdefault('children', []).append(len(nodes) - 1)
    while len(out) % 4:
        out.append(0)
    doc['accessors'], doc['bufferViews'], doc['buffers'] = accessors, views, [{'byteLength': len(out)}]
    doc['extensionsUsed'] = doc['extensionsRequired'] = ['KHR_mesh_quantization']
    doc['asset']['generator'] = 'make_body.py (web copy)'
    js = json.dumps(doc, sort_keys=True, separators=(',', ':')).encode('ascii')
    js += b' ' * (-len(js) % 4)
    body = struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(out), 0x004E4942) + bytes(out)
    return b'glTF' + struct.pack('<II', 2, 12 + len(body)) + body


def build(out_dir=HERE):
    """Write stackchan.glb and stackchan.params.json into out_dir; returns the glb path."""
    glb, params = assemble()
    out_dir = Path(out_dir)
    (out_dir / 'stackchan.glb').write_bytes(glb)
    (out_dir / 'stackchan.web.glb').write_bytes(quantized(glb))   # the same model, stored small for a web page
    (out_dir / 'stackchan.params.json').write_text(json.dumps(params, indent=1, sort_keys=True) + '\n')
    return out_dir / 'stackchan.glb'


def main(argv):
    if '--check' in argv:
        glb, params = assemble()
        here = Path(HERE)
        same = ((here / 'stackchan.glb').exists() and (here / 'stackchan.glb').read_bytes() == glb and (here / 'stackchan.web.glb').exists()
                and (here / 'stackchan.web.glb').read_bytes() == quantized(glb) and (here / 'stackchan.params.json').exists()
                and (here / 'stackchan.params.json').read_text() == json.dumps(params, indent=1, sort_keys=True) + '\n')
        print('model files match the source files' if same else 'model files are stale: run python3 scripts/virtual-unit/model/make_body.py')
        return 0 if same else 1
    out = build()
    print('wrote stackchan.glb (%d bytes) and stackchan.params.json' % out.stat().st_size)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
