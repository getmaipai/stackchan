"""A small software renderer for the body model previews: standard library only.

Orthographic camera, depth buffer, flat shading, depth outlines, 2x supersampling, PNG output.
Used by render_previews.py; nothing at run time depends on it.
"""
import math
import struct
import zlib


def read_stl(path):
    """Read a binary or ascii STL as a list of triangles, each a tuple of nine floats. Parses data only."""
    data = open(path, 'rb').read()
    if len(data) >= 84:
        count = struct.unpack_from('<I', data, 80)[0]
        if 84 + 50 * count == len(data):
            return [struct.unpack_from('<9f', data, 84 + 50 * i + 12) for i in range(count)]
    tris, cur = [], []
    for line in data.decode('ascii', 'replace').splitlines():
        parts = line.split()
        if len(parts) == 4 and parts[0] == 'vertex':
            cur.extend(float(p) for p in parts[1:])
            if len(cur) == 9:
                tris.append(tuple(cur))
                cur = []
    if not tris:
        raise ValueError('%s holds no triangles: check that the file is an STL and download it again' % path)
    return tris


def camera(azimuth_deg, elevation_deg):
    """Right, up and forward unit vectors of a camera that looks at the origin. Azimuth 0 looks at the front (+Z face)."""
    a, e = math.radians(azimuth_deg), math.radians(elevation_deg)
    pos = (math.sin(a) * math.cos(e), math.sin(e), math.cos(a) * math.cos(e))
    fwd = (-pos[0], -pos[1], -pos[2])
    if abs(pos[1]) > 0.999:
        right = (1.0, 0.0, 0.0)
    else:
        n = math.hypot(fwd[2], fwd[0])
        right = (-fwd[2] / n, 0.0, fwd[0] / n)
    up = (right[1] * fwd[2] - right[2] * fwd[1], right[2] * fwd[0] - right[0] * fwd[2], right[0] * fwd[1] - right[1] * fwd[0])
    return right, up, fwd


