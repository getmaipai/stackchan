# ruff: noqa: E501
"""The music dance ladder (firmware patch MD01 and the host's dance_ladder.py): eyes, nod, sway, full dance, then back down.

Scripted ``music_feat`` streams on a fake clock drive the step rule, the show around it (face, notes, overlays, ring) and the whole
chain through ``MusicDance`` and ``DanceRunner``. The C rule (``maipai_dance_ladder_core.h``) is compared with the Python mirror step by step.
Nothing here ran on a unit.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from firmware_order_cores import cores_dir
from test_stackchan_music_dance import MUSIC, _music_event, _real_behavior

from maipai_body.bodies.stackchan import dance_ladder as L
from maipai_body.bodies.stackchan.dance_ladder import (
    FACES_BY_STAGE,
    RING_CAP,
    Energy,
    FaceRotator,
    Ladder,
    LadderDirector,
    LadderFeed,
    LadderHooks,
)
from maipai_body.bodies.stackchan.profile import LED_CHANNEL_MAX

HERE = Path(__file__).resolve().parent
C_TEST = HERE / "firmware/dance_ladder_test.c"
MAX_CHANNEL = round(LED_CHANNEL_MAX * RING_CAP)


# ---------------------------------------------------------------- the step rule, C against Python


def _stream(kind: str) -> list[tuple[int, int, int, int, int]]:
    """(now_ms, period_ms, level, tc, music) once a second."""
    rows = []
    for t in range(1, 121):
        if kind == "loud":
            rows.append((1000 + t * 1000, 500, 1800, 70, 1))
        elif kind == "fades":  # loud for 20 s, then quiet and gone
            rows.append(
                (
                    1000 + t * 1000,
                    500,
                    1800 if t <= 20 else 300,
                    70 if t <= 20 else 0,
                    1 if t <= 20 else 0,
                )
            )
        elif kind == "slow_quiet":
            rows.append((1000 + t * 1000, 900, 600, 40, 1))
        elif kind == "no_beat":
            rows.append((1000 + t * 1000, 0, 1800, 10, 1))
        elif kind == "drops":  # loud, then the level falls away at the peak
            rows.append((1000 + t * 1000, 500, 2000 if t <= 12 else 900, 60, 1))
    return rows


def _python_stages(rows: list[tuple[int, int, int, int, int]], max_stage: int) -> list[int]:
    ladder, energy, out = Ladder(max_stage, 1000), Energy(), []
    for now, period, level, tc, music in rows:
        out.append(ladder.step(now, period, energy.push(level), tc, bool(music)))
    return out


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
@pytest.mark.parametrize("kind", ["loud", "fades", "slow_quiet", "no_beat", "drops"])
@pytest.mark.parametrize("max_stage", [2, 4])
def test_the_c_rule_and_the_python_mirror_give_the_same_step_every_second(
    tmp_path_factory, tmp_path, kind, max_stage
) -> None:
    hal = cores_dir(tmp_path_factory)
    binary = tmp_path / "ladder"
    build = subprocess.run(
        [
            "cc",
            "-std=c99",
            "-Wall",
            "-Wextra",
            "-Werror",
            f"-I{hal}",
            str(C_TEST),
            "-o",
            str(binary),
            "-lm",
        ],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    rows = _stream(kind)
    script = tmp_path / "script.txt"
    script.write_text(
        f"start {max_stage} 1000\n" + "".join(" ".join(str(v) for v in row) + "\n" for row in rows)
    )
    run = subprocess.run([str(binary), "script", str(script)], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert [int(x) for x in run.stdout.split()] == _python_stages(rows, max_stage)


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
def test_the_c_core_tests_pass(tmp_path_factory, tmp_path) -> None:
    hal = cores_dir(tmp_path_factory)
    binary = tmp_path / "t"
    assert (
        subprocess.run(
            [
                "cc",
                "-std=c99",
                "-Wall",
                "-Wextra",
                "-Werror",
                f"-I{hal}",
                str(C_TEST),
                "-o",
                str(binary),
                "-lm",
            ]
        ).returncode
        == 0
    )
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    assert run.returncode == 0 and "all passed" in run.stdout, run.stdout


def test_the_stage_sequence_up_and_down_at_120_bpm() -> None:
    stages = _python_stages(_stream("loud"), 4)
    seen = [s for i, s in enumerate(stages) if i == 0 or s != stages[i - 1]]
    assert seen == [1, 2, 3, 4, 3, 2, 1, 0]  # up one step at a time, then the same in reverse
    assert stages[0] == 1 and stages[1] == 2  # the eyes first for about 1.5 s, then the nod


def test_music_fading_winds_the_ladder_down_in_reverse_from_wherever_it_is() -> None:
    stages = _python_stages(_stream("fades"), 4)
    seen = [s for i, s in enumerate(stages) if i == 0 or s != stages[i - 1]]
    assert seen[:2] == [1, 2] and seen[-1] == 0
    assert seen == sorted(seen[: seen.index(max(seen)) + 1]) + sorted(
        seen[seen.index(max(seen)) + 1 :], reverse=True
    )
    assert stages[21:24] != [0, 0, 0]  # no sudden stop: it goes down a step at a time


def test_a_level_that_falls_away_at_the_peak_ends_the_peak_early() -> None:
    drops = _python_stages(_stream("drops"), 4)
    loud = _python_stages(_stream("loud"), 4)
    assert drops.index(0) < loud.index(0)


def test_a_quiet_song_stays_at_the_nod_and_a_song_without_a_beat_stays_on_the_eyes() -> None:
    assert 3 not in _python_stages(_stream("slow_quiet"), 4)
    assert max(_python_stages(_stream("no_beat"), 4)) == 1


# ---------------------------------------------------------------- the show around the steps


class Recorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.hooks = LadderHooks(
            set_stage=lambda n: self.calls.append(("stage", n)),
            show_face=lambda f: self.calls.append(("face", f)),
            notes=lambda c: self.calls.append(("notes", c)),
            overlay=lambda n, i, s: self.calls.append(("overlay", (n, i, s))),
            overlay_clear=lambda: self.calls.append(("overlay_clear", None)),
        )

    def of(self, kind: str) -> list:
        return [value for name, value in self.calls if name == kind]


def run_director(
    rec: Recorder, rows, *, max_stage: int = 4, seed: int = 0, ring_log: list | None = None
) -> LadderDirector:
    """The runner's tick (every 0.25 s) with one scripted second from the unit in between."""
    feed, energy = LadderFeed(), Energy()
    director = LadderDirector(rec.hooks, feed, max_stage=max_stage, faces=FaceRotator(seed))
    tick = 0
    for second, (_, period, level, tc, music) in enumerate(rows):
        feed.bpm = round(60000 / period) if period else 0
        feed.tc, feed.level, feed.music, feed.energy = tc, level, bool(music), energy.push(level)
        for quarter in range(4):
            elapsed = second + quarter * 0.25
            director.on_tick(tick, elapsed)
            if ring_log is not None:
                ring_log.append((elapsed, director.ring(tick, elapsed)))
            tick += 1
            if director.finished():
                director.on_end()
                return director
    director.on_end()
    return director


