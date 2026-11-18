"""Face tool behavior in the virtual unit."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("vunit", ROOT / "scripts" / "virtual-unit" / "vunit.py")
vunit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vunit)
sys.path.insert(0, str(ROOT / "scripts" / "virtual-unit"))
import tools as tool_registry
for _module in sorted((ROOT / "scripts" / "virtual-unit" / "tools").glob("[a-z]*.py")):
    __import__(f"tools.{_module.stem}")


def unit():
    """Construct without starting the display renderer."""
    return vunit.VirtualUnit()


class FakeUnit:
    def __init__(self):
        self.now_ms = 0
        self.state = {}

    def advance(self, ms):
        self.now_ms += ms

    def call(self, name, args):
        return tool_registry.REGISTRY[name](self, args)


def test_bench_caption_stores_text_and_clears_with_empty_default():
    u = FakeUnit()
    assert u.call("self.face.bench_caption", {"text": "hello"}) == {"ok": True}
    assert u.state["face"]["caption"] == "hello"
    assert u.call("self.face.bench_caption", {}) == {"ok": True}
    assert u.state["face"]["caption"] == ""


def test_bench_caption_refuses_when_face_not_ready():
    u = FakeUnit()
    u.state["face"] = {"ready": False}
    assert u.call("self.face.bench_caption", {"text": "hello"}) == {"ok": False, "error": "no face"}


def test_bench_fps_returns_firmware_rate_shape():
    u = FakeUnit()
    u.now_ms = 2500
    out = u.call("self.face.bench_fps", {})
    assert out["ok"] is True
    assert out["seconds"] == 0.0
    assert {"refresh_per_s", "avg_render_ms", "p99_gap_ms", "face_task_stack_min_free"} <= out.keys()
    assert out["refresh_per_s"] == 0.0  # Hardware counters are unavailable in the virtual unit.


def test_bench_mode_sets_ab_switch_and_refuses_invalid_value():
    u = FakeUnit()
    assert u.call("self.face.bench_mode", {"dirty": 1}) == {"ok": True}
    assert u.state["face"]["legacy_mode"] == 1
    assert u.call("self.face.bench_mode", {"dirty": 2})["ok"] is False


def test_bench_run_advances_fake_clock_and_refuses_unknown_workload():
    u = FakeUnit()
    out = u.call("self.face.bench_run", {"what": "idle", "seconds": 2, "level": 0})
    assert out["ok"] is True and out["what"] == "idle"
    assert u.now_ms == 2000
    assert out["refresh_per_s"] == 0.0  # The firmware measures hardware counters unavailable here.
    assert u.call("self.face.bench_run", {"what": "bogus"})["ok"] is False


def test_decor_list_matches_build_names():
    u = FakeUnit()
    out = u.call("self.face.decor_list", {})
    assert out == {"ok": True, "decorators": ["sweat", "shy", "dizzy", "heart", "anger", "tears", "sparkles", "stars", "zzz", "notes"]}


def test_decorate_validates_seconds_before_none_clears():
    u = FakeUnit()
    assert u.call("self.face.decorate", {"name": "none", "seconds": 0})["error"].startswith("seconds must be 1 to 60")


def test_decorate_changes_state_refuses_unknown_and_none_clears():
    u = FakeUnit()
    assert u.call("self.face.decorate", {"name": "sweat"}) == {"ok": True}
    assert u.state["face"]["decorator"] == "sweat"
    assert u.call("self.face.decorate", {"name": "mystery"})["error"].startswith("unknown decorator")
    assert u.call("self.face.decorate", {"name": "none"}) == {"ok": True}
    assert u.state["face"]["decorator"] == "none"


def test_gaze_moves_and_expires_on_fake_clock():
    u = FakeUnit()
    assert u.call("self.face.gaze", {"x": 50, "y": -10, "ms": 200}) == {"ok": True}
    face = u.state["face"]
    assert face["gaze"] == {"x": 50, "y": -10} and face["gaze_until"] == 200
    assert u.call("self.face.gaze", {"x": 101, "y": 0, "ms": 200})["ok"] is False
    u.advance(200)
    assert u.call("self.face.gaze", {"x": 50, "y": -10, "ms": 200}) == {"ok": True}
    u.advance(200)
    face = u.state["face"]
    assert face["gaze"] == {"x": 0, "y": 0}


def test_gaze_refuses_when_face_not_ready():
    u = FakeUnit()
    u.state["face"] = {"ready": False}
    assert u.call("self.face.gaze", {}) == {"ok": False, "error": "the face is not ready: try again in a moment"}
