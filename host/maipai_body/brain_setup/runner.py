"""Start and stop the local model server (llama.cpp `llama-server`) and time one test turn. Both are injectable for tests."""

from __future__ import annotations

import subprocess
import threading
import time
import wave
from collections.abc import Callable
from pathlib import Path
from typing import Any

from maipai_body.brain_setup import catalog


class LlamaServer:
    """One `llama-server` child on 127.0.0.1 only. It stops with the host."""

    def __init__(self, popen: Callable[..., Any] = subprocess.Popen) -> None:
        self._popen = popen
        self._proc: Any = None
        self._lock = threading.Lock()

    def start(self, server: str, model: str, port: int = catalog.LLAMA_PORT) -> None:
        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                return
            if not Path(server).is_file() or not Path(model).is_file():
                raise RuntimeError("The local model server or model is missing. Open the Brain page and press Install again.")
            self._proc = self._popen([server, "-m", model, "--host", "127.0.0.1", "--port", str(port), "-c", "2048", "--no-webui"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def stop(self) -> None:
        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=5)
                except Exception:
                    self._proc.kill()
            self._proc = None

    def running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None


def wait_until_up(url: str, *, timeout: float = 90.0, get: Callable[..., Any] | None = None, sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic) -> bool:
    import requests

    get = get or requests.get
    end = clock() + timeout
    while clock() < end:
        try:
            if get(f"{url}/health", timeout=2).status_code == 200:
                return True
        except requests.RequestException:
            pass
        sleep(0.5)
    return False


def time_one_turn(base_url: str, model: str, *, post: Callable[..., Any] | None = None, clock: Callable[[], float] = time.monotonic) -> dict[str, Any]:
    """One short streamed chat turn against the local model: seconds to the first word and to the end (both measured)."""
    import json

    import requests

    post = post or requests.post
    started = clock()
    response = post(f"{base_url}/v1/chat/completions", json={"model": model, "messages": [{"role": "user", "content": "Say hello in one short sentence."}], "max_tokens": 24, "stream": True}, timeout=120, stream=True)
    response.raise_for_status()
    first: float | None = None
    text = ""
    for raw in response.iter_lines():
        line = raw.decode() if isinstance(raw, bytes) else raw
        if not line.startswith("data:") or line.strip() == "data: [DONE]":
            continue
        try:
            piece = json.loads(line[5:])["choices"][0].get("delta", {}).get("content") or ""
        except (ValueError, KeyError, IndexError):
            continue
        if piece and first is None:
            first = clock() - started
        text += piece
    total = clock() - started
    return {"model_first_word_s": round(first if first is not None else total, 2), "model_total_s": round(total, 2), "reply": text[:80]}


def time_speech(paths: dict[str, str]) -> dict[str, Any]:
    """Seconds for the speech to text on a real spoken clip from the model's own package and for the first sentence of text to speech, when the speech engines load.
    Returns {} when they do not (the page says the speech stages are timed on the first real turn)."""
    try:
        import numpy as np

        from maipai_body.speech.sherpa_engines import MoonshineStt, PiperTts

        stt = MoonshineStt(paths["stt_model_dir"])
        tts = PiperTts("local", paths["tts_model"], paths["tts_tokens"], paths["tts_data_dir"])
        clip = Path(paths["stt_model_dir"]) / "test_wavs" / "0.wav"  # a real spoken sentence that ships in the model's package
        if clip.is_file():
            with wave.open(str(clip)) as handle:
                rate = handle.getframerate()
                samples = np.frombuffer(handle.readframes(handle.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        else:
            rate, samples = 16000, np.zeros(16000 * 3, dtype=np.float32)
        began = time.monotonic()
        text = stt.transcribe(samples, rate)
        stt_s = time.monotonic() - began
        began = time.monotonic()
        next(iter(tts.synthesize("Hello. This is a test.")), None)
        return {"stt_s": round(stt_s, 2), "stt_clip_s": round(len(samples) / rate, 1), "stt_heard": text[:60], "tts_first_sentence_s": round(time.monotonic() - began, 2)}
    except Exception:  # sherpa-onnx missing or a model that does not load: reported by the caller as untimed
        return {}
