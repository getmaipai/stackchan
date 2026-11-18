"""The music dance ladder, host half: a dance that builds up on the beat and winds down again.

The unit plays the motion (firmware patch MD01, ``BeatDanceModifier``): step 1 the eyes look side to side on the beat with the
head still, 2 the head nods, 3 it sways side to side, 4 pan, tilt and sway together. The host decides WHICH step runs from what the
unit measures each second (tempo, tempo confidence, level) and tells the unit with ``self.music.stage`` only when the step changes.
Around the motion the host shows the rest of the dance: the music notes (none, 1, 2, 3 by step), the ring (dark in the first step,
a slow soft glow, then a chase, brighter and faster per step; at the peak the unit paints a soft swell on the beat itself), the
disco ball behind the face and a burst of confetti at the peak, and a face that changes on the beat phrases and never repeats.

``Ladder`` is the pure step rule and mirrors ``firmware/main/hal/maipai_dance_ladder_core.h`` (a test feeds both the same scripted
seconds). ``LadderDirector`` is the show: it runs inside the dance runner's tick (``Plan.on_tick``).

Safety, all unchanged and checked by the caller: the gates (night, asleep, a camera cue, full quiet, muted, locked, carried, a low
battery, the emergency stop) live in ``DanceRunner`` and ``MusicDance``; the ring never goes over half brightness, never changes
faster than a slow swell, and never shows a status color (gold, lime, mint, sky, lilac, warm white only).
"""

from __future__ import annotations

import logging
import random
from collections.abc import Callable
from dataclasses import dataclass

from maipai_body.bodies.stackchan.dance import GOLD, LED_COUNT, LIME, MINT, SPARKLE, Rgb
from maipai_body.bodies.stackchan.profile import LED_CHANNEL_MAX

logger = logging.getLogger("maipai_body.bodies.stackchan.dance_ladder")

# ---------------------------------------------------------------- the step rule (mirrors maipai_dance_ladder_core.h)

EYES_BEATS, EYES_MIN_MS, EYES_MAX_MS = 3, 1500, 3000
STEP_BEATS, STEP_MIN_MS, STEP_MAX_MS = 8, 4000, 8000
PEAK_BEATS, PEAK_MIN_MS, PEAK_MAX_MS = 24, 12000, 20000
DOWN_BEATS, DOWN_MIN_MS, DOWN_MAX_MS = 4, 2000, 4000
MAX_CYCLE_MS = 75000
LEVEL_MID, LEVEL_HIGH = 800, 1500
CLIMB_LEVEL = {3: 800, 4: 1000}
CLIMB_TC = {2: 20, 3: 30, 4: 35}
PEAK_DROP_PCT, PEAK_DROP_MS = 70, 6000
LOST_MS = 3000


def _clamp(value: int, low: int, high: int) -> int:
    return low if value < low else high if value > high else value


def _period(period_ms: int) -> int:
    return period_ms if 250 <= period_ms <= 2000 else 600


def dwell_ms(stage: int, down: bool, period_ms: int) -> int:
    p = _period(period_ms)
    if down:
        return _clamp(p * DOWN_BEATS, DOWN_MIN_MS, DOWN_MAX_MS)
    if stage <= 1:
        return _clamp(p * EYES_BEATS, EYES_MIN_MS, EYES_MAX_MS)
    if stage >= 4:
        return _clamp(p * PEAK_BEATS, PEAK_MIN_MS, PEAK_MAX_MS)
    return _clamp(p * STEP_BEATS, STEP_MIN_MS, STEP_MAX_MS)


class Energy:
    """The level: a moving average of the last four seconds."""

    def __init__(self) -> None:
        self._values: list[int] = []

    def reset(self) -> None:
        self._values.clear()

    def push(self, level: int) -> int:
        self._values.append(int(level))
        del self._values[:-4]
        return sum(self._values) // len(self._values)


