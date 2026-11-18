# ruff: noqa: E501
"""The installed set in the virtual unit (scripts/virtual-unit/assets_sim.py, schema/asset-kinds.json; owner decision 17, docs/plan/installed-set.md B1 to B5): slots per kind, a signed install in
pieces, swap, remove, refusals with the pair error / error_es and a code, a power cut in the middle of an install, and the memory returning to the baseline. Needs the screens renderer for the turn."""

from __future__ import annotations

import base64
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VU = ROOT / "scripts" / "virtual-unit"
sys.path.insert(0, str(VU))
needs_render = pytest.mark.skipif(not (ROOT / ".runs" / "vu-screens" / "render").exists(), reason="screens renderer not built")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, VU / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


A = _load("assets_sim")
vunit = _load("vunit")


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def test_the_kind_table_is_one_file_and_the_header_is_128_bytes():
    kinds = json.loads((ROOT / "schema" / "asset-kinds.json").read_text())
    assert [k["kind"] for k in kinds["kinds"]] == ["language", "font", "style", "look", "game", "sound", "phrase"]
    assert kinds["pool"]["sectors"] == 382 and A.HEADER.size == 128
    h, sig, body = A.make_asset("style", "face-01", b"{}")
    assert len(h) == 128 and len(sig) == 64 and h[:8] == A.MAGIC


def test_slot_counts_per_kind_are_enforced_and_a_refusal_says_what_to_do_in_two_languages():
    s = A.AssetStore()
    for n in range(8):
        h, sig, body = A.make_asset("style", f"s{n}", b"{}")
        assert A.install_all(s, "style", h, sig, body)["ok"]
    h, sig, body = A.make_asset("style", "ninth", b"{}")
    r = A.install_all(s, "style", h, sig, body)
    assert not r["ok"] and r["code"] == "slots_full" and "remove one" in r["error"] and r["error_es"]
    assert s.slots()["kinds"]["style"] == {"used": 8, "slots": 8, "active": "s0"}


def test_every_refusal_has_a_code_and_both_texts():
    s = A.AssetStore()
    h, sig, body = A.make_asset("style", "ok1", b"{}")
    bad_sig = bytes(64)
    cases = [
        (s.install("nope", -1, _b64(h), _b64(sig)), "kind_unknown"),
        (s.install("style", -1, _b64(h[:100]), _b64(sig)), "bad_header"),
        (s.install("style", -1, _b64(h), _b64(bad_sig)), "bad_signature"),
    ]
    h2, sig2, _ = A.make_asset("style", "big", b"x" * 300)
    cases.append((s.install("style", -1, _b64(h2), _b64(sig2)), "too_big"))    # the style cap is 256 bytes
    h3, sig3, _ = A.make_asset("style", "other-board", b"{}", board=b"OTHERBRD")
    cases.append((s.install("style", -1, _b64(h3), _b64(sig3)), "wrong_board"))
    for r, code in cases:
        assert not r["ok"] and r["code"] == code and r["error"] and r["error_es"], (code, r)
    assert not s.data(0, "AA==")["ok"] and not s.commit()["ok"]   # nothing is running


def test_a_damaged_piece_a_wrong_offset_and_an_older_version_are_refused():
    s = A.AssetStore()
    h, sig, body = A.make_asset("game", "g1", b"G" * 5000, version=2)
    assert A.install_all(s, "game", h, sig, body)["ok"]
    h1, sig1, body1 = A.make_asset("game", "g1", b"G" * 5000, version=1)
    assert s.install("game", -1, _b64(h1), _b64(sig1))["code"] == "older_version"
    h3, sig3, body3 = A.make_asset("game", "g2", b"H" * 5000)
    assert s.install("game", -1, _b64(h3), _b64(sig3))["ok"]
    assert s.data(2048, _b64(body3[2048:4096]))["code"] == "bad_offset"
    assert s.data(0, _b64(body3[:2048]))["ok"]
    s.inflight["buf"][0] ^= 1   # a flipped bit in the piece that arrived
    for at in (2048, 4096):
        s.data(at, _b64(body3[at : at + 2048]))
    assert s.commit()["code"] == "bad_hash" and s.inflight is None


