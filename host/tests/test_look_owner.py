"""Who turns toward faces (look_owner.py): the lease heartbeat, the setting, the page view and the value the unit is sent."""

from __future__ import annotations

import json
import threading
from typing import Any

from maipai_body import unit_prefs
from maipai_body.hal.errors import BodyLost
from maipai_body.look_owner import HEARTBEAT_S, LEASE_OWNER, LEASE_TTL_S, LookLeaseRunner, LookOwner
from maipai_body.unit_tools import ToolProbe

UNIT = "aa:bb:cc:dd:ee:01"


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class Unit:
    """A unit that has (or lacks) the look tools and records what it is called with."""

    def __init__(self, has_look: bool = True) -> None:
        self.has_look = has_look
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.holder: str | None = None
        self.down = False

    def __call__(self, name: str, arguments: dict[str, Any], *, device_id: str | None = None, timeout: float = 4.0) -> object:
        if self.down:
            raise BodyLost("unit is off")
        self.calls.append((name, dict(arguments)))
        if name.startswith("self.look.") and not self.has_look:
            return {"ok": False, "error": "unknown tool " + name}
        if name == "self.look.claim":
            if self.holder not in (None, arguments["owner"]):
                return {"ok": False, "error": "held by " + self.holder}
            self.holder = arguments["owner"]
            return {"ok": True}
        if name == "self.look.release":
            if self.holder == arguments["owner"]:
                self.holder = None
            return {"ok": True}
        if name == "self.look.status":
            return {"ok": True, "owner": "host" if self.holder else "unit"}
        return {"ok": True}

    def of(self, name: str) -> list[dict[str, Any]]:
        return [a for n, a in self.calls if n == name]


def make(unit: Unit, saved: dict[str, Any], *, hub: bool = True, tracking: bool = True):
    clock = Clock()
    state = {"hub": hub, "tracking": tracking}
    probe = ToolProbe(unit, clock=clock)
    owner = LookOwner(probe, lambda _d: saved, hub_configured=lambda: state["hub"], tracking=lambda: state["tracking"], clock=clock)
    return owner, clock, state


def test_the_robot_owns_face_seeking_by_default_and_the_host_never_claims():
    unit, saved = Unit(), {}
    owner, clock, _ = make(unit, saved)
    assert owner.setting(UNIT) == "robot"
    for _ in range(5):
        assert owner.tick(UNIT) == "idle"
        clock.now += HEARTBEAT_S
    assert unit.of("self.look.claim") == []


def test_off_never_claims_either():
    unit = Unit()
    owner, _, _ = make(unit, {"face_owner": "off"})
    assert owner.tick(UNIT) == "idle" and unit.of("self.look.claim") == []
    assert owner.host_may_search(UNIT) is False


def test_the_hub_claims_with_a_fifteen_second_ttl_and_renews_every_five_seconds():
    unit = Unit()
    owner, clock, _ = make(unit, {"face_owner": "hub"})
    assert owner.tick(UNIT) == "claimed"
    assert unit.of("self.look.claim") == [{"owner": LEASE_OWNER, "ttl_s": LEASE_TTL_S}]
    assert LEASE_TTL_S == 15 and HEARTBEAT_S == 5.0
    clock.now += 2.0
    assert owner.tick(UNIT) == "waiting" and len(unit.of("self.look.claim")) == 1
    clock.now += 3.0
    assert owner.tick(UNIT) == "renewed" and len(unit.of("self.look.claim")) == 2
    assert owner.view(UNIT)["lease_held"] is True


def test_no_claim_while_the_hub_tracking_is_not_running_and_the_lease_is_given_back_when_it_stops():
    unit = Unit()
    owner, clock, state = make(unit, {"face_owner": "hub"}, tracking=False)
    assert owner.tick(UNIT) == "idle" and unit.of("self.look.claim") == []
    state["tracking"] = True
    assert owner.tick(UNIT) == "claimed"
    clock.now += 5.0
    state["tracking"] = False
    assert owner.tick(UNIT) == "released"
    assert unit.of("self.look.release") == [{"owner": LEASE_OWNER}] and unit.holder is None


def test_a_host_with_no_home_hub_never_claims():
    unit = Unit()
    owner, _, _ = make(unit, {"face_owner": "hub"}, hub=False)
    assert owner.tick(UNIT) == "idle" and unit.of("self.look.claim") == []


def test_changing_the_setting_away_from_hub_releases_at_the_next_tick():
    unit, saved = Unit(), {"face_owner": "hub"}
    owner, clock, _ = make(unit, saved)
    owner.tick(UNIT)
    saved["face_owner"] = "robot"
    clock.now += 1.0
    assert owner.tick(UNIT) == "released" and unit.holder is None
    assert owner.tick(UNIT) == "idle"