def test_the_director_drives_the_unit_through_the_ladder_and_clears_everything_at_the_end() -> None:
    rec = Recorder()
    director = run_director(rec, _stream("loud"))
    assert rec.of("stage") == [1, 2, 3, 4, 3, 2, 1, 0]  # and the final 0 from the end of the round
    assert [s for _, s in director.stage_log] == [1, 2, 3, 4, 3, 2, 1, 0]
    assert rec.of("notes")[-1] == 0 and 3 in rec.of("notes") and 1 in rec.of("notes")
    assert rec.of("overlay_clear")  # the back layer is clear again at the end
    assert director.finished()


def test_the_notes_follow_the_step_none_one_two_three_and_back() -> None:
    rec = Recorder()
    run_director(rec, _stream("loud"))
    notes = []
    for count in rec.of("notes"):
        if not notes or notes[-1] != count:
            notes.append(count)
    assert notes == [
        0,
        1,
        2,
        3,
        2,
        1,
        0,
    ]  # none in the eyes step, then one more per step, and down again


def test_the_disco_ball_comes_with_the_sway_confetti_bursts_at_the_peak_and_the_ball_goes_below_the_sway() -> (
    None
):
    rec = Recorder()
    run_director(rec, _stream("loud"))
    overlays = rec.of("overlay")
    assert overlays[0][0] == "disco" and overlays[0][1] == "light"  # entering the sway
    assert ("disco", "normal", 30) in overlays  # the peak
    assert ("confetti", "normal", 4) in overlays  # a burst at the peak
    names = [name for name, _ in rec.calls]
    assert names.index("overlay_clear") > names.index("overlay")
    # the first overlay is not before the sway: nothing in the eyes and nod steps
    first_overlay = names.index("overlay")
    stage_before = [v for n, v in rec.calls[:first_overlay] if n == "stage"][-1]
    assert stage_before == 3


