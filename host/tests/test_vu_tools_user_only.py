"""Behavior checks for the virtual unit user-only tools."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("vunit_user_only_test", ROOT / "scripts/virtual-unit/vunit.py")
vunit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vunit)


def test_wifi_switch_reorders_and_requests_disconnect():
    with vunit.VirtualUnit() as u:
        u.state["network"] = {"wifi": [{"ssid": "first"}, {"ssid": "second"}]}
        assert u.call("self.wifi.switch", {"index": 1}) == {"ok": True}
        assert [n["ssid"] for n in u.state["network"]["wifi"]] == ["second", "first"]
        assert u.state["network"]["wifi_disconnect_requested"] is True


def test_lock_clear_refuses_when_no_code_is_set():
    with vunit.VirtualUnit() as u:
        result = u.call("self.lock.clear", {})
        assert result == {"ok": False, "reason": "no_code"}


def test_lock_config_off_requires_current_even_when_already_off():
    with vunit.VirtualUnit() as u:
        u.state["apps"] = {"code": "1234", "auto_minutes": 0, "locked": False}
        handler = vunit._tools.REGISTRY["self.lock.config"]
        assert handler(u, {"auto_minutes": 0}) == {"ok": False, "reason": "current_needed"}
        assert handler(u, {"auto_minutes": 0, "current": "1234"}) == {"ok": True}