class Canvas:
    def __init__(self, width, height, bg=(244, 245, 247), ss=2):
        self.w, self.h, self.ss = width, height, ss
        self.W, self.H = width * ss, height * ss
        self.bg = bg
        self.rgb = [bg] * (self.W * self.H)
        self.z = [1e30] * (self.W * self.H)

    def draw(self, tris, color, cam, scale, center=(0.0, 0.0, 0.0), emissive=False):
        """Draw world-space triangles (nine floats each) in one color. `scale` is pixels per world unit."""
        (rx, ry, rz), (ux, uy, uz), (fx, fy, fz) = cam
        s = scale * self.ss
        W, H, rgb, zb = self.W, self.H, self.rgb, self.z
        ox, oy = W / 2.0, H / 2.0
        cx, cy, cz = center
        # one light up and to the left of the camera, plus fill
        lx, ly, lz = (-0.45 * rx + 0.55 * ux - 0.70 * fx, -0.45 * ry + 0.55 * uy - 0.70 * fy, -0.45 * rz + 0.55 * uz - 0.70 * fz)
        ln = math.sqrt(lx * lx + ly * ly + lz * lz)
        lx, ly, lz = lx / ln, ly / ln, lz / ln
        for t in tris:
            ax, ay, az, bx, by, bz, qx, qy, qz = t
            ex, ey, ez = bx - ax, by - ay, bz - az
            gx, gy, gz = qx - ax, qy - ay, qz - az
            nx, ny, nz = ey * gz - ez * gy, ez * gx - ex * gz, ex * gy - ey * gx
            nl = math.sqrt(nx * nx + ny * ny + nz * nz)
            if nl == 0.0:
                continue
            nx, ny, nz = nx / nl, ny / nl, nz / nl
            if nx * fx + ny * fy + nz * fz > 0.0:  # faces away: light it as if it faced the camera
                nx, ny, nz = -nx, -ny, -nz
            if emissive:
                shade = 1.0
            else:
                shade = 0.42 + 0.58 * max(0.0, nx * lx + ny * ly + nz * lz) + 0.10 * max(0.0, -(nx * fx + ny * fy + nz * fz))
            col = (min(255, int(color[0] * shade)), min(255, int(color[1] * shade)), min(255, int(color[2] * shade)))
            pts = []
            for px, py, pz in ((ax, ay, az), (bx, by, bz), (qx, qy, qz)):
                px, py, pz = px - cx, py - cy, pz - cz
                pts.append((ox + s * (px * rx + py * ry + pz * rz), oy - s * (px * ux + py * uy + pz * uz), px * fx + py * fy + pz * fz))
            pts.sort(key=lambda p: p[1])
            (x0, y0, z0), (x1, y1, z1), (x2, y2, z2) = pts
            if y2 - y0 < 1e-9:
                continue
            ya, yb = max(0, int(math.ceil(y0))), min(H - 1, int(math.floor(y2)))
            for y in range(ya, yb + 1):
                tl = (y - y0) / (y2 - y0)
                xl, zl = x0 + (x2 - x0) * tl, z0 + (z2 - z0) * tl
                if y < y1:
                    d = y1 - y0
                    ts = (y - y0) / d if d > 1e-12 else 0.0
                    xs, zs = x0 + (x1 - x0) * ts, z0 + (z1 - z0) * ts
                else:
                    d = y2 - y1
                    ts = (y - y1) / d if d > 1e-12 else 0.0
                    xs, zs = x1 + (x2 - x1) * ts, z1 + (z2 - z1) * ts
                if xs < xl:
                    xl, xs, zl, zs = xs, xl, zs, zl
                xa, xb = max(0, int(math.ceil(xl))), min(W - 1, int(math.floor(xs)))
                if xb < xa:
                    continue
                dz = (zs - zl) / (xs - xl) if xs - xl > 1e-12 else 0.0
                zv = zl + (xa - xl) * dz
                row = y * W
                for i in range(row + xa, row + xb + 1):
                    if zv < zb[i]:
                        zb[i] = zv
                        rgb[i] = col
                    zv += dz

    def pixels(self, outline=0.0012):
        """Downsample to the output size as RGB bytes, with dark outlines where the depth jumps by more than `outline` world units."""
        W, H, ss, zb, rgb = self.W, self.H, self.ss, self.z, self.rgb
        if outline:
            edge = set()
            for y in range(H - 1):
                row = y * W
                for i in range(row, row + W - 1):
                    z = zb[i]
                    if abs(z - zb[i + 1]) > outline or abs(z - zb[i + W]) > outline:
                        edge.add(i)
            for i in edge:
                r, g, b = rgb[i]
                rgb[i] = (r * 2 // 5, g * 2 // 5, b * 2 // 5)
        out = bytearray(self.w * self.h * 3)
        n = ss * ss
        o = 0
        for y in range(self.h):
            for x in range(self.w):
                r = g = b = 0
                for dy in range(ss):
                    base = (y * ss + dy) * W + x * ss
                    for dx in range(ss):
                        p = rgb[base + dx]
                        r += p[0]
                        g += p[1]
                        b += p[2]
                out[o] = r // n
                out[o + 1] = g // n
                out[o + 2] = b // n
                o += 3
        return out


def write_png(path, width, height, rgb):
    def chunk(tag, body):
        return struct.pack('>I', len(body)) + tag + body + struct.pack('>I', zlib.crc32(tag + body) & 0xffffffff)
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw += rgb[y * width * 3:(y + 1) * width * 3]
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(bytes(raw), 9)) + chunk(b'IEND', b''))


def tile(images, cols, width, height, gap=6, bg=(255, 255, 255)):
    """Lay equal-size RGB images out in a grid; returns (width, height, rgb)."""
    rows = (len(images) + cols - 1) // cols
    tw, th = cols * width + (cols + 1) * gap, rows * height + (rows + 1) * gap
    out = bytearray(bytes(bg) * (tw * th))
    for n, img in enumerate(images):
        x0, y0 = gap + (n % cols) * (width + gap), gap + (n // cols) * (height + gap)
        for y in range(height):
            o = ((y0 + y) * tw + x0) * 3
            out[o:o + width * 3] = img[y * width * 3:(y + 1) * width * 3]
    return tw, th, out
