"""Wire the little dance (dance.py) to a running StackChan service.

One function, ``wire_dance``, so the service's own wiring in app.py stays a few lines: it builds the
runner from the live robot, light service, night rule and behavior, then hooks the two triggers
(the spoken ask through ``HeadCommander`` and the hub's "dance" device command through
``behavior.dance_command``; ``behavior.dance_events`` only ends a running dance) and tells the
behavior when a dance is running so the ambient head moves, the face watchdog and the look-around
stay out of its way.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import replace
from typing import Any

from maipai_body.bodies.stackchan.dance_ladder import FaceRotator, LadderHooks, UnitSessionPlan, synthetic_ladder_plan
from maipai_body.bodies.stackchan.dance import (
    LED_COUNT,
    DanceHooks,
    DanceRunner,
    DanceSituation,
)

logger = logging.getLogger("maipai_body.bodies.stackchan.dance_wiring")
UNIT_DANCE_ALIASES = {"bob": "nod_yes"}

BATTERY_TTL_S = 5.0  # the battery is read over the link; a dance checks it every quarter second


def wire_dance(
    *,
    voice: Any,
    behavior: Any,
    light: Any,
    night: Any,
    head_commander: Any,
    level_head: Callable[[], object],
    device_connected: Callable[[], bool],
    # HOOK: no muted or full-quiet flag exists in the settings registry yet (the modes are being
    # designed). Return a plain reason ("muted", "full quiet") while one is on, else None.
    full_quiet_reason: Callable[[], str | None] = lambda: None,
    # Called once as a dance starts (the start chime, bodies/stackchan/sounds.py); never raises.
    on_start: Callable[[], object] | None = None,
) -> DanceRunner:
    battery: dict[str, Any] = {"at": float("-inf"), "percent": None, "charging": None}

    def read_battery() -> None:
        now = time.monotonic()
        if now - battery["at"] < BATTERY_TTL_S:
            return
        battery["at"] = now
        try:
            status = voice.robot.client.get_battery_status()
            percent, charging = status.get("percent"), status.get("charging")
            battery["percent"] = (
                percent if isinstance(percent, int) and not isinstance(percent, bool) else None
            )
            battery["charging"] = charging if isinstance(charging, bool) else None
        except Exception:
            battery["percent"] = None  # unknown: a dance on battery is refused
            battery["charging"] = None

    def situation() -> DanceSituation:
        read_battery()
        facts = light.facts
        limit = getattr(behavior, "motion_limit", None)
        motion = limit.state() if limit is not None else None
        return DanceSituation(
            awake=behavior._rest.stage == "awake",
            night=bool(night.night),
            in_turn=behavior._active.is_set(),
            estop=bool(voice.robot.robot.estop_engaged),
            upright=not behavior.pose_held(),
            connected=bool(device_connected()),
            offline=facts.offline,
            camera_cue=facts.camera,
            live_cue=facts.live,
            battery_percent=battery["percent"],
            charging=battery["charging"],
            battery_low=facts.battery_low,
            full_quiet=full_quiet_reason(),
            muted=bool(getattr(getattr(behavior, "privacy", None), "muted", False)),
            motion=motion.state if motion is not None else "free",
            motion_dance_max=motion.dance_max if motion is not None else 4,
        )

    def write_ring(pixels: list[tuple[int, int, int]]) -> None:
        # Through the adapter, so the camera cue's pink still wins if a picture is being taken.
        voice.robot.robot.leds.many(
            [{"index": i, "rgb": list(pixels[i])} for i in range(LED_COUNT)]
        )

    def wake() -> None:
        now = time.monotonic()
        behavior._last_person_seen = now  # the rest policy treats the request as a person
        behavior.rest_step(now)

    def hold(held: bool) -> None:
        behavior._note_own_move()  # the head's own motion is not the picture changing

    companion = voice.robot.client.companion

    def start_dance(name: str) -> object:
        if on_start is not None:
            try:
                on_start()
            except Exception:  # a chime never stops a dance
                logger.warning("the dance start sound failed", exc_info=True)
        # The song phrases name the up and down nod 'bob' (the older firmware's dance); this firmware's is 'nod_yes'.
        # A unit with the beat dance (firmware MD01, known once it took a step) plays bob as the real nod on the beat; an older unit gets nod_yes.
        if name == "bob" and getattr(behavior, "unit_has_beat_dance", False):
            return companion().dance("bob")
        return companion().dance(UNIT_DANCE_ALIASES.get(name, name))

    hooks = DanceHooks(
        start_dance=start_dance,
        stop_dance=lambda: companion().stop_dance(),
        show_face=lambda expression: behavior.show_face(expression),
        write_ring=write_ring,
        take_ring=light.take_ring,
        give_ring_back=light.give_ring_back,
        level_head=level_head,
        situation=situation,
        wake=wake,
        hold=hold,
    )
    runner = DanceRunner(hooks, behavior.dance_settings)
    runners: dict[str, DanceRunner] = {}  # one dance runner per robot (decision 16): two robots can dance at once, each gated by its own state
    runner_lock = threading.Lock()

    def runner_for(unit: str | None) -> DanceRunner:
        """The primary robot (and a call that names none) uses ``runner``; every other robot gets its own, with its hooks bound to that robot."""
        if not unit or unit == behavior.primary_unit() or behavior.primary_unit() is None:
            return runner
        with runner_lock:
            if unit not in runners:
                runners[unit] = DanceRunner(_bound_hooks(unit), behavior.dance_settings)
            return runners[unit]

    def _bound_hooks(unit: str) -> DanceHooks:
        from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT

        def bind(fn):
            def call(*args, **kwargs):
                token = ACTIVE_UNIT.set(unit)  # the hook's calls to the robot go to this robot
                try:
                    return fn(*args, **kwargs)
                finally:
                    ACTIVE_UNIT.reset(token)
            return call

        privacy = getattr(behavior, "privacy_units", None)

        def situation_for() -> DanceSituation:
            base = situation()
            muted = bool(privacy.state_for(unit).muted) if privacy is not None else base.muted
            return replace(base, connected=unit in voice._sessions, muted=muted)

        return DanceHooks(
            start_dance=bind(hooks.start_dance), stop_dance=bind(hooks.stop_dance), show_face=bind(hooks.show_face), write_ring=bind(hooks.write_ring),
            take_ring=hooks.take_ring, give_ring_back=hooks.give_ring_back, level_head=bind(hooks.level_head), situation=situation_for, wake=hooks.wake, hold=hooks.hold,
        )

    def ladder_call(unit: str | None, name: str, arguments: dict) -> object:
        from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT

        token = ACTIVE_UNIT.set(unit) if unit else None
        try:
            return voice.robot.client._call(name, arguments)
        finally:
            if token is not None:
                ACTIVE_UNIT.reset(token)

    def ladder_hooks_for(unit: str | None) -> LadderHooks:
        from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT

        def call(name: str, arguments: dict) -> object:
            token = ACTIVE_UNIT.set(unit) if unit else None
            try:
                return voice.robot.client._call(name, arguments)
            finally:
                if token is not None:
                    ACTIVE_UNIT.reset(token)

        return LadderHooks(
            set_stage=lambda stage: call("self.music.stage", {"stage": stage}),
            show_face=lambda expression: behavior.show_face(expression),
            notes=lambda count: call("self.face.music_notes", {"count": count}),
            overlay=lambda name, intensity, seconds: call("self.overlay.set", {"name": name, "intensity": intensity, "seconds": seconds}),
            overlay_clear=lambda: call("self.overlay.clear", {}),
        )

    def request_show(trigger: str, unit: str | None, name: str = "happy"):
        """A dance chosen by hand (a button, a tool, a spoken ask) shows the whole ladder at the dance's tempo when the robot has the beat dance
        (`self.music.stage`); a robot without it, or a limiter that allows no dances, keeps the little dance."""
        target = runner_for(unit)
        limit = getattr(behavior, "motion_limit", None)
        top = min(4, max(1, limit.state().dance_max if limit is not None else 4))
        hooks_for_unit = ladder_hooks_for(unit)
        # The robot's own ladder session (firmware SF51, `self.dance.session`) is the one implementation: used when the robot announces it in its
        # hello features (`dance_session`). Otherwise the host shows the ladder with its own session when the robot has the beat dance, and a robot
        # with neither plays the little dance.
        try:
            has_session = bool(voice.device_supports("dance_session", unit))
        except Exception:
            has_session = False
        if has_session:
            plan = UnitSessionPlan(lambda args: ladder_call(unit, "self.dance.session", args), lambda: ladder_call(unit, "self.robot.stop_dance", {}), name, top, None)
            return target.request(trigger, plan.as_plan())
        try:
            hooks_for_unit.set_stage(0)  # a harmless probe: an older robot answers unknown tool
            return target.request(trigger, synthetic_ladder_plan(hooks_for_unit, name, max_stage=top, faces=FaceRotator()))
        except Exception:
            return target.request(trigger)

    def on_events(events: list, now: float) -> None:
        runner.on_events(events, now)

    def command(payload: dict) -> dict:
        unit = str(payload.get("device_id", "")) or None if isinstance(payload, dict) else None
        reply = request_show("hub", unit, str(payload.get("name", "happy")) if isinstance(payload, dict) else "happy")
        return {"dance": "started" if reply.started else "refused", "why": reply.why}

    behavior.dance_runner_for = runner_for
    behavior.dance_active = lambda: runner.running or any(r.running for r in list(runners.values()))
    behavior.dance_events = on_events
    behavior.dance_command = command
    def spoken_dance() -> str:
        from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT

        return request_show("voice", ACTIVE_UNIT.get()).line

    head_commander.dance = spoken_dance
    return runner
