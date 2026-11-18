import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "virtual-unit"))
from vunit import VirtualUnit


def test_facepic_begin_and_status():
    u = VirtualUnit()
    result = u.call("self.facepic.begin", {})
    assert result == {"ok": True, "max_bytes": 512 * 1024, "max_frames": 42, "frame_bytes": 153600}
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
