#!/usr/bin/env python3
"""Render preview PNGs (and a GIF when ffmpeg is installed) of stackchan.glb through its node hierarchy.

Every frame is drawn from the glb itself: the joints are turned by rotating the yaw_joint and pitch_joint
nodes about the axes in their extras, so the previews show what the rig does.
Run: python3 scripts/virtual-unit/model/render_previews.py [out_dir]
"""
from __future__ import annotations

import json
import math
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from softrender import Canvas, look_basis  # noqa: E402

REPO = HERE.parents[2]
OUT = REPO / "docs" / "dev" / "model-previews"


def read_glb(path):
    data = Path(path).read_bytes()
    magic, version, length = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67 or version != 2:
        raise ValueError(f"{path} is not a glTF 2.0 binary file; rebuild it with make_body.py")
    jlen, _ = struct.unpack_from("<II", data, 12)
    j = json.loads(data[20:20 + jlen])
    blen, _ = struct.unpack_from("<II", data, 20 + jlen)
    return j, data[28 + jlen:28 + jlen + blen]


def accessor(j, buf, i):
    a = j["accessors"][i]
    v = j["bufferViews"][a["bufferView"]]
    n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}[a["type"]]
    fmt = {5126: "f", 5123: "H", 5125: "I"}[a["componentType"]]
    vals = struct.unpack_from(f"<{a['count'] * n}{fmt}", buf, v["byteOffset"])
    return [vals[k:k + n] for k in range(0, len(vals), n)] if n > 1 else list(vals)


