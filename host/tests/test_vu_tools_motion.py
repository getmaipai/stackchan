import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/virtual-unit"))
import tools.motion  # noqa: E402,F401
import tools as handlers  # noqa: E402


class Unit:
    now_ms = 0
    state = {}


def call(name, args=None):
    u = Unit()
    u.state = {}
    return handlers.REGISTRY[name](u, args or {}), u


def test_look_tools():
    out,u=call("self.look.bench_address"); assert out=={"ok":True}
    out,u=call("self.look.claim",{"owner":"host","ttl_s":10}); assert out["ttl_s"]==10 and u.state["motion"]["lease"]=="host"
    out,u=call("self.look.release",{"owner":"host"}); assert out=={"ok":True}
    assert "enabled" in call("self.look.status")[0]
    assert call("self.look.calibrate")[0]=={"ok":True,"started":True}
    assert "face" in call("self.look.detect_status")[0]
    assert "done" in call("self.look.detect_test")[0]
    out,u=call("self.look.detect_track",{"on":True}); assert out["armed"] and u.state["motion"]["armed"]


def test_limiter_tools():
    u=Unit(); u.state={}; out=handlers.REGISTRY["self.motion.force"](u,{"carried":1}); assert out=={"ok":True} and u.state["motion"]["force"][0]==1
    assert handlers.REGISTRY["self.motion.status"](u,{})["state"]=="carried"
    out=handlers.REGISTRY["self.motion.set"](u,{"usb_limit":"off"}); assert out["usb_limit"]=="off" and u.state["motion"]["usb_limit"]=="off"


def test_reaction_tools():
    u=Unit(); u.state={}; out=handlers.REGISTRY["self.reaction.set_table"](u,{"table":'[{"say":"hello","face":"happy"}]'}); assert out["table"][0]["say"]=="hello"
    assert handlers.REGISTRY["self.reaction.get_table"](u,{})["ok"]
    assert handlers.REGISTRY["self.reaction.test"](u,{"text":"hello"})["match"]
    assert handlers.REGISTRY["self.reaction.reset"](u,{})["builtin"]


def test_robot_tools():
    assert call("self.robot.dance",{"name":"happy"})[0]["ok"]
    assert call("self.robot.dance_list")[0]["builtin"]
    assert call("self.robot.stop_dance")[0]["ok"]
    assert call("self.robot.get_events")[0]=={"events":[]}
    out,u=call("self.robot.set_idle_motion",{"enabled":True}); assert out["ok"] and u.state["motion"]["idle"]
    out,u=call("self.robot.create_reminder",{"duration_seconds":30,"message":"x","repeat":False}); assert out["id"]==1 and u.state["motion"]["reminders"]
    # One unit owns the reminder queue for create, list and stop.
    u=Unit(); u.state={}; made=handlers.REGISTRY["self.robot.create_reminder"](u,{"duration_seconds":30,"message":"x","repeat":False}); assert made["id"]==1
    assert handlers.REGISTRY["self.robot.get_reminders"](u,{})["reminders"][0]["message"]=="x"
    assert handlers.REGISTRY["self.robot.stop_reminder"](u,{"id":1})["ok"]
