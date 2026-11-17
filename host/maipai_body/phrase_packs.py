# ruff: noqa: E501
"""Offline phrases as a pack: the sixteen short clips the robot says when it cannot reach Home, in the household's voice.

The unit's image carries sixteen clips in one voice and one language (firmware patch V02). A pack of type ``phrase`` is the same
sixteen files, ``ph_<group>_<n>.ogg`` (Ogg Opus, mono, 16 kHz, 24 kbps, 60 ms frames, like the image's), made here with the host's
own speech engine (the one replies use) and the language of the household, stored in a zip with no further compression (audio that
is already compressed). The library keeps one pack per voice and language; the host sends the one that matches the unit's language
and voice (``pack_auto``), and the unit says the pack's clip where it has one and the image's clip where it does not.

The texts are one short sentence each. English is the sentences of the image's clips; Spanish is written for this module. A language
with no text set here has no phrase pack: the unit says the clips built into its image.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from maipai_body import fillers as fillers_mod
from maipai_body import packs as packs_mod

logger = logging.getLogger("maipai_body.phrase_packs")

RATE = 16000
GROUPS: dict[str, int] = {
    "no_wifi": 4,
    "no_host": 4,
    "refused": 3,
    "connecting": 3,
    "back": 2,
}  # the firmware's MS_GROUP_SIZE
TOTAL = sum(GROUPS.values())  # 16
MIN_CLIP = 64  # bytes; the unit refuses less
MAX_CLIP = 60_000  # bytes; the unit refuses more
MAX_SECONDS = 4.0
PEAK = 0.7

TEXTS: dict[str, dict[str, tuple[str, ...]]] = {
    "es": {
        "no_wifi": (
            "No encuentro el Wi-Fi.",
            "Ahora mismo no estoy en el Wi-Fi.",
            "Todavía no veo el Wi-Fi.",
            "El Wi-Fi no me responde.",
        ),
        "no_host": (
            "Ahora mismo no puedo llegar a mi casa base.",
            "Tengo problemas para llegar a casa.",
            "Casa todavía no me responde.",
            "No consigo comunicarme con casa ahora.",
        ),
        "refused": (
            "Necesito que me aprueben otra vez.",
            "Casa tiene que dejarme entrar de nuevo.",
            "Estoy esperando que Casa me apruebe.",
        ),
        "connecting": (
            "Todavía me estoy conectando, un momento.",
            "Casi estoy conectado, dame un momento.",
            "Espera, todavía me estoy conectando.",
        ),
        "back": ("Ya volví.", "Estoy conectado a casa otra vez."),
    },
}

SAY: dict[str, tuple[str, str]] = {
    "no_engine": (
        "There is no local voice engine to make the phrases with. Set up the local speech server in robot.toml, then try again.",
        "No hay un motor de voz local para crear las frases. Configura el servidor de voz local en robot.toml e inténtalo de nuevo.",
    ),
    "no_encoder": (
        "The audio tool ffmpeg is not installed on this computer, so the phrases cannot be made. Install ffmpeg, then try again.",
        "La herramienta de audio ffmpeg no está instalada en este equipo, así que no se pueden crear las frases. Instala ffmpeg e inténtalo de nuevo.",
    ),
    "busy": (
        "The phrases are already being made. Wait for them to finish.",
        "Las frases ya se están creando. Espera a que terminen.",
    ),
    "failed": (
        "The voice engine did not answer, so no phrases were made. Check that the local speech server is running, then try again.",
        "El motor de voz no respondió, así que no se crearon frases. Comprueba que el servidor de voz local esté activo e inténtalo de nuevo.",
    ),
    "started": ("Making the phrases. This takes a minute.", "Creando las frases. Tarda un minuto."),
}


def say(lang: str | None, code: str) -> str:
    english, spanish = SAY[code]
    return spanish if (lang or "").lower().startswith("es") else english


def english_texts() -> dict[str, tuple[str, ...]]:
    """The sentences of the clips in the image (the firmware's phrases.json), group by group."""
    path = (
        Path(__file__).parent
        / "bodies"
        / "stackchan"
        / "firmware"
        / "assets"
        / "phrases"
        / "phrases.json"
    )
    clips = json.loads(path.read_text())["clips"]
    out: dict[str, list[str]] = {g: [""] * n for g, n in GROUPS.items()}
    for clip in clips:
        out[clip["group"]][int(clip["variant"]) - 1] = str(clip["text"])
    return {g: tuple(v) for g, v in out.items()}


def texts_for(lang: str) -> dict[str, tuple[str, ...]] | None:
    """The sentences for a language, or None when this module has none (the unit then says the clips in its image)."""
    if lang == "en":
        return english_texts()
    return TEXTS.get(lang)


def languages() -> list[str]:
    return ["en", *TEXTS]


def clip_name(group: str, variant: int) -> str:
    return f"ph_{group}_{variant}.ogg"


def encode_ogg_opus(samples: np.ndarray, rate: int = RATE) -> bytes:
    """Mono float samples to an Ogg Opus file in the format of the image's clips (ffmpeg, libopus, 24 kbps, 60 ms frames)."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise FileNotFoundError("ffmpeg")
    pcm = (
        np.clip(np.asarray(samples, dtype=np.float32).reshape(-1), -1.0, 1.0)
        .astype("<f4")
        .tobytes()
    )
    run = subprocess.run(
        [
            ffmpeg, "-loglevel", "error", "-f", "f32le", "-ar", str(rate), "-ac", "1", "-i", "pipe:0",
            "-c:a", "libopus", "-b:a", "24k", "-frame_duration", "60", "-application", "voip", "-f", "ogg", "pipe:1",
        ],
        input=pcm, capture_output=True, timeout=60, check=True,
    )  # fmt: skip
    return run.stdout


def render_clip(samples: np.ndarray, rate: int) -> np.ndarray | None:
    """One synthesized sentence at the clip rate, trimmed, level set; None when it came out empty or silent."""
    mono = fillers_mod.resample(np.asarray(samples, dtype=np.float32).reshape(-1), rate, RATE)
    cut = fillers_mod.trim_silence(mono, RATE, margin_s=0.05)
    if len(cut) < int(0.2 * RATE):
        return None
    return fillers_mod.normalize(cut[: int(MAX_SECONDS * RATE)], RATE, peak=PEAK, fade_s=0.02)


class PhraseGenerator:
    """Renders a phrase pack with ``synth(text) -> (samples, rate)`` and keeps it in the library for one voice and language."""

    def __init__(
        self,
        synth: Callable[[str], tuple[np.ndarray, int]] | None,
        library: packs_mod.PackLibrary,
        encoder: Callable[[np.ndarray, int], bytes] | None = None,
    ) -> None:
        self.synth, self.library = synth, library
        self.encoder = encoder or encode_ogg_opus
        self.status: dict[str, Any] = {
            "running": False,
            "done": 0,
            "total": TOTAL,
            "error": "",
            "last": "",
        }
        self._lock = threading.Lock()

    def render(
        self, lang: str = "en", progress: Callable[[int, int], None] | None = None
    ) -> tuple[bytes, int]:
        """The pack payload (a zip of up to sixteen clips) and how many clips it holds. A sentence that fails is left out."""
        assert self.synth is not None
        sentences = texts_for(lang)
        if sentences is None:
            raise packs_mod.PackError(f"No phrase text set for language {lang!r}.", "no_text")
        files: dict[str, bytes] = {}
        done = 0
        for group, count in GROUPS.items():
            for variant in range(1, count + 1):
                done += 1
                if progress:
                    progress(done, TOTAL)
                try:
                    samples, rate = self.synth(sentences[group][variant - 1])
                    clip = render_clip(samples, rate)
                    if clip is None:
                        continue
                    ogg = self.encoder(clip, RATE)
                except Exception:
                    logger.debug("phrase %s %d not made", group, variant, exc_info=True)
                    continue
                if MIN_CLIP <= len(ogg) <= MAX_CLIP and ogg[:4] == b"OggS":
                    files[clip_name(group, variant)] = ogg
        index = {"lang": lang, "format": "ogg-opus-16k-mono-24k-60ms", "clips": sorted(files)}
        payload_files = dict(files)
        if files:
            payload_files["index.json"] = json.dumps(index, separators=(",", ":")).encode()
        return packs_mod.zip_payload(payload_files, stored=True), len(files)

    def generate(self, voice: str, lang: str = "en") -> dict[str, Any]:
        if self.synth is None:
            raise packs_mod.PackError(say(lang, "no_engine"), "no_engine")
        if self.encoder is encode_ogg_opus and shutil.which("ffmpeg") is None:
            raise packs_mod.PackError(say(lang, "no_encoder"), "no_encoder")
        payload, count = self.render(lang, lambda d, t: self.status.update(done=d, total=t))
        if count == 0:
            raise packs_mod.PackError(say(lang, "failed"), "failed")
        if len(payload) > packs_mod.MAX_BYTES["phrase"]:
            raise packs_mod.PackError(
                packs_mod.say(
                    lang,
                    "too_big",
                    kind="phrase",
                    size=-(-len(payload) // 1000),
                    limit=packs_mod.MAX_BYTES["phrase"] // 1000,
                ),
                "too_big",
            )
        pack = packs_mod.make_pack(
            "phrase", f"Phrases {lang}", payload, voice=voice or "default", lang=lang
        )
        return self.library.add(pack, lang)

    def start(
        self, voice: str, lang: str = "en", on_done: Callable[[dict[str, Any]], None] | None = None
    ) -> dict[str, Any]:
        if self.synth is None:
            raise packs_mod.PackError(say(lang, "no_engine"), "no_engine")
        with self._lock:
            if self.status["running"]:
                raise packs_mod.PackError(say(lang, "busy"), "busy")
            self.status.update(running=True, done=0, total=TOTAL, error="", last="")

        def work() -> None:
            try:
                info = self.generate(voice, lang)
                self.status["last"] = info["id"]
                if on_done is not None:
                    on_done(info)
            except Exception as error:
                logger.warning("offline phrases not made: %s", error)
                self.status["error"] = (
                    str(error) if isinstance(error, packs_mod.PackError) else say(lang, "failed")
                )
            finally:
                self.status["running"] = False

        threading.Thread(target=work, name="phrase-generator", daemon=True).start()
        return {"ok": True, "message": say(lang, "started"), "status": dict(self.status)}
