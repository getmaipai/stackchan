"""Shape and state checks for the virtual unit apps tools."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("vunit_apps_test", ROOT / "scripts/virtual-unit/vunit.py")
vunit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vunit)


class Unit:
    def __init__(self):
        self.now_ms = 0
        self.state = {}


def unit():
    return Unit()


def test_clock_tools_shapes_and_state():
    u=unit()
    assert vunit._tools.REGISTRY["self.clock.get"](u,{} )["clock_set"] is False
    assert len(vunit._tools.REGISTRY["self.clock.zones"](u,{})["zones"]) == 31
    assert "not in the list" in vunit._tools.REGISTRY["self.clock.set_zone"](u,{"zone":"no_such_zone"})["error"]
    assert vunit._tools.REGISTRY["self.clock.set"](u,{"epoch":1704067200})["clock_set"] is True


def test_game_tools_shapes_and_state():
    u=unit(); h=vunit._tools.REGISTRY
    games=h["self.game.list"](u,{})["games"]
    assert [g["id"] for g in games] == ["memory","whack","tictactoe","bopit","rps","eightball","dice"]
    assert h["self.game.start"](u,{"name":"memory"}) == {"ok":True}
    assert h["self.game.status"](u,{})["active"] is True
    assert h["self.game.bench_tap"](u,{"x":0,"y":120})["edge"] is True
    assert h["self.game.bench_event"](u,{"event":5}) == {"ok":True,"posted":True}
    assert h["self.game.bench_swipe"](u,{"x0":200,"y0":100,"x1":100,"y1":100,"ms":200}) == {"ok":True}
    assert h["self.game.bench_request_stop"](u,{}) == {"ok":True,"asked":True}
    assert h["self.game.status"](u,{})["board"] == "000000000"
    assert h["self.game.stop"](u,{}) == {"ok":True,"was":True}
    assert h["self.game.scores"](u,{"name":"bogus"})["ok"] is False
    empty_gaps=h["self.game.bench_gaps"](u,{})
    assert empty_gaps["count"] == 0 and empty_gaps["p50_ms"] == empty_gaps["p99_ms"] == 255
    assert h["self.game.bench_install"](u,{"pack":"!","done":True})["ok"] is False


def test_lock_tools_shapes_and_state():
    u=unit();h=vunit._tools.REGISTRY
    assert h["self.lock.status"](u,{})["ok"] is True
    assert h["self.lock.status"](u,{})["locked"] is False
    assert h["self.lock.now"](u,{}) == {"ok":False,"reason":"no_code"}
    u.state["apps"].update(locked=True,code=None)
    assert h["self.lock.now"](u,{}) == {"ok":True,"locked":True}
    assert h["self.lock.bench_touch"](u,{}) == {"ok":False,"reason":"not_locked"}
    assert h["self.lock.bench_key"](u,{"key":"1"}) == {"ok":False,"reason":"not_locked"}


def test_timer_tools_shapes_and_state():
    u=unit();h=vunit._tools.REGISTRY
    assert h["self.timer.alarm"](u,{"hour":0,"minute":0}) == {"ok":False,"error":"no_clock"}
    made=h["self.timer.set"](u,{"seconds":1,"label":"tea","silent":False})
    assert set(made)=={"ok","id"}
    assert h["self.timer.list"](u,{})["timers"][0]["label"]=="tea"
    assert set(h["self.timer.list"](u,{})["timers"][0]) == {"id","kind","left","label"}
    assert h["self.timer.cancel"](u,{"id":made["id"]}) == {"ok":True}
    assert h["self.timer.cancel"](u,{"id":999}) == {"ok":False,"error":"not_found"}
    assert h["self.timer.stop"](u,{}) == {"ok":False,"error":"not_ringing"}
    assert h["self.timer.snooze"](u,{"seconds":300}) == {"ok":False,"error":"not_found"}
    u.state["apps"].update(last_ring=("wake",True),last_ring_at=u.now_ms)
    snooze=h["self.timer.snooze"](u,{"seconds":9999})
    assert snooze["ok"] is True
    assert h["self.timer.list"](u,{})["timers"][-1]["left"] == 3600


def test_all_requested_apps_tools_are_registered_and_return_dicts():
    names=["self.clock.get","self.clock.set","self.clock.set_zone","self.clock.zones",
      "self.game.bench_event","self.game.bench_gaps","self.game.bench_install","self.game.bench_request_stop","self.game.bench_swipe","self.game.bench_tap","self.game.list","self.game.scores","self.game.start","self.game.status","self.game.stop",
      "self.lock.bench_key","self.lock.bench_touch","self.lock.now","self.lock.status",
      "self.timer.alarm","self.timer.cancel","self.timer.list","self.timer.set","self.timer.snooze","self.timer.stop"]
    assert len(names)==25
    for name in names:
        assert name in vunit._tools.REGISTRY
        assert isinstance(vunit._tools.REGISTRY[name](unit(),{}),dict)