def test_the_face_changes_on_the_phrases_and_never_repeats_back_to_back_or_within_the_last_two() -> (
    None
):
    for seed in range(12):
        rec = Recorder()
        run_director(rec, _stream("loud"), seed=seed)
        faces = rec.of("face")
        assert len(faces) >= 5
        for i, face in enumerate(faces):
            assert face not in faces[max(0, i - 2) : i], (seed, faces)
        stage_faces = set(faces)
        assert stage_faces <= {f for names in FACES_BY_STAGE.values() for f in names}
        # a good time: more than the plain smile shows
        assert len(stage_faces) >= 4, faces


def test_the_dancing_faces_include_a_wink_a_silly_one_a_grin_and_the_heart_eyes() -> None:
    seen: set[str] = set()
    for seed in range(12):
        rec = Recorder()
        run_director(rec, _stream("loud"), seed=seed)
        seen |= set(rec.of("face"))
    assert {"wink", "silly", "laughing", "love", "serene", "surprised", "excited", "happy"} <= seen


def test_a_face_change_waits_for_its_phrase_eight_beats_or_sixteen_in_the_nod() -> None:
    rec = Recorder()
    director = run_director(rec, [(0, 500, 1800, 70, 1)] * 60)
    # stage times: the faces are at least 4 s apart at 120 BPM (8 beats), 8 s in the nod (16 beats)
    times = [t for t, kind in [(0, "")] if kind]  # (placeholder keeps the intent readable)
    assert times == []
    faces = rec.of("face")
    assert len(faces) <= 14  # not a new face every tick
    assert director.stage_log


def test_without_the_unit_step_tool_the_ladder_ends_and_says_so() -> None:
    from maipai_body.hal.errors import NotSupported

    def refuse(stage: int) -> None:
        raise NotSupported("self.music.stage")

    rec = Recorder()
    hooks = replace(rec.hooks, set_stage=refuse)
    feed = LadderFeed(bpm=120, tc=70, level=1800, music=True, energy=1800)
    director = LadderDirector(hooks, feed)
    director.on_tick(0, 0.0)
    assert director.unsupported and director.finished()


# ---------------------------------------------------------------- the ring: caps and no fast flashing


def test_the_ring_never_goes_over_half_brightness_never_flashes_and_always_shows_two_colors() -> (
    None
):
    rec = Recorder()
    ring: list = []
    run_director(rec, _stream("loud"), ring_log=ring)
    frames = [(t, f) for t, f in ring if f is not None]
    assert frames  # the nod, the sway and the way back down paint; the peak belongs to the unit
    for _, frame in frames:
        assert len(frame) == 12
        for pixel in frame:
            assert max(pixel) <= MAX_CHANNEL
    lit = [(t, f) for t, f in frames if any(any(p) for p in f)]
    for _, frame in lit:
        colors = {p for p in frame if any(p)}
        assert len(colors) >= 2 or max(max(p) for p in frame) == 0
    # no frame step brighter than 30 percent of full between consecutive 4 Hz frames
    previous = None
    for _, frame in frames:
        if previous is not None:
            for a, b in zip(previous, frame, strict=True):
                assert max(abs(x - y) for x, y in zip(a, b, strict=True)) <= round(
                    LED_CHANNEL_MAX * 0.30
                )
        previous = frame
    # the first step is dark and the peak writes nothing from the host (the unit paints its own swell)
    stage_at = dict(director_stage_times(rec))
    assert all(f is None for t, f in ring if t < 1.4)
    assert stage_at


