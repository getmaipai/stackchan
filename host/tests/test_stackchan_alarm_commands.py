"""Voice alarms and timers with no model: the words, the cancel rule, and plain failure lines."""

from __future__ import annotations

from datetime import datetime

import pytest

from maipai_body.bodies.stackchan.alarm_commands import AlarmControl, parse_alarm_command

NOON = datetime(2026, 11, 17, 12, 0, 0)
EVENING = datetime(2026, 11, 17, 21, 0, 0)


@pytest.mark.parametrize(
    "text, now, hour, minute",
    [
        ("Set an alarm for 10:30.", NOON, 22, 30),  # the next 10:30 after noon is tonight
        ("Hey, set an alarm for 10:30", EVENING, 22, 30),
        ("set an alarm for 7 am", NOON, 7, 0),
        ("Set an alarm for 6:15 p.m.", NOON, 18, 15),
        ("wake me up at 7", EVENING, 7, 0),
        ("set an alarm for ten thirty", NOON, 22, 30),
        ("set an alarm for 14:05", NOON, 14, 5),
    ],
)
def test_set_alarm_words(text: str, now: datetime, hour: int, minute: int) -> None:
    command = parse_alarm_command(text, now)
    assert command is not None and command.kind == "set_alarm"
    assert (command.hour, command.minute) == (hour, minute)


@pytest.mark.parametrize(
    "text, seconds",
    [("set a timer for 10 minutes", 600), ("set a timer for an hour and 5 minutes", 300), ("start a timer for 30 seconds", 30)],
)
def test_set_timer_words(text: str, seconds: int) -> None:
    command = parse_alarm_command(text, NOON)
    assert command is not None and command.kind == "set_timer"
    assert command.seconds is not None


@pytest.mark.parametrize(
    "text", ["what is the weather", "I set my alarm at home", "tell me about timers", "it is 10:30", "play some music"]
)
def test_ordinary_talk_is_left_to_the_model(text: str) -> None:
    assert parse_alarm_command(text, NOON) is None


def test_cancel_words() -> None:
    assert parse_alarm_command("cancel my alarm", NOON).kind == "cancel"
    assert parse_alarm_command("cancel all alarms", NOON).everything is True
    c = parse_alarm_command("cancel the 10:30 alarm", NOON)
    assert c.kind == "cancel" and (c.hour, c.minute) == (22, 30)
    assert parse_alarm_command("what alarms do I have", NOON).kind == "list"


class FakeTimers:
    def __init__(self, rows):
        self.rows = rows
        self.canceled: list[int] = []
        self.next_id = 50

    def list_timers(self):
        return {"ok": True, "timers": self.rows}

    def cancel(self, timer_id=None):
        self.canceled.append(timer_id)
        self.rows = [r for r in self.rows if r["id"] != timer_id]

    def set_alarm(self, hour, minute, label=""):
        self.next_id += 1
        self.rows.append({"id": self.next_id, "kind": "alarm", "left": 3600, "label": ""})
        return {"ok": True, "id": self.next_id}

    def set_timer(self, seconds, label=""):
        self.next_id += 1
        self.rows.append({"id": self.next_id, "kind": "timer", "left": seconds, "label": ""})
        return {"ok": True, "id": self.next_id}


def control(rows, clock=lambda: 1000.0):
    timers = FakeTimers(rows)
    return timers, AlarmControl(timers, now=lambda: NOON, clock=clock)


def test_one_alarm_is_canceled_at_once() -> None:
    timers, ctl = control([{"id": 3, "kind": "alarm", "left": 3600, "label": ""}])
    line = ctl.run(ctl.parse("cancel my alarm"))
    assert timers.canceled == [3] and "Canceled" in line and "1:00 PM" in line


def test_the_alarm_just_set_is_the_one_canceled_when_there_are_several() -> None:
    now = [1000.0]
    timers, ctl = control([{"id": 3, "kind": "alarm", "left": 7200, "label": ""}], clock=lambda: now[0])
    ctl.run(ctl.parse("set an alarm for 1 pm"))
    now[0] += 60
    ctl.run(ctl.parse("cancel my alarm"))
    assert timers.canceled == [51]  # the new one, not id 3


def test_several_and_not_recent_asks_which() -> None:
    now = [1000.0]
    rows = [{"id": 3, "kind": "alarm", "left": 7200, "label": ""}, {"id": 4, "kind": "alarm", "left": 14400, "label": ""}]
    timers, ctl = control(rows, clock=lambda: now[0])
    line = ctl.run(ctl.parse("cancel my alarm"))
    assert timers.canceled == [] and "Say cancel, then the time" in line and "2:00 PM" in line


def test_cancel_by_time_and_cancel_all() -> None:
    rows = [{"id": 3, "kind": "alarm", "left": 7200, "label": ""}, {"id": 4, "kind": "alarm", "left": 36000, "label": ""}]
    timers, ctl = control(rows)
    ctl.run(ctl.parse("cancel the 10 pm alarm"))
    assert timers.canceled == [4]
    ctl.run(ctl.parse("cancel all alarms"))
    assert timers.canceled == [4, 3]


def test_a_unit_that_is_away_gets_a_plain_line() -> None:
    class Away:
        def list_timers(self):
            raise ConnectionError("StackChan is not connected. Check that unit's power and Wi-Fi, then retry.")

    ctl = AlarmControl(Away(), now=lambda: NOON)
    assert "Wi-Fi" in ctl.run(ctl.parse("cancel my alarm"))
