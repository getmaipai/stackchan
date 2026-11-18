import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "virtual-unit"))
import tools  # noqa: E402
import tools.page_overlay  # noqa: E402,F401


class Unit:
    def __init__(self):
        self.now_ms = 0
        self.state = {}

    def advance(self, ms):
        self.now_ms += ms


def call(unit, name, args=None):
    return tools.REGISTRY[name](unit, args or {})


def test_page_bench_swipe_shape():
    u = Unit()
    assert call(u, "self.page.bench_swipe", {"x0": 0, "y0": 0, "x1": 200, "y1": 100, "ms": 200}) == {"ok": True, "open": False, "position": 0, "sheet": False}
    assert u.now_ms == 200
    assert u.state["page_overlay"]["page"] == "face"


def test_page_bench_tap_shape():
    u = Unit()
    assert call(u, "self.page.bench_tap", {"x": 10, "y": 20, "hold_ms": 120}) == {"ok": True, "open": False, "position": 0, "sheet": False}
    assert u.state["page_overlay"]["page"] == "face"


def test_page_show_changes_page_and_refuses_unknown():
    u = Unit()
    assert call(u, "self.page.show", {"name": "tiles"}) == {"ok": True}
    assert u.state["page_overlay"]["page"] == "tiles"
    assert call(u, "self.page.show", {"name": "bogus"})["ok"] is False


def test_page_tiles_updates_and_refuses_non_array():
    u = Unit()
    assert call(u, "self.page.tiles", {"json": '[{"icon":"sun","label":"Today","value":"72 F"}]'}) == {"ok": True, "tiles": 1}
    assert u.state["page_overlay"]["tiles"][0]["label"] == "Today"
    assert call(u, "self.page.tiles", {"json": "{}"})["ok"] is False


def test_overlay_clear_clears_both_layers():
    u = Unit()
    assert call(u, "self.overlay.set", {"name": "rain", "intensity": "light", "seconds": 5}) == {"ok": True}
    assert call(u, "self.overlay.set", {"name": "hearts", "intensity": "heavy", "seconds": 0}) == {"ok": True}
    assert call(u, "self.overlay.clear") == {"ok": True}
    assert all(row["name"] == "none" for row in call(u, "self.overlay.status")["layers"])


def test_overlay_set_validates_and_status_expires():
    u = Unit()
    assert call(u, "self.overlay.set", {"name": "rain", "intensity": "normal", "seconds": 1}) == {"ok": True}
    status = call(u, "self.overlay.status")
    assert status["layers"][0]["name"] == "rain"
    assert status["names"]
    assert call(u, "self.overlay.set", {"name": "unknown", "intensity": "normal", "seconds": 1})["ok"] is False
    u.now_ms = 1000
    assert call(u, "self.overlay.status")["layers"][0]["name"] == "none"


def test_overlay_set_accepts_preset_and_status_has_three_layers():
    u = Unit()
    assert call(u, "self.overlay.set", {"name": "stormy", "intensity": "normal", "seconds": 8}) == {"ok": True}
    status = call(u, "self.overlay.status")
    assert [layer["layer"] for layer in status["layers"]] == ["weather", "event", "front"]
    assert "stormy" in status["names"]
    assert status["layers"][0]["name"] == "stormy"
