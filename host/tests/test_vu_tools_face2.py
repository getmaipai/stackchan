import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("vunit", ROOT / "scripts" / "virtual-unit" / "vunit.py")
vunit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vunit)


def unit():
    u = vunit.VirtualUnit()
    u.now_ms = 500
    return u


def test_get_and_set_config():
    u = unit()
    original = u.call("self.face.get_config")
    assert original["ok"] is True
    assert original["style"] == "big_eyes"
    assert "features" in original
    updated = u.call("self.face.set_config", {"config": '{"style":"minimal"}'})
    assert updated["style"] == "minimal"
    assert u.call("self.face.get_config")["style"] == "minimal"
    refused = u.call("self.face.set_config", {"config": '{"style":"bad"}'})
    assert refused == {"ok": False, "error": "style: unknown face style: use big_eyes, eyes_only, stock, classic or minimal"}
    fixed = u.call("self.face.set_config", {"config": '{"caption_size":"large","background":"none","emotion_tint":false,"lang":"fr"}'})
    assert (fixed["caption_size"], fixed["background"], fixed["emotion_tint"], fixed["lang"]) == ("large", "none", False, "fr")


def test_music_notes_range_and_expiry():
    u = unit()
    assert u.call("self.face.music_notes", {"count": 2}) == {"ok": True}
    assert u.state["face2"]["music_notes"] == 2
    assert u.state["face2"]["notes_until_ms"] == 30500
    assert u.call("self.face.music_notes", {"count": 4})["ok"] is False
    u.state["face2"]["privacy_bits"] = 1
    refused = u.call("self.face.music_notes", {"count": 1})
    assert refused["ok"] is False and "mute" in refused["error"]
    assert u.state["face2"]["music_notes"] == 2


def test_clock_refusal_display_and_clear():
    u = unit()
    assert "not set yet" in u.call("self.face.show_clock", {"seconds": 30})["error"]
    u.state.setdefault("face2", {})["time_set"] = True
    assert u.call("self.face.show_clock", {"seconds": 3}) == {"ok": True}
    assert u.state["face2"]["clock_until_ms"] == 3500
    assert u.call("self.face.show_clock", {"seconds": 0}) == {"ok": True}
    assert u.state["face2"]["clock_until_ms"] == 0


def test_thinking_state_and_timeout():
    u = unit()
    assert u.call("self.face.thinking", {"on": True}) == {"ok": True}
    assert u.state["face2"]["thinking"] is True
    assert u.state["face2"]["thinking_until_ms"] == 45500
    u.call("self.face.thinking", {"on": False})
    assert u.state["face2"]["thinking"] is False
    assert u.state["face2"]["thinking_until_ms"] == 0
