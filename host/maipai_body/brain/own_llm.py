"""Own-LLM brain using owner-configured HTTP services and optional local speech models."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import re
import threading
import uuid
import wave
from collections import deque
from collections.abc import Callable, Iterator
from pathlib import Path
from urllib.parse import urlsplit

import numpy as np
import requests

from maipai_body.brain.interface import BrainFeature, TurnRequest
from maipai_body.speech.turn_client import TurnEvent

_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_CHAT_PATH = "/v1/chat/completions"
NOT_INSTALLED = "I could not reach the model at the configured model; check robot.toml."


def _endpoint(base: str, path: str) -> str:
    """Join an OpenAI-style base and a /v1/... path; a base already ending in /v1 or the full path is kept."""
    base = base.rstrip("/")
    if base.endswith(path):
        return base
    if base.endswith("/v1") and path.startswith("/v1/"):
        return base + path[3:]
    return base + path


def _sentences(text: str) -> tuple[list[str], str]:
    parts = _SENTENCE.split(text)
    complete = [part.strip() for part in parts[:-1] if part.strip()]
    return complete, parts[-1]


def _whole_completion(lines: list[str]) -> str:
    """The text of a non-streamed chat completion body (read line by line), else empty."""
    try:
        body = json.loads("\n".join(lines))
        content = body["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        return ""
    return content.strip() if isinstance(content, str) else ""


def _host(url: str) -> str:
    try:
        return urlsplit(url).hostname or "the configured model"
    except ValueError:
        return "the configured model"


def _wav_bytes(samples: np.ndarray, sample_rate: int) -> bytes:
    data = np.clip(samples, -1, 1)
    pcm = (data * 32767).astype("<i2").tobytes()
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)
    return output.getvalue()


class OwnLLMBrain:
    """OpenAI-compatible turn client with bounded in-memory conversation history."""

    def __init__(
        self,
        config,
        *,
        session: requests.Session | None = None,
        stt_engine=None,
        tts_engine=None,
        on_sentence: Callable[[str], None] | None = None,
    ) -> None:
        self.config = config
        self._session = session or requests.Session()
        self._stt_engine = stt_engine
        self._tts_engine = tts_engine
        self._on_sentence = on_sentence
        self.memory = None  # the memory notes package, set by build_brain only when it is switched on
        self._history: dict[str, deque[dict[str, str]]] = {}
        self._cancel: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def capabilities(self) -> frozenset[BrainFeature]:
        provided = {BrainFeature.LLM, BrainFeature.TIMERS}
        local_speech_ready = importlib.util.find_spec("sherpa_onnx") is not None
        stt_files = (
            [
                Path(self.config.stt_model_dir) / name
                for name in (
                    "preprocess.onnx",
                    "encode.int8.onnx",
                    "uncached_decode.int8.onnx",
                    "cached_decode.int8.onnx",
                    "tokens.txt",
                )
            ]
            if self.config.stt_model_dir
            else []
        )
        tts_files = [
            Path(path)
            for path in (self.config.tts_model, self.config.tts_tokens, self.config.tts_data_dir)
            if path
        ]
        if (
            self.config.stt_url
            or self._stt_engine is not None
            or (
                local_speech_ready
                and len(stt_files) == 5
                and all(path.is_file() for path in stt_files)
            )
        ):
            provided.add(BrainFeature.STT)
        if (
            self.config.tts_url
            or self._tts_engine is not None
            or (
                local_speech_ready
                and len(tts_files) == 3
                and all(path.exists() for path in tts_files)
            )
        ):
            provided.add(BrainFeature.TTS)
        return frozenset(provided)

    def stream_turn(self, request: TurnRequest) -> Iterator[TurnEvent]:
        if not self.config.url or not self.config.model:
            yield TurnEvent(reply_text=NOT_INSTALLED)
            return
        speaker = (request.speaker_evidence or {}).get("person_id") if self.memory is not None else None
        if self.memory is not None:
            spoken = self.memory.handle(request.text, speaker)
            if spoken is not None:  # a remember, forget or read-back request: answered here, no model call
                yield TurnEvent(reply_text=spoken, delta_text=spoken, delta_whole=True)
                return
        turn_id = uuid.uuid4().hex
        stop = threading.Event()
        with self._lock:
            self._cancel[turn_id] = stop
        conversation = request.conversation_id or "default"
        history = self._history.setdefault(
            conversation, deque(maxlen=max(1, self.config.history_messages))
        )
        system = self.config.persona
        if request.instructions:
            system = f"{system}\n\n{request.instructions}"
        if self.memory is not None:
            notes_text = self.memory.context(speaker)
            if notes_text:
                system = f"{system}\n\n{notes_text}"
        messages = [{"role": "system", "content": system}]
        messages.extend(history)
        messages.append({"role": "user", "content": request.text})
        headers = {"Content-Type": "application/json"}
        env_name = self.config.api_key_env
        if env_name and os.environ.get(env_name):
            headers["Authorization"] = f"Bearer {os.environ[env_name]}"
        url = _endpoint(self.config.url, _CHAT_PATH)
        reply = ""
        pending = ""
        raw: list[str] = []
        saw_delta = False
        spoken_any = False

        def piece(sentence: str) -> TurnEvent:
            if self._on_sentence is not None:
                self._on_sentence(sentence)
            return TurnEvent(
                reply_text=sentence, turn_id=turn_id, delta_text=sentence, delta_whole=True
            )

        try:
            with self._session.post(
                url,
                json={"model": self.config.model, "messages": messages, "stream": True},
                headers=headers,
                stream=True,
                timeout=self.config.timeout_seconds,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines(chunk_size=1, decode_unicode=True):
                    if stop.is_set():
                        return
                    if not line:
                        continue
                    if isinstance(line, bytes):
                        line = line.decode("utf-8", errors="replace")
                    if not saw_delta:
                        raw.append(line)
                    if line.startswith("data:"):
                        line = line[5:].strip()
                    if line == "[DONE]":
                        break
                    try:
                        chunk = json.loads(line)
                        delta = chunk["choices"][0].get("delta", {}).get("content", "")
                    except (ValueError, KeyError, IndexError, TypeError):
                        continue
                    if not isinstance(delta, str) or not delta:
                        continue
                    saw_delta = True
                    raw.clear()
                    reply += delta
                    pending += delta
                    complete, pending = _sentences(pending)
                    for sentence in complete:
                        spoken_any = True
                        yield piece(sentence)
            if stop.is_set():
                return
            if not saw_delta:
                # The endpoint did not stream: the body is one ordinary completion.
                whole = _whole_completion(raw)
                if whole:
                    reply = whole
                    complete, pending = _sentences(whole + " ")
                    for sentence in complete:
                        spoken_any = True
                        yield piece(sentence)
                    pending = ""
            if pending.strip():
                spoken_any = True
                yield piece(pending.strip())
            if reply.strip():
                history.extend(
                    (
                        {"role": "user", "content": request.text},
                        {"role": "assistant", "content": reply.strip()},
                    )
                )
            yield TurnEvent(reply_text=reply.strip(), turn_id=turn_id, conversation_id=conversation)
        except Exception as exc:  # the voice link always receives a spoken failure result
            del exc
            message = f"I could not reach the model at {_host(self.config.url)}; check robot.toml."
            # After some sentences were already spoken, the failure is one more spoken sentence.
            yield TurnEvent(
                reply_text=message,
                turn_id=turn_id,
                conversation_id=conversation,
                delta_text=message if spoken_any else None,
                delta_whole=spoken_any,
            )
        finally:
            with self._lock:
                self._cancel.pop(turn_id, None)

    def cancel_turn(self, turn_id: str) -> bool:
        with self._lock:
            stop = self._cancel.get(turn_id)
        if stop is None:
            return False
        stop.set()
        return True

    def transcribe_stream(self, samples, sample_rate: int = 16000, **_kwargs) -> str:
        if self.config.stt_url:
            audio = _wav_bytes(np.asarray(samples, dtype=np.float32), sample_rate)
            response = self._session.post(
                _endpoint(self.config.stt_url, "/v1/audio/transcriptions"),
                files={"file": ("speech.wav", audio, "audio/wav")},
                data={"model": self.config.model},
                timeout=self.config.timeout_seconds,
            )
            response.raise_for_status()
            return str(response.json().get("text", "")).strip()
        engine = self._stt_engine or self._local_stt()
        return engine.transcribe(np.asarray(samples, dtype=np.float32), sample_rate)

    def speak(
        self, text: str, *, playback=None, stop_event=None, sample_rate: int = 16000, **_kwargs
    ):
        if self.config.tts_url:
            if playback is None:
                raise RuntimeError(
                    "Audio playback is unavailable; connect the robot speaker and try again."
                )
            response = self._session.post(
                _endpoint(self.config.tts_url, "/v1/audio/speech"),
                json={"model": self.config.model, "input": text, "response_format": "wav"},
                stream=True,
                timeout=self.config.timeout_seconds,
            )
            response.raise_for_status()
            payload = bytearray()
            for chunk in response.iter_content(4096):
                if stop_event is not None and stop_event.is_set():
                    response.close()
                    return False
                payload.extend(chunk)
            with wave.open(io.BytesIO(payload), "rb") as wav:
                channels, rate, width = wav.getnchannels(), wav.getframerate(), wav.getsampwidth()
                if width != 2:
                    raise ValueError("Speech server returned audio that is not 16-bit PCM.")
                pcm = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2")
                if channels > 1:
                    pcm = pcm.reshape(-1, channels)[:, 0]
                audio = (pcm.astype(np.float32) / 32768.0).astype(np.float32)
            from maipai_body.speech.tts_playback import resample_audio

            audio = resample_audio(audio, rate, playback.output_samplerate())
            if stop_event is not None and stop_event.is_set():
                return False
            return playback.push(audio)
        engine = self._tts_engine or self._local_tts()
        if playback is None:
            return engine.synthesize(text)
        for segment in engine.synthesize(text):
            if stop_event is not None and stop_event.is_set():
                return False
            from maipai_body.speech.tts_playback import resample_audio

            audio = resample_audio(
                segment.samples, segment.sample_rate, playback.output_samplerate()
            )
            if not playback.push(audio):
                return False
        return True

    def _local_stt(self):
        if not self.config.stt_model_dir:
            raise RuntimeError(
                "Local speech recognition is not configured; set llm.stt_url or "
                "install a speech model."
            )
        from maipai_body.speech.sherpa_engines import EngineUnavailable, MoonshineStt

        try:
            return MoonshineStt(Path(self.config.stt_model_dir))
        except EngineUnavailable as exc:
            raise RuntimeError(str(exc)) from exc

    def _local_tts(self):
        if not all((self.config.tts_model, self.config.tts_tokens, self.config.tts_data_dir)):
            raise RuntimeError(
                "Local speech output is not configured; set llm.tts_url or install a voice model."
            )
        from maipai_body.speech.sherpa_engines import EngineUnavailable, PiperTts

        try:
            return PiperTts(
                "local", self.config.tts_model, self.config.tts_tokens, self.config.tts_data_dir
            )
        except EngineUnavailable as exc:
            raise RuntimeError(str(exc)) from exc

    def describe(self, request):
        del request
        return None

    def people(self):
        return []

    def settings(self):
        return {}

    def reminders(self, operation, payload=None):
        del operation, payload
        return []


# Kept as an import alias for callers upgraded from the placeholder phase.
NotYetBuilt = OwnLLMBrain
