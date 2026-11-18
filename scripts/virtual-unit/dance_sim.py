"""The music dance in the virtual unit: the unit's real ladder core (firmware patch MD01) driven by a simulated song, the beat dance modifier ported line by line, and, in "home"
mode, the host's own show (dance_ladder.py: notes, ring, disco ball, confetti, faces) around it.

  unit half  maipai_dance_ladder_core.h, compiled from the patch (dance_core.py): the step rule, the pose of each step, the 90 head moves a minute, the ring swell. The unit's own
             cycle (maipai_music.cc ladder_tick) and BeatDanceModifier::_update (eyes, head, the ring at the peak) are ported here; the rule inside them is the C one.
  home half  LadderDirector from host/maipai_body/bodies/stackchan/dance_ladder.py, called as the host calls it (a step 4 times a second, the feed once a second, the same tool calls).
             With no Home reachable the unit alone shows only what the firmware shows: the eyes, the head and the ring at the peak ("unit" mode).

The song is a fake tempo and level curve (SONGS). Time is the virtual unit's fake clock: the unit calls tick() every 50 ms of it (VirtualUnit.tickers). What the screen cannot draw is listed in
docs/dev/virtual-unit-dance.md. Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import ctypes  # noqa: E402

import dance_core  # noqa: E402

TICK_MS = 66
CLOCK_BASE = 1000  # the core treats 0 as "not set": the sim's clock starts at one second, as the host director's does
SHOW_FACES = {"happy", "serene", "laughing", "love", "surprised", "wink", "silly", "excited", "neutral", "content"}


def fold_bpm(bpm: int) -> int:
    """The tempo the unit's beat grid uses: halves and doubles folded into 70 to 140 (the host's fold_bpm, the same rule)."""
    if bpm <= 0:
        return 0
    while bpm < 70:
        bpm *= 2
    while bpm > 140:
        bpm = (bpm + 1) // 2
    return bpm


# song name -> (description, function of seconds since the song began -> (bpm, level, tempo confidence, music))
def _slow(t):
    return 66, 700, 40, True


def _fast(t):
    return 150, 1200, 60, True


def _loud_peak(t):
    if t > 90:
        return 0, 0, 0, False
    up = min(1.0, t / 20.0)
    down = 1.0 if t < 70 else max(0.0, 1.0 - (t - 70) / 10.0)
    return 120, int(300 + 1700 * up * down), 70, True


def _very_fast(t):
    return 280, 1800, 70, True


def _quiet(t):
    return 90, 250, 25, True


def _fades(t):
    return (120, 1800, 70, True) if t <= 20 else (0, 300, 0, False)


SONGS = {
    "slow": ("a slow song: 66 BPM, medium level, a steady beat", _slow),
    "fast": ("a fast song: 150 BPM, a loud steady beat", _fast),
    "loud_peak": ("120 BPM that builds from quiet to very loud in 20 s, holds, then fades from 70 s and stops at 90 s", _loud_peak),
    "very_fast": ("280 BPM folds to 140 (a 428 ms beat): the head moves every second beat, the eyes every beat", _very_fast),
    "quiet": ("a quiet song: 90 BPM at a level too low to climb past the nod", _quiet),
    "fades": ("loud for 20 s, then quiet and gone (the way down starts at once)", _fades),
}


class DanceSim:
    """One per VirtualUnit (u.dance). Everything it changes goes through the unit: renderer commands (gaze, face, overlay, notes), the head, the 12 lights."""

    def __init__(self, u) -> None:
        self.u = u
        self.L = dance_core.lib()
        self.h = self.L.sim_new()
        self._budget = self.L.sim_new()
        self.song_name = "fast"
        self.mode = "home"
        self.running = False  # a session (the host's or the unit's own cycle) is running
        self.stage = 0  # the step the beat dance plays (maipai_music_stage_get)
        self.song_t0 = 0
        self.max_stage = 4
        self.cycle_active = False
        self.rest_ms = 0
        self.next_second = 0
        self.next_plan = 0
        self.tick_no = 0
        self.stage_log: list[tuple[float, int]] = []  # (seconds since the session began, step)
        self.beats: list[dict] = []  # one entry per eye beat while a step plays
        self.head_moves: list[int] = []  # the clock of every head move the modifier made
        self.refused_moves = 0
        self.leds = [(0, 0, 0)] * 12
        self.ring_on = False
        self.overlays: list[str] = []
        self.notes = 0
        self.face = "neutral"
        self.eye = (0, 0)
        self.feat = {"bpm": 0, "level": 0, "tc": 0, "music": False, "avg": 0}
        self.director = None
        self.feed = None
        self.t_start = 0
        self._reset_modifier()
        self.kf = None  # a keyframe dance: (name, started ms)
        u.tickers.append(self.tick)

    # ---- the session -----------------------------------------------------------------------------------------------

    def song(self, name: str) -> None:
        if name not in SONGS:
            raise ValueError(f"unknown song {name}: use one of {sorted(SONGS)}")
        self.song_name = name
        self.song_t0 = self.u.now_ms

    def start(self, song: str | None = None, mode: str | None = None, max_stage: int = 4) -> None:
        """Start a music dance session: Home's show (mode "home") or the unit's own cycle (mode "unit"), on a simulated song."""
        if mode:
            self.mode = mode
        if song:
            self.song_name = song
        self.stop()
        u = self.u
        u.call("self.music.set", {"enabled": True})
        self.running = True
        self.song_t0 = u.now_ms
        self.t_start = u.now_ms
        self.max_stage = max_stage
        self.stage_log = []
        self.beats = []
        self.head_moves = []
        self.next_second = u.now_ms + 1000
        self.next_plan = u.now_ms
        self.tick_no = 0
        self._reset_modifier()
        self._read_feat(u.now_ms)
        if self.mode == "home":
            self._home_begin()
        else:
            self._cycle_begin(u.now_ms)

    def stop(self) -> None:
        """The dance ends (a stop, a touch, the music gone): eyes ahead, head level, lights dark, notes and overlays cleared."""
        was = self.stage
        if self.director is not None:
            try:
                self.director.on_end()
            except Exception:
                pass
        self.director = None
        self.running = False
        self.cycle_active = False
        self.rest_ms = 0
        self._set_stage(0)
        if was or self.overlays or self.notes:
            self._show_notes(0)
            self._overlay_clear()

    def keyframe_start(self, name: str) -> None:
        """A keyframe dance (happy, robot, panic, look_around) replaces a beat dance (as maipai_dance_play does); its eyes and mouth follow the table, the head follows hw.dance_offset."""
        if self.stage or self.running:
            self.stop()
        self.kf = (name, self.u.now_ms, -1)

    def bob(self) -> bool:
        """self.robot.dance bob: the nod on the beat until the dance is stopped (maipai_dance_play, patch MD01)."""
        return self._set_stage(2) == 2

    # ---- features of the simulated song -----------------------------------------------------------------------------

    def _read_feat(self, now: int) -> dict:
        t = max(0.0, (now - self.song_t0) / 1000.0)
        bpm, level, tc, music = SONGS[self.song_name][1](t)
        self.feat.update(bpm=bpm, level=level, tc=tc, music=music)
        return self.feat

    def beat(self, now: int):
        """maipai_beat_get: (period_ms, ref_ms) while a beat was measured with a confidence of at least 30 and music is on, else None."""
        f = self.feat
        if f["music"] and f["tc"] >= 30 and f["bpm"] > 0:
            return 60000 // fold_bpm(f["bpm"]), self.song_t0 + CLOCK_BASE
        return None

    # ---- the unit's step (maipai_music_stage_set) ----------------------------------------------------------------------

    def _limits(self) -> dict:
        return self.u.call("self.motion.status", {})

    def _set_stage(self, stage: int) -> int:
        """Sets the beat dance's step: refused while muted or in full quiet, clamped to what the limiter allows (carried or very low battery: none). Returns the step now."""
        u = self.u
        from tools.audio import _state as audio_state

        audio = audio_state(u)
        priv = audio["privacy"]
        refuse = stage > 0 and bool(priv.get("muted") or priv.get("quiet"))
        cap = int(self._limits().get("dance_max", 4))
        if stage > cap:
            stage = cap
        if refuse:
            stage = 0
        was = self.stage
        self.stage = stage
        if stage != was:
            self.stage_log.append((round((u.now_ms - self.t_start) / 1000.0, 2), stage))
        audio["stage"] = stage
        if stage == 0:
            if was > 0:
                self._gaze(0, 0)
                if was >= 2:
                    self._move_head(0, 0, 200)
            self._ring_dark()
            self._reset_modifier()
        elif was == 0:
            self._reset_modifier()
        return stage

    # ---- the unit's own cycle (maipai_music.cc, ladder_begin and ladder_tick) -----------------------------------------------

    def _cycle_begin(self, now: int) -> None:
        self.L.sim_start(self.h, self.max_stage, (now - self.t_start) + CLOCK_BASE)
        self.cycle_active = True
        self.rest_ms = 0
        self._set_stage(1)

    def _cycle_tick(self, now: int) -> None:
        f = self.feat
        local = (now - self.t_start) + CLOCK_BASE
        beat = self.beat(now)
        avg = ctypes.c_int(0)
        if not self.cycle_active:
            if self.rest_ms == 0:
                self.rest_ms = local or 1
            elif f["music"] and local - self.rest_ms >= 2000:
                self._cycle_begin(now)
            return
        stage = self.L.sim_tick(self.h, local, beat[0] if beat else 0, f["level"], f["tc"], 1 if f["music"] else 0, ctypes.byref(avg))
        f["avg"] = avg.value
        if stage == 0:
            self.cycle_active = False
            self.rest_ms = local or 1
            self._set_stage(0)
        elif stage != self.stage:
            self._set_stage(stage)

    # ---- the host's show (LadderDirector) ------------------------------------------------------------------------------

    def _home_begin(self) -> None:
        sys.path.insert(0, str(ROOT / "host"))
        from maipai_body.bodies.stackchan import dance_ladder as DL

        self.DL = DL
        self.feed = DL.LadderFeed()
        hooks = DL.LadderHooks(set_stage=self._host_set_stage, show_face=self._show_face, notes=self._show_notes, overlay=self._overlay, overlay_clear=self._overlay_clear)
        self.director = DL.LadderDirector(hooks, self.feed, max_stage=self.max_stage)
        self._energy = DL.Energy()
        self._feed_update(self.u.now_ms)

    def _host_set_stage(self, stage: int):
        self.u.call("self.music.stage", {"stage": stage})
        return {"ok": True}

    def _feed_update(self, now: int) -> None:
        f = self.feat
        self.feed.bpm = f["bpm"]
        self.feed.tc = f["tc"]
        self.feed.level = f["level"]
        self.feed.music = bool(f["music"])
        self.feed.energy = self._energy.push(f["level"])
        f["avg"] = self.feed.energy

    def _home_plan(self, now: int) -> None:
        """The dance runner's tick (every 0.25 s): the director's step, then the ring."""
        elapsed = (now - self.t_start) / 1000.0
        d = self.director
        d.on_tick(self.tick_no, elapsed)
        ring = d.ring(self.tick_no, elapsed)
        if ring is not None:
            self.u.leds = [tuple(int(v) for v in px) for px in ring]
            self.leds = list(self.u.leds)
            self.ring_host = True
        self.tick_no += 1
        if d.finished():
            self.stop()

    # ---- what the show asks of the screen ------------------------------------------------------------------------------

    def _show_face(self, name: str) -> None:
        self.face = name
        self.u.raw(f"face {name if name in SHOW_FACES else 'happy'}")

    def _show_notes(self, count: int) -> None:
        r = self.u.call("self.face.music_notes", {"count": count})
        if r.get("ok"):
            self.notes = count
            self.u.raw(f"notes {count}")

    def _overlay(self, name: str, intensity: str, seconds: int):
        r = self.u.call("self.overlay.set", {"name": name, "intensity": intensity, "seconds": seconds})
        if r.get("ok"):
            level = {"light": 1, "normal": 2, "heavy": 3}.get(intensity, 2)
            self.u.raw(f"overlay {name} {level} {seconds}")
            if name not in self.overlays:
                self.overlays.append(name)
        return r

    def _overlay_clear(self):
        self.u.call("self.overlay.clear", {})
        self.u.raw("ovclear")
        self.overlays = []

    # ---- BeatDanceModifier::_update, ported ----------------------------------------------------------------------------------

    def _reset_modifier(self) -> None:
        self._t0 = None
        self._beat_seen = None
        self._last_period = 0
        self._last_ref = 0
        self._have_last = False
        self._have_eb = False
        self._have_hb = False
        self._last_eb = 0
        self._last_hb = 0
        self._head_moved = False
        self._ring_at = -10**9
        self.ring_host = False
        self.L.sim_budget_reset(self._budget)

    def _gaze(self, x: int, y: int) -> None:
        self.eye = (x, y)
        self.u.raw(f"gaze {x} {y}")

    def _move_head(self, yaw10: int, pitch10: int, speed: int) -> None:
        self.u.move_head(yaw10 / 10.0, pitch10 / 10.0, speed)

    def _ring_dark(self) -> None:
        if self.ring_on:
            self.ring_on = False
            self.u.leds = [(0, 0, 0)] * 12
            self.leds = list(self.u.leds)

    def _modifier(self, now: int) -> None:
        stage = self.stage
        if stage <= 0:
            self._ring_dark()
            return
        L = self.L
        if self._t0 is None:
            self._t0 = self._beat_seen = now
        fresh = self.beat(now)
        if fresh and fresh[0] >= 250:
            period, ref = fresh
            self._last_period, self._last_ref, self._have_last, self._beat_seen = period, ref, True, now
        elif self._have_last:
            period, ref = self._last_period, self._last_ref
        else:
            period, ref = 600, self._t0
        eff = L.sim_effective(stage, now - self._beat_seen)
        since = now - ref
        eb = since // period if since >= 0 else -1 - ((-since - 1) // period)
        step = 2 if period < 450 else 1
        hb = eb // step if eb >= 0 else -1 - ((-eb - 1) // step)
        loud = 1 if self.feat["level"] >= L.sim_consts(0) else 0
        if not self._have_eb or eb != self._last_eb:
            self._have_eb, self._last_eb = True, eb
            side = 1 if (eb & 1) else -1
            pose = (ctypes.c_int * 6)()
            L.sim_pose(eff, side, int(hb), period * step, loud, pose)
            self._gaze(pose[0], pose[1])
            moved = False
            if eff == 1 and self._head_moved:
                self._move_head(0, 0, 200)
                self._head_moved = False
            if pose[2] and (eb % step == 0) and not (self._have_hb and hb == self._last_hb):
                self._have_hb, self._last_hb = True, hb
                hside = 1 if (hb & 1) else -1
                hp = (ctypes.c_int * 6)()
                L.sim_pose(eff, hside, int(hb), period * step, loud, hp)
                if L.sim_budget_take(self._budget, now + CLOCK_BASE):
                    self._move_head(hp[3], hp[4], hp[5])
                    self.head_moves.append(now)
                    self._head_moved = moved = True
                else:
                    self.refused_moves += 1
            self.beats.append({"t_ms": now - self.t_start, "eb": int(eb), "step": stage, "eff": eff, "eye": (pose[0], pose[1]), "moved": moved, "period": period})
        if eff >= 4 and self._ring_allowed():
            if now - self._ring_at >= 50:
                self._ring_at = now
                span = period * step
                phase = (abs(since)) % span
                px = (ctypes.c_uint8 * 36)()
                L.sim_ring(px, L.sim_swell(phase, span), 1 if (eb & 1) else -1, int(hb // 8) if hb >= 0 else 0)
                self.u.leds = [(px[i * 3], px[i * 3 + 1], px[i * 3 + 2]) for i in range(12)]
                self.leds = list(self.u.leds)
                self.ring_on = True
        else:
            self._ring_dark()

    def _ring_allowed(self) -> bool:
        face = self.u.state.get("face", {})
        return not face.get("privacy_bits", 0) and not face.get("timers_ringing", False)

    # ---- the clock ----------------------------------------------------------------------------------------------------------

    def tick(self, now: int) -> None:
        if self.kf is not None:
            self._keyframe_face(now)
        if not (self.running or self.stage):
            return
        if self.running and now >= self.next_second:
            self.next_second += 1000
            self._read_feat(now)
            if self.mode == "home":
                self._feed_update(now)
            else:
                self._cycle_tick(now)
        if self.running and self.mode == "home" and now >= self.next_plan:
            self.next_plan += 250
            self._home_plan(now)
        if self.stage:
            self._modifier(now)
        # a touch, a lift or full quiet ends the dance at once (the gates of the real unit)
        if self.stage and self._limits().get("state") == "carried":
            self.stop()

    def _keyframe_face(self, now: int) -> None:
        import hw

        name, t0, last = self.kf
        pos = hw.keyframe_at(name, now - t0)
        if pos is None:
            self.kf = None
            self.u.raw("face neutral")
            self._gaze(0, 0)
            return
        i, _ = pos
        if i != last:
            self.kf = (name, t0, i)
            r = hw.KEYFRAMES[name][i]
            self._gaze(r[5], r[6])
            self.u.raw("face surprised" if r[8] >= 100 else "face happy" if (r[7] <= 50 or r[8] >= 40) else "face neutral")

    # ---- what the 3D view and the status read -------------------------------------------------------------------------------

    def status(self) -> dict:
        f = self.feat
        u = self.u
        recent = [t for t in self.head_moves if u.now_ms - t < 60000]
        return {
            "running": self.running or bool(self.stage), "mode": self.mode, "song": self.song_name, "step": self.stage, "step_name": ("still", "eyes", "nod", "sway", "full")[self.stage],
            "down": bool(self.L.sim_down(self.h)) if self.cycle_active else bool(getattr(self.director, "_ladder", None) and self.director._ladder.down),
            "bpm": f["bpm"], "level": f["level"], "avg_level": f.get("avg", 0), "tempo_confidence": f["tc"], "music": bool(f["music"]),
            "eye": list(self.eye), "head": u.head(), "ring": [list(px) for px in u.leds], "overlays": list(self.overlays), "notes": self.notes, "face": self.face,
            "head_moves_last_minute": len(recent), "head_moves_refused": self.refused_moves, "stage_log": list(self.stage_log),
        }
