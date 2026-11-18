"""Speech for a host with no Home: the unit's microphone and speaker through two local servers.

`LocalSttClient` and `LocalTtsClient` take the place of the hub's speech-to-text stream and
text-to-speech call in `StackChanTurnBridge` (same `run` and `speak` shapes). They talk to
OpenAI-style audio endpoints (`/v1/audio/transcriptions`, `/v1/audio/speech`) at the `stt_url` and
`tts_url` set under `[llm]` in robot.toml. Only audio the unit just recorded leaves this process,
and only to those two addresses.
"""

from __future__ import annotations

import io
import logging
import os
import threading
import time
import wave
from pathlib import Path

import numpy as np
import requests

from maipai_body.speech.stt_stream import WAKE_PATIENCE_S, SttStreamError, SttStreamResult
from maipai_body.speech.tts_playback import TtsLinkLost, TtsResult, resample_audio

LOG = logging.getLogger("maipai_body.speech.local_speech")

# Blocks are 32 ms. Speech starts when a block is clearly above the room's noise floor and ends
# after this much quiet. A hard cap keeps one turn from recording forever.
_START_RMS = 0.012
_FLOOR_MULTIPLE = 3.0
_END_QUIET_S = 0.9  # the "normal" wait; quick and patient are in WAIT_S
# Wait after you stop talking (setting): seconds of quiet that end the utterance, plus one more
# hold when the words so far stop mid-clause.
WAIT_S = {"quick": 0.65, "normal": 0.9, "patient": 1.3}
EXTRA_HOLD_S = 0.4
_JOINERS = {
    "and",
    "but",
    "so",
    "because",
    "or",
    "then",
    "if",
    "to",
    "with",
    "that",
    "when",
    "while",
}
_OPEN_ENDINGS = {
    "and",
    "but",
    "so",
    "because",
    "to",
    "or",
    "then",
    "if",
    "with",
    "that",
    "the",
    "a",
    "an",
    "of",
    "for",
    "in",
    "on",
    "at",
    "my",
    "your",
    "is",
    "are",
    "um",
    "uh",
    "like",
    "when",
    "while",
}


def unfinished(text: str) -> bool:
    """True when the words so far stop mid-clause (a comma, a dash, or a joining word last)."""
    cleaned = text.strip().lower()
    if not cleaned:
        return False
    if cleaned.endswith((",", "-", "\u2026", "...", ";", ":")):
        return True
    ended = cleaned.endswith((".", "?", "!"))
    last = (cleaned.rstrip(".?! ").split()[-1:] or [""])[0].strip(",")
    if ended:  # a full stop closes a phrase unless a joining word is the last word
        return last in _JOINERS
    return last in _OPEN_ENDINGS


_MAX_UTTERANCE_S = 20.0
_PRE_ROLL_BLOCKS = 10
_BLOCK_S = 0.032
_POLL_IDLE_S = 0.01


def _wav_bytes(samples: np.ndarray, rate: int = 16000) -> bytes:
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    out = io.BytesIO()
    with wave.open(out, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm.tobytes())
    return out.getvalue()


def _url(base: str, path: str) -> str:
    base = base.rstrip("/")
    return base + path[3:] if base.endswith("/v1") else base + path



def _dump_uplink(samples: np.ndarray) -> None:
    """Debug aid, off unless MAIPAI_DUMP_UPLINK names a folder: keeps the audio of a turn that heard sound but no words,
    so the owner can listen to what the microphone really sent. Household audio never leaves that folder; at most 20 files stay."""
    folder = os.environ.get("MAIPAI_DUMP_UPLINK", "").strip()
    if not folder:
        return
    try:
        path = Path(folder).expanduser()
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        (path / f"empty-{int(time.time())}.wav").write_bytes(_wav_bytes(samples))
        for old in sorted(path.glob("empty-*.wav"))[:-20]:
            old.unlink()
    except OSError:
        LOG.warning("local speech: could not save the uplink clip; check the folder in MAIPAI_DUMP_UPLINK")