class Ladder:
    """One cycle of the ladder: climb 1 to 4, hold the peak, go back down, end at 0."""

    def __init__(self, max_stage: int = 4, now_ms: int = 0) -> None:
        self.max_stage = _clamp(max_stage, 1, 4)
        self.stage = 1
        self.down = False
        self.started = True
        self.cycle_ms = now_ms
        self.stage_ms = now_ms
        self.peak_level = 0
        self.low_ms = 0
        self.lost_ms = 0

    def _go_down(self, now: int) -> None:
        if not self.down:
            self.down = True
            self.stage_ms = now

    @staticmethod
    def _can_climb(to: int, level: int, tc: int, music: bool) -> bool:
        if not music:
            return False
        if to == 2:
            return tc >= CLIMB_TC[2]
        if to in (3, 4):
            return level >= CLIMB_LEVEL[to] and tc >= CLIMB_TC[to]
        return True

    def step(self, now: int, period_ms: int, level: int, tc: int, music: bool) -> int:
        """The step to show now; 0 when the cycle is over (and from then on)."""
        if self.stage == 0:
            return 0
        if music:
            self.lost_ms = 0
        elif self.lost_ms == 0:
            self.lost_ms = now or 1
        if self.lost_ms and now - self.lost_ms >= LOST_MS:
            self._go_down(now)
        if not self.down and now - self.cycle_ms >= MAX_CYCLE_MS:
            self._go_down(now)
        held = now - self.stage_ms
        if self.down:
            if held >= dwell_ms(self.stage, True, period_ms):
                if self.stage <= 1:
                    self.stage = 0
                    return 0
                self.stage -= 1
                self.stage_ms = now
            return self.stage
        if self.stage >= 4:
            if self.peak_level == 0:
                self.peak_level = level if level > 1 else 1
            if level * 100 < self.peak_level * PEAK_DROP_PCT:
                if self.low_ms == 0:
                    self.low_ms = now or 1
            else:
                self.low_ms = 0
            if (self.low_ms and now - self.low_ms >= PEAK_DROP_MS) or held >= dwell_ms(
                4, False, period_ms
            ):
                self._go_down(now)
            return self.stage
        dwell = dwell_ms(self.stage, False, period_ms)
        if (
            held >= dwell
            and self.stage < self.max_stage
            and self._can_climb(self.stage + 1, level, tc, music)
        ):
            self.stage += 1
            self.stage_ms = now
            self.peak_level = 0
            self.low_ms = 0
        elif held >= dwell and self.stage >= self.max_stage:
            self._go_down(now)
        return self.stage


# ---------------------------------------------------------------- the show

RING_CAP = 0.5  # of full scale: nothing brighter, ever
RING_SKY = (0.45, 0.75, 1.0)  # the face palette's sky and lilac: no status meaning
RING_LILAC = (0.75, 0.6, 1.0)

NOTES_FOR_STAGE = {0: 0, 1: 0, 2: 1, 3: 2, 4: 3}
NOTES_REFRESH_S = 10.0  # the unit hides the notes 30 s after the last call
OVERLAY_REFRESH_S = 20.0
CONFETTI_EVERY_BEATS = 32

# The faces the unit draws (firmware MD02 and the older ones), by how much the dance is going. A face is chosen from the list of
# the step, never the one just shown nor the one before it.
FACES_BY_STAGE: dict[int, tuple[str, ...]] = {
    1: ("happy",),
    2: ("happy", "serene", "laughing", "love"),
    3: ("happy", "serene", "laughing", "love", "surprised", "wink"),
    4: ("laughing", "love", "surprised", "wink", "silly", "excited", "happy", "serene"),
}


class FaceRotator:
    """Picks the next face of the dance: from the step's list, never the last face and never one of the last two."""

    def __init__(self, seed: int = 0) -> None:
        self._rng = random.Random(seed)
        self.history: list[str] = []

    def next(self, stage: int) -> str:
        pool = FACES_BY_STAGE.get(stage) or FACES_BY_STAGE[2]
        last = self.history[-1:]
        choices = [face for face in pool if face not in self.history[-2:]]
        if not choices:
            choices = [face for face in pool if face not in last] or list(pool)
        face = self._rng.choice(choices)
        self.history.append(face)
        del self.history[:-6]
        return face


def _frac(color: tuple[float, float, float], fraction: float) -> Rgb:
    """A color at ``fraction`` of full scale (never above ``RING_CAP``)."""
    fraction = max(0.0, min(RING_CAP, fraction))
    r, g, b = (max(0, min(LED_CHANNEL_MAX, round(LED_CHANNEL_MAX * c * fraction))) for c in color)
    return (r, g, b)


DARK: Rgb = (0, 0, 0)


def breath_frame(t_s: float, beat_s: float, depth: float = 1.0, scale: float = 1.0) -> list[Rgb]:
    """The nod's glow: both sides breathe slowly, mint on one and gold on the other, 0.10 to 0.18 of full. The breath is four beats
    long, held between 1.5 and 4 seconds."""
    import math

    period = max(1.5, min(4.0, 4.0 * beat_s))
    swell = 0.5 - 0.5 * math.cos(2.0 * math.pi * t_s / period)
    level = (0.10 + 0.08 * depth * swell) * scale
    half = LED_COUNT // 2
    return [_frac(MINT if i < half else GOLD, level) for i in range(LED_COUNT)]


