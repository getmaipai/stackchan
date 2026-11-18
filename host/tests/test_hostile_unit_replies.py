# ruff: noqa: E501
"""The host's parsers of what a unit sends back, fed garbage: a unit that is broken or hostile can answer any tool call with any JSON. Random but seeded (the same inputs every run).
Whatever it sends, the parsers return an empty or partial result and never raise (a raise here would take a host loop down). Playground report 15."""

from __future__ import annotations

import json
import random

from maipai_body.bodies.stackchan.companion import StackChanCompanion
from maipai_body.bodies.stackchan.privacy import PrivacyState, _parse

KEYS = ["kind", "at_ms", "volume", "brightness", "index", "ssid", "muted", "vision_off", "quiet", "mic_off_verified", "mute_source", "extra", "state", "ok", "reasons", "scale", "name", "text", "version"]
ATOMS = [None, True, False, 0, -1, 2**70, 1e308, float("nan"), float("inf"), "", "x", "A" * 5000, "\u0000", "{", "[]", 12, 3.5, -(2**31)]


def _value(rng: random.Random, depth: int = 0):
    r = rng.random()
    if depth > 3 or r < 0.5:
        return rng.choice(ATOMS)
    if r < 0.75:
        return [_value(rng, depth + 1) for _ in range(rng.randint(0, 5))]
    return {rng.choice(KEYS + [f"k{rng.randint(0, 9)}"]): _value(rng, depth + 1) for _ in range(rng.randint(0, 6))}


def _event(rng: random.Random) -> dict:
    return {
        "kind": rng.choice(["touch", "privacy", "wake_stats", "head_x", "timer_fired", _value(rng), "boot", "camera"]),
        "at_ms": rng.choice([0, 5, -1, 2**40, True, "7", None, 1.5]),
        **{k: _value(rng) for k in rng.sample(["volume", "brightness", "muted", "quiet", "vision_off", "mic_off_verified", "mute_source", "text", "name"], rng.randint(0, 4))},
    }


def test_garbage_from_a_unit_never_raises_in_the_hosts_parsers():
    rng = random.Random(7)
    failures: list[str] = []
    for _ in range(3000):
        result = rng.choice([[_event(rng) for _ in range(rng.randint(0, 6))], json.dumps([_event(rng)]), _value(rng), json.dumps(_value(rng), default=str), "not json", None])
        companion = StackChanCompanion(lambda name, args, r=result: r)
        state = PrivacyState()
        try:
            events = companion.poll_events()
            companion.wifi_list()
            _parse(result)
            for event in events:
                state.observe(event.kind, event.extra)
            extra = _value(rng)
            state.observe(rng.choice(["privacy", "wake_stats", "camera", "boot", "x"]), extra if isinstance(extra, dict) else {k: _value(rng) for k in ("muted", "quiet", "vision_off", "mic_off_verified", "mute_source", "local_unmute")})
        except Exception as error:  # noqa: BLE001
            failures.append(f"{type(error).__name__}: {error} for {str(result)[:80]}")
    assert not failures, failures[:3]
