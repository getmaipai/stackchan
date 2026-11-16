"""How the robot reacts to being touched, shaken and praised (owner requests 2026-10-21).

Touch, swipe and shake events come from the unit (patch 021's event queue). The unit already shows
its own dizzy and heart faces for a shake and a stroke; this adds what only the host can do: a short
spoken line after a shake, and a loving heart only when it is earned. The heart is rare on purpose:
a pet, or kind words such as "you're so helpful", or a very cute picture, and never twice within
a minute.
"""

from __future__ import annotations

import logging
import random
import re
import time
from collections.abc import Callable

logger = logging.getLogger("maipai_body.bodies.stackchan.reactions")

SHAKE_LINES = ("Whoa!", "Hey! Easy!", "Eep! Where are we going?")
SHAKE_COOLDOWN_S = 20.0
# How long a reaction face (heart, surprise) stays before the neutral face is put back. The unit's
# own happy face after a stroke is open-mouthed and was left on far too long. It is also the only
# gap between two pet reactions: while one plays no new one starts, and the next real pet reacts at
# once when it ends (owner ruling 2026-10-21: no cooldown after the petted animation).
FACE_HOLD_S = 3.0
SYMBOL_RETRY_S = 600.0
# The unit's own motion must never start a reaction (a feedback loop: motion shakes the sensor, the
# reaction moves or talks, the sensor shakes again). After a commanded head move or a spoken line
# every sensor event is ignored for REFRACTORY_S, at most MAX_REACTIONS_PER_MIN reactions run in
# a minute, and a shake counts only when it is sustained: two shake events SUSTAIN_S or more apart
# within SUSTAIN_WINDOW_S (one jolt is a bump, not a shake).
REFRACTORY_S = 1.5
MAX_REACTIONS_PER_MIN = 6
SUSTAIN_S = 0.3
SUSTAIN_WINDOW_S = 2.0

# What it would love to hear. A short, closed list: a heart must be earned, not guessed.
_LOVE_CUES = re.compile(
    r"\b(you'?re so helpful|you are so helpful|thank you so much|thanks so much|i love you|"
    r"love you|you'?re the best|you are the best|good robot|you'?re adorable|you are adorable|"
    r"you'?re so cute|you are so cute|you'?re cute|so adorable)\b"
)
# Reply moods from the hub's cue that mean a very cute picture or real affection.
LOVE_MOODS = frozenset({"love", "affection", "adoration"})

_PET_EVENTS = {"head_touch", "head_tap"}
_SWIPE_EVENTS = {"head_swipe_forward", "head_swipe_back"}


def has_love_cue(text: str | None) -> bool:
    spoken = re.sub(r"[^\w' ]+", " ", (text or "").lower())
    return bool(_LOVE_CUES.search(re.sub(r"\s+", " ", spoken)))


