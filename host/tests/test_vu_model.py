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


# ---- the 3D view loads the model ---------------------------------------------------------------------

VU = ROOT / "scripts" / "virtual-unit"


def test_view_script_uses_the_model_nodes_and_no_stand_in_table():
    js = (VU / "view3d.js").read_text()
    j, _ = read_glb(GLB)
    by = nodes_by_name(j)
    assert "DIMS" not in js, "the stand-in size table is gone; sizes come from the model"
    assert "/model/stackchan.glb" in js
    for name in re.findall(r"\bN\.([a-z_0-9]+)", js) + re.findall(r"'((?:ring_light|usb_c|power|screen|yaw|pitch)[a-z_0-9]*)'", js):
        assert name in by or name in ("ring_light_", "yaw", "pitch"), f"view3d.js uses node {name}, which the model does not have"
    assert "geometry_free_deg" in by["pitch_joint"][1]["extras"]["joint"], "the view holds the head inside this range"
    assert "examples/js" not in js and "GLTFLoader" not in js, "the page loads no second script from the network"


def test_view_serves_the_model_bytes():
    import subprocess
    import time
    import urllib.request

    import pytest
    if not ((ROOT / ".runs" / "vu-screens" / "render").exists() or (ROOT / ".runs" / "vu-build" / "render").exists()):
        pytest.skip("needs a renderer: bash scripts/virtual-unit/build-screens.sh")
    proc = subprocess.Popen([sys.executable, str(VU / "view.py"), "0"], stdout=subprocess.PIPE, text=True)
    try:
        base = proc.stdout.readline().split()[-1]
        time.sleep(0.6)
        res = urllib.request.urlopen(base + "model/stackchan.glb" if base.endswith("/") else base + "/model/stackchan.glb")
        assert res.headers["Content-Type"] == "model/gltf-binary" and res.read() == GLB.read_bytes()
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_inside_parts_ride_on_the_right_link_and_are_marked_assumed():
    j, _ = read_glb(GLB)
    by = nodes_by_name(j)
    yaw_kids, head_kids = descendants(j, by["yaw_joint"][0]), descendants(j, by["head"][0])
    for name in ("servo_yaw", "servo_pitch", "battery", "cable"):
        assert name in yaw_kids and name not in head_kids, f"{name} turns with yaw and does not tilt"
        assert by[name][1]["extras"]["basis"] == "assumed" and "mesh" in by[name][1]
    assert "board" in head_kids and by["board"][1]["extras"]["basis"] == "assumed"
    d = json.loads((MODEL / "stackchan.params.json").read_text())["dimensions"]
    assert d["servo_size"] == {"value": [0.0232, 0.0121, 0.02525], "basis": "measured", "note": "servo data sheet: 23.2 x 12.1 x 25.25 mm, both servos"}
    assert d["battery_capacity_mah"]["value"] == 550 and d["battery_capacity_mah"]["basis"] == "measured"
    for key in ("battery_size", "servo_positions", "boards", "cable"):
        assert d[key]["basis"] == "assumed", f"{key} has no published figure and must say so"
    # the pan servo's shaft is on the turn axis and the tilt servo's on the nod axis
    pitch_y = by["pitch_joint"][1]["translation"][1]
    acc = j["accessors"][j["meshes"][by["servo_pitch"][1]["mesh"]]["primitives"][0]["attributes"]["POSITION"]]
    t = by["servo_pitch"][1]["translation"]
    assert t[1] + acc["min"][1] < pitch_y < t[1] + acc["max"][1] and acc["max"][0] + t[0] > 0.019


def test_view_has_the_inside_motion_and_demo_controls():
    html, js = (VU / "view.html").read_text(), (VU / "view3d.js").read_text()
    for ident in ('id="inside"', 'id="motion"', 'id="vdemo"', 'id="axes"', 'id="vreset"'):
        assert ident in html, f"{ident} missing from the view"
    for hook in ("insideOn", "motionOn", "demoDone"):
        assert hook in html and hook in js
    assert "demoPose" in js and "applyLook" in js


# ---- the camera controls of the 3D view, run in node with stand-in page objects --------------------------