def chase_frame(beat_index: int, level_frac: float, scale: float = 1.0) -> list[Rgb]:
    """The sway's chase: a two-pixel head walks round one pixel per beat (the side the head goes to is a little brighter) over a faint
    mint wash. 0.18 to 0.30 of full by the level."""
    base = 0.08 * scale
    bright = (0.18 + 0.12 * max(0.0, min(1.0, level_frac))) * scale
    head = beat_index % LED_COUNT
    half = LED_COUNT // 2
    lean_left = beat_index % 2 == 0
    pixels = []
    for i in range(LED_COUNT):
        side_gain = 1.0 if ((i < half) == lean_left) else 0.75
        if i in (head, (head - 1) % LED_COUNT):
            color = GOLD if i == head else LIME
            pixels.append(_frac(color, bright * side_gain))
        else:
            pixels.append(_frac(MINT, base * side_gain))
    return pixels


# ---------------------------------------------------------------- the director


@dataclass
class LadderFeed:
    """What the unit last said (the director reads it; the wiring writes it once a second)."""

    bpm: int = 0
    tc: int = 0
    level: int = 0
    music: bool = False
    at: float = float("-inf")
    energy: int = 0


@dataclass
class LadderHooks:
    set_stage: Callable[[int], object]  # self.music.stage
    show_face: Callable[[str], object]
    notes: Callable[[int], object]  # self.face.music_notes
    overlay: Callable[[str, str, int], object]  # (name, intensity, seconds)
    overlay_clear: Callable[[], object]


def fold_bpm(bpm: int) -> int:
    """The tempo the unit's beat grid uses: halves and doubles folded into 70 to 140."""
    if bpm <= 0:
        return 0
    while bpm < 70:
        bpm *= 2
    while bpm > 140:
        bpm = (bpm + 1) // 2
    return bpm