class Reactions:
    """Decides what the robot shows and says; the callables do it."""

    def __init__(
        self,
        *,
        face: Callable[[str], object],
        say: Callable[[str], bool],
        quiet: Callable[[], bool] = lambda: False,
        busy: Callable[[], bool] = lambda: False,
        symbol: Callable[[str], object] | None = None,
        head_moved_ago: Callable[[], float | None] = lambda: None,
        clock: Callable[[], float] = time.monotonic,
        rng: random.Random | None = None,
    ) -> None:
        self._face = face
        self._say = say
        self._quiet = quiet
        self._busy = busy
        self._symbol = symbol
        self._head_moved_ago = head_moved_ago
        self._spoke_at = float("-inf")
        self._reacted: list[float] = []
        self._shake_first: float | None = None
        self._clock = clock
        self._rng = rng or random.Random()
        self._last_shake = float("-inf")
        self._playing_until = float("-inf")
        self._symbol_retry_at = float("-inf")
        self._last_line: str | None = None
        self._neutral_at: float | None = None

    # -- the unit's events ----------------------------------------------------

    def on_events(self, kinds: list[str]) -> None:
        """Touch, swipe and shake events read from the unit since the last look."""
        if self._busy():
            # In a conversation the reply owns the face and the voice; say so once a look.
            logger.info(
                "StackChan touch reaction skipped: a conversation is on (%s)", ", ".join(kinds)
            )
            return
        if self._refractory():
            logger.info("StackChan sensor reaction skipped: the unit's own motion or voice just ran (%s)", ", ".join(kinds))
            return
        if "shake" in kinds and self._sustained_shake() and self._allow_reaction():
            self._shaken()
        if any(kind in _PET_EVENTS for kind in kinds) or any(k in _SWIPE_EVENTS for k in kinds):
            # The unit shows its own open-mouthed happy face for a stroke; take it back soon.
            self._hold_face()
        if any(kind in _PET_EVENTS or kind in _SWIPE_EVENTS for kind in kinds):
            self._petted("tapped" if "head_tap" in kinds else "petted")
        # A stroke across the head already makes the unit show its own happy face and heart.

    def note_spoke(self) -> None:
        """A line was spoken by the unit: its own sound shakes the sensor, so events wait."""
        self._spoke_at = self._clock()

    def _refractory(self) -> bool:
        now = self._clock()
        if now - self._spoke_at < REFRACTORY_S:
            return True
        try:
            moved = self._head_moved_ago()
        except Exception:
            moved = None
        return moved is not None and moved < REFRACTORY_S

    def _sustained_shake(self) -> bool:
        now = self._clock()
        first = self._shake_first
        if first is None or now - first > SUSTAIN_WINDOW_S:
            self._shake_first = now
            return False
        if now - first < SUSTAIN_S:
            return False
        self._shake_first = None
        return True

    def _allow_reaction(self) -> bool:
        now = self._clock()
        self._reacted = [t for t in self._reacted if now - t < 60.0]
        if len(self._reacted) >= MAX_REACTIONS_PER_MIN:
            logger.info("StackChan reaction skipped: %d reactions in the last minute", len(self._reacted))
            return False
        self._reacted.append(now)
        return True

    def _shaken(self) -> None:
        now = self._clock()
        if now - self._last_shake < SHAKE_COOLDOWN_S:
            return
        self._last_shake = now
        self._face("dizzy")
        self._hold_face()
        if self._quiet():
            logger.info("StackChan was shaken (quiet hours: face only)")
            return
        line = self._pick_line()
        logger.info("StackChan was shaken; says %r", line)
        self._say(line)
        self.note_spoke()

    def _pick_line(self) -> str:
        choices = [line for line in SHAKE_LINES if line != self._last_line] or list(SHAKE_LINES)
        self._last_line = self._rng.choice(choices)
        return self._last_line

    def _petted(self, how: str = "petted") -> None:
        """A pet, or a tap the unit confirmed with its motion sensor (firmware patch 081): the same
        heart, so a touch always gets one reaction, and the log says which it was."""
        if self.heart(how):
            logger.info("StackChan was %s", how)

    def _hold_face(self) -> None:
        self._neutral_at = self._clock() + FACE_HOLD_S

    def tick(self) -> None:
        """Put the neutral face back once a reaction face has been held long enough."""
        if self._neutral_at is None or self._clock() < self._neutral_at:
            return
        self._neutral_at = None
        if not self._busy():
            self._face("neutral")

    # -- the heart, rare on purpose ----------------------------------------------

    def on_user_words(self, text: str | None) -> None:
        if has_love_cue(text):
            self.heart("kind words")

    def on_reply_mood(self, mood: str | None) -> None:
        if mood in LOVE_MOODS:
            self.heart("a loving reply")

    def heart(self, reason: str) -> bool:
        """Show the heart (or, until the unit can, a smile), unless one is still playing."""
        now = self._clock()
        if now < self._playing_until:
            return False
        self._playing_until = now + FACE_HOLD_S
        shown = False
        if self._symbol is not None and now >= self._symbol_retry_at:
            try:
                self._symbol("heart")
                shown = True
            except Exception:
                # This firmware has no symbol tool yet: smile instead, and do not ask for a while.
                self._symbol_retry_at = now + SYMBOL_RETRY_S
        if not shown:
            self._face("love")
        self._hold_face()
        logger.info("StackChan heart (%s): %s", reason, "heart" if shown else "smile")
        return True