ORBIT_HARNESS = r"""
const fs = require('fs');
const any = () => new Proxy(function () {}, {get: (t, k) => (k === Symbol.toPrimitive ? () => 0 : any()), apply: () => any(), construct: () => any(), set: () => true});
const listeners = {};
const el = () => ({style: {}, appendChild() {}, set textContent(v) {}});
const cv = {style: {}, clientWidth: 600, clientHeight: 500, parentElement: el(), addEventListener: (n, f) => { listeners[n] = f; },
            setPointerCapture() { throw new Error('no active pointer'); }, getBoundingClientRect: () => ({left: 0, top: 0, width: 600, height: 500})};
global.window = {devicePixelRatio: 1}; global.addEventListener = () => {}; global.document = {createElement: el};
global.fetch = () => new Promise(() => {}); global.setInterval = () => 0; global.Image = function () {};
const initRobot = new Function(fs.readFileSync(process.argv[2], 'utf8') + '; return initRobot;')();
const hooks = {physicsOn: () => false, on: () => true, axesVisible: () => true};
const rob = initRobot(any(), cv, hooks);
const ev = (o) => Object.assign({pointerId: 1, button: 0, clientX: 0, clientY: 0, preventDefault() {}}, o);
const snap = () => ({az: rob.view.az, el: rob.view.el, dist: rob.view.dist});
const out = {start: snap()};
listeners.pointerdown(ev({clientX: 100, clientY: 100})); listeners.pointermove(ev({clientX: 200, clientY: 130})); listeners.pointerup(ev({clientX: 200, clientY: 130}));
out.afterDrag = snap();
listeners.pointerdown(ev({clientX: 100, clientY: 100, shiftKey: true})); listeners.pointermove(ev({clientX: 180, clientY: 100, shiftKey: true})); listeners.pointerup(ev({clientX: 180, clientY: 100}));
out.afterShiftDrag = snap();
listeners.pointerdown(ev({clientX: 100, clientY: 100, button: 2})); listeners.pointermove(ev({clientX: 180, clientY: 100, button: 2})); listeners.pointerup(ev({clientX: 180, clientY: 100}));
out.afterRightDrag = snap();
listeners.wheel(ev({deltaY: -300})); out.afterWheel = snap();
listeners.wheel(ev({deltaY: -30, ctrlKey: true})); out.afterPinch = snap();
hooks.presets.left(); hooks.presets.up(); hooks.presets.zoomOut(); out.afterButtons = snap();
listeners.dblclick(ev({})); out.afterDoubleClick = snap();
out.hasContextMenuGuard = typeof listeners.contextmenu === 'function';
console.log(JSON.stringify(out));
"""