def test_a_power_cut_in_the_middle_of_an_install_keeps_the_directory_and_the_install_can_be_repeated():
    s = A.AssetStore()
    h, sig, body = A.make_asset("game", "keep", b"K" * 3000)
    assert A.install_all(s, "game", h, sig, body)["ok"]
    h2, sig2, body2 = A.make_asset("game", "lost", b"L" * 9000)
    s.cut_at = 2
    r = A.install_all(s, "game", h2, sig2, body2)
    assert r["code"] == "power_cut" and s.inflight is None
    assert [it["name"] for it in s.list()["kinds"][4]["items"]] == ["keep"]     # what was committed is still there
    assert A.install_all(s, "game", h2, sig2, body2)["ok"] and s.slots()["kinds"]["game"]["used"] == 2


def test_the_pool_has_the_real_geometry_and_a_full_pool_refuses():
    s = A.AssetStore()
    assert s.free_bytes() == 382 * 4096
    for n in range(2):
        h, sig, body = A.make_asset("look", f"pic{n}", b"P" * 700_000, psram=700_000)
        assert A.install_all(s, "look", h, sig, body)["ok"]
    h, sig, body = A.make_asset("sound", "big", b"S" * 300_000)
    r = A.install_all(s, "sound", h, sig, body)
    assert not r["ok"] and r["code"] == "pool_full"      # two looks of 700 KB leave no room for 300 KB beside them in a 1.56 MB pool


@needs_render
def test_three_faces_from_twenty_swap_one_remove_one_a_turn_with_each_and_the_memory_returns_to_baseline():
    with vunit.VirtualUnit(profile="screens") as u:
        mem = u.memory
        base = mem.snapshot()
        catalog = A.face_catalog(20)
        assert len(catalog) == 20
        picked = [catalog[1], catalog[7], catalog[13]]   # three of the twenty
        for name, h, sig, body in picked:
            assert A.install_all(u.assets, "style", h, sig, body)["ok"], name
        assert u.assets.slots()["kinds"]["style"]["used"] == 3 and u.assets.slots()["kinds"]["style"]["active"] == "face-02"
        assert "asset.style" in mem.loaded and mem.numbers()["psram_free"] < TABLE_PSRAM_FREE(mem)
        seen = []

        def a_turn(label):
            u.call("self.face.bench_emotion", {"emotion": "happy"})
            u.call("self.face.bench_speak", {"level": 60, "seconds": 1})
            u.advance(1500)
            seen.append((label, u.assets.slots()["kinds"]["style"]["active"], u.snapshot()))

        a_turn("first")
        assert u.assets.swap("style", 2)["ok"]                      # swap: the third face becomes the one on the robot
        a_turn("swapped")
        assert u.assets.slots()["kinds"]["style"]["active"] == "face-14"
        assert u.assets.remove("style", 1)["ok"]                    # remove the second
        a_turn("after remove")
        assert u.assets.slots()["kinds"]["style"]["used"] == 2
        assert len({hash(png) for _, _, png in seen}) >= 2          # the pictures differ between the faces
        for slot in (0, 2):
            assert u.assets.remove("style", slot)["ok"]
        u.advance(300)
        mem.assert_back_to(base, "after every installed face was removed")
        assert u.assets.slots()["kinds"]["style"]["used"] == 0 and u.assets.free_bytes() == 382 * 4096


def TABLE_PSRAM_FREE(mem):
    return mem.base["psram_free"]


@needs_render
def test_the_thumbnail_script_draws_every_face_overlay_and_language_and_the_manifest_matches_the_files(tmp_path):
    import hashlib
    import subprocess

    done = subprocess.run([sys.executable, str(VU / "thumbnails.py"), "--out", str(tmp_path)], capture_output=True, text=True, timeout=600)
    assert done.returncode == 0, done.stderr[-400:]
    m = json.loads((tmp_path / "manifest.json").read_text())
    kinds = {}
    for it in m["items"]:
        kinds.setdefault(it["kind"], []).append(it["name"])
        data = (tmp_path / it["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == it["sha256"] and (it["width"], it["height"]) == (160, 120), it["file"]
    assert len(kinds["face"]) == 5 and len(kinds["overlay"]) >= 26 and set(kinds["language"]) == {"en", "es", "fr", "de", "pt", "it"}
    assert len({i["sha256"] for i in m["items"] if i["kind"] == "face"}) == 5       # each face style draws differently
