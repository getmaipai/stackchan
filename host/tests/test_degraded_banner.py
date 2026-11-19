"""The degraded banner (firmware SF97): one short line on the unit while a part needs you, repeated inside the unit's 10 minute clear, cleared once when it is over."""

from __future__ import annotations

from maipai_body.degraded_banner import REPEAT_S, DegradedBanner, line_for

OK = {"state": "ok", "parts": []}
FAILED = {"state": "failed", "parts": [{"part": "voice server", "plain": "the voice server", "state": "failed"}]}
RESTARTING = {"state": "degraded", "parts": [{"part": "settings page", "plain": "the settings page", "state": "restarting"}]}


def test_the_line_is_plain_short_and_empty_when_all_is_well():
    assert line_for(OK) == ""
    assert line_for(FAILED) == "Needs you: the voice se…" and len(line_for(FAILED)) <= 24
    assert line_for(RESTARTING).startswith("Restarting: ") and len(line_for(RESTARTING)) <= 24
    assert line_for({"state": "failed", "parts": []}) == "Needs you: a part"


class Rig:
    def __init__(self):
        self.doc, self.units, self.tools, self.sent, self.now = OK, ["a", "b"], {"a", "b"}, [], 0.0
        self.banner = DegradedBanner(health=lambda: self.doc, units=lambda: self.units, has_tool=lambda u: u in self.tools, send=lambda u, a: self.sent.append((u, a)), clock=lambda: self.now)


def test_nothing_is_sent_while_all_is_well():
    rig = Rig()
    rig.banner.tick()
    assert rig.sent == []


def test_a_failure_is_sent_to_every_unit_that_has_the_tool_repeated_and_cleared_once():
    rig = Rig()
    rig.tools = {"a"}   # unit b runs an older image
    rig.doc = FAILED
    rig.banner.tick()
    assert rig.sent == [("a", {"text": "Needs you: the voice se…", "kind": "degraded"})]
    rig.now += 60
    rig.banner.tick()
    assert len(rig.sent) == 1, "not repeated inside the repeat window"
    rig.now += REPEAT_S
    rig.banner.tick()
    assert len(rig.sent) == 2, "repeated before the unit clears it by itself"
    rig.doc = OK
    rig.banner.tick()
    assert rig.sent[-1] == ("a", {"text": "", "kind": "degraded"})
    rig.banner.tick()
    assert len(rig.sent) == 3, "cleared once, not again"


def test_a_unit_that_rejoins_is_told_again_and_a_failed_send_is_retried():
    rig = Rig()
    rig.doc = FAILED
    rig.banner.tick()
    rig.units = ["b"]
    rig.banner.tick()
    rig.units = ["a", "b"]
    before = len(rig.sent)
    rig.banner.tick()
    assert len(rig.sent) == before + 1, "unit a came back and is told again"
    calls = {"n": 0}

    def flaky(unit, args):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("not now")

    other = DegradedBanner(health=lambda: FAILED, units=lambda: ["a"], has_tool=lambda u: True, send=flaky, clock=lambda: 0.0)
    other.tick()
    other.tick()
    assert calls["n"] == 2, "the first send failed, so the next pass sends again"
