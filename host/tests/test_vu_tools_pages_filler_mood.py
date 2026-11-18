import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "virtual-unit"))
from vunit import VirtualUnit


def test_pages_get_and_set():
    u = VirtualUnit()
    assert u.call("self.pages.get") == {
        "ok": True, "left": ["clock", "timers", "games"], "right": ["actions", "frame", "tiles"],
        "sheet_s": 8, "idle_s": 30,
        "actions": ["find", "beep", "dance", "game", "hello"],
        "sheet_items": ["volume", "brightness", "mute", "quiet", "light", "find", "timers", "games", "wifi", "battery", "tailnet", "address"],
    }
    assert u.call("self.pages.set", {"json": '{"left":["clock"],"right":["games"],"sheet_s":12}'}) == {"ok": True}
    assert u.call("self.pages.get")["left"] == ["clock"]
    assert u.call("self.pages.get")["sheet_s"] == 12
    assert u.call("self.pages.set", {"json": '{"left":["clock"],"right":["clock"]}'})["ok"] is False


def test_pages_status_shape_and_fake_clock():
    u = VirtualUnit()
    got = u.call("self.pages.status")
    assert got == {
        "ok": True, "version": 1, "open": False, "page": "face", "position": 0, "sheet": False,
        "tiles": 0, "tiles_age_s": 0,
        "pages": ["clock", "timers", "games", "actions", "frame", "tiles"],
        "actions": ["find", "beep", "dance", "game", "hello"],
        "sheet_items": ["volume", "brightness", "mute", "quiet", "light", "find", "timers", "games", "wifi", "battery", "tailnet", "address"],
    }
    assert u.now_ms == 0


def test_filler_play_and_status():
    u = VirtualUnit()
    assert u.call("self.filler.status")["ok"] is True
    assert u.call("self.filler.play", {"mode": "tone"}) == {"ok": True, "played": True, "what": "tone"}
    assert u.call("self.filler.status")["played"] == 1
    assert u.call("self.filler.play", {"mode": "invalid"})["ok"] is False


def test_mood_get_and_test_restore():
    u = VirtualUnit()
    assert u.call("self.mood.get") == {"ok": True, "care": 50, "level": "plain", "pets_today": 0, "day": 0, "test": False}
    assert u.call("self.mood.test", {"care": 80}) == {"ok": True, "care": 80, "level": "happy"}
    assert u.call("self.mood.get")["test"] is True
    assert u.call("self.mood.test", {"care": -1}) == {"ok": True, "care": 50, "level": "plain"}