class LadderDirector:
    """Runs one cycle of the ladder inside the dance runner's tick: the unit's step, the face, the notes, the overlays, the ring."""

    def __init__(
        self,
        hooks: LadderHooks,
        feed: LadderFeed,
        *,
        max_stage: int = 4,
        faces: FaceRotator | None = None,
        on_stage: Callable[[int, int], None] | None = None,
    ) -> None:
        self._hooks = hooks
        self._feed = feed
        self._max_stage = max_stage
        self._faces = faces or FaceRotator()
        self._on_stage = on_stage
        self._ladder: Ladder | None = None
        self.stage = 0
        self.ended = False
        self.unsupported = False
        self.stage_log: list[tuple[float, int]] = []  # (seconds, step) at every change
        self._stage_at = 0.0
        self._next_face_at = 0.0
        self._notes_at = float("-inf")
        self._overlay_at = float("-inf")
        self._confetti_beat = 0
        self._started_at = 0.0
        self._last_face = ""

    # -- the plan's three hooks

    def finished(self) -> bool:
        return (
            self.ended or self.unsupported or (self._ladder is not None and self._ladder.stage == 0)
        )

    def on_tick(self, tick: int, elapsed: float) -> None:
        if self.finished():
            return
        feed = self._feed
        period_ms = 60000 // fold_bpm(feed.bpm) if feed.bpm > 0 else 0
        now_ms = int(elapsed * 1000) + 1000
        if self._ladder is None:
            self._ladder = Ladder(self._max_stage, now_ms)
            self._started_at = elapsed
            self._enter(1, elapsed, now_ms, period_ms)
        music = feed.music
        stage = self._ladder.step(now_ms, period_ms, feed.energy, feed.tc, music)
        if stage != self.stage:
            if stage == 0:
                self._log_stage(elapsed, 0)
                self.stage = 0
                return
            self._enter(stage, elapsed, now_ms, period_ms)
        else:
            self._refresh(elapsed, period_ms)

    def on_end(self) -> None:
        """The dance ended (done, music gone, a gate, a touch): the unit stands still, notes and overlays go."""
        self.ended = True
        for step in (
            lambda: self._hooks.set_stage(0),
            lambda: self._hooks.notes(0),
            self._hooks.overlay_clear,
        ):
            try:
                step()
            except Exception:
                logger.debug("StackChan dance ladder end step failed", exc_info=True)
        self.stage = 0

    # -- what a step change does

    def _log_stage(self, elapsed: float, stage: int) -> None:
        self.stage_log.append((round(elapsed, 2), stage))
        logger.info("StackChan dance ladder: step %d at %.1f s", stage, elapsed)

    def _enter(self, stage: int, elapsed: float, now_ms: int, period_ms: int) -> None:
        previous = self.stage
        self.stage = stage
        self._stage_at = elapsed
        self._log_stage(elapsed, stage)
        from maipai_body.hal.errors import NotSupported

        try:
            self._hooks.set_stage(stage)
        except NotSupported:
            self.unsupported = True
            logger.info("StackChan firmware has no music dance steps; the ladder stays off")
            return
        except Exception:
            logger.warning(
                "StackChan dance ladder: the unit did not take step %d", stage, exc_info=True
            )
        if self._on_stage is not None:
            self._on_stage(previous, stage)
        if not (
            stage == 1 and previous >= 2
        ):  # going back down to the eyes keeps the face it has: no repeat
            self._face(stage, elapsed, period_ms)
        self._notes(stage, elapsed, force=True)
        self._overlays(previous, stage, elapsed, force=True)

    def _phrase_s(self, stage: int, period_ms: int) -> float:
        beats = (
            16 if stage == 2 else 8
        )  # the nod stays calm: a face every 16 beats; the rest every 8
        return beats * (period_ms or 600) / 1000.0

    def _face(self, stage: int, elapsed: float, period_ms: int) -> None:
        face = self._faces.next(stage)
        self._last_face = face
        try:
            self._hooks.show_face(face)
        except Exception:
            logger.debug("StackChan dance ladder face failed", exc_info=True)
        self._next_face_at = elapsed + self._phrase_s(stage, period_ms)

    def _notes(self, stage: int, elapsed: float, *, force: bool = False) -> None:
        if not force and elapsed - self._notes_at < NOTES_REFRESH_S:
            return
        self._notes_at = elapsed
        try:
            self._hooks.notes(NOTES_FOR_STAGE.get(stage, 0))
        except Exception:
            logger.debug("StackChan dance ladder notes failed", exc_info=True)

    def _overlays(self, previous: int, stage: int, elapsed: float, *, force: bool = False) -> None:
        h = self._hooks
        try:
            if stage >= 3:
                if force or elapsed - self._overlay_at >= OVERLAY_REFRESH_S:
                    self._overlay_at = elapsed
                    h.overlay("disco", "normal" if stage >= 4 else "light", 30)
                if stage >= 4 and previous < 4:
                    h.overlay("confetti", "normal", 4)  # the peak: a burst
                    self._confetti_beat = 0
            elif previous >= 3:
                h.overlay_clear()  # below the sway the back layer is clear again
        except Exception:
            logger.debug("StackChan dance ladder overlay failed", exc_info=True)

    def _refresh(self, elapsed: float, period_ms: int) -> None:
        stage = self.stage
        if stage >= 2 and elapsed >= self._next_face_at:
            self._face(stage, elapsed, period_ms)
        self._notes(stage, elapsed)
        if stage >= 3 and elapsed - self._overlay_at >= OVERLAY_REFRESH_S:
            self._overlays(stage, stage, elapsed, force=True)
        if stage >= 4 and self._feed.energy >= LEVEL_HIGH:
            beat_s = (period_ms or 600) / 1000.0
            beats = int((elapsed - self._stage_at) / beat_s)
            if beats // CONFETTI_EVERY_BEATS > self._confetti_beat:
                self._confetti_beat = beats // CONFETTI_EVERY_BEATS
                try:
                    self._hooks.overlay(
                        "confetti", "normal", 4
                    )  # at the peak again while it stays loud
                except Exception:
                    logger.debug("StackChan dance ladder confetti failed", exc_info=True)

    # -- the ring (the plan's ring function, every 0.25 s)

    def ring(self, tick: int, elapsed: float) -> list[Rgb] | None:
        ladder = self._ladder
        if ladder is None or self.finished():
            return None
        stage = self.stage
        feed = self._feed
        beat_s = (60.0 / fold_bpm(feed.bpm)) if feed.bpm > 0 else 0.6
        level_frac = (feed.energy - LEVEL_MID) / float(LEVEL_HIGH - LEVEL_MID)
        scale = 0.7 if ladder.down else 1.0
        t = elapsed - self._stage_at
        if stage == 1:
            if not ladder.down:
                return None  # dark in the first step
            return self._fade(t)
        if stage == 2:
            depth = 1.0 if feed.energy >= LEVEL_MID else 0.6
            return breath_frame(elapsed, beat_s, depth)
        if stage == 3:
            beat = int(elapsed / beat_s)
            return chase_frame(beat, level_frac, scale)
        return None  # the peak: the unit paints its own swell on the beat

    def _fade(self, t_s: float) -> list[Rgb] | None:
        """The last step going down: the glow of the nod fades to dark over two seconds (a ramp, not a cut)."""
        if t_s >= 2.0:
            return None if getattr(self, "_dark_sent", False) else self._dark_once()
        level = 0.10 * max(0.0, 1.0 - t_s / 2.0)
        half = LED_COUNT // 2
        return [_frac(MINT if i < half else GOLD, level) for i in range(LED_COUNT)]

    def _dark_once(self) -> list[Rgb]:
        self._dark_sent = True
        return [DARK] * LED_COUNT


__all__ = [
    "FACES_BY_STAGE",
    "FaceRotator",
    "Ladder",
    "LadderDirector",
    "LadderFeed",
    "LadderHooks",
    "Energy",
    "breath_frame",
    "chase_frame",
    "dwell_ms",
    "fold_bpm",
    "SPARKLE",
]
