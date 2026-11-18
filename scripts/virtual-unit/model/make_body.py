#!/usr/bin/env python3
"""Build the rigged 3D model of the robot (stackchan.glb and stackchan.params.json) from source/.

Deterministic: the same source files give byte-identical output. Pure Python, standard library only.
The official structure files are read as data with our own STL reader; nothing in them is executed.

Frame: meters, Y up, the robot faces +Z, X is the robot's left. Origin: the yaw axis (the turntable
center) on the table plane. Run: python3 scripts/virtual-unit/model/make_body.py
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from softrender import read_stl  # noqa: E402

SRC = HERE / "source"
MM = 0.001

# ---------------------------------------------------------------------------------------------
# Assembly. Every part file has its own CAD offset. All parts share one orientation (file +Z is up,
# file -Y is the front); the offsets below put each part into the Base file's frame. How each was
# found is in MATCH.md ("Assembly"): the servo holder sits on the base turntable (same center),
# the pitch arms' hole fits the shaft stub on the holder, the shell's center is on the pitch axis and
# its front is set by the published 61.5 mm depth with the screen 1 mm ahead of the base front.
# ---------------------------------------------------------------------------------------------
AXIS_X, AXIS_Y = 106.73, -320.56       # yaw axis in the Base file frame (holder ring and stub center)
TABLE_Z = -32.6 - 1.51                 # base bottom minus the bottom cover plate (1.51 mm)
PITCH_Z = 9.30                         # pitch axis height in the Base file frame (stub and arm hole center)
BASE_TOP_Z = -21.5                     # top of the base turntable seat

PARTS = {
    # name: (file stem, translation into the Base frame (mm), rotation key, group)
    "base_body": ("Base", (0.0, 0.0, 0.0), None, "base"),
    "base_cover": ("BaseCover", (106.73, -338.445, 8.68), None, "base"),
    "servo_holder": ("ServoBody", (-123.0, 0.0, 0.0), None, "neck"),
    "servo_cover": ("ServoCover", (-123.0, 0.0, 0.0), None, "neck"),
    "servo_side_cover": ("ServoSideCover", (-123.0, 0.0, 0.0), None, "neck"),
    "servo_arm": ("ServoArm", (-246.0, 123.0, 0.0), None, "head"),
    "bearing_fixture": ("BearingFixture", (-199.1, 123.0, 0.0), None, "head"),
    "shell": ("MainBody", (-369.0, 13.0, 0.0), None, "head"),
    "light_bar_left": ("LightGuideBar-A", None, "bar_left", "head"),
    "light_bar_right": ("LightGuideBar-B", None, "bar_right", "head"),
}

# Head shell outer box in the Base frame (from the shell file plus its offset).
SHELL_X0, SHELL_X1 = 79.73, 133.73
SHELL_Y0 = -339.01                     # shell front (file -352.01 + 13)
SHELL_Z0, SHELL_Z1 = -17.7, 36.3
CORE_DEPTH = 14.8                      # controller unit depth: 61.5 published head depth minus the 46.7 shell
BAR_WINDOW_Y = -347.225 + 13.0         # center of the light bar window in the shell side (file frame + offset)


def to_model(p):
    """Base-file millimeters -> model meters (Y up, front +Z, origin on the yaw axis at the table)."""
    x, y, z = p
    return ((x - AXIS_X) * MM, (z - TABLE_Z) * MM, -(y - AXIS_Y) * MM)


YAW_ORIGIN = to_model((AXIS_X, AXIS_Y, BASE_TOP_Z))
PITCH_ORIGIN = to_model((AXIS_X, AXIS_Y, PITCH_Z))

# Joint limits: the firmware servo layer's hard limits. Source: the upstream firmware tree pinned in
# firmware/BASE, file firmware/main/hal/hal_servo.cpp, Hal::servo_init(): yaw angleLimit (-1280, 1280)
# and pitch angleLimit (30, 870), both in tenths of a degree.
YAW_LIMIT = (-128.0, 128.0)
PITCH_LIMIT = (3.0, 87.0)
LIMIT_SOURCE = "firmware/main/hal/hal_servo.cpp (upstream tree pinned in firmware/BASE), Hal::servo_init angleLimit, tenths of a degree"

COLORS = {  # base color RGBA, assumed from product photos
    "base": (0.36, 0.37, 0.39, 1.0),
    "neck": (0.60, 0.61, 0.63, 1.0),
    "shell": (0.90, 0.91, 0.92, 1.0),
    "core": (0.86, 0.87, 0.88, 1.0),
    "glass": (0.05, 0.05, 0.06, 1.0),
    "screen": (0.0, 0.0, 0.0, 1.0),
    "light_bar": (0.95, 0.97, 0.97, 1.0),
    "pcb": (0.10, 0.35, 0.30, 1.0),
    "servo": (0.45, 0.46, 0.48, 1.0),
    "port": (0.12, 0.12, 0.13, 1.0),
    "button": (0.80, 0.81, 0.82, 1.0),
    "camera": (0.20, 0.17, 0.15, 1.0),
    "light_off": (0.30, 0.30, 0.32, 1.0),
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ------------------------------- geometry helpers --------------------------------------------
def translate(tris, d):
    return [tuple((p[0] + d[0], p[1] + d[1], p[2] + d[2]) for p in t) for t in tris]


def bar_transform(tris, side):
    """Light bar file: long axis Y, light exits at +X (x = 5.18). Stand it up in the shell side window:
    long axis vertical, exit face outward, flush with the shell side."""
    out = []
    for t in tris:
        q = []
        for x, y, z in t:
            # quarter turn about X: file Y -> up (Z), file Z -> depth (-Y)
            nx, ny, nz = x, -z, y
            if side == "bar_left":    # robot's left is file +X: exit face at +X
                nx, ny, nz = nx - 5.18 + SHELL_X1, ny + BAR_WINDOW_Y, nz + PITCH_Z
            else:                      # half turn about the vertical: exit face at -X
                nx, ny, nz = -nx + 5.18 + SHELL_X0, -ny + BAR_WINDOW_Y, nz + PITCH_Z
            q.append((nx, ny, nz))
        out.append(tuple(q))
    return out


def box(x0, x1, y0, y1, z0, z1):
    """Axis-aligned box in Base-frame mm as 12 triangles (outward winding)."""
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6), (1, 2, 6), (1, 6, 5), (3, 0, 4), (3, 4, 7)]
    return [(v[a], v[b], v[c]) for a, b, c in f]


def rounded_slab_y(x0, x1, z0, z1, y0, y1, r, seg=6):
    """A slab facing front/back (thickness along file Y) whose outline in X-Z has rounded corners."""
    cx = [(x1 - r, z1 - r, 0), (x0 + r, z1 - r, 90), (x0 + r, z0 + r, 180), (x1 - r, z0 + r, 270)]
    ring = []
    for ccx, ccz, a0 in cx:
        for i in range(seg + 1):
            a = math.radians(a0 + 90.0 * i / seg)
            ring.append((ccx + r * math.cos(a), ccz + r * math.sin(a)))
    mx, mz = (x0 + x1) / 2, (z0 + z1) / 2
    tris = []
    n = len(ring)
    for i in range(n):
        (ax, az), (bx, bz) = ring[i], ring[(i + 1) % n]
        tris.append(((mx, y0, mz), (bx, y0, bz), (ax, y0, az)))      # front face (toward -Y)
        tris.append(((mx, y1, mz), (ax, y1, az), (bx, y1, bz)))      # back face
        tris.append(((ax, y0, az), (bx, y0, bz), (bx, y1, bz)))      # side wall
        tris.append(((ax, y0, az), (bx, y1, bz), (ax, y1, az)))
    return tris


def disc_y(cx, cz, y, r, seg=20, facing=-1):
    tris = []
    for i in range(seg):
        a0, a1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
        p0 = (cx + r * math.cos(a0), y, cz + r * math.sin(a0))
        p1 = (cx + r * math.cos(a1), y, cz + r * math.sin(a1))
        tris.append(((cx, y, cz), p1, p0) if facing < 0 else ((cx, y, cz), p0, p1))
    return tris


# ------------------------------- parts ------------------------------------------------------
def load_parts():
    parts = {}
    for name, (stem, d, rot, group) in PARTS.items():
        tris = read_stl(SRC / f"StackChan-{stem}.stl")
        tris = bar_transform(tris, rot) if rot else translate(tris, d)
        parts[name] = (tris, group)
    return parts


def primitives():
    """Parts the official files do not cover, in Base-frame mm. Positions from the published drawing."""
    front = SHELL_Y0 - CORE_DEPTH                         # controller front face (file -Y is the front)
    p = {}
    p["core_unit"] = (rounded_slab_y(SHELL_X0, SHELL_X1, SHELL_Z0, SHELL_Z1, front + 0.4, SHELL_Y0, 4.0), "head", "core")
    p["front_glass"] = (rounded_slab_y(SHELL_X0 + 1.75, SHELL_X1 - 1.75, SHELL_Z0 + 1.6, SHELL_Z1 - 1.6, front, front + 0.4, 3.0), "head", "glass")
    p["camera_lens"] = (disc_y(AXIS_X, SHELL_Z1 - 47.6, front - 0.05, 1.5), "head", "camera")
    p["board"] = (box(SHELL_X0 + 1.8, SHELL_X1 - 1.8, SHELL_Y0, SHELL_Y0 + 1.0, SHELL_Z0 + 3.0, SHELL_Z1 - 2.0), "head", "pcb")
    # the pitch servo case between the holder top (13.5) and the servo cover (18.7), file frame of the holder minus 123
    p["pitch_servo"] = (box(210.73 - 123.0 + 1.0, 240.83 - 123.0 - 1.0, -333.0, -299.0, 13.5, 18.7), "neck", "servo")
    return p


def markers():
    """Small marker meshes for named parts, each in its own node (Base-frame mm boxes)."""
    front = SHELL_Y0 - CORE_DEPTH
    head_top = SHELL_Z1
    m = {}
    # power button and USB-C (OTG) on the controller's right side (file -X); centers from the drawing's right view
    m["power_button"] = (box(SHELL_X0 - 0.6, SHELL_X0 + 0.2, front + 4.6, front + 10.6, head_top - 17.9, head_top - 9.9), "button")
    m["usb_c_otg"] = (box(SHELL_X0 - 0.3, SHELL_X0 + 0.2, front + 6.2, front + 9.4, head_top - 34.0, head_top - 25.0), "port")
    m["port_a"] = (box(SHELL_X0 - 0.3, SHELL_X0 + 0.2, front + 5.5, front + 10.0, head_top - 45.0, head_top - 36.5), "port")
    # charge and data USB-C on the base back (file +Y), centerd, 8 mm above the table
    m["usb_c_port"] = (box(AXIS_X - 4.45, AXIS_X + 4.45, -296.58 - 0.6, -296.58 + 0.3, TABLE_Z + 8.0 - 1.6, TABLE_Z + 8.0 + 1.6), "port")
    return m


def screen_quad():
    """The 2.0 inch 320x240 display, 41.5 x 31.6 mm, centerd on the controller face (drawing front view)."""
    front = SHELL_Y0 - CORE_DEPTH - 0.06
    w, h = 41.5, 31.6
    cz = (SHELL_Z0 + SHELL_Z1) / 2
    x0, x1, z0, z1 = AXIS_X - w / 2, AXIS_X + w / 2, cz - h / 2, cz + h / 2
    # robot faces -Y in the file frame; seen from the front, the screen's left edge is at file +X
    tl, tr, br, bl = (x1, front, z1), (x0, front, z1), (x0, front, z0), (x1, front, z0)
    return [tl, tr, br, bl], [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)], (w, h)


def ring_light_centers():
    """Six lights per bar on the outward face, 5 mm apart (assumed). 0..5: robot's left bar, top to bottom;
    6..11: robot's right bar, bottom to top (the order the docs' light drawings use; unverified)."""
    pts = []
    offs = [12.5, 7.5, 2.5, -2.5, -7.5, -12.5]
    for o in offs:
        pts.append((SHELL_X1 + 0.15, BAR_WINDOW_Y, PITCH_Z + o))
    for o in reversed(offs):
        pts.append((SHELL_X0 - 0.15, BAR_WINDOW_Y, PITCH_Z + o))
    return pts


# ------------------------------- glTF writer ------------------------------------------------
class Glb:
    def __init__(self):
        self.bin = bytearray()
        self.j = {"asset": {"version": "2.0", "generator": "make_body.py"}, "scene": 0, "scenes": [{"name": "stackchan", "nodes": [0]}],
                  "nodes": [], "meshes": [], "materials": [], "accessors": [], "bufferViews": [], "buffers": []}
        self.mat_index = {}

    def material(self, name, rgba, emissive=None, alpha=False):
        if name in self.mat_index:
            return self.mat_index[name]
        m = {"name": name, "pbrMetallicRoughness": {"baseColorFactor": [round(c, 4) for c in rgba], "metallicFactor": 0.0, "roughnessFactor": 0.7}}
        if emissive:
            m["emissiveFactor"] = list(emissive)
        if alpha:
            m["alphaMode"] = "BLEND"
        self.j["materials"].append(m)
        self.mat_index[name] = len(self.j["materials"]) - 1
        return self.mat_index[name]

    def _view(self, data, target):
        while len(self.bin) % 4:
            self.bin.append(0)
        off = len(self.bin)
        self.bin += data
        self.j["bufferViews"].append({"buffer": 0, "byteOffset": off, "byteLength": len(data), "target": target})
        return len(self.j["bufferViews"]) - 1

    def _acc(self, view, ctype, count, typ, mn=None, mx=None):
        a = {"bufferView": view, "componentType": ctype, "count": count, "type": typ}
        if mn is not None:
            a["min"], a["max"] = mn, mx
        self.j["accessors"].append(a)
        return len(self.j["accessors"]) - 1

    def primitive(self, positions, normals, indices, mat, uvs=None):
        f32 = lambda vals: [struct.unpack("<f", struct.pack("<f", v))[0] for v in vals]
        pos = [f32(p) for p in positions]
        mn = [min(p[i] for p in pos) for i in range(3)]
        mx = [max(p[i] for p in pos) for i in range(3)]
        pv = self._view(b"".join(struct.pack("<3f", *p) for p in pos), 34962)
        attrs = {"POSITION": self._acc(pv, 5126, len(pos), "VEC3", mn, mx)}
        nv = self._view(b"".join(struct.pack("<3f", *n) for n in normals), 34962)
        attrs["NORMAL"] = self._acc(nv, 5126, len(normals), "VEC3")
        if uvs:
            tv = self._view(b"".join(struct.pack("<2f", *t) for t in uvs), 34962)
            attrs["TEXCOORD_0"] = self._acc(tv, 5126, len(uvs), "VEC2")
        big = len(pos) > 65535
        iv = self._view(b"".join(struct.pack("<I" if big else "<H", i) for i in indices), 34963)
        ia = self._acc(iv, 5125 if big else 5123, len(indices), "SCALAR")
        return {"attributes": attrs, "indices": ia, "material": mat}

    def mesh(self, name, prims):
        self.j["meshes"].append({"name": name, "primitives": prims})
        return len(self.j["meshes"]) - 1

    def node(self, name, translation=None, mesh=None, extras=None):
        n = {"name": name}
        if translation and any(abs(v) > 0 for v in translation):
            n["translation"] = [round(v, 6) for v in translation]
        if mesh is not None:
            n["mesh"] = mesh
        if extras:
            n["extras"] = extras
        self.j["nodes"].append(n)
        return len(self.j["nodes"]) - 1

    def child(self, parent, child):
        self.j["nodes"][parent].setdefault("children", []).append(child)

    def write(self, path):
        while len(self.bin) % 4:
            self.bin.append(0)
        self.j["buffers"] = [{"byteLength": len(self.bin)}]
        js = json.dumps(self.j, separators=(",", ":"), sort_keys=False).encode()
        while len(js) % 4:
            js += b" "
        out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(self.bin))
        out += struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(self.bin), 0x004E4942) + bytes(self.bin)
        Path(path).write_bytes(out)


def smooth_indexed(tris_model, crease_deg=35.0):
    """Indexed vertices with normals: corners share a normal across faces within the crease angle."""
    cos_c = math.cos(math.radians(crease_deg))
    fn = []
    for a, b, c in tris_model:
        u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        l = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
        fn.append((n[0] / l, n[1] / l, n[2] / l) if l > 0 else None)
    key = lambda p: (round(p[0] * 1e7), round(p[1] * 1e7), round(p[2] * 1e7))
    around = {}
    for fi, t in enumerate(tris_model):
        if fn[fi] is None:
            continue
        for p in t:
            around.setdefault(key(p), []).append(fi)
    verts, norms, index, idx = [], [], {}, []
    for fi, t in enumerate(tris_model):
        n0 = fn[fi]
        if n0 is None:
            continue
        for p in t:
            k = key(p)
            sx = sy = sz = 0.0
            for fj in around[k]:
                n1 = fn[fj]
                if n0[0] * n1[0] + n0[1] * n1[1] + n0[2] * n1[2] >= cos_c:
                    sx, sy, sz = sx + n1[0], sy + n1[1], sz + n1[2]
            l = math.sqrt(sx * sx + sy * sy + sz * sz) or 1.0
            n = (round(sx / l, 4), round(sy / l, 4), round(sz / l, 4))
            vk = (k, n)
            if vk not in index:
                index[vk] = len(verts)
                verts.append(p)
                norms.append(n)
            idx.append(index[vk])
    return verts, norms, idx


def local(tris_mm, origin):
    """Base-frame mm triangles -> meters relative to a node origin (model frame)."""
    out = []
    for t in tris_mm:
        q = []
        for p in t:
            m = to_model(p)
            q.append((m[0] - origin[0], m[1] - origin[1], m[2] - origin[2]))
        out.append(tuple(q))
    return out


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def build(out_dir=HERE):
    parts = load_parts()
    prims = primitives()
    g = Glb()
    groups = {"base": (0.0, 0.0, 0.0), "neck": YAW_ORIGIN, "head": PITCH_ORIGIN}
    part_color = {"base_body": "base", "base_cover": "base", "servo_holder": "neck", "servo_cover": "neck", "servo_side_cover": "neck",
                  "servo_arm": "neck", "bearing_fixture": "neck", "shell": "shell", "light_bar_left": "light_bar", "light_bar_right": "light_bar"}
    by_group = {"base": [], "neck": [], "head": []}
    for name, (tris, group) in parts.items():
        by_group[group].append((part_color[name], tris))
    for name, (tris, group, color) in prims.items():
        by_group[group].append((color, tris))
    tri_count = 0

    def group_mesh(group):
        nonlocal tri_count
        merged = {}
        for color, tris in by_group[group]:
            merged.setdefault(color, []).extend(tris)
        plist = []
        for color in sorted(merged):
            v, n, i = smooth_indexed(local(merged[color], groups[group]))
            tri_count += len(i) // 3
            plist.append(g.primitive(v, n, i, g.material(color, COLORS[color], alpha=(color == "light_bar"))))
        return g.mesh(group, plist)

    def marker_mesh(name, tris_mm, color, origin):
        v, n, i = smooth_indexed(local(tris_mm, origin))
        return g.mesh(name, [g.primitive(v, n, i, g.material(color, COLORS[color]))])

    root = g.node("stackchan", extras={"units": "meters", "up": "+Y", "front": "+Z", "left": "+X",
                                         "origin": "yaw axis (turntable center) on the table plane", "params": "stackchan.params.json"})
    base = g.node("base", mesh=group_mesh("base"))
    g.child(root, base)
    mk = markers()
    usb = g.node("usb_c_port", translation=to_model((AXIS_X, -296.58, TABLE_Z + 8.0)),
                 mesh=marker_mesh("usb_c_port", mk["usb_c_port"][0], "port", to_model((AXIS_X, -296.58, TABLE_Z + 8.0))),
                 extras={"what": "USB-C for charging and data on the back of the base"})
    g.child(base, usb)
    for i, (hx, hy) in enumerate([(90.73, -348.57), (122.73, -348.57), (122.73, -300.57), (90.73, -300.57)]):
        f = g.node(f"foot_{i}", translation=to_model((hx, hy, TABLE_Z)),
                   extras={"what": "corner mounting hole on the base underside (the base has no separate feet; the bottom plate rests on the table)"})
        g.child(base, f)
    g.child(base, g.node("col_base", translation=to_model((106.73, -324.565, (TABLE_Z + BASE_TOP_Z) / 2)),
                         extras={"collider": {"shape": "box", "size": [0.048, round((BASE_TOP_Z - TABLE_Z) * MM, 5), 0.056]}}))

    yaw = g.node("yaw_joint", translation=YAW_ORIGIN, mesh=None, extras={"joint": {
        "type": "revolute", "axis": [0.0, -1.0, 0.0], "positive": "turns the head toward the robot's right",
        "limit_deg": list(YAW_LIMIT), "rest_deg": 0.0, "source": LIMIT_SOURCE}})
    g.child(base, yaw)
    neck = g.node("neck", mesh=group_mesh("neck"), extras={"what": "servo holder that turns with yaw: holder, covers, pitch servo"})
    g.child(yaw, neck)
    g.child(yaw, g.node("col_neck", translation=sub(to_model((AXIS_X, AXIS_Y, -4.4)), YAW_ORIGIN),
                        extras={"collider": {"shape": "cylinder", "radius": 0.023, "height": 0.0358}}))

    pitch = g.node("pitch_joint", translation=sub(PITCH_ORIGIN, YAW_ORIGIN), extras={"joint": {
        "type": "revolute", "axis": [-1.0, 0.0, 0.0], "positive": "tilts the face up",
        "limit_deg": list(PITCH_LIMIT), "rest_deg": 0.0, "source": LIMIT_SOURCE,
        "note": "rest pose 0 = face level as drawn; the firmware clamps to 3..87 so the unit never sits exactly at 0; the product page says 5..85"}})
    g.child(yaw, pitch)
    head = g.node("head", mesh=group_mesh("head"), extras={"what": "shell, controller unit, light bars, pitch arms"})
    g.child(pitch, head)

    corners, uv, (sw, sh) = screen_quad()
    sv = [sub(to_model(p), PITCH_ORIGIN) for p in corners]
    center = tuple(sum(c[i] for c in sv) / 4 for i in range(3))
    sv = [sub(p, center) for p in sv]
    smat = g.material("screen", COLORS["screen"], emissive=[0.0, 0.0, 0.0])
    sp = g.primitive(sv, [(0.0, 0.0, 1.0)] * 4, [0, 3, 2, 0, 2, 1], smat, uvs=uv)
    screen = g.node("screen_plane", translation=center, mesh=g.mesh("screen_plane", [sp]),
                    extras={"screen": {"pixels": [320, 240], "size_m": [round(sw * MM, 4), round(sh * MM, 4)],
                                       "uv": "0,0 top-left to 1,1 bottom-right as seen from the front; set the live 320x240 frame as the material texture"}})
    g.child(head, screen)
    for name in ("power_button", "usb_c_otg", "port_a"):
        tris, color = mk[name]
        xs = [p[0] for t in tris for p in t]; ys = [p[1] for t in tris for p in t]; zs = [p[2] for t in tris for p in t]
        c = sub(to_model(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2)), PITCH_ORIGIN)
        origin = tuple(a + b for a, b in zip(PITCH_ORIGIN, c))
        what = {"power_button": "power button on the controller's right side", "usb_c_otg": "USB-C (OTG) on the controller's right side",
                "port_a": "I2C port A on the controller's right side"}[name]
        g.child(head, g.node(name, translation=c, mesh=marker_mesh(name, tris, color, origin), extras={"what": what}))
    for i, p in enumerate(ring_light_centers()):
        c = sub(to_model(p), PITCH_ORIGIN)
        origin = tuple(a + b for a, b in zip(PITCH_ORIGIN, c))
        s = 1.0
        x0, x1 = (p[0] - 0.1, p[0] + 0.3) if i < 6 else (p[0] - 0.3, p[0] + 0.1)
        tris = box(x0, x1, p[1] - 1.6, p[1] + 1.6, p[2] - s, p[2] + s)
        v, n, ix = smooth_indexed(local(tris, origin))
        mat = g.material(f"ring_light_{i}", COLORS["light_off"], emissive=[0.0, 0.0, 0.0])
        side = "left" if i < 6 else "right"
        g.child(head, g.node(f"ring_light_{i}", translation=c, mesh=g.mesh(f"ring_light_{i}", [g.primitive(v, n, ix, mat)]),
                             extras={"light": {"bar": side, "index_in_bar": i % 6, "set": "emissiveFactor of material ring_light_%d" % i}}))
    hc = to_model(((SHELL_X0 + SHELL_X1) / 2, SHELL_Y0 - CORE_DEPTH + 61.5 / 2, (SHELL_Z0 + SHELL_Z1) / 2))
    g.child(head, g.node("col_head", translation=sub(hc, PITCH_ORIGIN),
                         extras={"collider": {"shape": "box", "size": [0.054, 0.054, 0.0615]}}))

    out = Path(out_dir)
    g.write(out / "stackchan.glb")
    params = make_params(tri_count)
    (out / "stackchan.params.json").write_text(json.dumps(params, indent=1) + "\n")
    return out / "stackchan.glb"


def make_params(tri_count):
    m, a = "measured", "assumed"
    head_front = to_model((AXIS_X, SHELL_Y0 - CORE_DEPTH, 0))[2]
    return {
        "units": "meters and degrees",
        "frame": {"up": "+Y", "front": "+Z", "left": "+X", "origin": "yaw axis on the table plane"},
        "source": {"files": "source/ (official structure files, see SOURCE.md)", "sha256": {p.name: sha256(p) for p in sorted(SRC.glob("*.stl"))}},
        "triangles": tri_count,
        "dimensions": {
            "overall_height": {"value": round(to_model((0, 0, SHELL_Z1))[1], 5), "basis": m, "note": "70.5 mm published; files give 70.41"},
            "head_width": {"value": 0.054, "basis": m, "note": "shell file and published drawing"},
            "head_height": {"value": 0.054, "basis": m},
            "head_depth": {"value": 0.0615, "basis": m, "note": "published drawing; shell file 46.7 mm plus the controller unit"},
            "shell_depth": {"value": 0.0467, "basis": m},
            "controller_depth": {"value": round(CORE_DEPTH * MM, 5), "basis": a, "note": "61.5 published depth minus the 46.7 shell; the controller is not in the files"},
            "base_width": {"value": 0.048, "basis": m}, "base_depth": {"value": 0.056, "basis": m},
            "base_height": {"value": round((BASE_TOP_Z - TABLE_Z) * MM, 5), "basis": m, "note": "base 11.1 mm plus 1.51 mm bottom plate"},
            "base_mount_holes": {"value": [0.032, 0.048], "basis": m, "note": "corner hole spacing across and front to back"},
            "head_front_from_axis": {"value": round(head_front, 5), "basis": a, "note": "set so the screen is 1 mm ahead of the base front as drawn"},
            "base_center_from_axis": {"value": [0.0, 0.0, round(-(-324.565 - AXIS_Y) * MM, 5)], "basis": m, "note": "the turntable sits 4 mm behind the base footprint center"},
            "screen_active_area": {"value": [0.0415, 0.0316], "basis": m, "note": "drawing front view; 2.0 inch 320x240"},
            "light_bar": {"value": [0.005, 0.031, 0.0053], "basis": m, "note": "light guide file; window in the shell side is 5.6 x 40.5 mm"},
            "ring_light_spacing": {"value": 0.005, "basis": a},
        },
        "joints": {
            "yaw_joint": {"axis": [0, -1, 0], "origin": [round(v, 6) for v in YAW_ORIGIN], "limit_deg": list(YAW_LIMIT), "basis": m, "source": LIMIT_SOURCE,
                          "direction_basis": a, "direction_note": "positive turns toward the robot's right, as the virtual unit view draws it"},
            "pitch_joint": {"axis": [-1, 0, 0], "origin": [round(v, 6) for v in PITCH_ORIGIN], "limit_deg": list(PITCH_LIMIT), "basis": m, "source": LIMIT_SOURCE,
                            "published_limit_deg": [5, 85], "published_basis": "product page text, recommended range",
                            "direction_basis": a, "direction_note": "positive tilts the face up; 0 is the level pose in the drawing"},
            "pitch_axis_height": {"value": round(PITCH_ORIGIN[1], 5), "basis": m, "note": "servo shaft stub and arm hole center; equals the head's vertical center"},
        },
        "mass_kg": {"total": {"value": 0.25, "basis": a, "note": "estimate: controller about 0.08, battery 0.012, two servos about 0.04, plastics about 0.1; weigh the unit to replace"},
                    "head": {"value": 0.14, "basis": a}, "neck": {"value": 0.06, "basis": a}, "base": {"value": 0.05, "basis": a}},
        "colors": {"value": {k: list(v) for k, v in COLORS.items()}, "basis": a, "note": "from product photos"},
    }


if __name__ == "__main__":
    p = build()
    print(f"wrote {p} ({p.stat().st_size} bytes)")