def mat_mul(a, b):
    return [[sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]


def trs(t=(0, 0, 0), axis=None, deg=0.0):
    m = [[1.0, 0, 0, t[0]], [0, 1.0, 0, t[1]], [0, 0, 1.0, t[2]], [0, 0, 0, 1.0]]
    if axis and deg:
        x, y, z = axis
        c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        C = 1 - c
        r = [[c + x * x * C, x * y * C - z * s, x * z * C + y * s], [y * x * C + z * s, c + y * y * C, y * z * C - x * s], [z * x * C - y * s, z * y * C + x * s, c + z * z * C]]
        for i in range(3):
            for k in range(3):
                m[i][k] = r[i][k]
    return m


class Scene:
    def __init__(self, glb):
        self.j, self.buf = read_glb(glb)
        self.cache = {}

    def mesh_items(self, mi):
        if mi not in self.cache:
            out = []
            for p in self.j["meshes"][mi]["primitives"]:
                pos = accessor(self.j, self.buf, p["attributes"]["POSITION"])
                idx = accessor(self.j, self.buf, p["indices"])
                col = self.j["materials"][p["material"]]["pbrMetallicRoughness"]["baseColorFactor"]
                em = self.j["materials"][p["material"]].get("emissiveFactor")
                name = self.j["materials"][p["material"]]["name"]
                out.append((pos, idx, col, em, name))
            self.cache[mi] = out
        return self.cache[mi]

    def items(self, yaw=0.0, pitch=0.0, lights=None, screen=None):
        """World-space triangle lists per material with the joints turned to (yaw, pitch) degrees."""
        res = []

        def walk(ni, parent):
            n = self.j["nodes"][ni]
            name = n.get("name", "")
            ang = yaw if name == "yaw_joint" else pitch if name == "pitch_joint" else 0.0
            axis = n.get("extras", {}).get("joint", {}).get("axis")
            m = mat_mul(parent, trs(n.get("translation", (0, 0, 0)), axis, ang))
            if "mesh" in n:
                for pos, idx, col, em, mname in self.mesh_items(n["mesh"]):
                    w = [(m[0][0] * x + m[0][1] * y + m[0][2] * z + m[0][3], m[1][0] * x + m[1][1] * y + m[1][2] * z + m[1][3],
                          m[2][0] * x + m[2][1] * y + m[2][2] * z + m[2][3]) for x, y, z in pos]
                    tris = [(w[idx[k]], w[idx[k + 1]], w[idx[k + 2]]) for k in range(0, len(idx), 3)]
                    rgb = tuple(int(255 * min(1.0, c)) for c in col[:3])
                    if lights and mname.startswith("ring_light_"):
                        rgb = lights
                    if screen and mname == "screen":
                        rgb = screen
                    res.append((tris, rgb))
            for c in n.get("children", []):
                walk(c, m)

        walk(self.j["scenes"][0]["nodes"][0], trs())
        return res


CENTER = (0.0, 0.037, 0.0)
VIEWS = {
    "front": (0, 0), "rear": (180, 0), "left": (90, 0), "right": (-90, 0), "top": (0, 89.9),
    "three-quarter": (35, 22), "rear-three-quarter": (215, 22),
}


def render(scene, view, size=420, yaw=0.0, pitch=0.0, scale=None, label=None):
    az, el = VIEWS[view] if isinstance(view, str) else view
    cv = Canvas(size, size)
    cv.draw(scene.items(yaw, pitch, lights=(90, 200, 230), screen=(25, 40, 60)), look_basis(az, el), CENTER, scale or size / 0.105)
    if label:
        cv.label(label, 6, 6)
    return cv


def paste(dst, src, ox, oy):
    for y in range(src.h):
        dst.color[oy + y][ox * 3:(ox + src.w) * 3] = src.color[y]


def main(out=OUT):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    scene = Scene(HERE / "stackchan.glb")
    for name in VIEWS:
        render(scene, name, label=name).save(out / f"{name}.png")
    # joint demonstration: yaw min / center / max, pitch min / center / max, each drawn from the rig
    meta = {n["name"]: n.get("extras", {}).get("joint") for n in scene.j["nodes"] if n.get("name") in ("yaw_joint", "pitch_joint")}
    ylo, yhi = meta["yaw_joint"]["limit_deg"]
    plo, phi = meta["pitch_joint"]["limit_deg"]
    frames = [(("three-quarter", ylo, 0.0), f"YAW {ylo:g}"), (("three-quarter", 0.0, 0.0), "YAW 0"), (("three-quarter", yhi, 0.0), f"YAW {yhi:g}"),
              (("right", 0.0, plo), f"PITCH {plo:g}"), (("right", 0.0, (plo + phi) / 2), f"PITCH {(plo + phi) / 2:g}"), (("right", 0.0, phi), f"PITCH {phi:g}")]
    s = 300
    sheet = Canvas(s * 3, s * 2)
    for k, ((v, y, p), lab) in enumerate(frames):
        if v == "three-quarter":
            v = (25, 55)  # high three-quarter so the turn reads
        paste(sheet, render(scene, v, s, y, p, label=lab), (k % 3) * s, (k // 3) * s)
    sheet.save(out / "joints-contact-sheet.png")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        with tempfile.TemporaryDirectory() as td:
            seq = []
            for t in range(24):
                seq.append(((25, 55), ylo + (yhi - ylo) * (0.5 - 0.5 * math.cos(math.pi * t / 23)), 0.0))
            for t in range(16):
                seq.append(((-60, 15), 0.0, plo + (phi - plo) * (0.5 - 0.5 * math.cos(math.pi * t / 15))))
            for t in range(10):
                seq.append(((-60, 15), 0.0, phi - (phi - plo) * t / 9))
            for i, (v, y, p) in enumerate(seq):
                render(scene, v, 240, y, p, label=f"Y {y:4.0f} P {p:3.0f}").save(Path(td) / f"f{i:03d}.png")
            subprocess.run([ffmpeg, "-loglevel", "error", "-y", "-framerate", "10", "-i", str(Path(td) / "f%03d.png"),
                            "-vf", "split[a][b];[a]palettegen=max_colors=64[p];[b][p]paletteuse=dither=none", str(out / "joints.gif")], check=True)
    print(f"previews in {out}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else OUT)
