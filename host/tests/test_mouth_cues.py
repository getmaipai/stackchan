"""Host-computed mouth cues: 4 to 11 updates a second while speaking, smooth, closed at the end."""

import numpy as np

from maipai_body import mouth_cues as mc

RATE = 16000


def _speechlike(seconds=3.0, seed=1):
    """Loud and quiet syllables about 4 a second, like talking."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * RATE)) / RATE
    envelope = (np.sin(2 * np.pi * 4 * t) > 0).astype(np.float32) * 0.4 + 0.01
    return (rng.standard_normal(len(t)).astype(np.float32) * envelope).clip(-1, 1)


def test_speech_gets_between_four_and_eleven_cues_a_second():
    cues = mc.mouth_cues(_speechlike(), RATE)
    assert 4.0 <= mc.rate_hz(cues) <= 11.0, mc.rate_hz(cues)


def test_never_faster_than_the_unit_can_draw():
    cues = mc.mouth_cues(_speechlike(2.0), RATE)
    gaps = np.diff([t for t, _ in cues])
    assert gaps.min() >= 1000 / mc.MAX_RATE_HZ - 1


def test_silence_still_sends_a_cue_every_quarter_second_but_stays_closed():
    cues = mc.mouth_cues(np.zeros(2 * RATE, dtype=np.float32), RATE)
    assert all(level == 0 for _, level in cues)
    assert np.diff([t for t, _ in cues]).max() <= 1000 / mc.MIN_RATE_HZ + mc.WINDOW_MS


def test_loud_opens_wider_than_quiet_and_the_reply_ends_closed():
    quiet = mc.mouth_cues(_speechlike() * 0.1, RATE)
    loud = mc.mouth_cues(_speechlike(), RATE)
    assert max(level for _, level in loud) > max(level for _, level in quiet)
    assert loud[-1][1] == 0 and quiet[-1][1] == 0
    assert all(0 <= level < mc.LEVELS for _, level in loud)


def test_an_empty_reply_is_one_closed_cue():
    assert mc.mouth_cues(np.zeros(0, dtype=np.float32), RATE) == [(0, 0)]
