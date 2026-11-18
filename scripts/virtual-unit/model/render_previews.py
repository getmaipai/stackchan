#!/usr/bin/env python3
"""Render the preview pictures of stackchan.glb: six views of the outside and both joints through their ranges.

Every frame is drawn from the glb itself, through its node hierarchy, with the joints turned about the axes stored in
the node extras. Standard library only; the animated GIF needs ffmpeg and is skipped without it.
Run: python3 scripts/virtual-unit/model/render_previews.py [output folder, default docs/dev/model-previews]
"""
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import softrender as sr  # noqa: E402


def load_glb(path):
    data = open(path, 'rb').read()
    if data[:4] != b'glTF':
        raise ValueError('%s is not a glb file: run make_body.py to build it again' % path)
    n = struct.unpack_from('<I', data, 12)[0]
    doc = json.loads(data[20:20 + n])
    return doc, data[20 + n + 8:]


def accessor(doc, blob, i):
    a = doc['accessors'][i]
    v = doc['bufferViews'][a['bufferView']]
    width = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3}[a['type']]
    fmt = {5126: 'f', 5123: 'H', 5125: 'I'}[a['componentType']]
    flat = struct.unpack_from('<%d%s' % (a['count'] * width, fmt), blob, v.get('byteOffset', 0))
    return flat if width == 1 else [flat[k:k + width] for k in range(0, len(flat), width)]


def rot(axis, deg):
    x, y, z = axis
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    t = 1 - c
    return ((t * x * x + c, t * x * y - s * z, t * x * z + s * y), (t * x * y + s * z, t * y * y + c, t * y * z - s * x), (t * x * z - s * y, t * y * z + s * x, t * z * z + c))


def mul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def apply(m, t, p):
    return (m[0][0] * p[0] + m[0][1] * p[1] + m[0][2] * p[2] + t[0], m[1][0] * p[0] + m[1][1] * p[1] + m[1][2] * p[2] + t[1], m[2][0] * p[0] + m[2][1] * p[1] + m[2][2] * p[2] + t[2])


IDENT = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def srgb(c):
    return tuple(int(255 * max(0.0, min(1.0, v)) ** (1 / 2.2)) for v in c[:3])


class Model:
    def __init__(self, path):
        self.doc, self.blob = load_glb(path)
        self.cache = {}

    def mesh_tris(self, mi):
        if mi not in self.cache:
            out = []
            for prim in self.doc['meshes'][mi]['primitives']:
                pos = accessor(self.doc, self.blob, prim['attributes']['POSITION'])
                idx = accessor(self.doc, self.blob, prim['indices'])
                out.append((prim['material'], [(pos[idx[k]], pos[idx[k + 1]], pos[idx[k + 2]]) for k in range(0, len(idx), 3)]))
            self.cache[mi] = out
        return self.cache[mi]

    def posed(self, angles):
        """World-space triangles per material for joint angles {'yaw_joint': deg, 'pitch_joint': deg}."""
        out = {}
        nodes = self.doc['nodes']

        def walk(i, m, t):
            n = nodes[i]
            t = apply(m, t, n.get('translation', (0.0, 0.0, 0.0)))
            joint = n.get('extras', {}).get('joint')
            if joint and n['name'] in angles:
                m = mul(m, rot(joint['axis'], angles[n['name']]))
            if 'mesh' in n:
                for mat, tris in self.mesh_tris(n['mesh']):
                    dst = out.setdefault(mat, [])
                    for a, b, c in tris:
                        dst.append(apply(m, t, a) + apply(m, t, b) + apply(m, t, c))
                if n['name'] == 'screen_plane':  # a plain face so the screen side is obvious in the pictures
                    for cx, cy, w, h in ((-0.009, 0.004, 0.0028, 0.0028), (0.009, 0.004, 0.0028, 0.0028), (0.0, -0.005, 0.009, 0.0009)):
                        q = [apply(m, t, (cx + sx * w / 2, cy + sy * h / 2, 0.0001)) for sx, sy in ((-1, 1), (-1, -1), (1, -1), (1, 1))]
                        out.setdefault('face', []).extend([q[0] + q[1] + q[2], q[0] + q[2] + q[3]])
            for ch in n.get('children', []):
                walk(ch, m, t)
        for r in self.doc['scenes'][self.doc['scene']]['nodes']:
            walk(r, IDENT, (0.0, 0.0, 0.0))
        return out

    def render(self, angles, azimuth, elevation, size, scale=None, center=(0.0, 0.036, 0.002), hide=()):
        cam = sr.camera(azimuth, elevation)
        cv = sr.Canvas(size, size)
        scale = scale or size / 0.094
        for mat, tris in sorted(self.posed(angles).items(), key=lambda kv: str(kv[0])):
            if mat == 'face':
                if 'screen' in hide:
                    continue
                cv.draw(tris, (245, 245, 245), cam, scale, center, emissive=True)
                continue
            m = self.doc['materials'][mat]
            name = m['name']
            if name in hide:
                continue
            if name == 'screen':
                cv.draw(tris, (16, 18, 22), cam, scale, center, emissive=True)
            elif name.startswith('ring_light_'):
                cv.draw(tris, (70, 225, 215), cam, scale, center, emissive=True)
            else:
                cv.draw(tris, srgb(m['pbrMetallicRoughness']['baseColorFactor']), cam, scale, center)
        return cv.pixels()


