import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "virtual-unit"))
from vunit import VirtualUnit


def test_facepic_begin_and_status():
    u = VirtualUnit()
    result = u.call("self.facepic.begin", {})
    assert result == {"ok": True, "max_bytes": 1_000_000, "max_frames": 14, "frame_bytes": 153600}
    assert u.call("self.facepic.status", {})["held"] is True


def test_facepic_frame_and_data_progress():
    u = VirtualUnit()
    u.call("self.facepic.begin", {})
    payload = b"abc"
    import zlib
    assert u.call("self.facepic.frame", {"slot": "neutral", "bytes": len(payload), "crc": f"{zlib.crc32(payload):08x}"}) == {"ok": True}
    assert u.call("self.facepic.data", {"slot": "neutral", "at": 0, "b64": base64.b64encode(payload).decode()}) == {"ok": True, "got": 3, "done": True}


def test_facepic_commit_clear_and_bench_force():
    u = VirtualUnit()
    u.call("self.facepic.begin", {})
    payload = b"x"
    import zlib
    u.call("self.facepic.frame", {"slot": "neutral", "bytes": 1, "crc": f"{zlib.crc32(payload):08x}"})
    u.call("self.facepic.data", {"slot": "neutral", "at": 0, "b64": base64.b64encode(payload).decode()})
    assert u.call("self.facepic.commit", {}) == {"ok": True, "frames": 1, "bytes": 1}
    assert u.call("self.facepic.bench_force", {"slot": "happy", "seconds": 1}) == {"ok": True}
    assert u.now_ms == 0
    assert u.call("self.facepic.clear", {}) == {"ok": True}
    assert u.call("self.facepic.status", {})["held"] is False


def test_facepic_refusals():
    u = VirtualUnit()
    assert u.call("self.facepic.data", {})["ok"] is False
    assert u.call("self.facepic.begin", {"mode": "bad"})["ok"] is False
    u.call("self.facepic.begin", {})
    assert u.call("self.facepic.commit", {})["ok"] is False


def test_facepic_firmware_limits_overlay_status_and_bench_override():
    u = VirtualUnit()
    # Actual firmware keys and defaults are accepted regardless of selected mode.
    assert u.call("self.facepic.begin", {"overlay": '{"lx":112,"ly":100,"rx":208,"ry":100,"eye_w":28,"eye_h":36,"mx":160,"my":170,"mouth_w":70,"mouth_h":40,"color":"#141414"}'})["ok"]
    status = u.call("self.facepic.status", {})
    assert status["held"] and status["fps"] == 6 and status["slots"] == {}
    assert "psram_free" in status and status["psram_free"] == 0
    assert u.call("self.facepic.frame", {"index": 1, "bytes": 1, "crc": "1"})["code"] == "index"
    assert u.call("self.facepic.begin", {"mode": "sequence"})["ok"]
    for idx in range(6):
        assert u.call("self.facepic.frame", {"slot": "neutral", "index": idx, "bytes": 1, "crc": "1"}) == {"ok": True}
    for slot in ("happy", "sad"):
        for idx in range(4):
            assert u.call("self.facepic.frame", {"slot": slot, "index": idx, "bytes": 1, "crc": "1"}) == {"ok": True}
    result = u.call("self.facepic.frame", {"slot": "angry", "bytes": 1})
    assert result["ok"] is False and "limit" in result["error"]
    assert u.call("self.facepic.bench_force", {"slot": "happy", "seconds": 1, "ignore_privacy": True}) == {"ok": True}
    assert u.state["facepic"]["bench_ignore_privacy"] is True
    assert u.state["facepic"]["shown"] == "happy"


def test_facepic_overlay_empty_or_invalid_nonempty_and_crc_leniency():
    u = VirtualUnit()
    assert u.call("self.facepic.begin", {"mode": "overlay", "overlay": ""})["ok"]
    result = u.call("self.facepic.begin", {"overlay": '{"left_eye":1}'})
    assert result["ok"] is False and "Overlay" in result["error"]
    assert u.call("self.facepic.frame", {"slot": "neutral", "bytes": 1, "crc": "1"}) == {"ok": True}