class LocalSttClient:
    """One `run` is one wake's worth of listening: find the speech, end on quiet, transcribe."""

    def __init__(
        self,
        stt_url: str | None,
        *,
        engine=None,
        model: str = "",
        session: requests.Session | None = None,
        timeout_s: float = 30.0,
        wake_patience_s: float = WAKE_PATIENCE_S,
        wait=lambda: "quick",
    ) -> None:
        self._wait = wait
        # No address means the built-in engine (`engine.transcribe(samples, rate)`).
        self._engine = engine
        self._url = _url(stt_url, "/v1/audio/transcriptions") if stt_url else "built-in engine/v1"
        self._model, self._timeout = model, timeout_s
        self._session = session or requests.Session()
        self._patience = wake_patience_s

    def _transcribe(self, samples: np.ndarray) -> str:
        if self._engine is not None:
            try:
                return str(self._engine().transcribe(samples, 16000)).strip()
            except Exception as exc:
                raise SttStreamError(f"built-in speech-to-text failed: {exc}") from exc
        try:
            response = self._session.post(
                self._url,
                files={"file": ("speech.wav", _wav_bytes(samples), "audio/wav")},
                data={"model": self._model} if self._model else None,
                timeout=self._timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise SttStreamError(f"local speech-to-text failed: {exc}") from exc
        return str(response.json().get("text", "")).strip()

    def run(self, capture, *, patience_s: float | None = None) -> SttStreamResult:
        began = time.monotonic()
        deadline = began + (self._patience if patience_s is None else patience_s)
        speech_at = None
        pre: list[np.ndarray] = []
        kept: list[np.ndarray] = []
        floor = None
        speaking = False
        loud_run = 0
        quiet = 0.0
        total = 0.0
        wait_s = WAIT_S.get(self._wait(), WAIT_S["quick"])
        extended = False
        text: str | None = None
        while True:
            now = time.monotonic()
            if not speaking and now >= deadline:
                return SttStreamResult(kind="no_speech")
            if total >= _MAX_UTTERANCE_S or (getattr(capture, "closed", False) and speaking):
                break
            blocks = capture.poll_blocks()
            if not blocks:
                time.sleep(_POLL_IDLE_S)
                continue
            for block in blocks:
                rms = (
                    float(np.sqrt(np.mean(np.square(block, dtype=np.float64))))
                    if block.size
                    else 0.0
                )
                if not speaking:
                    floor = rms if floor is None else 0.95 * floor + 0.05 * rms
                    pre.append(block)
                    del pre[:-_PRE_ROLL_BLOCKS]
                    loud_run = (
                        loud_run + 1
                        if rms > max(_START_RMS, _FLOOR_MULTIPLE * (floor or 0.0))
                        else 0
                    )
                    if loud_run >= 3:  # about 100 ms: a click or a pop is not speech
                        speaking = True
                        speech_at = time.monotonic()
                        kept = list(pre)
                        quiet = 0.0
                    continue
                kept.append(block)
                total += _BLOCK_S
                if rms > max(_START_RMS * 0.6, 1.5 * (floor or 0.0)):
                    quiet = 0.0
                    extended = False
                else:
                    quiet += _BLOCK_S
            if speaking and quiet >= wait_s + (EXTRA_HOLD_S if extended else 0.0):
                # Words so far, to see whether the person stopped mid-clause ("and ...").
                text = self._transcribe(np.concatenate(kept))
                if not extended and unfinished(text):
                    extended = True
                    LOG.info(
                        "local speech: the words stop mid-clause; holding %.1f s more", EXTRA_HOLD_S
                    )
                    continue
                break
        samples = np.concatenate(kept) if kept else np.zeros(0, dtype=np.float32)
        if samples.size < 16000 * 0.25:
            return SttStreamResult(kind="no_speech")
        ended = time.monotonic()
        if text is None:
            text = self._transcribe(samples)
        LOG.info(
            "local speech: speech began %.2f s after listening opened, ended %.2f s later "
            "(%.2f s of audio), transcribed in %.2f s",
            (speech_at or began) - began,
            ended - (speech_at or began),
            samples.size / 16000,
            time.monotonic() - ended,
        )
        if not text:
            _dump_uplink(samples)
            return SttStreamResult(kind="no_speech")
        return SttStreamResult(
            kind="final",
            text=text,
            audio=samples,
            speech_s=total,
            engine=(
                "built-in speech engine"
                if self._engine is not None
                else f"local speech server {self._url.split('/v1')[0]}"
            ),
        )


class LocalTtsClient:
    """`speak(text)` fetches one WAV and pushes it into the unit's playback."""

    def __init__(
        self,
        tts_url: str | None,
        playback,
        *,
        engine=None,
        model: str = "",
        session: requests.Session | None = None,
        timeout_s: float = 60.0,
    ) -> None:
        self._engine = engine  # callable returning an object with synthesize(text); None means the address
        self._url = _url(tts_url, "/v1/audio/speech") if tts_url else ""
        self._playback, self._model, self._timeout = playback, model, timeout_s
        self._session = session or requests.Session()

    def speak(
        self,
        text: str,
        *,
        on_first_chunk=None,
        stop_event: threading.Event | None = None,
        turn_id=None,
        generation=None,
    ) -> TtsResult:
        generation = self._playback.generation
        if self._engine is not None:
            return self._speak_built_in(text, stop_event, generation, on_first_chunk)
        try:
            response = self._session.post(
                self._url,
                json={"model": self._model, "input": text, "response_format": "wav"},
                timeout=self._timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise TtsLinkLost(f"local text-to-speech failed: {exc}") from exc
        if stop_event is not None and stop_event.is_set():
            return TtsResult(kind="canceled")
        with wave.open(io.BytesIO(response.content), "rb") as wav:
            if wav.getsampwidth() != 2:
                return TtsResult(
                    kind="error", error="the speech server did not return 16-bit audio"
                )
            rate, channels = wav.getframerate(), wav.getnchannels()
            pcm = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2")
        if channels > 1:
            pcm = pcm.reshape(-1, channels)[:, 0]
        audio = resample_audio(
            (pcm.astype(np.float32) / 32768.0).astype(np.float32),
            rate,
            self._playback.output_samplerate(),
        )
        if not self._playback.push(audio, generation=generation):
            return TtsResult(kind="canceled")
        if on_first_chunk is not None:
            on_first_chunk()
        return TtsResult(kind="done", first_chunk_pushed=True)

    def _speak_built_in(self, text, stop_event, generation, on_first_chunk) -> TtsResult:
        try:
            segments = self._engine().synthesize(text)
        except Exception as exc:
            raise TtsLinkLost(f"built-in text-to-speech failed: {exc}") from exc
        pushed = False
        for segment in segments:
            if stop_event is not None and stop_event.is_set():
                return TtsResult(kind="canceled")
            audio = resample_audio(
                segment.samples, segment.sample_rate, self._playback.output_samplerate()
            )
            if not self._playback.push(audio, generation=generation):
                return TtsResult(kind="canceled")
            if not pushed and on_first_chunk is not None:
                on_first_chunk()
            pushed = True
        return TtsResult(kind="done", first_chunk_pushed=pushed)


def builtin_stt_factory(llm):
    """A callable that builds the built-in speech-to-text engine once, from [llm] model folders."""
    cache: list = []

    def get():
        if not cache:
            if not llm.stt_model_dir:
                raise RuntimeError(
                    "No speech-to-text is set. Set stt_url under [llm] in robot.toml, or "
                    "stt_model_dir to a speech model folder."
                )
            from maipai_body.speech.sherpa_engines import MoonshineStt

            cache.append(MoonshineStt(Path(llm.stt_model_dir)))
        return cache[0]

    return get


def builtin_tts_factory(llm):
    """The same for text-to-speech, from tts_model, tts_tokens and tts_data_dir."""
    cache: list = []

    def get():
        if not cache:
            if not all((llm.tts_model, llm.tts_tokens, llm.tts_data_dir)):
                raise RuntimeError(
                    "No text-to-speech is set. Set tts_url under [llm] in robot.toml, or "
                    "tts_model, tts_tokens and tts_data_dir to a voice model."
                )
            from maipai_body.speech.sherpa_engines import PiperTts

            cache.append(PiperTts("local", llm.tts_model, llm.tts_tokens, llm.tts_data_dir))
        return cache[0]

    return get
