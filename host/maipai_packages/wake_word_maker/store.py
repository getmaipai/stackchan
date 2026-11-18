"""Clips on disk: one folder per word, positives and negatives, each a mono 16-bit 16 kHz WAV of about a second."""

from __future__ import annotations

import io
import re
import shutil
import wave
from pathlib import Path

MIN_SECONDS, MAX_SECONDS = 0.5, 2.0
MAX_CLIP_BYTES = 120_000
MAX_CLIPS = 60
MIN_CLIPS = 12
_WORD = re.compile(r"^[a-z][a-z0-9_-]{1,31}$")
KINDS = ("positive", "negative")


class ClipError(ValueError):
    """The clip was not stored; the message says why and what to do."""


class WakeStore:
    def __init__(self, folder: Path) -> None:
        self.folder = Path(folder)

    def word_dir(self, word: str) -> Path:
        if not _WORD.match(word):
            raise ClipError("Name the word with 2 to 32 lowercase letters, digits, dashes or underscores, starting with a letter.")
        return self.folder / word

    def clip_dir(self, word: str, kind: str) -> Path:
        if kind not in KINDS:
            raise ClipError("A clip is either the wake word (positive) or other speech (negative).")
        return self.word_dir(word) / kind

    def add_clip(self, word: str, kind: str, wav: bytes) -> int:
        folder = self.clip_dir(word, kind)
        if len(wav) > MAX_CLIP_BYTES:
            raise ClipError("That recording is too long. Record about one second.")
        try:
            with wave.open(io.BytesIO(wav), "rb") as handle:
                rate, width, channels, frames = handle.getframerate(), handle.getsampwidth(), handle.getnchannels(), handle.getnframes()
        except (wave.Error, EOFError):
            raise ClipError("That recording is not a WAV file. Try recording again.") from None
        if (rate, width, channels) != (16000, 2, 1):
            raise ClipError("The recording must be mono, 16-bit, 16000 samples a second. Try recording again.")
        if not MIN_SECONDS <= frames / rate <= MAX_SECONDS:
            raise ClipError("Record about one second of the word, not more than two and not less than half a second.")
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        count = len(list(folder.glob("clip-*.wav")))
        if count >= MAX_CLIPS:
            raise ClipError(f"That is the most clips ({MAX_CLIPS}). Train now, or clear the clips and start again.")
        (folder / f"clip-{count + 1:03d}.wav").write_bytes(wav)
        return count + 1

    def counts(self, word: str) -> dict[str, int]:
        return {kind: len(list(self.clip_dir(word, kind).glob("clip-*.wav"))) for kind in KINDS}

    def clear(self, word: str) -> None:
        shutil.rmtree(self.word_dir(word), ignore_errors=True)

    def words(self) -> list[str]:
        return sorted(p.name for p in self.folder.iterdir() if p.is_dir() and _WORD.match(p.name)) if self.folder.is_dir() else []
