"""State and response checks for the virtual unit network tool group."""
import base64
import hashlib
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "virtual-unit"))
spec = importlib.util.spec_from_file_location("vunit", ROOT / "scripts" / "virtual-unit" / "vunit.py")
vunit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vunit)


def test_update_network_test_and_version_shapes():
    with vunit.VirtualUnit() as u:
        assert u.call("self.firmware.update", {"url": "https://example.com/fw", "size": 10, "version": "1"}) == {"started": False, "reason": "update_not_available"}
        net = u.call("self.network.test")
        assert net["ok"] and {s["step"] for s in net["steps"]} == {"wifi", "host", "private"}
        assert set(u.call("self.version.get")) >= {"ok", "version", "tag", "image", "slot", "uptime_s"}


def test_wifi_state_and_refusal_shapes():
    with vunit.VirtualUnit() as u:
        assert u.call("self.wifi.add", {"ssid": "Home", "password": "secret"}) == {"ok": True}
        assert u.call("self.wifi.list_saved") == {"result": [{"index": 0, "ssid": "Home"}]}
        assert u.call("self.wifi.add", {"ssid": "", "password": ""}) == {"ok": False}
        assert u.call("self.wifi.switch", {"index": 0}) == {"ok": True}
        assert u.call("self.wifi.forget", {"index": 5}) == {"ok": False}


def test_pack_transfer_and_refusals():
    payload = b"pack"
    digest = hashlib.sha256(payload).hexdigest()
    with vunit.VirtualUnit() as u:
        assert u.call("self.pack.begin", {"type": "look", "name": "Pack", "version": 1, "size": len(payload), "sha256": digest})["ok"]
        assert u.call("self.pack.data", {"at": 0, "b64": base64.b64encode(payload).decode()}) == {"ok": True, "got": 4}
        assert u.call("self.pack.commit")["cached"] == "pending"
        assert u.call("self.pack.status", {"type": "look"})["held"]
        assert u.call("self.pack.remove", {"type": "look"}) == {"ok": True}
        assert not u.call("self.pack.commit")["ok"]


def test_tailnet_and_prefer_state():
    with vunit.VirtualUnit() as u:
        status = u.call("self.tailnet.status")
        assert set(status) >= {"compiled", "enabled", "key_saved", "peer_saved", "state", "ready", "route"}
        assert u.call("self.tailnet.set", {"enabled": True, "key": "", "peer": "bad", "now": False, "forget": False}) == {"ok": False, "error": "bad_address"}
        assert u.call("self.network.prefer_tailnet", {"minutes": 5})["error"] == "no_hub_address"


def test_remote_session_action_say_and_history():
    with vunit.VirtualUnit() as u:
        assert u.call("self.remote.session", {"active": True, "label": "controller"}) == {"ok": True, "active": True}
        token = u.call("self.remote.action", {"kind": "say", "text": "hello", "seconds": 4})["token"]
        assert u.call("self.remote.say", {"text": "hello", "token": token})["ok"]
        assert u.call("self.remote.say_status")["result"] == "none"
        assert u.call("self.remote.history")["items"][0]["kind"] == "say"
        assert u.call("self.remote.session", {"active": False, "label": "controller"}) == {"ok": True, "active": False}
