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
    assert vunit._tools.REGISTRY["self.clock.set"](u,{"epoch":2147483647}) == {"ok":False,"error":"time"}


def test_game_tools_shapes_and_state():
    u=unit(); h=vunit._tools.REGISTRY
    games=h["self.game.list"](u,{})["games"]
    assert [g["id"] for g in games] == ["memory","whack","tictactoe","bopit","rps","eightball","dice"]
    assert h["self.game.start"](u,{"name":"memory"}) == {"ok":True}
    assert h["self.game.status"](u,{})["active"] is True and "inputs" in h["self.game.status"](u,{})
    assert h["self.game.bench_tap"](u,{"x":0,"y":120})["edge"] is True
    assert h["self.game.bench_event"](u,{"event":5}) == {"ok":True,"posted":True}
    assert h["self.game.bench_event"](u,{"event":12})["error"] == "bad_argument"
    assert h["self.game.bench_swipe"](u,{"x0":200,"y0":100,"x1":100,"y1":100,"ms":200}) == {"ok":True}
    assert h["self.game.bench_swipe"](u,{"x0":320,"y0":100,"x1":100,"y1":100,"ms":200})["error"] == "bad_argument"
    assert h["self.game.bench_request_stop"](u,{}) == {"ok":True,"asked":True}
    assert h["self.game.status"](u,{})["board"] == "000000000"
    assert h["self.game.stop"](u,{}) == {"ok":True,"was":True}
    assert "inputs" not in h["self.game.status"](u,{}) and "board" not in h["self.game.status"](u,{})
    assert h["self.game.scores"](u,{"name":"bogus"})["ok"] is False
    empty_gaps=h["self.game.bench_gaps"](u,{})
    assert empty_gaps["count"] == 0 and empty_gaps["p50_ms"] == empty_gaps["p99_ms"] == 255
    assert h["self.game.bench_install"](u,{"pack":"!","done":True})["ok"] is False
    pack=__import__("base64").b64encode(b'{"name":"demo"}').decode()
    assert h["self.game.bench_install"](u,{"pack":pack}) == {"ok":True,"id":"demo"}


def test_lock_tools_shapes_and_state():
    u=unit();h=vunit._tools.REGISTRY
    assert h["self.lock.status"](u,{})["ok"] is True
    assert h["self.lock.status"](u,{})["locked"] is False
    assert h["self.lock.now"](u,{}) == {"ok":False,"reason":"no_code"}
    u.state["apps"].update(locked=True,code=None)
    assert h["self.lock.now"](u,{}) == {"ok":True,"locked":True}
    assert h["self.lock.bench_touch"](u,{}) == {"ok":False,"reason":"not_locked"}
    assert h["self.lock.bench_key"](u,{"key":"1"}) == {"ok":False,"reason":"not_locked"}
    u.state["apps"].update(locked=True,ui_on=True,code="12")
    assert h["self.lock.bench_touch"](u,{}) == {"ok":True}
    assert h["self.lock.bench_key"](u,{"key":"x"})["ok"] is True and u.state["apps"]["entered"] == ""


def test_timer_tools_shapes_and_state():
    u=unit();h=vunit._tools.REGISTRY
    assert h["self.timer.alarm"](u,{"hour":0,"minute":0}) == {"ok":False,"error":"no_clock"}
    made=h["self.timer.set"](u,{"seconds":1,"label":"tea","silent":False})
    assert set(made)=={"ok","id"}
    assert "ok" not in h["self.timer.list"](u,{}) and h["self.timer.list"](u,{})["timers"][0]["label"]=="tea"
    assert set(h["self.timer.list"](u,{})["timers"][0]) == {"id","kind","left","label"}
    assert h["self.timer.cancel"](u,{"id":made["id"]}) == {"ok":True}
    assert h["self.timer.cancel"](u,{"id":999}) == {"ok":False,"error":"not_found"}
    assert h["self.timer.cancel"](u,{"id":1000001}) == {"ok":False,"error":"bad_argument"}
    assert h["self.timer.stop"](u,{}) == {"ok":False,"error":"not_ringing"}
    assert h["self.timer.snooze"](u,{"seconds":300}) == {"ok":False,"error":"not_found"}
    assert h["self.timer.snooze"](u,{"seconds":0}) == {"ok":False,"error":"bad_argument"}
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


def test_clock_and_alarms_follow_the_zones_own_posix_rule_with_daylight_saving():
    """timer.alarm and clock.get use the zone rule from the unit's table (US and Australian daylight saving), not a fixed offset."""
    import datetime as dt

    summer = int(dt.datetime(2026, 7, 1, 16, 0, tzinfo=dt.timezone.utc).timestamp())  # 12:00 in New York, 02:00 next day in Sydney
    winter = int(dt.datetime(2026, 12, 1, 17, 0, tzinfo=dt.timezone.utc).timestamp())  # 12:00 in New York, 04:00 next day in Sydney
    with vunit.VirtualUnit() as u:
        u.call("self.clock.set_zone", {"zone": "america_new_york"})
        u.call("self.clock.set", {"epoch": summer})
        assert u.call("self.clock.get")["local"].endswith("12:00")  # UTC-4 in July
        out = u.call("self.timer.alarm", {"hour": 13, "minute": 0})
        assert out["ok"] and 3599 <= u.call("self.timer.list")["timers"][0]["left"] <= 3600  # one hour, to the second
        u.call("self.clock.set", {"epoch": winter})
        assert u.call("self.clock.get")["local"].endswith("12:00")  # UTC-5 in December
        u.call("self.clock.set_zone", {"zone": "australia_sydney"})
        assert u.call("self.clock.get")["local"].endswith("04:00")  # UTC+11 in December
