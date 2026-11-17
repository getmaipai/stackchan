# ruff: noqa: E501
"""Filler sounds: the small non-word sounds a person makes while thinking (hmm, uh, ah, oh).

Two halves live here, both on the host:

* :class:`FillerGenerator` renders a pack of short sounds with the host's own local voice (the same speech
  server the replies use), several takes each, trims the silence, normalizes the loudness, packs them as 8-bit
  mu-law at 16 kHz (about 16 KB a second, so a full set stays under the 400 KB pack limit) and keeps the pack
  in the library per voice (``~/.config/maipai/stackchan-fillers``, mode 700).
* :class:`FillerPlayer` plays one when a turn has had no first audio for the unit's wait (the "While it thinks"
  setting: none, tone or phrase). A unit that has the ``self.filler.play`` tool plays its own cached copy; a unit
  without it gets one short sound through the voice link from the host, once per turn. Never the same sound twice
  in a row; mute and full quiet are checked by the caller before it asks.

The pack payload is a zip with ``index.json`` (``{"rate": 16000, "codec": "mulaw", "clips": [{"name", "file",
"ms"}]}``) and one ``.ulaw`` file per take.
"""

from __future__ import annotations

import json
import logging
import random
import threading
from collections.abc import Callable
from typing import Any

import numpy as np

from maipai_body import packs as packs_mod
from maipai_body.unit_tools import ToolProbe

logger = logging.getLogger("maipai_body.fillers")

RATE = 16000  # the stored rate
OUT_RATE = 24000  # what the voice link plays
MAX_CLIP_S = 1.2
TARGET_PEAK = 0.5  # about -6 dBFS: a filler is quieter than speech
SILENCE_DB = -42.0

# Sound name -> three takes, written so the same voice says them a little differently each time.
RECIPES: dict[str, dict[str, tuple[str, ...]]] = {
    "en": {
        "hmm": ("Hmm.", "Hmmm...", "Mmm."),
        "uh": ("Uh...", "Uh,", "Uhh."),
        "um": ("Um...", "Um,", "Umm."),
        "ah": ("Ah.", "Ahh.", "Ah!"),
        "oh": ("Oh.", "Ohh.", "Oh!"),
        "aha": ("Aha!", "Aha.", "Ahaa."),
        "mm_hm": ("Mm-hm.", "Mm hm.", "Mhm."),
        "sigh": ("Haaah.", "Hhhaah.", "Hah."),
        "breath": ("Hhh.", "Hh.", "Hhhh."),
        "laugh": ("Heh.", "Heh heh.", "Hehe."),
        "throat": ("Ahem.", "Ahem,", "Ahem!"),
    },
    "es": {
        "hmm": ("Mmm.", "Mmmm...", "Hmm."),
        "uh": ("Eh...", "Eh,", "Ehh."),
        "um": ("Este...", "Esto...", "Pues..."),
        "ah": ("Ah.", "Ahh.", "Ah!"),
        "oh": ("Oh.", "Ohh.", "Oh!"),
        "aha": ("Ajá!", "Ajá.", "Ajaa."),
        "mm_hm": ("Mm-hm.", "Mm hm.", "Aja."),
        "sigh": ("Haaah.", "Ayy.", "Hah."),
        "breath": ("Hhh.", "Hh.", "Hhhh."),
        "laugh": ("Je.", "Je je.", "Jeje."),
        "throat": ("Ejem.", "Ejem,", "Ejem!"),
    },
}

SAY: dict[str, tuple[str, str]] = {
    "no_engine": (
        "There is no local voice engine to make the sounds with. Set up the local speech server in robot.toml, then try again.",
        "No hay un motor de voz local para crear los sonidos. Configura el servidor de voz local en robot.toml e inténtalo de nuevo.",
    ),
    "busy": (
        "The sounds are already being made. Wait for them to finish.",
        "Los sonidos ya se están creando. Espera a que terminen.",
    ),
    "failed": (
        "The voice engine did not answer, so no sounds were made. Check that the local speech server is running, then try again.",
        "El motor de voz no respondió, así que no se crearon sonidos. Comprueba que el servidor de voz local esté activo e inténtalo de nuevo.",
    ),
    "started": ("Making the sounds. This takes a minute.", "Creando los sonidos. Tarda un minuto."),
}


