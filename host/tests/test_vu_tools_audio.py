"""Coverage for the virtual unit audio and adjacent tool group."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("vunit_audio", ROOT / "scripts" / "virtual-unit" / "vunit.py")
vunit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vunit)


def unit():
    return vunit.VirtualUnit()


@pytest.mark.parametrize("name,args", [
    ("self.audio.hourly_chime", {"enabled": 1, "test": True}),
    ("self.audio.notify", {"text": "hello", "urgent": False}),
    ("self.audio.offline_phrase", {"group": "no_host", "dry": True}),
    ("self.audio.play_sound", {"name": "success", "urgent": False, "test": False}),
    ("self.audio.set_sound_policy", {"enabled": False, "night_ok": False, "muted": False, "dark": False, "quiet_from": -1, "quiet_to": -1}),
    ("self.audio.sound_info", {}),
    ("self.bench.inject", {"q": 1, "wake": 1, "gap_ms": 1800, "tail_ms": 9000, "gain_pct": 100}),
    ("self.bench.noise", {"seconds": 60, "gain_pct": 100}),
    ("self.camera.cue_test", {}), ("self.listen.test", {}), ("self.music.get_status", {}),
    ("self.music.set", {"enabled": True}), ("self.music.stage", {"stage": 0, "source": "", "token": 0}),
    ("self.power.keep_awake", {}), ("self.prefs.get", {}), ("self.prefs.set", {"json": "{}"}),
    ("self.privacy.get", {"local_unmute": False}),
    ("self.privacy.set", {"mute": -1, "vision_off": -1, "quiet": -1}),
    ("self.privacy.set_policy", {"local_unmute": False}),
])
def test_tool_result_shape_and_state_change(name, args):
    u = unit()
    out = u.call(name, args)
    assert not out.get("isError"), out
    assert isinstance(out, dict)
    if name == "self.audio.hourly_chime":
        assert out == {"ok": True, "enabled": True, "result": "chime"}
    elif name == "self.audio.notify":
        assert set(out) == {"ok", "spoken"}
    elif name == "self.audio.offline_phrase":
        assert set(out) == {"ok", "kind", "group", "variant", "bytes", "dry"}
    elif name == "self.audio.play_sound":
        assert out == {"ok": True}
    elif name == "self.audio.set_sound_policy":
        assert out == {"ok": True, "changed": True}
    elif name == "self.audio.sound_info":
        assert {"enabled", "night", "played", "clips_present"} <= set(out)
    elif name in {"self.bench.inject", "self.bench.noise", "self.camera.cue_test", "self.music.set", "self.prefs.set"}:
        assert out["ok"] is True
    elif name == "self.listen.test":
        assert {"sound", "light", "face", "ring_frames"} <= set(out)
    elif name == "self.music.get_status":
        assert {"enabled", "state", "stage"} <= set(out)
    elif name == "self.music.stage":
        assert out == {"ok": True, "stage": 0, "beat": False}
    elif name in {"self.power.keep_awake", "self.privacy.set_policy"}:
        assert out == {"ok": True}
    elif name == "self.prefs.get":
        assert {"values", "chosen", "unit_keys"} <= set(out)
    elif name == "self.privacy.get":
        assert {"muted", "vision_off", "quiet", "mic_off_verified"} <= set(out)
    elif name == "self.privacy.set":
        assert {"muted", "vision_off", "quiet"} <= set(out)