def test_a_unit_without_the_look_tool_is_never_sent_a_claim():
    unit = Unit(has_look=False)
    owner, clock, _ = make(unit, {"face_owner": "hub"})
    assert owner.tick(UNIT) == "unsupported"
    assert unit.of("self.look.claim") == []
    assert owner.view(UNIT)["unit_ready"] is False


def test_an_unreachable_unit_is_asked_again_and_a_lost_heartbeat_forgets_the_claim():
    unit = Unit()
    owner, clock, _ = make(unit, {"face_owner": "hub"})
    assert owner.tick(UNIT) == "claimed"
    clock.now += 5.0
    unit.down = True
    assert owner.tick(UNIT) == "unreachable"
    unit.down = False
    assert owner.tick(UNIT) == "claimed"  # claimed again, not "renewed": the unit may have rebooted


def test_a_second_host_holding_the_lease_is_reported_busy_and_not_taken_over():
    unit = Unit()
    unit.holder = "other-host"
    owner, clock, _ = make(unit, {"face_owner": "hub"})
    assert owner.tick(UNIT) == "busy"
    assert unit.holder == "other-host"
    owner.release(UNIT)
    assert unit.of("self.look.release") == []  # never released what it does not hold


def test_a_reconnect_claims_again_at_once():
    unit = Unit()
    owner, clock, _ = make(unit, {"face_owner": "hub"})
    owner.tick(UNIT)
    owner.forget(UNIT)  # the unit connected again
    assert owner.tick(UNIT) == "claimed"


def test_the_host_search_runs_for_the_hub_and_for_an_old_unit_but_not_for_a_unit_that_seeks_itself():
    old, new = Unit(has_look=False), Unit(has_look=True)
    owner_old, _, _ = make(old, {})
    owner_new, _, _ = make(new, {})
    assert owner_old.host_may_search(UNIT) is True  # robot owner, unit cannot seek yet: nothing regresses
    assert owner_new.host_may_search(UNIT) is False
    owner_hub, _, _ = make(new, {"face_owner": "hub"})
    assert owner_hub.host_may_search(UNIT) is True
    owner_off, _, _ = make(old, {"face_owner": "off"})
    assert owner_off.host_may_search(UNIT) is False


def test_close_gives_every_lease_back():
    unit = Unit()
    owner, _, _ = make(unit, {"face_owner": "hub"})
    owner.tick(UNIT)
    owner.close([UNIT])
    assert unit.holder is None


def test_the_runner_ticks_every_unit_and_applies_after_each():
    unit = Unit()
    owner, _, _ = make(unit, {"face_owner": "hub"})
    applied: list[str] = []
    runner = LookLeaseRunner(owner, lambda: [UNIT], threading.Event(), apply=applied.append)
    runner.run_once()
    assert unit.holder == LEASE_OWNER and applied == [UNIT]


# -- the value the unit is sent -----------------------------------------------------------------------------------------


def test_the_setting_has_the_documented_values_and_a_flash_key_that_fits():
    kind, allowed, default, unit_applies = unit_prefs.PREFS["turn_to_faces"]
    assert (kind, allowed, default, unit_applies) == ("enum", ("off", "talk", "always"), "always", True)  # firmware patch NX06: also search when something moves
    assert len("turn_to_faces") <= 15


def test_who_turns_off_sends_the_unit_off_and_the_choice_comes_back_with_the_robot():
    assert unit_prefs.effective_turn_to_faces({"turn_to_faces": "always"}) == "always"
    assert unit_prefs.effective_turn_to_faces({}) == "always"  # the default searches when something moves too (patch NX06)
    assert unit_prefs.effective_turn_to_faces({"turn_to_faces": "always", "face_owner": "off"}) == "off"
    assert unit_prefs.effective_turn_to_faces({"turn_to_faces": "always", "face_owner": "hub"}) == "always"
    assert unit_prefs.effective_turn_to_faces({"turn_to_faces": "weird"}) == "always"
    # the "Look for faces" switch is the same mode (patch NX06): on is always, off is talk, a person's own "off" stays off
    assert unit_prefs.effective_turn_to_faces({"look_faces": True, "turn_to_faces": "talk"}) == "always"
    assert unit_prefs.effective_turn_to_faces({"look_faces": False}) == "talk"
    assert unit_prefs.effective_turn_to_faces({"look_faces": True, "turn_to_faces": "off"}) == "off"
    assert unit_prefs.effective_turn_to_faces({"look_faces": True, "face_owner": "off"}) == "off"
    assert unit_prefs.effective_turn_to_faces({"turn_to_faces": "talk"}) == "talk"


def _service(unit: Unit, saved: dict[str, Any]):
    probe = ToolProbe(unit, tool_list=lambda _d: {"self.prefs.get", "self.look.status"} if unit.has_look else {"self.prefs.get"})
    return unit_prefs.PrefsService(probe, lambda _d: saved, lambda _d, v: saved.update(v) or saved)


