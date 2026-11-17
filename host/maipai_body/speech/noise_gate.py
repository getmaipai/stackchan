"""A gate in front of the language model: drop what is not a person talking to the robot.

A fan, a kettle or the room's hiss can wake a speech engine into inventing "thank you". The gate
looks at the audio (is anything voiced, is the sound just steady noise) and at the words (the usual
invented phrases), and says why it dropped an utterance. Levels: ``low``, ``medium``, ``high``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

LEVELS = ("low", "medium", "high")
DEFAULT_LEVEL = "medium"
FRAME = 512  # 32 ms at 16 kHz
RATE = 16000
_PITCH_LAGS = (RATE // 400, RATE // 70)  # 70 to 400 Hz


@dataclass(frozen=True)
class Thresholds:
    min_voiced_s: float  # least voiced audio worth answering
    steady_cv: float  # energy variation below this is steady noise (speech is bursty)
    pitch_corr: float  # autocorrelation peak that counts a frame as voiced
    min_rms: float  # frames quieter than this are never voiced


THRESHOLDS = {
    "low": Thresholds(0.2, 0.20, 0.30, 0.004),
    "medium": Thresholds(0.4, 0.35, 0.35, 0.006),
    "high": Thresholds(0.6, 0.50, 0.45, 0.010),
}

# What speech engines invent from noise, per language. Matched on the whole normalized utterance.
HALLUCINATIONS = {
    "en": {
        "thank you",
        "thanks",
        "you",
        "bye",
        "bye bye",
        "okay",
        "ok",
        "oh",
        "uh",
        "um",
        "hmm",
        "yeah",
        "so",
        "the",
        "i",
        "thanks for watching",
        "thank you for watching",
        "goodbye",
    },
    "es": {
        "gracias",
        "adios",
        "adiós",
        "hola",
        "si",
        "sí",
        "eh",
        "mmm",
        "ah",
        "vale",
        "gracias por ver el video",
    },
}
_PUNCT = re.compile(r"[^\w\s']", re.UNICODE)


def level_from(value: object) -> str:
    return value if isinstance(value, str) and value in LEVELS else DEFAULT_LEVEL


def _frames(samples: np.ndarray) -> np.ndarray:
    n = len(samples) // FRAME
    return samples[: n * FRAME].reshape(n, FRAME).astype(np.float64) if n else np.zeros((0, FRAME))


def _pitched(frame: np.ndarray) -> float:
    """Normalized autocorrelation peak between 70 and 400 Hz (0 to 1)."""
    frame = frame - frame.mean()
    energy = float(np.dot(frame, frame))
    if energy <= 1e-12:
        return 0.0
    spec = np.fft.rfft(frame, 2 * FRAME)
    corr = np.fft.irfft(spec * np.conj(spec))[:FRAME]
    lo, hi = _PITCH_LAGS
    return float(np.max(corr[lo:hi]) / energy)


@dataclass(frozen=True)
class Verdict:
    keep: bool
    reason: str = ""
    voiced_s: float = 0.0


def check_audio(samples: np.ndarray, level: str = DEFAULT_LEVEL) -> Verdict:
    t = THRESHOLDS[level_from(level)]
    frames = _frames(np.asarray(samples, dtype=np.float32))
    if not len(frames):
        return Verdict(False, "no audio")
    rms = np.sqrt(np.mean(frames**2, axis=1))
    voiced = np.array([r >= t.min_rms and _pitched(f) >= t.pitch_corr for f, r in zip(frames, rms)])
    voiced_s = float(voiced.sum()) * FRAME / RATE
    loud = rms[rms >= t.min_rms]
    mean = float(rms.mean())
    cv = float(rms.std() / mean) if mean > 1e-9 else 0.0
    if not len(loud):
        return Verdict(False, "too quiet", voiced_s)
    if cv < t.steady_cv:
        return Verdict(False, f"steady background noise (energy variation {cv:.2f})", voiced_s)
    if voiced_s < t.min_voiced_s:
        return Verdict(
            False, f"only {voiced_s:.2f} s of voiced sound (needs {t.min_voiced_s:.1f})", voiced_s
        )
    return Verdict(True, "", voiced_s)


def normalize(text: str) -> str:
    return " ".join(_PUNCT.sub(" ", text.lower()).split())


def check_text(text: str, language: str = "en") -> Verdict:
    words = normalize(text)
    if not words:
        return Verdict(False, "only punctuation or nothing")
    if words in HALLUCINATIONS.get(language[:2].lower(), HALLUCINATIONS["en"]):
        return Verdict(False, f"a phrase engines invent from noise ({words!r})")
    parts = words.split()
    if len(parts) >= 3 and len(set(parts)) == 1:
        return Verdict(False, "one word repeated")
    return Verdict(True)