GLYPH = {  # 3x5 glyphs, rows top to bottom, 3 bits each
    '0': (7, 5, 5, 5, 7), '1': (2, 6, 2, 2, 7), '2': (7, 1, 7, 4, 7), '3': (7, 1, 7, 1, 7), '4': (5, 5, 7, 1, 1), '5': (7, 4, 7, 1, 7), '6': (7, 4, 7, 5, 7),
    '7': (7, 1, 1, 2, 2), '8': (7, 5, 7, 5, 7), '9': (7, 5, 7, 1, 7), '-': (0, 0, 7, 0, 0), ' ': (0, 0, 0, 0, 0), 'Y': (5, 5, 2, 2, 2), 'A': (2, 5, 7, 5, 5),
    'W': (5, 5, 5, 7, 5), 'P': (6, 5, 6, 4, 4), 'I': (7, 2, 2, 2, 7), 'T': (7, 2, 2, 2, 2), 'C': (7, 4, 4, 4, 7), 'H': (5, 5, 7, 5, 5)}


def label(rgb, size, text, k=3):
    x0 = y0 = 8
    for ch in text:
        g = GLYPH.get(ch, GLYPH[' '])
        for r in range(5):
            for c in range(3):
                if g[r] >> (2 - c) & 1:
                    for dy in range(k):
                        for dx in range(k):
                            o = ((y0 + r * k + dy) * size + x0 + c * k + dx) * 3
                            rgb[o:o + 3] = b'\x20\x20\x28'
        x0 += 4 * k
    return rgb


VIEWS = [('front', 0, 0), ('rear', 180, 0), ('left', 90, 0), ('right', -90, 0), ('top', 0, 90), ('three-quarter', -38, 22), ('rear-three-quarter', 142, 22)]


def main(argv):
    out = argv[0] if argv else os.path.join(HERE, '..', '..', '..', 'docs', 'dev', 'model-previews')
    os.makedirs(out, exist_ok=True)
    model = Model(os.path.join(HERE, 'stackchan.glb'))
    joints = {n['name']: n['extras']['joint'] for n in model.doc['nodes'] if 'joint' in n.get('extras', {})}
    (y0, y1), (p0, p1) = joints['yaw_joint']['limit_deg'], joints['pitch_joint']['limit_deg']
    rest = {'yaw_joint': 0.0, 'pitch_joint': 0.0}
    for name, az, el in VIEWS:
        sr.write_png(os.path.join(out, name + '.png'), 720, 720, model.render(rest, az, el, 720))
        print('wrote', name + '.png')
    # cutaway: the shell, the controller and the holder taken off, so the servos, battery, boards and cable show
    off = ('shell', 'core', 'glass', 'screen', 'camera', 'button', 'port', 'port_red', 'neck', 'servo', 'light_bar')
    for name, az in (('cutaway-rear', 142), ('cutaway-front', -38)):
        sr.write_png(os.path.join(out, name + '.png'), 720, 720, model.render(rest, az, 22, 720, hide=off))
        print('wrote', name + '.png')
    S = 400
    wide = S / 0.118  # room for the head swinging round
    poses = [('YAW %d' % y0, {'yaw_joint': y0, 'pitch_joint': p0}), ('YAW 0', {'yaw_joint': 0.0, 'pitch_joint': p0}), ('YAW %d' % y1, {'yaw_joint': y1, 'pitch_joint': p0}),
             ('PITCH %d' % p0, {'yaw_joint': 0.0, 'pitch_joint': p0}), ('PITCH %d' % ((p0 + p1) / 2), {'yaw_joint': 0.0, 'pitch_joint': (p0 + p1) / 2}),
             ('PITCH %d' % p1, {'yaw_joint': 0.0, 'pitch_joint': p1})]
    tiles = [label(model.render(a, -38 if i < 3 else -80, 22 if i < 3 else 8, S, wide), S, text) for i, (text, a) in enumerate(poses)]
    w, h, rgb = sr.tile(tiles, 3, S, S)
    sr.write_png(os.path.join(out, 'joints-contact-sheet.png'), w, h, rgb)
    print('wrote joints-contact-sheet.png')
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        print('ffmpeg not found: joints.gif skipped; install ffmpeg and run again to make it')
        return 0
    steps = [(0.0, p0 + (p1 - p0) * i / 9.0) for i in range(10)] + [(0.0, p1 - (p1 - p0) * i / 9.0) for i in range(1, 10)]
    steps += [(y1 * i / 6.0, p0) for i in range(1, 7)] + [(y1 + (y0 - y1) * i / 12.0, p0) for i in range(1, 13)] + [(y0 - y0 * i / 6.0, p0) for i in range(1, 7)]
    tmp = tempfile.mkdtemp(prefix='model-frames-')
    try:
        G = 320
        for i, (yw, pt) in enumerate(steps):
            px = label(model.render({'yaw_joint': yw, 'pitch_joint': pt}, -38, 22, G, G / 0.118), G, 'YAW %d  PITCH %d' % (yw, pt), 2)
            sr.write_png(os.path.join(tmp, 'f%03d.png' % i), G, G, px)
        subprocess.run([ffmpeg, '-v', 'error', '-y', '-framerate', '8', '-i', os.path.join(tmp, 'f%03d.png'),
                        '-filter_complex', 'split[a][b];[a]palettegen=max_colors=64[p];[b][p]paletteuse=dither=none', os.path.join(out, 'joints.gif')], check=True)
        print('wrote joints.gif (%d frames)' % len(steps))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
