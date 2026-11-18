"""Mouth cues computed on the host from the speech audio (step 3 of the plan).

The firmware moves the mouth from the audio it plays, which tops out at a low and uneven frame rate.
The host knows the whole reply before it is played, so it can send the unit a short list of
(time, openness) cues that the unit applies on its own clock: 4 to 11 updates a second, smoothed,
with the mouth always closing at the end. The unit side (a `self.face.mouth_cues` tool taking
`{"cues": [[ms, level], ...]}`) is a firmware patch; this module and its test fix the data it receives.
"""

from __future__ import annotations

import numpy as np

LEVELS = 5  # 0 closed .. 4 wide open
MIN_RATE_HZ = 4.0  # while speaking, a cue at least this often
MAX_RATE_HZ = 11.0  # and never faster than the unit can draw
WINDOW_MS = 40
ATTACK = 0.7  # how fast the mouth opens toward a louder window (0..1 per window)
RELEASE = 0.35  # how fast it closes
FLOOR_DB, CEIL_DB = -50.0, -14.0  # window loudness mapped onto the levels


def _window_levels(samples: np.ndarray, sample_rate: int) -> np.ndarray:
    size = max(1, int(sample_rate * WINDOW_MS / 1000))
    count = max(1, len(samples) // size)
    chunk = samples[: count * size].reshape(count, size).astype(np.float32)
    rms = np.sqrt(np.mean(chunk * chunk, axis=1) + 1e-12)
    db = 20.0 * np.log10(rms + 1e-9)
    raw = np.clip((db - FLOOR_DB) / (CEIL_DB - FLOOR_DB), 0.0, 1.0)
    smooth = np.zeros_like(raw)
    value = 0.0
    for index, target in enumerate(raw):
        rate = ATTACK if target > value else RELEASE
        value += (target - value) * rate
        smooth[index] = value
    return smooth


def mouth_cues(samples: np.ndarray, sample_rate: int) -> list[tuple[int, int]]:
    """Cues for one reply: (milliseconds from the start of playback, level 0..4), ending closed.

    A cue is sent when the level changes, but no faster than MAX_RATE_HZ, and one is repeated at least
    every 1/MIN_RATE_HZ seconds so the unit never waits long for the next update."""
    if len(samples) == 0:
        return [(0, 0)]
    smooth = _window_levels(np.asarray(samples, dtype=np.float32), sample_rate)
    min_gap, max_gap = 1000.0 / MAX_RATE_HZ, 1000.0 / MIN_RATE_HZ
    cues: list[tuple[int, int]] = []
    last_t, last_level = -1e9, -1
    for index, value in enumerate(smooth):
        t = index * WINDOW_MS
        level = int(round(value * (LEVELS - 1)))
        due = t - last_t
        if (level != last_level and due >= min_gap) or due >= max_gap:
            cues.append((int(t), level))
            last_t, last_level = t, level
    end = len(smooth) * WINDOW_MS
    if not cues or cues[-1][1] != 0:
        cues.append((int(max(end, last_t + min_gap + 1)), 0))
    return cues


def rate_hz(cues: list[tuple[int, int]]) -> float:
    if len(cues) < 2:
        return 0.0
    return (len(cues) - 1) / ((cues[-1][0] - cues[0][0]) / 1000.0)
