"""A small software renderer for the model previews: pure Python, no dependencies.

Reads binary or ASCII STL files (as data only), rasterizes triangles with a z-buffer and simple
two-light shading, and writes PNG files with the standard library. Slow but deterministic; meant for
previews of a few hundred pixels.
"""
from __future__ import annotations

import math
import struct
import zlib


def read_stl(path):
    """Return a list of triangles ((x,y,z),(x,y,z),(x,y,z)) from a binary or ASCII STL file."""
    data = open(path, "rb").read()
    if len(data) >= 84:
        n = struct.unpack_from("<I", data, 80)[0]
        if 84 + 50 * n == len(data):
            tris = []
            for i in range(n):
                v = struct.unpack_from("<9f", data, 84 + 50 * i + 12)
                tris.append(((v[0], v[1], v[2]), (v[3], v[4], v[5]), (v[6], v[7], v[8])))
            return tris
    text = data.decode("ascii", "replace")
    verts = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 4 and parts[0] == "vertex":
            verts.append(tuple(float(p) for p in parts[1:]))
    if len(verts) % 3:
        raise ValueError(f"{path}: the STL file is cut short ({len(verts)} vertices); download it again")
    return [tuple(verts[i:i + 3]) for i in range(0, len(verts), 3)]


def write_png(path, width, height, rgb_rows):
    """rgb_rows: list of bytearrays, each width*3 bytes."""
    raw = b"".join(b"\x00" + bytes(r) for r in rgb_rows)

    def chunk(tag, body):
        c = struct.pack(">I", len(body)) + tag + body
        return c + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def _norm(v):
    l = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) or 1.0
    return (v[0] / l, v[1] / l, v[2] / l)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def look_basis(azimuth_deg, elevation_deg):
    """Camera basis for an orthographic view. Azimuth 0 looks at the robot's front (camera on +Z),
    90 puts the camera on +X; elevation lifts the camera above the horizon. Y is up."""
    az, el = math.radians(azimuth_deg), math.radians(elevation_deg)
    back = (math.sin(az) * math.cos(el), math.sin(el), math.cos(az) * math.cos(el))  # toward the camera
    right = _norm(_cross((0.0, 1.0, 0.0), back)) if abs(el) < math.radians(89.9) else (1.0, 0.0, 0.0)
    up = _cross(back, right)
    return right, up, back