def say(lang: str | None, code: str) -> str:
    english, spanish = SAY[code]
    return spanish if (lang or "").lower().startswith("es") else english


# ---- audio helpers (numpy only) ----------------------------------------------------------------------


def resample(samples: np.ndarray, rate: int, target: int) -> np.ndarray:
    if rate == target or len(samples) == 0:
        return samples.astype(np.float32)
    n = max(1, int(round(len(samples) * target / rate)))
    return np.interp(np.linspace(0, len(samples) - 1, n), np.arange(len(samples)), samples).astype(np.float32)


def trim_silence(samples: np.ndarray, rate: int, *, margin_s: float = 0.02) -> np.ndarray:
    """Cut the quiet at both ends, keeping a short margin so a soft start is not clipped."""
    if len(samples) == 0:
        return samples
    peak = float(np.max(np.abs(samples)))
    if peak <= 1e-6:
        return samples[:0]
    floor = peak * 10 ** (SILENCE_DB / 20)
    loud = np.nonzero(np.abs(samples) > floor)[0]
    if len(loud) == 0:
        return samples[:0]
    margin = int(margin_s * rate)
    return samples[max(0, loud[0] - margin) : min(len(samples), loud[-1] + margin + 1)]


def normalize(samples: np.ndarray, rate: int, *, peak: float = TARGET_PEAK, fade_s: float = 0.006) -> np.ndarray:
    if len(samples) == 0:
        return samples
    top = float(np.max(np.abs(samples)))
    out = (samples * (peak / top)).astype(np.float32) if top > 0 else samples
    fade = min(int(fade_s * rate), len(out) // 2)
    if fade > 0:
        ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
        out[:fade] *= ramp
        out[-fade:] *= ramp[::-1]
    return out


_MU = 255.0


def mulaw_encode(samples: np.ndarray) -> bytes:
    x = np.clip(samples, -1.0, 1.0)
    y = np.sign(x) * np.log1p(_MU * np.abs(x)) / np.log1p(_MU)
    return ((y + 1.0) * 127.5).round().astype(np.uint8).tobytes()


def mulaw_decode(data: bytes) -> np.ndarray:
    y = np.frombuffer(data, dtype=np.uint8).astype(np.float32) / 127.5 - 1.0
    return (np.sign(y) * ((1.0 + _MU) ** np.abs(y) - 1.0) / _MU).astype(np.float32)


def render_clip(samples: np.ndarray, rate: int) -> np.ndarray | None:
    """One synthesized take, trimmed to its sound, normalized, at the stored rate; None if it came out empty."""
    mono = resample(np.asarray(samples, dtype=np.float32).reshape(-1), rate, RATE)
    cut = trim_silence(mono, RATE)
    if len(cut) < int(0.06 * RATE):
        return None
    return normalize(cut[: int(MAX_CLIP_S * RATE)], RATE)


# ---- the generator ----------------------------------------------------------------------------------


class FillerGenerator:
    """Renders a pack of fillers with ``synth(text) -> (samples, rate)`` and keeps it in the library."""

    def __init__(self, synth: Callable[[str], tuple[np.ndarray, int]] | None, library: packs_mod.PackLibrary) -> None:
        self.synth, self.library = synth, library
        self.status: dict[str, Any] = {"running": False, "done": 0, "total": 0, "error": "", "last": ""}
        self._lock = threading.Lock()

    def render(self, lang: str = "en", progress: Callable[[int, int], None] | None = None) -> tuple[bytes, list[dict[str, Any]]]:
        """The pack payload and its clip list. Takes that fail are skipped; a sound with no take is left out."""
        assert self.synth is not None
        recipe = RECIPES.get("es" if lang == "es" else "en")
        assert recipe is not None
        total, done = sum(len(v) for v in recipe.values()), 0
        clips: list[dict[str, Any]] = []
        files: dict[str, bytes] = {}
        for name, takes in recipe.items():
            for take, text in enumerate(takes, 1):
                done += 1
                if progress:
                    progress(done, total)
                try:
                    samples, rate = self.synth(text)
                except Exception:
                    logger.debug("filler %s take %d not made", name, take, exc_info=True)
                    continue
                clip = render_clip(samples, rate)
                if clip is None:
                    continue
                file = f"{name}_{take}.ulaw"
                files[file] = mulaw_encode(clip)
                clips.append({"name": name, "file": file, "ms": int(len(clip) * 1000 / RATE)})
        # Keep the pack inside the size gate: drop the third takes first, then the second ones.
        while sum(len(b) for b in files.values()) > packs_mod.MAX_BYTES["filler"] - 2000:
            drop = next((c for take in (3, 2) for c in clips if c["file"].endswith(f"_{take}.ulaw")), None)
            if drop is None:
                break
            clips.remove(drop)
            del files[drop["file"]]
        index = {"rate": RATE, "codec": "mulaw", "lang": lang, "clips": clips}
        files["index.json"] = json.dumps(index, separators=(",", ":")).encode()
        return packs_mod.zip_payload(files), clips

    def generate(self, voice: str, lang: str = "en") -> dict[str, Any]:
        """Make and keep the pack for one voice. Blocking; :meth:`start` runs it in the background."""
        if self.synth is None:
            raise packs_mod.PackError(say(lang, "no_engine"), "no_engine")
        payload, clips = self.render(lang, lambda d, t: self.status.update(done=d, total=t))
        if not clips:
            raise packs_mod.PackError(say(lang, "failed"), "failed")
        pack = packs_mod.make_pack("filler", f"Fillers {lang}", payload, voice=voice or "default", lang=lang)
        return self.library.add(pack, lang)

    def start(self, voice: str, lang: str = "en") -> dict[str, Any]:
        if self.synth is None:
            raise packs_mod.PackError(say(lang, "no_engine"), "no_engine")
        with self._lock:
            if self.status["running"]:
                raise packs_mod.PackError(say(lang, "busy"), "busy")
            self.status.update(running=True, done=0, total=0, error="", last="")

        def work() -> None:
            try:
                info = self.generate(voice, lang)
                self.status["last"] = info["id"]
            except Exception as error:
                logger.warning("filler sounds not made: %s", error)
                self.status["error"] = str(error) if isinstance(error, packs_mod.PackError) else say(lang, "failed")
            finally:
                self.status["running"] = False

        threading.Thread(target=work, name="filler-generator", daemon=True).start()
        return {"ok": True, "message": say(lang, "started"), "status": dict(self.status)}


def local_synth(tts_url: str, *, model: str = "", timeout_s: float = 30.0) -> Callable[[str], tuple[np.ndarray, int]]:
    """``synth(text)`` against the host's own local speech server (the one replies use)."""
    import io
    import wave

    import requests

    from maipai_body.speech.local_speech import _url

    url = _url(tts_url, "/v1/audio/speech")

    def synth(text: str) -> tuple[np.ndarray, int]:
        response = requests.post(url, json={"model": model, "input": text, "response_format": "wav"}, timeout=timeout_s)
        response.raise_for_status()
        with wave.open(io.BytesIO(response.content), "rb") as wav:
            rate, channels = wav.getframerate(), wav.getnchannels()
            pcm = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2")
        if channels > 1:
            pcm = pcm.reshape(-1, channels)[:, 0]
        return pcm.astype(np.float32) / 32768.0, rate

    return synth


# ---- the player -------------------------------------------------------------------------------------


def tone(rate: int = OUT_RATE) -> np.ndarray:
    """The "tone" option: two short soft notes, language-free, about a quarter second."""
    out = []
    for freq, length in ((660.0, 0.09), (880.0, 0.12)):
        t = np.arange(int(length * rate)) / rate
        env = np.sin(np.pi * t / length) ** 2
        out.append((0.18 * env * np.sin(2 * np.pi * freq * t)).astype(np.float32))
    return np.concatenate(out)


class FillerPlayer:
    """Plays the "While it thinks" sound: the unit's own copy when it has the tool, else one from the host."""

    def __init__(
        self,
        library: packs_mod.PackLibrary,
        active: packs_mod.ActiveStore | None = None,
        probe: ToolProbe | None = None,
        *,
        rng: random.Random | None = None,
        tone_on_unit: Callable[[str], bool] | None = None,
    ) -> None:
        self.library, self.active, self.probe = library, active, probe
        # True when the unit plays its own thinking tone (the firmware's, on by default): the host then
        # stays silent for the "tone" choice instead of doubling it.
        self._tone_on_unit = tone_on_unit or (lambda _device_id: False)
        self._rng = rng or random.Random()
        self._last: dict[str, str] = {}
        self._clips: dict[str, list[tuple[str, np.ndarray]]] = {}
        self._lock = threading.Lock()
        self.played: list[tuple[str, str]] = []  # (device id tail, sound) for the last few, for tests and the log

    def _pack_for(self, device_id: str, lang: str | None) -> str | None:
        if self.active is not None:
            pid = self.active.get(device_id).get("filler")
            if pid:
                return pid
        want = "es" if (lang or "").lower().startswith("es") else "en"
        listed = self.library.list("filler")
        for item in listed:
            if item.get("lang") == want:
                return item["id"]
        return listed[0]["id"] if listed else None

    def _load(self, pack_id: str) -> list[tuple[str, np.ndarray]]:
        with self._lock:
            if pack_id in self._clips:
                return self._clips[pack_id]
        try:
            files = packs_mod.unzip_payload(self.library.get(pack_id).payload)
            index = json.loads(files["index.json"])
            rate = int(index.get("rate", RATE))
            clips = [(c["name"], resample(mulaw_decode(files[c["file"]]), rate, OUT_RATE)) for c in index["clips"] if c["file"] in files]
        except Exception:
            logger.debug("filler pack %s unreadable", pack_id, exc_info=True)
            clips = []
        with self._lock:
            self._clips[pack_id] = clips
        return clips

    def pick(self, device_id: str, lang: str | None) -> tuple[str, np.ndarray] | None:
        """A random take of a sound that is not the one played last on this unit; None with no pack."""
        pack_id = self._pack_for(device_id, lang)
        clips = self._load(pack_id) if pack_id else []
        if not clips:
            return None
        # "mm_hm", "hmm", "uh", "um", "ah" and "oh" suit a wait; sighs and laughs do not
        fit = [c for c in clips if c[0] in {"hmm", "uh", "um", "ah", "oh", "aha", "mm_hm"}] or clips
        names = sorted({n for n, _ in fit})
        last = self._last.get(device_id)
        choices = [n for n in names if n != last] or names
        name = self._rng.choice(choices)
        sample = self._rng.choice([c for c in fit if c[0] == name])
        self._last[device_id] = name
        return sample

    def play(self, playback: Any, device_id: str, mode: str, lang: str | None = None) -> bool:
        """Play one filler. True when something was played or asked of the unit."""
        if mode not in ("tone", "phrase"):
            return False
        if mode == "tone" and self._tone_on_unit(device_id):
            return False
        if self.probe is not None and self.probe.has(device_id, "filler") is True:
            try:
                reply = self.probe.call(device_id, "self.filler.play", {"mode": mode})
                return reply.get("ok") is True
            except Exception:
                logger.debug("unit filler not played", exc_info=True)
                return False
        name, samples = "tone", tone()
        if mode == "phrase":
            picked = self.pick(device_id, lang)
            if picked is not None:
                name, samples = picked[0], picked[1]
        playback.push_audio_sample(samples)
        end = getattr(playback, "end_sentence", None)
        if end is not None:
            end()
        self.played = [*self.played[-9:], (device_id[-5:], name)]
        return True
