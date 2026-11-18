"""The coding agent is its own bus source: tone and light only, below the host's routines, rate limited, gates apply."""

from maipai_body import command_bus as bus_mod
from maipai_body.command_bus import Command, CommandBus, Gate


def _bus(gate=None, clock=None):
    calls = []
    executors = {"light.look": lambda d, a: calls.append(("light", a)) or True, "sound.play": lambda d, a: calls.append(("sound", a)) or True}
    kwargs = {"gate": (lambda d: gate)} if gate else {}
    if clock:
        kwargs["clock"] = clock
    return CommandBus(executors, **kwargs), calls


def test_the_agent_may_only_set_the_light_and_play_a_quiet_sound():
    bus, calls = _bus()
    assert bus.send("u", Command("light.look", {"color": "amber", "seconds": 20}, source="agent")).ok
    assert bus.send("u", Command("sound.play", {"name": "popup"}, source="agent")).ok
    for cmd, args in (("fx.set", {"name": "rain"}), ("scene.set", {"name": "party"}), ("face.mood", {"mood": "happy"}), ("head.move", {}), ("camera.photo", {}), ("privacy.set", {})):
        assert not bus.send("u", Command(cmd, args, source="agent")).ok, cmd


def test_the_agent_never_gets_red_or_a_loud_sound():
    bus, _ = _bus()
    assert not bus.send("u", Command("light.look", {"color": "red"}, source="agent")).ok
    assert not bus.send("u", Command("sound.play", {"name": "vibration"}, source="agent")).ok


def test_the_tone_is_limited_to_once_a_minute_and_the_light_is_coalesced():
    now = [100.0]
    bus, calls = _bus(clock=lambda: now[0])
    assert bus.send("u", Command("sound.play", {"name": "popup"}, source="agent")).ok
    now[0] += 30
    assert not bus.send("u", Command("sound.play", {"name": "popup"}, source="agent")).ok
    now[0] += 31
    assert bus.send("u", Command("sound.play", {"name": "popup"}, source="agent")).ok
    for _ in range(bus_mod.AGENT_LIMITS["light.look"]["minute"]):
        bus.send("u", Command("light.look", {"color": "blue", "seconds": 5}, source="agent"))
        now[0] += 1
    assert not bus.send("u", Command("light.look", {"color": "blue", "seconds": 5}, source="agent")).ok


def test_every_gate_applies_to_the_agent():
    for gate, why in ((Gate(muted=True), "muted"), (Gate(blocked=True), "asleep"), (Gate(remote=True), "remote")):
        bus, calls = _bus(gate)
        assert not bus.send("u", Command("light.look", {"color": "blue"}, source="agent")).ok, why
        assert not bus.send("u", Command("sound.play", {"name": "popup"}, source="agent")).ok, why
        assert calls == []


def test_the_agent_ranks_below_the_hosts_routines_and_the_owner():
    assert bus_mod.PRIORITY["routines"] < bus_mod.PRIORITY["agent"] < bus_mod.PRIORITY["model"]
    bus, _ = _bus()
    assert bus.send("u", Command("light.look", {"color": "green", "seconds": 30}, source="routines")).ok
    assert not bus.send("u", Command("light.look", {"color": "blue", "seconds": 30}, source="agent")).ok