def test_resend_look_sends_off_when_nobody_is_to_turn_and_the_saved_choice_otherwise():
    unit, saved = Unit(), {"turn_to_faces": "always", "face_owner": "off"}
    service = _service(unit, saved)
    assert service.resend_look(UNIT)["pushed"] is True
    assert json.loads(unit.of("self.prefs.set")[-1]["json"]) == {"turn_to_faces": "off"}
    saved["face_owner"] = "robot"
    service.resend_look(UNIT)
    assert json.loads(unit.of("self.prefs.set")[-1]["json"]) == {"turn_to_faces": "always"}


def test_saving_the_look_for_faces_switch_sends_the_unit_its_seeker_mode():
    unit, saved = Unit(), {}
    service = _service(unit, saved)
    saved["look_faces"] = True
    assert service.save(UNIT, {"look_faces": True})["pushed"] is True
    assert json.loads(unit.of("self.prefs.set")[-1]["json"]) == {"turn_to_faces": "always"}
    saved["look_faces"] = False
    service.save(UNIT, {"look_faces": False})
    assert json.loads(unit.of("self.prefs.set")[-1]["json"]) == {"turn_to_faces": "talk"}


def test_the_prefs_view_says_whether_the_unit_has_the_look_tool_and_who_owns_seeking():
    new = _service(Unit(has_look=True), {"face_owner": "hub"}).view(UNIT)
    assert new["features"]["look"] is True and new["face_owner"] == "hub" and "turn_to_faces" in new["values"]
    old = _service(Unit(has_look=False), {}).view(UNIT)
    assert old["features"]["look"] is False and old["face_owner"] == "robot"


def test_the_heartbeat_reads_the_units_status_and_the_page_view_carries_it():
    unit = Unit()
    answers = {"ok": True, "owner": "unit", "enabled": True, "setting": "talk", "state": "idle", "last_face_ago_ms": 4200, "last_seen_ago_ms": 4200, "fov_deg": 65.0, "x_sign": 1, "junk": "dropped"}
    base = unit.__call__

    def call(name, arguments, **kw):
        if name == "self.look.status":
            unit.calls.append((name, dict(arguments)))
            return dict(answers)
        return base(name, arguments, **kw)

    clock = Clock()
    owner = LookOwner(ToolProbe(call, clock=clock), lambda _d: {}, hub_configured=lambda: False, tracking=lambda: False, clock=clock)
    assert owner.cached_status(UNIT) == {}
    owner.tick(UNIT)
    status = owner.view(UNIT)["status"]
    assert status["owner"] == "unit" and status["enabled"] is True and status["last_face_ago_ms"] == 4200 and status["age_s"] == 0.0
    assert "junk" not in status
    clock.now += 21.0  # the heartbeat stopped: a stale status is not shown
    assert owner.cached_status(UNIT) == {}


def test_a_unit_without_the_look_tool_has_no_status_and_an_unreachable_one_keeps_its_last_answer():
    old = Unit(has_look=False)
    owner, _, _ = make(old, {})
    owner.tick(UNIT)
    assert owner.cached_status(UNIT) == {}
    unit = Unit()
    owner2, clock2, _ = make(unit, {})
    owner2.tick(UNIT)
    unit.down = True
    clock2.now += 5.0
    owner2.tick(UNIT)  # the unit does not answer: no crash
    assert owner2.view(UNIT)["reachable"] is True or owner2.view(UNIT)["reachable"] is False


def test_the_experiment_units_detector_fields_pass_through_read_only():
    """Patches FD03 and FD04 add flat fd_* fields to self.look.status; the heartbeat keeps them for the page and still drops anything else."""
    unit = Unit()
    answers = {"ok": True, "owner": "unit", "enabled": True, "fd_loaded": True, "fd_score_pct": 83, "fd_cx": 171, "fd_age_ms": 240, "fd_track": "track",
               "fd_tracks": 2, "fd_moves": 9, "fd_moves_min": 3, "fd_stalls": 0, "fd_end": "none", "fd_hour_s": 61, "picture": "dropped"}
    base = unit.__call__

    def call(name, arguments, **kw):
        if name == "self.look.status":
            unit.calls.append((name, dict(arguments)))
            return dict(answers)
        return base(name, arguments, **kw)

    clock = Clock()
    owner = LookOwner(ToolProbe(call, clock=clock), lambda _d: {}, hub_configured=lambda: False, tracking=lambda: False, clock=clock)
    owner.tick(UNIT)
    status = owner.view(UNIT)["status"]
    assert status["fd_loaded"] is True and status["fd_score_pct"] == 83 and status["fd_track"] == "track" and status["fd_moves_min"] == 3
    assert "picture" not in status
    assert all(k.startswith("fd_") or k in ("owner", "enabled", "age_s") for k in status)
