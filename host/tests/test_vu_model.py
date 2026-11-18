"""Virtual unit 3D model: the rigged glb's node names and hierarchy, joint limits, byte-identical rebuild, source hashes."""

import hashlib
import importlib.util
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "scripts" / "virtual-unit" / "model"
GLB = MODEL / "stackchan.glb"


def read_glb(path):
    """Minimal glTF binary reader: the JSON chunk and the binary chunk."""
    data = Path(path).read_bytes()
    magic, version, length = struct.unpack_from("<III", data, 0)
    assert magic == 0x46546C67 and version == 2 and length == len(data)
    jlen, jtype = struct.unpack_from("<II", data, 12)
    assert jtype == 0x4E4F534A
    j = json.loads(data[20:20 + jlen])
    blen, btype = struct.unpack_from("<II", data, 20 + jlen)
    assert btype == 0x004E4942 and blen == j["buffers"][0]["byteLength"]
    return j, data[28 + jlen:28 + jlen + blen]


def nodes_by_name(j):
    return {n["name"]: (i, n) for i, n in enumerate(j["nodes"])}


def descendants(j, i):
    out = set()
    for c in j["nodes"][i].get("children", []):
        out.add(j["nodes"][c]["name"])
        out |= descendants(j, c)
    return out


def test_node_names_and_hierarchy():
    j, _ = read_glb(GLB)
    by = nodes_by_name(j)
    required = ["base", "yaw_joint", "pitch_joint", "head", "screen_plane", "usb_c_port", "power_button"]
    required += [f"ring_light_{i}" for i in range(12)] + [f"foot_{i}" for i in range(4)]
    for name in required:
        assert name in by, f"node {name} missing"
    assert len([n for n in by if n.startswith("col_")]) >= 3
    yaw, pitch, head = by["yaw_joint"][0], by["pitch_joint"][0], by["head"][0]
    assert by["pitch_joint"][0] in j["nodes"][yaw]["children"], "pitch_joint must be a child of yaw_joint"
    assert head in j["nodes"][pitch]["children"], "head must be a child of pitch_joint"
    assert {"pitch_joint", "head", "screen_plane"} <= descendants(j, yaw)
    assert "screen_plane" in descendants(j, head)
    assert {f"ring_light_{i}" for i in range(12)} <= descendants(j, head), "the lights move with the head"
    assert "yaw_joint" in descendants(j, by["base"][0])
    for n in j["nodes"]:
        if n["name"].startswith("col_"):
            assert "mesh" not in n and "collider" in n.get("extras", {}), f"{n['name']} must be an unrendered collider"


def test_joint_limits_match_the_firmware_limiter():
    j, _ = read_glb(GLB)
    by = nodes_by_name(j)
    yaw = by["yaw_joint"][1]["extras"]["joint"]
    pitch = by["pitch_joint"][1]["extras"]["joint"]
    # firmware/main/hal/hal_servo.cpp: yaw angleLimit (-1280, 1280), pitch (30, 870), tenths of a degree
    assert yaw["limit_deg"] == [-128.0, 128.0]
    assert pitch["limit_deg"] == [3.0, 87.0]
    assert sorted(abs(v) for v in yaw["axis"]) == [0.0, 0.0, 1.0] and yaw["axis"][1] != 0
    assert sorted(abs(v) for v in pitch["axis"]) == [0.0, 0.0, 1.0] and pitch["axis"][0] != 0
    assert "hal_servo.cpp" in yaw["source"] and "hal_servo.cpp" in pitch["source"]
    params = json.loads((MODEL / "stackchan.params.json").read_text())
    assert params["joints"]["pitch_joint"]["published_limit_deg"] == [5, 85]


def test_screen_plane_is_a_uv_quad():
    j, buf = read_glb(GLB)
    n = nodes_by_name(j)["screen_plane"][1]
    prim = j["meshes"][n["mesh"]]["primitives"][0]
    a = j["accessors"][prim["attributes"]["TEXCOORD_0"]]
    v = j["bufferViews"][a["bufferView"]]
    uv = struct.unpack_from(f"<{a['count'] * 2}f", buf, v["byteOffset"])
    assert a["count"] == 4 and set(uv) == {0.0, 1.0}
    assert n["extras"]["screen"]["pixels"] == [320, 240]


def test_size_and_every_value_marked():
    assert GLB.stat().st_size < 6 * 1024 * 1024
    params = json.loads((MODEL / "stackchan.params.json").read_text())
    for group in ("dimensions", "mass_kg"):
        for key, val in params[group].items():
            assert val["basis"] in ("measured", "assumed"), f"{group}.{key} is not marked measured or assumed"
    height = params["dimensions"]["overall_height"]["value"]
    assert abs(height - 0.0705) < 0.001, "overall height must stay near the published 70.5 mm"


