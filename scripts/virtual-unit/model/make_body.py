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
    ('LightGuideBar-A', 'head', 'light_bar', _bar(+1)),
    ('LightGuideBar-B', 'head', 'light_bar', _bar(-1)),
]

MATERIALS = [  # name, base color (linear RGBA), metallic, roughness, emissive. Colors are judged from product photos.
    ('base', (0.125, 0.125, 0.13, 1.0), 0.0, 0.75, None),
    ('port', (0.012, 0.012, 0.014, 1.0), 0.0, 0.5, None),
    ('neck', (0.56, 0.56, 0.57, 1.0), 0.0, 0.7, None),
    ('servo', (0.19, 0.19, 0.20, 1.0), 0.0, 0.7, None),
    ('camera', (0.22, 0.13, 0.08, 1.0), 0.5, 0.3, None),
    ('core', (0.74, 0.74, 0.74, 1.0), 0.0, 0.6, None),
    ('glass', (0.004, 0.004, 0.005, 1.0), 0.0, 0.12, None),
    ('light_bar', (0.42, 0.70, 0.72, 1.0), 0.0, 0.35, None),
    ('pcb', (0.01, 0.10, 0.07, 1.0), 0.0, 0.6, None),
    ('shell', (0.72, 0.72, 0.72, 1.0), 0.0, 0.6, None),
    ('screen', (0.0, 0.0, 0.0, 1.0), 0.0, 0.4, (1.0, 1.0, 1.0)),
    ('button', (0.83, 0.83, 0.83, 1.0), 0.0, 0.6, None),
    ('port_metal', (0.42, 0.43, 0.46, 1.0), 0.6, 0.4, None),
    ('port_red', (0.45, 0.03, 0.02, 1.0), 0.0, 0.6, None),
    ('servo_case', (0.012, 0.014, 0.02, 1.0), 0.0, 0.5, None),
    ('battery', (0.02, 0.09, 0.42, 1.0), 0.0, 0.5, None),
    ('cable', (0.45, 0.45, 0.47, 1.0), 0.0, 0.6, None),
    ('touch_pad', (0.60, 0.62, 0.66, 1.0), 0.0, 0.5, None),
    ('port_teal', (0.0, 0.33, 0.36, 1.0), 0.0, 0.5, None),
    ('sticker', (0.80, 0.80, 0.79, 1.0), 0.0, 0.7, None),
    ('sticker_ink', (0.012, 0.012, 0.014, 1.0), 0.0, 0.7, None),
    ('led_charge', (0.10, 0.012, 0.01, 1.0), 0.0, 0.4, None),
    ('led_bottom', (0.02, 0.06, 0.03, 1.0), 0.0, 0.4, None),
    ('print', (0.30, 0.30, 0.31, 1.0), 0.0, 0.7, None),
    ('tongue', (0.20, 0.20, 0.21, 1.0), 0.0, 0.5, None),
    ('screw', (0.55, 0.55, 0.57, 1.0), 0.8, 0.35, None),
    ('screw_dark', (0.02, 0.02, 0.022, 1.0), 0.6, 0.4, None),
    ('chip', (0.015, 0.015, 0.018, 1.0), 0.0, 0.45, None),
    ('conn', (0.74, 0.71, 0.62, 1.0), 0.0, 0.6, None),
    ('flex', (0.62, 0.72, 0.80, 1.0), 0.0, 0.5, None),
    ('wire_red', (0.50, 0.02, 0.02, 1.0), 0.0, 0.6, None),
    ('sticker_dark', (0.06, 0.06, 0.065, 1.0), 0.0, 0.7, None),
    ('sticker_orange', (0.75, 0.13, 0.02, 1.0), 0.0, 0.7, None),
    ('sticker_gray', (0.45, 0.45, 0.46, 1.0), 0.0, 0.7, None),
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
ORIGIN = {'base': (0.0, 0.0, 0.0), 'neck': YAW_O, 'head': PITCH_O}


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
    geo = {'base': {}, 'neck': {}, 'head': {}}
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
    geo['head']['camera'] = prism(circle(2.0), 0.0, row, face, face + 0.03)
    dots = prism(circle(1.3), 0.0, row, face + 0.03, face + 0.05)
    geo['head']['button'] = []
    for dx in (-14.1, 6.9, 9.0, 14.1):                        # two microphones and the two sensor windows, off the published drawing
        geo['head']['button'] += prism(circle(0.4, 8), dx, row, face, face + 0.03)
    for r in range(13):                                       # speaker grille on the robot's left side of the controller
        for c in range(4):
            dots += disc_x((27.02, top - 10.5 - 2.0 * r - (1.0 if c % 2 else 0.0), face - 5.6 - 1.6 * c), 0.4, 1, 8)
    dots += quad_x(1, 27.02, top - 45.0, top - 38.0, front + 0.1, front + 1.0)   # the dark notch at the seam under the grille
    geo['head']['port'] = dots
    prints = []                                               # small gray marks printed on the controller

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
    button_tris = tube(side, moved(rounded_outline(6.1, 8.7, 1.9), button_c[1], button_c[2]), -0.8, 0.35)
    button_tris += flat(side, moved(rounded_outline(6.1, 8.7, 1.9), button_c[1], button_c[2]), 0.35)
    prints += band(side, moved(circle(0.85, 16), top - 8.2, face - 8.0), moved(circle(0.6, 16), top - 8.2, face - 8.0), 0.02)   # the power mark above the button
    prints += flat(side, [(top - 7.6, face - 8.12), (top - 7.0, face - 8.12), (top - 7.0, face - 7.88), (top - 7.6, face - 7.88)], 0.03)
    for k in range(4):                                        # the pin marks beside port A
        prints += flat(side, [(top - 38.6 - 2.0 * k, face - 4.6), (top - 39.5 - 2.0 * k, face - 4.6), (top - 39.5 - 2.0 * k, face - 4.2), (top - 38.6 - 2.0 * k, face - 4.2)], 0.02)
    otg_in = moved(rounded_outline(8.6, 2.7, 1.34), otg_c[1], otg_c[2])
    otg = {'port_metal': band(side, otg_hole, otg_in, -0.15) + tube(side, otg_hole, 0.0, -0.15) + tube(side, otg_in, -0.15, -5.5), 'port': flat(side, otg_in, -5.5),
           'tongue': slab(side, otg_c[1] - 3.3, otg_c[1] + 3.3, otg_c[2] - 0.35, otg_c[2] + 0.35, -5.5, -1.2)}
    port_a = {'port_red': tube(side, a_hole, 0.0, -0.25) + band(side, a_hole, a_room, -0.25) + tube(side, a_room, -0.25, -5.0) + flat(side, a_room, -5.0), 'port_metal': []}
    for k in range(4):
        u = port_a_c[1] - 3.0 + 2.0 * k
        port_a['port_metal'] += slab(side, u - 0.3, u + 0.3, port_a_c[2] - 0.3, port_a_c[2] + 0.3, -5.0, -1.6)

    # ---- under the controller: card slot, light hole, two short slots and the reset button (places from the underside photo, as shares of the depth)
    def below(u, v, c):                                       # u toward the robot's left, v toward the front, c down
        return (u, under - c, v)
    sd_c = (-6.8, under, face - 7.0)
    reset_c = (15.0, under, face - 6.6)
    led_bottom_c = (6.8, under - 0.02, face - 6.6)
    sd_hole = moved(rounded_outline(12.9, 1.3, 0.4), sd_c[0], sd_c[2])
    reset_well = moved(rounded_outline(8.6, 6.4, 3.0), reset_c[0], reset_c[2])
    slots = [moved(rounded_outline(0.8, 2.9, 0.38, 4), dx, face - 11.0) for dx in (5.6, 7.5)]
    cuts = [-23.0, 1.0, 6.55, 9.5, 23.0]
    for (u0, u1), hole in zip(zip(cuts, cuts[1:]), (sd_hole, slots[0], slots[1], reset_well)):
        core += holed(below, u0, u1, z0, z1, hole)
    for s in slots:
        geo['head']['port'] += tube(below, s, 0.0, -1.5) + flat(below, s, -1.5)
    geo['head']['port'] += tube(below, reset_well, 0.0, -0.8) + flat(below, reset_well, -0.8)
    sd_tris = tube(below, sd_hole, 0.0, -3.0) + flat(below, sd_hole, -3.0)
    reset_cap = moved(rounded_outline(7.6, 5.4, 2.6), reset_c[0], reset_c[2])
    reset_tris = tube(below, reset_cap, -0.8, 0.3) + flat(below, reset_cap, 0.3)
    led_bottom_tris = flat(below, moved(circle(0.5, 12), led_bottom_c[0], led_bottom_c[2]), 0.02)
    prints += band(below, moved(circle(0.95, 16), 20.9, face - 6.6), moved(circle(0.7, 16), 20.9, face - 6.6), 0.02)   # the restart mark beside the button
    geo['head']['core'] = core
    geo['head']['print'] = prints

    # ---- the two connectors in the top openings: black on the robot's right, teal on its left; each an open socket with four pins
    def above(u, v, c):
        return (u, top - 0.3 + c, v)
    for sx, material in ((-11.0, 'port'), (11.0, 'port_teal')):
        outer = moved(rounded_outline(10.2, 5.0, 0.3), sx, front - 3.3)
        room = moved(rounded_outline(8.6, 3.4, 0.2), sx, front - 3.3)
        geo['head'].setdefault(material, [])
        geo['head'][material] += band(above, outer, room, 0.0) + tube(above, room, 0.0, -2.0) + flat(above, room, -2.0) + tube(above, outer, 0.0, -1.5)
        for k in range(4):
            geo['head'].setdefault('port_metal', [])
            geo['head']['port_metal'] += slab(above, sx - 3.3 + 2.0 * k, sx - 2.7 + 2.0 * k, front - 3.6, front - 3.0, -2.0, -0.6)
    geo['head']['port'] += slab(above, -2.2, 2.2, front - 7.6, front - 0.4, -2.2, -2.0)   # dark behind the two small windows between the connectors

    # ---- the dark shapes between the three round side openings (through the shell wall; black in the photos)
    for sx in (-1, 1):
        for zc in (-5.35, 2.65):
            steps = [-3.6 + 0.45 * i for i in range(17)]
            half = [min(1.7, 4.0 - math.sqrt(max(0.0, 3.1 * 3.1 - dy * dy))) for dy in steps]
            for (d0, w0), (d1, w1) in zip(zip(steps, half), zip(steps[1:], half[1:])):
                geo['head']['port'] += both([(sx * 26.5, 60.5 + d0, zc - w0, sx * 26.5, 60.5 + d0, zc + w0, sx * 26.5, 60.5 + d1, zc + w1),
                                             (sx * 26.5, 60.5 + d0, zc - w0, sx * 26.5, 60.5 + d1, zc + w1, sx * 26.5, 60.5 + d1, zc - w1)])

    # ---- the boards in the head, seen through the open back (positions assumed; they clear the servo housing over the whole sweep)
    geo['head']['pcb'] = box((0.0, top - 3.1, (front - 1.5 + head_lo[2] + 9.0) / 2.0), (45.0, 1.2, front - 1.5 - head_lo[2] - 9.0))
    geo['head']['pcb'] += box((0.0, cy + 1.0, front - 1.1), (48.0, 46.0, 1.2))
    zb = front - 1.7                                          # the back of the upright board

    def onboard(u, v, c):                                     # u toward the robot's left, v up, c out of the board toward the back
        return (u, v, zb - c)
    board_parts = {'chip': [], 'conn': [], 'flex': [], 'port_metal': []}
    for material, x, dy, w, h, t in (('chip', 12.75, 16.0, 3.5, 3.5, 0.8), ('chip', 8.9, 16.0, 3.2, 2.9, 0.6), ('conn', 5.2, 12.1, 3.6, 2.0, 1.2),
                                     ('chip', -0.6, 17.0, 7.3, 8.8, 0.2), ('conn', -7.1, 16.5, 3.0, 3.8, 0.5), ('conn', -7.0, 12.2, 1.6, 2.4, 0.5),
                                     ('flex', -13.9, 9.5, 4.7, 11.1, 0.2), ('port_metal', 10.0, 8.0, 1.0, 1.0, 0.4), ('port_metal', 12.0, 8.0, 1.0, 1.0, 0.4),
                                     ('port_metal', 14.0, 8.0, 1.0, 1.0, 0.4), ('port_metal', 16.0, 8.0, 1.0, 1.0, 0.4), ('chip', 15.0, 24.0, 2.4, 2.4, 0.6),
                                     ('conn', -17.0, 22.0, 2.0, 5.0, 1.0), ('conn', 18.5, 30.0, 2.0, 6.0, 1.0)):
        board_parts[material] += slab(onboard, x - w / 2, x + w / 2, top - dy - h / 2, top - dy + h / 2, 0.0, t)
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
    cable = []                                                # the flat cable from the holder up toward the head (assumed path)
    path = [(-300.4, 9.0), (-299.4, 15.5), (-302.5, 20.3), (-308.5, 21.9)]
    for (y0, z0_), (y1, z1_) in zip(path, path[1:]):
        m0, m1 = world((ax + 14.0, y0, z0_)), world((ax + 14.0, y1, z1_))
        d = [(m1[i] - m0[i]) / 2.0 for i in range(3)]
        ln = math.sqrt(d[1] * d[1] + d[2] * d[2])
        cable += obox([(m0[i] + m1[i]) / 2.0 for i in range(3)], (4.0, 0, 0), (0, d[1] * 1.05, d[2] * 1.05), (0, -d[2] / ln * 0.2, d[1] / ln * 0.2))
    screen_c = (0.0, cy - SCREEN_DROP_MM, face + 0.03)

    def screw(f, u, v, r, c0, c1):
        """A screw head in a frame: a round head from c0 to c1 with a cross on top. Returns (head, cross)."""
        o = moved(circle(r, 14), u, v)
        cross = slab(f, u - r * 0.62, u + r * 0.62, v - r * 0.13, v + r * 0.13, c1, c1 + 0.03) + slab(f, u - r * 0.13, u + r * 0.13, v - r * 0.62, v + r * 0.62, c1, c1 + 0.03)
        return tube(f, o, c0, c1) + flat(f, o, c1), cross

    # ---- labels (drawn here; the print is stand-in marks, not copied text, except the product's own name on the side labels)
    stickers = {}
    lw, lh = 5.6, 41.0                                           # side labels: width, length (side photos)
    for side_x, name in ((-1, 'sticker_side_right'), (1, 'sticker_side_left')):
        x = side_x * 27.04
        zc, yc = front - 0.9 - lw / 2, top - 7.2 - lh / 2

        def lab(p, q, c=0.0, x=x, zc=zc, yc=yc, side_x=side_x):   # p toward the front, q up
            return (x + side_x * c, yc + q, zc + p)
        o = rounded_outline(lw, lh, 1.0)
        n = len(o) // 2
        parts = {'sticker': flat(lab, o), 'sticker_dark': [], 'sticker_ink': []}
        if side_x < 0:                                            # dark end at the bottom on the button side, at the top on the other
            parts['sticker_dark'] = flat(lab, o[n:] + [(lw / 2, -lh / 2 + 12.6), (-lw / 2, -lh / 2 + 11.4)], 0.01)
            fq = -lh / 2 + 6.2
        else:
            parts['sticker_dark'] = flat(lab, o[:n] + [(-lw / 2, lh / 2 - 11.4), (lw / 2, lh / 2 - 12.6)], 0.01)
            fq = lh / 2 - 6.2
        for dq in (-2.85, 2.85):                                  # the little face in the dark end: two dots and a line
            parts['sticker'] += flat(lab, moved(circle(0.5, 10), 1.2, fq + dq), 0.02)
        parts['sticker'] += flat(lab, [(-1.1, fq - 1.85), (-0.75, fq - 1.85), (-0.75, fq + 1.85), (-1.1, fq + 1.85)], 0.02)
        quads, length = lettering('StackChan', 3.5, 0.5)
        for quad in quads:                                        # the name runs along the label with the letter tops toward the front
            if side_x < 0:
                pts = [(-lw / 2 + 1.05 + b, lh / 2 - 2.9 - a) for a, b in quad]
            else:
                pts = [(-lw / 2 + 1.05 + b, -lh / 2 + 2.9 + a) for a, b in quad]
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
    pads = [(0.0, top + 0.03, pad_first - i * (pad_d + pad_gap)) for i in range(3)]

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
    base = g.node('base', root, mesh=g.mesh('base', prims('base')))
    base_bottom = -32.6 - BASE_DROP - TABLE_Z
    usb_c = (0.0, -24.65 - BASE_DROP - TABLE_Z, -(-296.58 - YAW_Y) + 0.8)

    def back(u, v, c):                                           # the back of the base: u toward the robot's left, v up, c out of the back
        return (u, usb_c[1] + v, -23.7 - c)
    shell_o, shell_i = rounded_outline(8.9, 3.2, 1.58), rounded_outline(8.3, 2.6, 1.28)
    usb = {'port': slab(back, -6.0, 6.0, 5.96 - usb_c[1], 10.95 - usb_c[1], -1.3, -1.1) + flat(back, shell_i, -5.0),   # dark round the socket and at its end
           'port_metal': band(back, shell_o, shell_i, 0.0) + tube(back, shell_o, 0.0, -1.1) + tube(back, shell_i, 0.0, -5.0),
           'tongue': slab(back, -3.3, 3.3, -0.35, 0.35, -5.0, -0.9)}
    g.node('usb_c_port', base, usb_c, g.mesh('usb_c_port', many(usb, usb_c)),
           {'what': 'USB-C for charging and data on the back of the base: an open socket with its tongue', 'opening': {'size': [mm(8.3), mm(2.6)], 'depth': mm(5.0)}})
    for i, (fx, fz) in enumerate([(-16.0, 24.0), (16.0, 24.0), (16.0, -24.0), (-16.0, -24.0)]):
        g.node('foot_%d' % i, base, (fx, base_bottom, mid + fz),
               extras={'what': 'corner mounting hole on the base underside (the base has no separate feet; the bottom plate rests on the table)'})

    def under_base(u, v, c=0.0):                                 # u toward the robot's left, v toward the front, c down
        return (u, -0.03 - c, v)
    for i, (sx, sz) in enumerate([(-9.0, 26.02), (9.0, 26.02), (9.0, -17.99), (-9.0, -17.99)]):   # hole centers measured in the plate file
        head_t, cross = screw(lambda u, v, c: (u, 0.9 - c, v), sx, sz, 1.5, 0.0, 0.45)
        c = (sx, 0.45, sz)
        g.node('screw_base_%d' % i, base, c, g.mesh('screw_base_%d' % i, [g.primitive(head_t, c, 'screw'), g.primitive(cross, c, 'screw_dark')]),
               {'what': 'screw that holds the bottom plate', 'basis': 'measured', 'note': 'hole from the plate file; the head is a stand-in'})
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
           {'what': 'label under the base, drawn for this model; the print is a stand-in', 'basis': 'assumed'})
    b_lo, b_hi = bounds([t for m in geo['base'].values() for t in m])
    g.node('col_base', base, [(b_lo[k] + b_hi[k]) / 2.0 for k in range(3)],
           extras={'collider': {'shape': 'box', 'size': [mm(b_hi[k] - b_lo[k]) for k in range(3)]}})

    yaw = g.node('yaw_joint', base, YAW_O, extras={'joint': {
        'type': 'revolute', 'axis': [0.0, -1.0, 0.0], 'positive': "turns the head toward the robot's right", 'limit_deg': list(YAW_LIMIT_DEG), 'rest_deg': 0.0,
        'source': limiter + ': yaw (-1280, 1280)', 'published': '360 degree servo, no angle restriction (product page)'}})
    g.node('neck', yaw, mesh=g.mesh('neck', prims('neck')), extras={'what': 'servo holder that turns with yaw: holder and its two covers'})
    led_w = world((YAW_X, -298.75, -17.4))
    g.node('back_charge_led', yaw, sub(led_w, YAW_O), g.mesh('back_charge_led', [g.primitive(box(led_w, (1.4, 2.8, 0.5)), led_w, 'led_charge')]),
           {'what': 'small red light in the holder back, between the two screws; lit while charging (behavior assumed, not driven by the firmware)', 'basis': 'assumed'})

    def holder_back(u, v, c):                                    # u toward the robot's left, v up, c out of the back
        return (u, v, -20.05 - c)
    for i, sx in enumerate((-11.0, 11.0)):                       # the two screws of the back cover, in its 4 mm recesses (cover file)
        head_t, cross = screw(holder_back, sx, 15.1, 1.5, 0.0, 1.1)
        c = (sx, 15.1, -21.15)
        g.node('screw_back_%d' % i, yaw, sub(c, YAW_O), g.mesh('screw_back_%d' % i, [g.primitive(head_t, c, 'screw'), g.primitive(cross, c, 'screw_dark')]),
               {'what': 'screw of the holder back cover', 'basis': 'measured', 'note': 'recess from the cover file; the head is a stand-in'})
    head_t, cross = screw(lambda u, v, c: (u, v, -17.25 - c), 14.7, 41.7, 1.2, 0.0, 0.5)   # the screw on the tilt servo's back end (back photo)
    c = (14.7, 41.7, -17.75)
    g.node('screw_servo', yaw, sub(c, YAW_O), g.mesh('screw_servo', [g.primitive(head_t, c, 'screw'), g.primitive(cross, c, 'screw_dark')]),
           {'what': "screw on the tilt servo's back end", 'basis': 'assumed'})
    inside = [('servo_yaw', {'servo_case': servo_yaw}, 'pan servo: its case turns with the holder, its shaft sits in the base socket (size from the data sheet, position assumed)'),
              ('servo_pitch', {'servo_case': servo_pitch}, 'tilt servo: its shaft drives the arm on the nod axis (size from the data sheet, position assumed)'),
              ('battery', {'battery': battery}, '550 mAh battery behind the holder back cover (capacity published; size and position assumed)'),
              ('battery_lead', battery_lead, 'red and black lead from the battery to a small plug (assumed)'),
              ('servo_wires', servo_wires, 'the three-wire leads of the two servos (assumed path)'),
              ('cable', {'cable': cable}, 'flat cable from the holder toward the head (assumed)')]
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
           {'what': "power button on the controller's right side: a white key in a dark gap", 'size': [mm(8.7), mm(6.1)]})
    g.node('usb_c_otg', head, sub(otg_c, PITCH_O), g.mesh('usb_c_otg', many(otg, otg_c)),
           {'what': "USB-C (OTG) on the controller's right side: an open socket with its tongue", 'opening': {'size': [mm(3.3), mm(9.2)], 'depth': mm(5.5)}})
    g.node('port_a', head, sub(port_a_c, PITCH_O), g.mesh('port_a', many(port_a, port_a_c)),
           {'what': "I2C port A on the controller's right side: a red socket with four pins", 'opening': {'size': [mm(5.3), mm(10.5)], 'depth': mm(5.0)}})
    board_c = (0.0, top - 3.1, (front - 1.5 + head_lo[2] + 9.0) / 2.0)
    g.node('board', head, sub(board_c, PITCH_O), extras={'what': 'the boards in the head: one flat under the top, one upright behind the controller; drawn in the head mesh (material pcb), position assumed', 'basis': 'assumed'})
    bp = (0.0, top - 16.0, zb)
    g.node('board_parts', head, sub(bp, PITCH_O), g.mesh('board_parts', many(board_parts, bp)),
           {'what': 'parts on the back of the upright board: chips, sockets, pin pads, a dark ribbon and a pale flat cable, as plain blocks (layout from the back photo)', 'basis': 'assumed'})
    for i, sx in enumerate((-21.85, 21.85)):                     # dark screws in the shell's two lower front holes, heads toward the back (holes from the shell file)
        head_t, cross = screw(lambda u, v, c: (u, v, 15.75 - c), sx, 21.88, 1.5, 0.0, 0.8)
        c = (sx, 21.88, 15.35)
        g.node('screw_head_%d' % i, head, sub(c, PITCH_O), g.mesh('screw_head_%d' % i, [g.primitive(head_t, c, 'screw_dark'), g.primitive(cross, c, 'chip')]),
               {'what': 'screw that holds the controller mount to the shell', 'basis': 'measured', 'note': 'hole from the shell file; the head is a stand-in'})
    g.node('reset_button', head, sub(reset_c, PITCH_O), g.mesh('reset_button', [g.primitive(reset_tris, reset_c, 'button')]),
           {'what': "reset button under the controller, beside the card slot: a white key in a dark gap; a press restarts the unit, a 3 second hold enters download mode", 'size': [mm(7.6), mm(5.4)]})
    g.node('sd_slot', head, sub(sd_c, PITCH_O), g.mesh('sd_slot', [g.primitive(sd_tris, sd_c, 'port')]),
           {'what': 'card slot under the controller: an open slot', 'opening': {'size': [mm(12.9), mm(1.3)], 'depth': mm(3.0)}})
    g.node('screen_bottom_led', head, sub(led_bottom_c, PITCH_O), g.mesh('screen_bottom_led', [g.primitive(led_bottom_tris, led_bottom_c, 'led_bottom')]),
           {'what': 'small light hole under the controller, between the card slot and the reset button; green in download mode (product picture); the firmware does not drive it', 'basis': 'assumed'})
    g.node('button_left_top', g.nodes.index(next(n for n in g.nodes if n['name'] == 'power_button')),
           extras={'what': 'another name for power_button: the button at the top of the side that is on the left when you face the screen'})
    for name in sorted(stickers):
        parts, c = stickers[name]
        g.node(name, head, sub(c, PITCH_O), g.mesh(name, many(parts, c)),
               {'what': 'label drawn for this model; the print is a stand-in', 'basis': 'assumed'})
    for i, c in enumerate(pads):
        g.node('touch_back_%d' % i, head, sub(c, PITCH_O), g.mesh('touch_back_%d' % i, [g.primitive(box(c, (pad_w, 0.06, pad_d)), c, 'touch_pad')]),
               {'touch': {'zone': i, 'of': 3, 'order': 'front to back'}, 'what': 'one zone of the head touch strip (three zones in the firmware; position and outline assumed)', 'basis': 'assumed'})
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
            'head_touch_from_pitch_axis': val([[mm(v) for v in sub(c, PITCH_O)] for c in pads], 'assumed', 'in a row on the head top behind the two connector openings, zone 0 at the front'),
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
        'colors': {'value': dict([(m[0], list(m[1])) for m in MATERIALS] + [('light_off', list(LIGHT_OFF))]), 'basis': 'assumed', 'note': 'from product photos'},
    }
    return glb, params


def build(out_dir=HERE):
    """Write stackchan.glb and stackchan.params.json into out_dir; returns the glb path."""
    glb, params = assemble()
    out_dir = Path(out_dir)
    (out_dir / 'stackchan.glb').write_bytes(glb)
    (out_dir / 'stackchan.params.json').write_text(json.dumps(params, indent=1, sort_keys=True) + '\n')
    return out_dir / 'stackchan.glb'


def main(argv):
    if '--check' in argv:
        glb, params = assemble()
        here = Path(HERE)
        same = ((here / 'stackchan.glb').exists() and (here / 'stackchan.glb').read_bytes() == glb and (here / 'stackchan.params.json').exists()
                and (here / 'stackchan.params.json').read_text() == json.dumps(params, indent=1, sort_keys=True) + '\n')
        print('model files match the source files' if same else 'model files are stale: run python3 scripts/virtual-unit/model/make_body.py')
        return 0 if same else 1
    out = build()
    print('wrote stackchan.glb (%d bytes) and stackchan.params.json' % out.stat().st_size)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
