"""A second unit's timer events reach that unit's own timer service, not the first unit's."""

import threading
from types import SimpleNamespace

from maipai_body import app as app_module
from maipai_body.bodies.stackchan.privacy import PrivacyUnits


def _voice(calls):
    client = SimpleNamespace(
        _call=lambda name, args: calls.append(("first", name)) or [],
        for_unit=lambda device: SimpleNamespace(_call=lambda name, args: calls.append((device, name)) or []),
        push_action=lambda *a, **k: None,
    )
    return SimpleNamespace(robot=SimpleNamespace(client=client), session_listeners=[], _sessions={})


def test_the_second_units_ring_is_handled_by_its_own_timer_service():
    calls: list = []
    said: list = []
    behavior = app_module.StackChanBehavior.__new__(app_module.StackChanBehavior)
    behavior.other_unit_event_handlers = []
    behavior.primary_unit = lambda: "unit-a"
    behavior.settings_listeners = []
    behavior.announce = lambda text: said.append(text) or True
    behavior.watch_level = lambda: "off"
    behavior.face_age = lambda: None
    behavior.night_active = lambda: False
    behavior.privacy_units = PrivacyUnits(lambda d: (lambda n, a: None))
    stop = threading.Event()
    voice = _voice(calls)
    try:
        app_module._wire_timers_and_announcements(voice, behavior, stop, None)
    finally:
        stop.set()
    (handler,) = behavior.other_unit_event_handlers
    event = SimpleNamespace(kind="timer_fired", extra={"id": 1, "what": "timer", "label": "bread"})
    handler("unit-b", [event])
    for listener in voice.session_listeners:
        listener("unit-b")
    assert behavior.timers._pending == {}, "the first unit's service did not take the second unit's ring"


def test_poll_events_hands_every_other_unit_its_events_to_the_handlers():
    seen = []
    units = PrivacyUnits(lambda d: (lambda n, a: None))
    event = SimpleNamespace(kind="timer_fired", extra={"id": 2})
    units.poll_events(
        ["unit-a", "unit-b"],
        primary="unit-a",
        events_of=lambda d: [event],
        handlers=[lambda device, events: seen.append((device, [e.kind for e in events]))],
    )
    assert seen == [("unit-b", ["timer_fired"])]