def test_regenerates_byte_identical(tmp_path):
    spec = importlib.util.spec_from_file_location("make_body", MODEL / "make_body.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(MODEL))
    try:
        spec.loader.exec_module(mod)
        out = mod.build(tmp_path)
    finally:
        sys.path.remove(str(MODEL))
    assert out.read_bytes() == GLB.read_bytes(), "stackchan.glb is stale: run python3 scripts/virtual-unit/model/make_body.py"
    assert (tmp_path / "stackchan.params.json").read_text() == (MODEL / "stackchan.params.json").read_text()


def test_source_hashes_match_source_md():
    text = (MODEL / "SOURCE.md").read_text()
    listed = dict(re.findall(r"`([\w.-]+\.stl|LICENSE)`\s*\|\s*`([0-9a-f]{64})`", text))
    files = sorted((MODEL / "source").glob("*.stl")) + [MODEL / "source" / "LICENSE"]
    assert len(files) == 11
    for f in files:
        assert f.name in listed, f"{f.name} has no hash in SOURCE.md"
        assert hashlib.sha256(f.read_bytes()).hexdigest() == listed[f.name], f"{f.name} differs from the hash in SOURCE.md"


def test_names_other_tracks_load_by_stay():
    j, _ = read_glb(GLB)
    by = nodes_by_name(j)
    for name in ("stackchan", "neck", "usb_c_otg", "port_a", "col_base", "col_neck", "col_head"):
        assert name in by, f"node {name} missing"
    mats = [m["name"] for m in j["materials"]]
    for name in ["base", "neck", "shell", "core", "glass", "screen", "light_bar"] + [f"ring_light_{i}" for i in range(12)]:
        assert mats.count(name) == 1, f"material {name} missing or repeated"
    params = json.loads((MODEL / "stackchan.params.json").read_text())
    assert {"units", "frame", "source", "triangles", "dimensions", "joints", "mass_kg", "colors"} <= set(params)
    for key in ("overall_height", "head_width", "head_depth", "shell_depth", "controller_depth", "base_width", "base_depth", "base_height",
                "base_mount_holes", "head_front_from_axis", "base_center_from_axis", "screen_active_area", "light_bar", "ring_light_spacing"):
        assert key in params["dimensions"], f"dimensions.{key} missing"


def test_glb_is_self_contained_and_has_normals():
    j, buf = read_glb(GLB)
    assert len(j["buffers"]) == 1 and "uri" not in j["buffers"][0], "the glb must embed its one buffer"
    assert not j.get("images") and not j.get("extensionsRequired") and not j.get("extensionsUsed")
    for mesh in j["meshes"]:
        for prim in mesh["primitives"]:
            pos, nrm, idx = (j["accessors"][prim["attributes"]["POSITION"]], j["accessors"][prim["attributes"]["NORMAL"]], j["accessors"][prim["indices"]])
            assert pos["count"] == nrm["count"] and idx["count"] % 3 == 0 and idx["componentType"] in (5123, 5125)
            view = j["bufferViews"][idx["bufferView"]]
            fmt = "H" if idx["componentType"] == 5123 else "I"
            assert max(struct.unpack_from(f"<{idx['count']}{fmt}", buf, view["byteOffset"])) < pos["count"]


def test_published_size_and_mass():
    d = json.loads((MODEL / "stackchan.params.json").read_text())
    assert abs(d["dimensions"]["overall_height"]["value"] - 0.0705) < 0.0002      # product page: 54.0 x 70.5 x 61.5 mm
    assert abs(d["dimensions"]["overall_depth"]["value"] - 0.0615) < 0.0002
    assert d["mass_kg"]["total"] == {"value": 0.1872, "basis": "measured", "note": "product page: 187.2 g"}
    parts = sum(d["mass_kg"][k]["value"] for k in ("head", "neck", "base"))
    assert abs(parts - d["mass_kg"]["total"]["value"]) < 1e-9
    lo, hi = d["joints"]["pitch_joint"]["geometry_free_range_deg"]
    assert lo <= d["joints"]["pitch_joint"]["limit_deg"][0] and d["joints"]["pitch_joint"]["limit_deg"][1] <= hi, "the firmware range must fit the geometry"


def test_lights_sit_on_the_two_top_corner_bars():
    j, _ = read_glb(GLB)
    by = nodes_by_name(j)
    t = [by[f"ring_light_{i}"][1]["translation"] for i in range(12)]       # relative to the pitch axis
    assert all(p[0] > 0.024 for p in t[:6]) and all(p[0] < -0.024 for p in t[6:]), "0..5 on the robot's left bar, 6..11 on the right"
    assert all(0.024 < p[1] < 0.027 for p in t), "the bars sit in the top corners of the shell, not on its sides"
    for bar in (t[:6], t[6:]):
        steps = [abs(bar[i + 1][2] - bar[i][2]) for i in range(5)]
        assert all(abs(s - 0.005) < 1e-6 for s in steps), "5 mm apart along the bar"
    assert t[0][2] > t[5][2] and t[6][2] < t[11][2], "left bar front to back, right bar back to front"
    assert [by[f"ring_light_{i}"][1]["extras"]["light"]["bar"] for i in (0, 5, 6, 11)] == ["left", "left", "right", "right"]


def test_rest_pose_parts_do_not_overlap_in_height():
    j, _ = read_glb(GLB)
    by = nodes_by_name(j)

    def y_range(node, origin_y):
        prims = j["meshes"][by[node][1]["mesh"]]["primitives"]
        acc = [j["accessors"][p["attributes"]["POSITION"]] for p in prims]
        return origin_y + min(a["min"][1] for a in acc), origin_y + max(a["max"][1] for a in acc)
    yaw_y = by["yaw_joint"][1]["translation"][1]
    pitch_y = yaw_y + by["pitch_joint"][1]["translation"][1]
    base, neck, head = y_range("base", 0.0), y_range("neck", yaw_y), y_range("head", pitch_y)
    assert abs(base[0]) < 1e-6, "the bottom plate rests on the table"
    assert 0.0 < neck[0] - base[1] < 0.001, "the servo holder sits just above the turntable ring"
    assert head[0] - base[1] > 0.004 and abs(head[1] - 0.0705) < 0.0002
    assert neck[1] < head[1] - 0.015, "the servo cover is screwed onto the holder, well below the head top"
