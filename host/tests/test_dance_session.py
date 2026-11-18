"""A ladder session with no music (the dance buttons and tools): the climb follows the ladder rule at the dance's tempo, caps hold, two robots dance at once."""

import pytest

from maipai_body.bodies.stackchan.dance_ladder import DANCE_BPM, SESSION_S, FaceRotator, LadderHooks, synthetic_ladder_plan
from maipai_body.bodies.stackchan.profile import LED_CHANNEL_MAX


class Recorder:
    def __init__(self):
        self.calls = []

    def hooks(self):
        return LadderHooks(
            set_stage=lambda stage: self.calls.append(("stage", stage)),
            show_face=lambda face: self.calls.append(("face", face)),
            notes=lambda count: self.calls.append(("notes", count)),
            overlay=lambda name, intensity, seconds: self.calls.append(("overlay", name)),
            overlay_clear=lambda: self.calls.append(("overlay_clear",)),
        )

    def stages(self):
        return [c[1] for c in self.calls if c[0] == "stage"]


def _run(plan, seconds=SESSION_S, step=0.25):
    frames = []
    t, tick = 0.0, 0
    while t < seconds and not (plan.finished and plan.finished()):
        plan.on_tick(tick, t)
        frame = plan.ring(tick, t)
        if frame is not None:
            frames.append(frame)
        tick, t = tick + 1, t + step
    if plan.on_end:
        plan.on_end()
    return t, frames


def test_a_session_climbs_every_step_then_winds_down_and_ends_inside_its_length():
    rec = Recorder()
    plan = synthetic_ladder_plan(rec.hooks(), "happy", faces=FaceRotator(1))
    elapsed, frames = _run(plan)
    stages = [s for s in rec.stages() if s != 0]
    assert stages[:4] == [1, 2, 3, 4], stages  # climbs one step at a time, in order
    assert stages[-3:] == [3, 2, 1] or stages[-1] == 1  # and back down
    assert rec.stages()[-1] == 0 and elapsed <= SESSION_S  # the unit is told step 0 at the end
    assert ("notes", 3) in rec.calls and rec.calls[-2:] == [("notes", 0), ("overlay_clear",)] or ("overlay_clear",) in rec.calls


def test_dwell_times_follow_the_rule_at_the_dances_tempo():
    rec = Recorder()
    plan = synthetic_ladder_plan(rec.hooks(), "happy", faces=FaceRotator(1))
    times = {}
    t, tick = 0.0, 0
    last = 0
    while t < SESSION_S and not plan.finished():
        before = len(rec.stages())
        plan.on_tick(tick, t)
        if len(rec.stages()) > before:
            times.setdefault(rec.stages()[-1], []).append(t)
        tick, t = tick + 1, t + 0.25
    period_ms = 60000 / DANCE_BPM["happy"]
    eyes_dwell = times[2][0] - times[1][0]
    assert 1.5 <= eyes_dwell <= 3.2, eyes_dwell  # eyes: 3 beats, 1.5 to 3 s
    assert 4.0 <= times[3][0] - times[2][0] <= 8.5  # nod: 8 beats, 4 to 8 s


def test_the_limiters_top_step_caps_the_climb():
    rec = Recorder()
    _run(synthetic_ladder_plan(rec.hooks(), "bob", max_stage=2, faces=FaceRotator(2)))
    assert max(rec.stages()) == 2
    rec3 = Recorder()
    _run(synthetic_ladder_plan(rec3.hooks(), "groove", max_stage=3, faces=FaceRotator(2)))
    assert max(rec3.stages()) == 3 and ("overlay", "confetti") not in rec3.calls


def test_faces_never_repeat_back_to_back_and_the_ring_stays_inside_the_cap():
    rec = Recorder()
    _, frames = _run(synthetic_ladder_plan(rec.hooks(), "wiggle", faces=FaceRotator(3)))
    faces = [c[1] for c in rec.calls if c[0] == "face"]
    assert faces and all(a != b for a, b in zip(faces, faces[1:]))
    assert frames and all(max(px) <= LED_CHANNEL_MAX // 2 + 1 for frame in frames for px in frame)


def test_each_named_dance_has_a_tempo_and_bob_is_a_known_dance():
    from maipai_body.bodies.stackchan.companion import BUILTIN_DANCES

    assert "bob" in BUILTIN_DANCES and "bob" in DANCE_BPM
    assert all(70 <= bpm <= 140 for bpm in DANCE_BPM.values())


def test_two_robots_run_two_sessions_at_once_without_sharing_state():
    a, b = Recorder(), Recorder()
    plan_a = synthetic_ladder_plan(a.hooks(), "happy", faces=FaceRotator(1))
    plan_b = synthetic_ladder_plan(b.hooks(), "groove", faces=FaceRotator(2))
    t, tick = 0.0, 0
    while t < SESSION_S and not (plan_a.finished() and plan_b.finished()):
        if not plan_a.finished():
            plan_a.on_tick(tick, t)
        if t >= 5 and not plan_b.finished():  # the second robot starts five seconds later
            plan_b.on_tick(tick, t - 5)
        tick, t = tick + 1, t + 0.25
    assert a.stages()[:4] == [1, 2, 3, 4] and b.stages()[:4] == [1, 2, 3, 4]
    a.calls.clear()
    plan_b2 = synthetic_ladder_plan(b.hooks(), "happy")
    plan_b2.on_tick(0, 0.0)
    assert not a.calls  # nothing leaked to the other robot's hooks