def test_orbit_drag_turns_the_camera_and_the_other_gestures_work(tmp_path):
    import shutil
    import subprocess

    import pytest
    node = shutil.which("node")
    if not node:
        pytest.skip("needs node to run the view script")
    harness = tmp_path / "orbit.js"
    harness.write_text(ORBIT_HARNESS)
    res = subprocess.run([node, str(harness), str(VU / "view3d.js")], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, res.stderr[-800:]
    o = json.loads(res.stdout.strip().splitlines()[-1])
    assert abs(o["afterDrag"]["az"] - (o["start"]["az"] - 0.8)) < 1e-6, "a drag of 100 pixels must turn the camera"
    assert abs(o["afterDrag"]["el"] - (o["start"]["el"] + 0.18)) < 1e-6, "a drag of 30 pixels down must tilt the camera"
    assert o["afterShiftDrag"] == o["afterDrag"] and o["afterRightDrag"] == o["afterDrag"], "shift-drag and right-drag slide the view, they do not turn it"
    assert o["afterWheel"]["dist"] < o["afterDrag"]["dist"] and o["afterPinch"]["dist"] < o["afterWheel"]["dist"], "wheel and pinch zoom"
    assert o["afterButtons"]["az"] != o["afterPinch"]["az"] and o["afterButtons"]["el"] > o["afterPinch"]["el"] and o["afterButtons"]["dist"] > o["afterPinch"]["dist"]
    assert o["afterDoubleClick"] == o["start"], "a double click puts the view back"
    assert o["hasContextMenuGuard"]


def test_reset_restarts_a_running_unit_and_head_touch_is_logged():
    sys.path.insert(0, str(VU))
    try:
        import hw
    finally:
        sys.path.remove(str(VU))
    h = hw.Hardware() if hasattr(hw, "Hardware") else None
    if h is None:
        cls = [v for v in vars(hw).values() if isinstance(v, type) and hasattr(v, "press_power")][0]
        h = cls()
    if not h.on:
        assert h.set("power", 1, 0) is None
    h.boot_started = None
    assert h.set("reset", 1, 5000) is None and h.on and h.boot_started == 5000 and "reset pressed" in h.events[-1]
    h.set("power", 1, 6000)
    assert not h.on and "off" in h.set("reset", 1, 7000)
    j, _ = read_glb(GLB)
    by = nodes_by_name(j)
    head = descendants(j, by["head"][0])
    assert "reset_button" in head and by["reset_button"][1]["translation"][1] < -0.026, "the reset button is under the controller"
    pads = [by[f"touch_back_{i}"][1] for i in range(3)]
    assert all(f"touch_back_{i}" in head for i in range(3)) and [p["extras"]["touch"]["zone"] for p in pads] == [0, 1, 2]
    assert pads[0]["translation"][2] > pads[1]["translation"][2] > pads[2]["translation"][2], "zone 0 is at the front"
    assert all(0.0255 < p["translation"][1] < 0.0268 for p in pads), "the pads sit just under the head top: the real unit shows nothing outside"
    assert "pevent head" in (VU / "vunit.py").read_text() and '"head"' in (VU / "view.py").read_text() and "pevent head" in (VU / "scenarios.py").read_text()


def test_details_seen_on_the_real_unit_are_named_nodes():
    j, _ = read_glb(GLB)
    by = nodes_by_name(j)
    head, yaw, base = descendants(j, by["head"][0]), descendants(j, by["yaw_joint"][0]), descendants(j, by["base"][0])
    for name in ("sd_slot", "screen_bottom_led", "reset_button", "button_left_top", "sticker_side_left", "sticker_side_right", "sticker_top"):
        assert name in head, f"{name} rides on the head"
    assert "back_charge_led" in yaw and "back_charge_led" not in head, "the charge light is in the holder, which does not tilt"
    assert "sticker_bottom" in base and "sticker_bottom" not in yaw
    assert "button_left_top" in descendants(j, by["power_button"][0]) and "mesh" not in by["button_left_top"][1]
    assert by["power_button"][1]["translation"][0] < -0.0269 and by["power_button"][1]["translation"][1] > 0.01, "top of the left side as you face the screen"
    sd, rs, led = (by[n][1]["translation"] for n in ("sd_slot", "reset_button", "screen_bottom_led"))
    assert sd[0] < led[0] < rs[0] and abs(sd[1] - rs[1]) < 0.0001, "slot, then the small light hole, then the button, left to right as you face the robot"
    assert by["back_charge_led"][1]["translation"][2] < -0.02, "on the back"
    mats = {m["name"] for m in j["materials"]}
    assert {"led_charge", "led_bottom", "sticker", "sticker_ink", "touch_pad"} <= mats
    for name in ("sticker_side_left", "sticker_side_right", "sticker_top", "sticker_bottom"):
        prims = j["meshes"][by[name][1]["mesh"]]["primitives"]
        assert {"sticker", "sticker_ink"} <= {j["materials"][p["material"]]["name"] for p in prims}, "paper and print, drawn as geometry"
    js = (VU / "view3d.js").read_text()
    assert "back_charge_led" in js and "st.hw.charging" in js and "screen_bottom_led" in js


def test_second_pass_openings_are_real_and_every_screw_is_a_node():
    j, _ = read_glb(GLB)
    by = nodes_by_name(j)
    assert GLB.stat().st_size < 8_000_000, "the model stays small enough to load at once"
    head, yaw, base = descendants(j, by["head"][0]), descendants(j, by["yaw_joint"][0]), descendants(j, by["base"][0])
    screws = sorted(n["name"] for n in j["nodes"] if n["name"].startswith("screw_"))
    assert screws == ["screw_back_0", "screw_back_1", "screw_base_0", "screw_base_1", "screw_base_2", "screw_base_3", "screw_head_0", "screw_head_1", "screw_servo"]
    assert {"screw_back_0", "screw_back_1", "screw_servo"} <= yaw - head and {"screw_head_0", "screw_head_1"} <= head
    assert {f"screw_base_{i}" for i in range(4)} <= base - yaw
    for name in ("screw_back_0", "screw_back_1"):
        assert by[name][1]["translation"][2] < -0.02, "on the holder back"

    def extent(name):   # size of a node's mesh from its accessor bounds, meters
        lo, hi = [9.0] * 3, [-9.0] * 3
        for p in j["meshes"][by[name][1]["mesh"]]["primitives"]:
            a = j["accessors"][p["attributes"]["POSITION"]]
            lo, hi = [min(x, y) for x, y in zip(lo, a["min"])], [max(x, y) for x, y in zip(hi, a["max"])]
        return [h - l for l, h in zip(lo, hi)]
    # each opening is a pocket with walls and a floor, not a flat patch: its mesh is as deep as the opening says
    for name, axis in (("usb_c_port", 2), ("usb_c_otg", 0), ("port_a", 0), ("sd_slot", 1)):
        depth = by[name][1]["extras"]["opening"]["depth"]
        assert depth >= 0.003 and extent(name)[axis] >= depth - 1e-5, f"{name} is a recessed opening"
    assert "print is a stand-in" in by["sticker_top"][1]["extras"]["what"]
    for name in ("board_parts", "battery_lead", "servo_wires"):
        assert by[name][1]["extras"]["basis"] == "assumed" and "mesh" in by[name][1]
    assert "board_parts" in head and {"battery_lead", "servo_wires"} <= yaw - head
    mats = {m["name"]: m for m in j["materials"]}
    button = [mats_name for mats_name in (j["materials"][p["material"]]["name"] for p in j["meshes"][by["power_button"][1]["mesh"]]["primitives"])]
    assert button == ["button"] and min(mats["button"]["pbrMetallicRoughness"]["baseColorFactor"][:3]) > 0.7, "the side button is a white key"
    assert [j["materials"][p["material"]]["name"] for p in j["meshes"][by["reset_button"][1]["mesh"]]["primitives"]] == ["button"]
    assert "0x58d68d" not in (VU / "view3d.js").read_text(), "the view does not tint the side button"


def test_rear_internals_seen_in_the_owners_photo_are_named_nodes():
    j, _ = read_glb(GLB)
    by = nodes_by_name(j)
    head, yaw, base = descendants(j, by["head"][0]), descendants(j, by["yaw_joint"][0]), descendants(j, by["base"][0])
    for name in ["ring_board", "green_connector", "flex_cable_ring", "board_7p", "light_bar_left", "light_bar_right"] + [f"ring_led_{i}" for i in range(12)]:
        assert name in head and "mesh" in by[name][1], f"{name} is drawn and rides on the head"
    assert {"black_bracket", "coil"} <= yaw - head and "base_board" in base - yaw
    assert by["base_board"][1]["extras"]["basis"] == "assumed" and "no picture of the open base" in by["base_board"][1]["extras"]["note"]
    mat = lambda name: [j["materials"][p["material"]]["name"] for p in j["meshes"][by[name][1]["mesh"]]["primitives"]]
    assert "silk" in mat("board_7p") and mat("green_connector") == ["conn_green"] and "flex_ink" in mat("flex_cable_ring")
    assert mat("light_bar_left") == ["light_bar"] and by["light_bar_left"][1]["extras"]["lights"] == [0, 1, 2, 3, 4, 5] and by["light_bar_right"][1]["extras"]["lights"] == [11, 10, 9, 8, 7, 6]
    pcb = next(m for m in j["materials"] if m["name"] == "pcb")["pbrMetallicRoughness"]["baseColorFactor"]
    assert max(pcb[:3]) < 0.05, "the boards are black, as in the owner's photo"
    for i in range(12):   # each small light sits on the ring board, inboard of its bar, at the same place along the head
        led, bar = by[f"ring_led_{i}"][1], by[f"ring_light_{i}"][1]
        assert led["extras"]["light"] == i and abs(led["translation"][2] - bar["translation"][2]) < 1e-4
        assert abs(led["translation"][0]) < abs(bar["translation"][0]) and led["translation"][0] * bar["translation"][0] > 0 and led["translation"][1] < bar["translation"][1]
    for i in range(3):
        assert set(mat(f"touch_back_{i}")) == {"touch_pad", "print"}, "each pad has an outline so it shows in Show inside"
    assert "lit while the unit has USB power (observed by the owner 2026-11-18)" in by["back_charge_led"][1]["extras"]["what"]
    assert "lit with USB power, same as the rear one" in by["screen_bottom_led"][1]["extras"]["what"]


def test_the_view_lights_glow_without_a_second_outside_script():
    js = (VU / "view3d.js").read_text()
    html = (VU / "view.html").read_text()
    assert "AdditiveBlending" in js and "PointLight" in js and "vertexColors" in js, "halos, light on nearby parts, and color along each bar"
    assert "UnrealBloom" not in js and "EffectComposer" not in js and html.count("<script src=") == 1, "one pinned outside script only"
    assert 'id="rich"' in html and 'id="dim"' in html and "richLights" in js and "dimRoom" in js
    assert "st.hw.vbus" in js, "both small power lights follow USB power"
    assert "SpotLight" in js and "l.target.position.set(at.x * 0.5, at.y - 0.02, at.z - 0.008)" in js, "the ring's thrown light points down and back, never at the controller"
    assert "touch_pad: 1" not in js, "the touch pads stay solid in Show inside"
    assert "STEP_MS = 50" in (VU / "view.py").read_text() and "},50);}" in html, "the unit and the page run at 20 a second"


def test_details_corrected_from_the_owners_photos():
    j, _ = read_glb(GLB)
    by = nodes_by_name(j)
    head, base = descendants(j, by["head"][0]), descendants(j, by["base"][0])
    assert {"ir_window_0", "ir_window_1", "red_led_side"} <= head and {"sleeve_left", "sleeve_right"} <= base
    assert "red_led_side" in descendants(j, by["screen_bottom_led"][0]) and "mesh" not in by["red_led_side"][1]
    assert "purpose not confirmed" in by["ir_window_0"][1]["extras"]["note"]
    col = {m["name"]: m["pbrMetallicRoughness"]["baseColorFactor"] for m in j["materials"]}
    assert col["led_bottom"][0] > 3 * col["led_bottom"][1], "the light under the controller is red"
    assert col["port_teal"][2] > col["port_teal"][1] > col["port_teal"][0], "the second top connector is light blue"
    assert col["camera"][0] > 0.6 and col["camera"][2] < 0.15, "a copper-orange ring round the lens"
    assert col["flex_ink"][2] > 0.5, "blue print on the flat cables"
    assert abs(by["coil"][1]["translation"][0]) < 0.001, "the folded cable is in the middle"
    src = (VU / "model" / "make_body.py").read_text()
    assert "enumerate((5.6, 7.7, 9.7))" in src and "range(8 if c == 1 else 9)" in src, "26 holes in the speaker grille: three columns of 9, 8 and 9"


def test_no_gap_between_the_controller_and_the_shell():
    src = (VU / "model" / "make_body.py").read_text()
    assert "prism(rounded_outline(53.2, 53.2, 3.7), 0.0, cy, front - 0.45, front + 0.05)" in src, "a plate inside the shell's front edge closes the joint"
    j, _ = read_glb(GLB)
    by = nodes_by_name(j)
    head = j["meshes"][by["head"][1]["mesh"]]["primitives"]
    core = next(p for p in head if j["materials"][p["material"]]["name"] == "core")
    shell = next(p for p in head if j["materials"][p["material"]]["name"] == "shell")
    zmin_core, zmax_shell = j["accessors"][core["attributes"]["POSITION"]]["min"][2], j["accessors"][shell["attributes"]["POSITION"]]["max"][2]
    assert zmin_core < zmax_shell - 0.0003, "the controller's body reaches inside the shell's front edge"
