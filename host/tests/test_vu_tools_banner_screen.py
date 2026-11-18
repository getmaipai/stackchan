"""Behavior checks for virtual banner and screen tools."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("vunit", ROOT / "scripts" / "virtual-unit" / "vunit.py")
vunit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vunit)


def unit():
    return vunit.VirtualUnit()


def test_face_seen_defaults_and_rate_limit():
    u = unit()
    u.state["banner_screen"] = {"status_icons": True}
    assert u.call("self.banner.face_seen", {}) == {"ok": True, "shown": True}
    assert u.call("self.banner.face_seen", {}) == {
        "ok": True, "shown": False, "reason": "status_icons_off_or_rate_limited"
    }
    u.now_ms += 501
    assert u.call("self.banner.face_seen", {"seconds": 12}) == {"ok": True, "shown": True}
    assert u.state["banner_screen"]["face_until_ms"] == 10501


def test_face_seen_refuses_when_status_icons_are_off():
    u = unit()
    assert u.call("self.banner.face_seen", {}) == {
        "ok": True, "shown": False, "reason": "status_icons_off_or_rate_limited"
    }


def test_get_level_uses_firmware_default_and_ranges():
    u = unit()
    assert u.call("self.screen.get_level", {}) == {"saved": 75, "live": 75}
    u.state["banner_screen"].update(saved_raw=140, live=-4)
    assert u.call("self.screen.get_level", {}) == {"saved": 100, "live": 0}


def test_get_level_reports_missing_backlight_as_zero():
    u = unit()
    u.state["banner_screen"] = {"backlight_present": False}
    assert u.call("self.screen.get_level", {}) == {"saved": 0, "live": 0}