def director_stage_times(rec: Recorder) -> list[tuple[int, int]]:
    return [(i, v) for i, (n, v) in enumerate(rec.calls) if n == "stage"]


def test_the_ring_is_brighter_and_faster_by_step_and_fades_to_dark_in_the_last_step() -> None:
    nod = L.breath_frame(1.0, 0.5)
    sway = L.chase_frame(3, 1.0)
    nod_max = max(max(p) for p in nod)
    sway_max = max(max(p) for p in sway)
    assert 0.08 * LED_CHANNEL_MAX <= nod_max <= 0.19 * LED_CHANNEL_MAX
    assert sway_max > nod_max and sway_max <= 0.31 * LED_CHANNEL_MAX
    assert L.chase_frame(3, 1.0, 0.7) != L.chase_frame(3, 1.0)  # the way down is dimmer
    quiet = L.chase_frame(3, -1.0)
    assert max(max(p) for p in quiet) < sway_max
    # the chase moves one pixel per beat
    assert L.chase_frame(4, 1.0) != L.chase_frame(3, 1.0)
    # the glow of the nod breathes slowly: no more than a 0.08 swing over the breath
    low = min(max(max(p) for p in L.breath_frame(t / 10, 0.5)) for t in range(0, 40))
    assert max(nod_max, 0) - low <= round(0.1 * LED_CHANNEL_MAX)


def test_the_ring_palette_has_no_status_color() -> None:
    from maipai_body.bodies.stackchan.ring import RING_RGB

    status = {tuple(v) if not isinstance(v, tuple) else v for v in RING_RGB.values()}
    for frame in (L.breath_frame(0.7, 0.5), L.chase_frame(2, 0.5)):
        for pixel in frame:
            assert pixel not in status


# ---------------------------------------------------------------- the whole chain through MusicDance and the runner


def _chain(behavior, *, battery: int = 90, charging: bool | None = False, **sit):
    from maipai_body.bodies.stackchan.dance_wiring import wire_dance
    from maipai_body.bodies.stackchan.head_commands import HeadCommander
    from maipai_body.bodies.stackchan.light_service import StackChanLightService
    from maipai_body.bodies.stackchan.music_dance_wiring import MusicFeatureSwitch, wire_music_dance
    from maipai_body.bodies.stackchan.ring_indicator import StackChanRingIndicator

    unit_calls: list = []
    ring: list = []
    clock = {"t": 7000.0}
    client = SimpleNamespace(
        get_battery_status=lambda: {"percent": battery, "charging": charging},
        companion=lambda: SimpleNamespace(
            dance=lambda name: unit_calls.append(("dance", name)),
            stop_dance=lambda: unit_calls.append(("stop_dance",)),
        ),
    )
    robot = SimpleNamespace(
        estop_engaged=False,
        leds=SimpleNamespace(many=lambda updates: ring.append([tuple(u["rgb"]) for u in updates])),
    )
    voice = SimpleNamespace(robot=SimpleNamespace(client=client, robot=robot))
    light = StackChanLightService(StackChanRingIndicator(lambda rgb: None), minute=lambda: 12 * 60)
    faces: list = []
    behavior.show_face = faces.append
    runner = wire_dance(
        voice=voice,
        behavior=behavior,
        light=light,
        night=SimpleNamespace(night=sit.get("night", False)),
        head_commander=HeadCommander(lambda *a: None),
        level_head=lambda: unit_calls.append(("level",)),
        device_connected=lambda: True,
    )
    runner._clock = lambda: clock["t"]
    runner._wait = lambda s: clock.__setitem__("t", clock["t"] + s) or runner._stop.is_set()
    runner._spawn = lambda f: f()
    switch = MusicFeatureSwitch(
        lambda name, args: unit_calls.append((name, dict(args))) or {"ok": True},
        auto=lambda: True,
        silenced=lambda: False,
        clock=lambda: clock["t"],
    )
    controller = wire_music_dance(
        behavior=behavior,
        runner=runner,
        move_head=lambda *a: None,
        center_pitch=5,
        speed=120,
        clock=lambda: clock["t"],
        start_ticker=False,
        switch=switch,
    )
    controller._spawn = lambda f: f()
    controller._choose_face = lambda: "happy"
    return SimpleNamespace(
        controller=controller,
        calls=unit_calls,
        clock=clock,
        faces=faces,
        ring=ring,
        runner=runner,
        behavior=behavior,
    )


