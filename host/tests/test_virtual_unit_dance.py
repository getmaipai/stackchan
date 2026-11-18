# ruff: noqa: E501
"""The music dance in the virtual unit (scripts/virtual-unit/dance_sim.py): the unit's real ladder core (firmware patch MD01) on simulated songs, the beat dance modifier ported, the host's show
around it. The step order, dwell times, climb thresholds and the head budget are checked against docs/design/dance-ladder-2026-11-17.md; the keyframe dances against the firmware's table (dance.h).
Needs the screens renderer (scripts/virtual-unit/build-screens.sh). Nothing here ran on a unit."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VU = ROOT / "scripts" / "virtual-unit"
sys.path.insert(0, str(VU))

pytestmark = pytest.mark.skipif(not (ROOT / ".runs" / "vu-screens" / "render").exists(), reason="screens renderer not built")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, VU / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


vunit = _load("vunit")


def _unit():
    return vunit.VirtualUnit(profile="screens")


def _run(song, mode, seconds, **kw):
    """A session of `seconds` on a fresh unit; returns the sim and what it recorded."""
    with _unit() as u:
        u.call("sim.music", {"action": "start", "song": song, "mode": mode, **kw})
        samples = []
        for _ in range(int(seconds * 10)):
            u.advance(100)
            d = u.dance
            samples.append((u.now_ms, d.stage, list(u.leds), list(d.overlays), d.notes))
        return u.dance, samples


def _segments(log, end_s):
    """[(step, seconds)] from the step log."""
    out = []
    for i, (t, st) in enumerate(log):
        nxt = log[i + 1][0] if i + 1 < len(log) else end_s
        out.append((st, nxt - t))
    return out


def test_the_core_is_the_patchs_own_header():
    import dance_core

    text = (ROOT / "firmware" / "patches" / "MD01-music-dance-ladder-and-beat-dance.patch").read_text()
    header = dance_core.extract_header().read_text()
    assert "mdl_step" in header and "mdl_pose" in header
    assert "+static inline int mdl_step(" in text   # the same function the patch adds, not a copy of the rule
    L = dance_core.lib()
    assert L.sim_consts(1) == 90   # MDL_BUDGET_MOVES
    assert L.sim_dwell(4, 0, 500) == 12000 and L.sim_dwell(1, 0, 500) == 1500 and L.sim_dwell(2, 1, 500) == 2000


def test_steps_climb_in_order_one_at_a_time_and_come_down_in_reverse():
    d, _ = _run("loud_peak", "unit", 40)
    steps = [s for _, s in d.stage_log]
    assert steps[:7] == [1, 2, 3, 4, 3, 2, 1]
    assert steps[7] == 0   # the cycle ends
    for a, b in zip(steps, steps[1:]):
        assert abs(a - b) == 1 or 0 in (a, b), (a, b)   # a step never skips


def test_dwell_times_follow_the_doc():
    d, _ = _run("loud_peak", "unit", 40)
    seg = _segments(d.stage_log, 40.0)
    eyes, nod, sway, full = seg[0][1], seg[1][1], seg[2][1], seg[3][1]
    assert 1.5 <= eyes <= 3.5          # eyes: 3 beats, 1.5 to 3 s (the rule runs once a second)
    assert 4.0 <= nod <= 9.0 and 4.0 <= sway <= 9.0   # nod and sway: 8 beats, 4 to 8 s
    assert 12.0 <= full <= 23.0        # the peak: 24 beats, 12 to 20 s, then the first step of the way down
    down = [s for st, s in seg[4:7]]
    assert all(2.0 <= x <= 5.0 for x in down)   # the way down: 4 beats, 2 to 4 s each


def test_climb_thresholds_a_quiet_or_slow_song_stays_where_it_is():
    d, _ = _run("quiet", "unit", 30)   # level 250, tempo confidence 25: the nod needs 20, the sway needs 800 and 30
    assert max(s for _, s in d.stage_log) == 2
    d, _ = _run("slow", "unit", 30)    # level 700, confidence 40: the sway needs level 800
    assert max(s for _, s in d.stage_log) == 2
    d, _ = _run("fast", "unit", 40)    # level 1200, confidence 60: the full dance needs 1000 and 35
    assert max(s for _, s in d.stage_log) == 4


def test_the_music_stopping_starts_the_way_down_at_once():
    d, _ = _run("fades", "unit", 45)
    log = d.stage_log
    first_down = next(i for i in range(1, len(log)) if log[i][1] < log[i - 1][1])
    assert 23 <= log[first_down][0] <= 20 + 1 + 3 + 4   # the music is gone from 21 s; 3 s with none starts the way down, and the full step shows one dwell (2 to 4 s) more
    assert [s for _, s in log[first_down:first_down + 3]] == [3, 2, 1] or [s for _, s in log[first_down:first_down + 4]][-1] == 0


def test_eyes_every_beat_the_head_still_in_step_one_and_at_most_once_a_beat_after():
    d, _ = _run("loud_peak", "unit", 40)
    beats = d.beats
    eyes_only = [b for b in beats if b["step"] == 1]
    assert eyes_only and all(not b["moved"] for b in eyes_only)       # the head stays still in step 1
    assert all(b["eye"][0] in (-100, 100) for b in eyes_only)         # side to side, 10 px (100 units), every beat
    xs = [b["eye"][0] for b in eyes_only]
    assert all(a != b for a, b in zip(xs, xs[1:]))                    # the side flips every beat
    nods = [b for b in beats if b["step"] == 2 and b["moved"]]
    assert nods and all(b["eye"][0] in (-40, 40) for b in beats if b["step"] == 2)   # the eyes follow with a small shift
    assert sum(1 for b in beats if b["moved"]) <= len(beats)


def test_the_head_moves_every_second_beat_above_133_bpm_and_never_over_90_a_minute():
    d, _ = _run("very_fast", "unit", 50)   # 280 BPM folds to 140: a 428 ms beat
    full = [b for b in d.beats if b["step"] >= 3]
    assert full and all(b["period"] < 450 for b in full)
    moved = [b for b in full if b["moved"]]
    assert 0.4 <= len(moved) / len(full) <= 0.6        # every second beat
    times = d.head_moves
    for t in times:
        assert sum(1 for x in times if t <= x < t + 60000) <= 90   # never more than 90 moves in any minute
    d2, _ = _run("fast", "unit", 120)
    for t in d2.head_moves:
        assert sum(1 for x in d2.head_moves if t <= x < t + 60000) <= 90


def test_the_ring_is_dark_until_the_peak_and_never_over_half_of_full():
    d, samples = _run("loud_peak", "unit", 40)   # unit alone: only the peak paints the ring
    for _, stage, leds, _, _ in samples:
        if stage < 4:
            assert all(px == (0, 0, 0) for px in leds)
        assert all(max(px) <= 84 for px in leds)     # half of the channel maximum 168
    assert any(stage == 4 and any(px != (0, 0, 0) for px in leds) for _, stage, leds, _, _ in samples)
    colors = {px for _, st, leds, _, _ in samples if st == 4 for px in leds}
    assert len(colors) > 3                              # gold, lime and mint at the swell's levels


def test_the_hosts_show_adds_ring_overlays_notes_and_faces_by_step():
    d, samples = _run("loud_peak", "home", 33)
    by = {}
    for _, stage, leds, overlays, notes in samples:
        by.setdefault(stage, []).append((leds, overlays, notes))
    assert all(px == (0, 0, 0) for leds, _, _ in by[1][:5] for px in leds)          # step 1: dark ring, no overlay
    assert not any("disco" in o for _, o, _ in by[1] + by[2])                        # no disco ball before the sway
    assert any(any(px != (0, 0, 0) for px in leds) for leds, _, _ in by[2])          # the nod: a slow breath
    assert any("disco" in o for _, o, _ in by[3]) and any("disco" in o for _, o, _ in by[4])   # disco ball from the sway on
    assert any("confetti" in o for _, o, _ in by[4])                                  # confetti at the peak
    assert max(n for _, _, n in by[4]) == 3 and max(n for _, _, n in by[2]) >= 1      # notes grow with the step
    assert all(max(px) <= 84 for _, _, leds in [(0, 0, x) for x in [s[2] for s in samples]] for px in leds)
    faces = {d.face}
    assert faces and d.face != "neutral"


def test_the_screen_draws_the_overlays_the_eyes_and_the_notes(tmp_path):
    with _unit() as u:
        u.call("sim.music", {"action": "start", "song": "loud_peak", "mode": "home"})
        u.advance(13300)   # the peak: the disco ball, confetti and three notes
        peak = u.snapshot()
        u.call("sim.music", {"action": "stop"})
        u.advance(600)
        rest = u.snapshot()
    assert peak != rest
    assert u.dance.overlays == [] and u.dance.notes == 0 and u.dance.eye == (0, 0)   # stopping clears them and turns the eyes ahead


def test_stop_dance_and_a_lift_end_the_dance_and_bob_is_the_nod():
    with _unit() as u:
        assert u.call("self.robot.dance", {"name": "bob"}).get("ok")   # patch MD01: bob is step 2 until stopped
        u.advance(3000)
        assert u.dance.stage == 2 and u.dance.beats       # a steady 600 ms beat with no song
        u.call("self.robot.stop_dance", {})
        u.advance(500)
        assert u.dance.stage == 0 and u.dance.eye == (0, 0) and u.head()["yaw"] == 0 and u.head()["pitch"] <= 3
        u.call("sim.music", {"action": "start", "song": "fast", "mode": "unit"})
        u.advance(5000)
        assert u.dance.stage >= 1
        u.call("self.motion.force", {"carried": 1})        # held: the limiter allows no movement and the dance ends (patch ML01)
        u.advance(300)
        assert u.dance.stage == 0


def test_muted_or_quiet_refuses_the_music_dance():
    with _unit() as u:
        from tools.audio import _state

        _state(u)["privacy"]["muted"] = 1
        u.call("sim.music", {"action": "start", "song": "fast", "mode": "unit"})
        u.advance(3000)
        assert u.dance.stage == 0


def test_keyframe_dances_play_the_firmwares_table():
    import hw

    assert hw.dance_ms("happy") == 4200 and hw.dance_ms("robot") == 2700 and hw.dance_ms("look_around") == 7500 and hw.dance_ms("panic") == 1100
    yaws = [hw.dance_offset("happy", t, 100, 1000)[0] for t in range(0, 4300, 100)]
    assert max(yaws) == 30.0 and min(yaws) == -30.0 and yaws[0] == 0.0 and abs(yaws[-1]) < 2.0      # sways 30 degrees each way and ends centered
    assert max(hw.dance_offset("robot", t, 100, 1000)[0] for t in range(0, 2700, 50)) == 45.0
    assert max(hw.dance_offset("look_around", t, 100, 1000)[0] for t in range(0, 7500, 50)) >= 55.0
    half = max(abs(hw.dance_offset("happy", t, 50, 1000)[0]) for t in range(0, 4200, 100))
    assert half == 15.0                                                                                # the USB limiter halves the excursion
    with _unit() as u:
        assert u.call("self.robot.dance", {"name": "happy"}).get("ok")
        u.advance(1200)
        assert u.dance.eye[0] == -10 or u.dance.eye[0] == 10        # the eyes follow the table's keyframes
        u.advance(4000)
        assert u.dance.kf is None                                    # the dance is over and the eyes are ahead
