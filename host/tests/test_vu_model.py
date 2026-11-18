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
