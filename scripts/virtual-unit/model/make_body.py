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
    ('ServoCover', 'neck', 'servo', lambda p: (p[0], p[1], p[2] - 12.0)),  # its screw holes meet the servo body's
    ('ServoSideCover', 'neck', 'neck', lambda p: p),
    ('MainBody', 'head', 'shell', lambda p: (p[0] - 246.0, p[1] + 13.0, p[2])),
    ('ServoArm', 'head', 'neck', lambda p: (YAW_X + WALL - (p[0] - 327.73), p[1] + 123.05, 2 * PITCH_Z - p[2])),
    ('BearingFixture', 'head', 'neck', lambda p: (YAW_X - WALL + (p[0] - 327.73), p[1] + 123.05, p[2])),
    ('LightGuideBar-A', 'head', 'light_bar', _bar(+1)),
    ('LightGuideBar-B', 'head', 'light_bar', _bar(-1)),
]

MATERIALS = [  # name, base color (linear RGBA), metallic, roughness, emissive. Colors are judged from product photos.
    ('base', (0.10, 0.10, 0.105, 1.0), 0.0, 0.75, None),
    ('port', (0.012, 0.012, 0.014, 1.0), 0.0, 0.5, None),
    ('neck', (0.26, 0.26, 0.27, 1.0), 0.0, 0.7, None),
    ('servo', (0.42, 0.42, 0.43, 1.0), 0.0, 0.7, None),
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


def circle(r, seg=20):
    return [(r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg)) for i in range(seg)]


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
    geo['head']['core'] = prism(rounded_outline(54.0, 54.0, CORE_R_MM), 0.0, cy, front, face - 0.2)
    geo['head']['glass'] = prism(rounded_outline(51.6, 51.6, 3.0), 0.0, cy, face - 0.2, face)
    row = top - 54.0 + 5.9                                    # camera, microphones and light sensor sit in one row under the screen
    geo['head']['camera'] = prism(circle(2.0), 0.0, row, face, face + 0.03)
    dots = prism(circle(1.3), 0.0, row, face + 0.03, face + 0.05)
    geo['head']['button'] = []
    for dx in (-14.1, 6.9, 9.0, 14.1):                        # two microphones and the two sensor windows, off the published drawing
        geo['head']['button'] += prism(circle(0.4, 8), dx, row, face, face + 0.03)
    side_z = face - 8.0                                       # buttons and ports sit this far behind the glass (published drawing)
    for r in range(13):                                       # speaker grille on the robot's left side of the controller
        for c in range(4):
            dots += disc_x((27.02, top - 10.5 - 2.0 * r - (1.0 if c % 2 else 0.0), face - 5.6 - 1.6 * c), 0.4, 1, 8)
    geo['head']['port'] = dots
    # the board under the head top, seen through the open back (position assumed; it clears the servo housing over the whole sweep)
    geo['head']['pcb'] = box((0.0, top - 3.1, (front - 1.5 + head_lo[2] + 9.0) / 2.0), (45.0, 1.2, front - 1.5 - head_lo[2] - 9.0))
    button_c = (-27.3, top - 13.9, side_z)
    otg_c = (-27.03, top - 26.9, side_z)
    port_a_c = (-27.03, top - 41.2, side_z)
    screen_c = (0.0, cy - SCREEN_DROP_MM, face + 0.03)

    g = Glb()
    for i in range(LIGHTS):
        g.mat['ring_light_%d' % i] = len(MATERIALS) + i

    def prims(node):
        return [g.primitive(geo[node][m[0]], ORIGIN[node], m[0]) for m in MATERIALS if geo[node].get(m[0])]

    def mm(v):
        return round(v / 1000.0, 6)

    limiter = 'firmware/main/hal/hal_servo.cpp (upstream tree pinned in firmware/BASE), Hal::servo_init angleLimit, tenths of a degree'
    root = g.node('stackchan', extras={'units': 'meters', 'up': '+Y', 'front': '+Z', 'left': '+X',
                                       'origin': 'yaw axis (turntable center) on the table plane', 'params': 'stackchan.params.json'})
    base = g.node('base', root, mesh=g.mesh('base', prims('base')))
    base_bottom = -32.6 - BASE_DROP - TABLE_Z
    usb_c = (0.0, -24.65 - BASE_DROP - TABLE_Z, -(-296.58 - YAW_Y) + 0.8)
    g.node('usb_c_port', base, usb_c, g.mesh('usb_c_port', [g.primitive(box(usb_c, (8.9, 3.2, 0.4)), usb_c, 'port_metal')]),
           {'what': 'USB-C for charging and data on the back of the base'})
    mid = -(BASE_MID_Y - YAW_Y)
    for i, (fx, fz) in enumerate([(-16.0, 24.0), (16.0, 24.0), (16.0, -24.0), (-16.0, -24.0)]):
        g.node('foot_%d' % i, base, (fx, base_bottom, mid + fz),
               extras={'what': 'corner mounting hole on the base underside (the base has no separate feet; the bottom plate rests on the table)'})
    b_lo, b_hi = bounds([t for m in geo['base'].values() for t in m])
    g.node('col_base', base, [(b_lo[k] + b_hi[k]) / 2.0 for k in range(3)],
           extras={'collider': {'shape': 'box', 'size': [mm(b_hi[k] - b_lo[k]) for k in range(3)]}})

    yaw = g.node('yaw_joint', base, YAW_O, extras={'joint': {
        'type': 'revolute', 'axis': [0.0, -1.0, 0.0], 'positive': "turns the head toward the robot's right", 'limit_deg': list(YAW_LIMIT_DEG), 'rest_deg': 0.0,
        'source': limiter + ': yaw (-1280, 1280)', 'published': '360 degree servo, no angle restriction (product page)'}})
    g.node('neck', yaw, mesh=g.mesh('neck', prims('neck')), extras={'what': 'servo holder that turns with yaw: holder and its two covers'})
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
    g.node('power_button', head, sub(button_c, PITCH_O), g.mesh('power_button', [g.primitive(box(button_c, (0.6, 8.0, 6.0)), button_c, 'button')]),
           {'what': "power button on the controller's right side"})
    g.node('usb_c_otg', head, sub(otg_c, PITCH_O), g.mesh('usb_c_otg', [g.primitive(box(otg_c, (0.1, 9.0, 3.3)), otg_c, 'port')]),
           {'what': "USB-C (OTG) on the controller's right side"})
    g.node('port_a', head, sub(port_a_c, PITCH_O), g.mesh('port_a', [g.primitive(box(port_a_c, (0.1, 10.0, 5.0)), port_a_c, 'port_red')]),
           {'what': "I2C port A on the controller's right side"})
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