class Canvas:
    def __init__(self, width, height, background=(244, 245, 247)):
        self.w, self.h = width, height
        self.color = [bytearray(background * width) for _ in range(height)]
        self.depth = [[-1e30] * width for _ in range(height)]

    def draw(self, items, basis, center, scale, light_dirs=None, outline=True):
        """items: list of (triangles, (r,g,b)) in world space. Orthographic projection."""
        right, up, back = basis
        lights = light_dirs or [(_norm((0.4, 0.7, 0.6)), 0.75), (_norm((-0.6, 0.3, -0.5)), 0.30)]
        w, h = self.w, self.h
        cx, cy = w / 2.0, h / 2.0
        for tris, base_color in items:
            for a, b, c in tris:
                n = _cross(_sub(b, a), _sub(c, a))
                nl = math.sqrt(_dot(n, n))
                if nl == 0:
                    continue
                n = (n[0] / nl, n[1] / nl, n[2] / nl)
                facing = _dot(n, back)
                if facing < 0:  # light both sides: some official files have flipped faces
                    n = (-n[0], -n[1], -n[2])
                shade = 0.32 + sum(max(0.0, _dot(n, ld)) * k for ld, k in lights)
                shade = min(shade, 1.15)
                col = tuple(min(255, int(ch * shade)) for ch in base_color)
                pts = []
                for p in (a, b, c):
                    d = _sub(p, center)
                    pts.append((cx + _dot(d, right) * scale, cy - _dot(d, up) * scale, _dot(d, back)))
                self._tri(pts, col)
        if outline:
            self._outline()

    def _tri(self, pts, col):
        (x0, y0, z0), (x1, y1, z1), (x2, y2, z2) = pts
        minx, maxx = max(int(min(x0, x1, x2)), 0), min(int(max(x0, x1, x2)) + 1, self.w - 1)
        miny, maxy = max(int(min(y0, y1, y2)), 0), min(int(max(y0, y1, y2)) + 1, self.h - 1)
        if minx > maxx or miny > maxy:
            return
        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if abs(area) < 1e-12:
            return
        inv = 1.0 / area
        r, g, b = col
        for py in range(miny, maxy + 1):
            sy = py + 0.5
            row_c, row_d = self.color[py], self.depth[py]
            for px in range(minx, maxx + 1):
                sx = px + 0.5
                w0 = ((x1 - sx) * (y2 - sy) - (x2 - sx) * (y1 - sy)) * inv
                w1 = ((x2 - sx) * (y0 - sy) - (x0 - sx) * (y2 - sy)) * inv
                w2 = 1.0 - w0 - w1
                if w0 < -1e-9 or w1 < -1e-9 or w2 < -1e-9:
                    continue
                z = w0 * z0 + w1 * z1 + w2 * z2
                if z > row_d[px]:
                    row_d[px] = z
                    i = px * 3
                    row_c[i], row_c[i + 1], row_c[i + 2] = r, g, b

    def _outline(self):
        """Darken pixels at a depth jump so edges read on flat-lit parts."""
        d = self.depth
        for y in range(1, self.h - 1):
            for x in range(1, self.w - 1):
                z = d[y][x]
                if z < -1e29:
                    continue
                m = max(abs(z - d[y][x + 1]), abs(z - d[y + 1][x]), abs(z - d[y][x - 1]), abs(z - d[y - 1][x]))
                if m > 0.0015:
                    i = x * 3
                    row = self.color[y]
                    row[i], row[i + 1], row[i + 2] = row[i] * 2 // 5, row[i + 1] * 2 // 5, row[i + 2] * 2 // 5

    def label(self, text, x, y, color=(30, 30, 30)):
        """Draw a short label with a tiny built-in 3x5 pixel font (letters, digits, a few marks), scaled 2x."""
        for ch in text.upper():
            glyph = _FONT.get(ch, _FONT[" "])
            for gy, rowbits in enumerate(glyph):
                for gx in range(3):
                    if rowbits >> (2 - gx) & 1:
                        for dy in range(2):
                            for dx in range(2):
                                px, py = x + gx * 2 + dx, y + gy * 2 + dy
                                if 0 <= px < self.w and 0 <= py < self.h:
                                    i = px * 3
                                    self.color[py][i:i + 3] = bytes(color)
            x += 8

    def save(self, path):
        write_png(path, self.w, self.h, self.color)


_FONT = {
    " ": [0, 0, 0, 0, 0], "-": [0, 0, 7, 0, 0], ".": [0, 0, 0, 0, 2], "+": [0, 2, 7, 2, 0], ":": [0, 2, 0, 2, 0],
    "0": [7, 5, 5, 5, 7], "1": [2, 6, 2, 2, 7], "2": [7, 1, 7, 4, 7], "3": [7, 1, 7, 1, 7], "4": [5, 5, 7, 1, 1],
    "5": [7, 4, 7, 1, 7], "6": [7, 4, 7, 5, 7], "7": [7, 1, 1, 1, 1], "8": [7, 5, 7, 5, 7], "9": [7, 5, 7, 1, 7],
    "A": [2, 5, 7, 5, 5], "B": [6, 5, 6, 5, 6], "C": [7, 4, 4, 4, 7], "D": [6, 5, 5, 5, 6], "E": [7, 4, 6, 4, 7],
    "F": [7, 4, 6, 4, 4], "G": [7, 4, 5, 5, 7], "H": [5, 5, 7, 5, 5], "I": [7, 2, 2, 2, 7], "J": [1, 1, 1, 5, 7],
    "K": [5, 5, 6, 5, 5], "L": [4, 4, 4, 4, 7], "M": [5, 7, 7, 5, 5], "N": [6, 5, 5, 5, 5], "O": [7, 5, 5, 5, 7],
    "P": [7, 5, 7, 4, 4], "Q": [7, 5, 5, 7, 1], "R": [7, 5, 6, 5, 5], "S": [7, 4, 7, 1, 7], "T": [7, 2, 2, 2, 2],
    "U": [5, 5, 5, 5, 7], "V": [5, 5, 5, 5, 2], "W": [5, 5, 7, 7, 5], "X": [5, 5, 2, 5, 5], "Y": [5, 5, 2, 2, 2],
    "Z": [7, 1, 2, 4, 7],
}