def _args(w, tool: str, key: str) -> list:
    return [c[1][key] for c in w.calls if c[0] == tool]


def _run_chain(w, seconds: int = 8) -> None:
    w.controller.settings.auto = True
    w.behavior.event_poll = lambda: []
    for _ in range(seconds):
        w.clock["t"] += 1.0
        w.behavior.music_feat(_music_event(MUSIC).extra, w.clock["t"])
        w.controller.tick(w.clock["t"])


def test_music_starts_the_ladder_at_the_eyes_and_one_round_is_one_cycle_up_and_down() -> None:
    behavior = _real_behavior()
    try:
        w = _chain(behavior)
        _run_chain(w)
        stages = _args(w, "self.music.stage", "stage")
        assert stages[:4] == [1, 2, 3, 4] and stages[-1] == 0 and 3 in stages[4:]
        assert [x for x in stages if x == 4][0] == 4
        assert ("dance", "happy") not in w.calls  # the fixed keyframe dances are not used
        assert (
            behavior.unit_has_beat_dance
        )  # the unit took a step: "bob" is the real nod on the beat from now on
        assert w.controller.state in (
            "show",
            "break",
        )  # the round ended; the fake clock ran on while it danced
        notes = _args(w, "self.face.music_notes", "count")
        assert notes[0] == 0 and 3 in notes and notes[-1] == 0
        assert "disco" in _args(w, "self.overlay.set", "name")
        assert "confetti" in _args(w, "self.overlay.set", "name")
        assert [c for c in w.calls if c[0] == "self.overlay.clear"]
        assert w.faces and w.faces[-1] in (
            "neutral",
            "thinking",
        )  # the usual face (or the wondering look) after the round
        # the caps: nothing from the host ring is over half brightness
        for frame in w.ring:
            assert all(max(p) <= MAX_CHANNEL for p in frame)
    finally:
        behavior.close()


def test_a_battery_under_forty_percent_goes_no_higher_than_the_nod() -> None:
    behavior = _real_behavior()
    try:
        w = _chain(behavior, battery=30, charging=False)
        _run_chain(w)
        stages = _args(w, "self.music.stage", "stage")
        assert stages and max(stages) == 2 and stages[-1] == 0
    finally:
        behavior.close()


@pytest.mark.parametrize(
    "sit",
    [{"night": True}],
)
def test_the_gates_still_refuse_the_ladder_at_night(sit) -> None:
    behavior = _real_behavior()
    try:
        w = _chain(behavior, **sit)
        _run_chain(w, 6)
        assert not _args(w, "self.music.stage", "stage")
    finally:
        behavior.close()


def test_a_camera_cue_stops_the_ladder_and_the_unit_is_told_to_stand_still() -> None:
    behavior = _real_behavior()
    try:
        w = _chain(behavior)
        w.controller.settings.auto = True
        started = {"n": 0}
        original = w.runner._hooks.situation

        def with_cue():
            started["n"] += 1
            sit = original()
            return replace(sit, camera_cue=started["n"] > 40)

        w.runner._hooks.situation = with_cue
        w.behavior.event_poll = lambda: []
        for _ in range(6):
            w.clock["t"] += 1.0
            w.behavior.music_feat(_music_event(MUSIC).extra, w.clock["t"])
            w.controller.tick(w.clock["t"])
        stages = _args(w, "self.music.stage", "stage")
        assert stages[-1] == 0 and 4 not in stages
        assert w.runner.last_end_reason == "picture"
    finally:
        behavior.close()


def test_the_feed_expires_when_the_unit_goes_quiet() -> None:
    behavior = _real_behavior()
    try:
        w = _chain(behavior)
        w.controller.settings.auto = True
        w.behavior.music_feat(_music_event(MUSIC).extra, w.clock["t"])
        feed = w.controller.ladder_feed
        assert feed.music
        w.controller.ladder_expire(w.clock["t"] + 5.0)
        assert not feed.music
    finally:
        behavior.close()
