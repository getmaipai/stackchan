#!/usr/bin/env python3
"""Game sounds, synthesized from nothing: short tones, clacks and noise bursts with attack-decay-sustain-release envelopes, mono 16 kHz, deterministic (the same bytes every run).
Writes docs/dev/game-sounds/<id>.wav (16 bit, to play), <id>.ulaw (8 kHz mu-law, the tiny form: about one byte a sample), manifest.json (id, what it is, sizes, peak and loudness, license)
and loudness.md. Every sound is original work released as CC0-1.0. All sounds are normalized to the same chime level (peak -10 dBFS), so none clips and none is louder than another.
Listening is not possible here: the numbers in loudness.md and the spectrogram sheet (--spectrogram, needs numpy) are the check; the WAV files are for a person to play.
Usage: python3 scripts/make-game-sounds.py [--out DIR] [--spectrogram]. Placement: docs tooling. Upstream: none."""
from __future__ import annotations

import json
import math
import struct
import sys
import wave
from pathlib import Path

RATE = 16000
PEAK = 10 ** (-10 / 20)   # -10 dBFS, chime level
ROOT = Path(__file__).resolve().parents[1]
LICENSE_ID = "CC0-1.0"
AUTHOR = "MaiPai playground track (original synthesis, no samples used)"


class Noise:
    """A fixed pseudo random sequence (a linear congruential generator): the same noise every run."""

    def __init__(self, seed: int = 12345) -> None:
        self.s = seed

    def __call__(self) -> float:
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self.s >> 8) / float(1 << 23) - 1.0


def adsr(n: int, a: float, d: float, s: float, r: float) -> list[float]:
    """An envelope over n samples: attack, decay to the sustain level, sustain, release (all but the level are seconds; the sustain fills the rest)."""
    A, D, R = int(a * RATE), int(d * RATE), int(r * RATE)
    out = []
    for i in range(n):
        if i < A:
            v = i / max(1, A)
        elif i < A + D:
            v = 1 - (1 - s) * (i - A) / max(1, D)
        elif i < n - R:
            v = s
        else:
            v = s * max(0.0, (n - i) / max(1, R))
        out.append(v)
    return out


def tone(freq: float, dur: float, wave_: str = "sine", env=(0.004, 0.05, 0.4, 0.05), slide: float = 0.0) -> list[float]:
    n = int(dur * RATE)
    e = adsr(n, *env)
    out, ph = [], 0.0
    for i in range(n):
        f = freq + slide * i / max(1, n)
        ph += 2 * math.pi * f / RATE
        if wave_ == "triangle":
            x = 2 / math.pi * math.asin(math.sin(ph))
        elif wave_ == "square":
            x = 1.0 if math.sin(ph) >= 0 else -1.0
            x *= 0.6
        else:
            x = math.sin(ph)
        out.append(x * e[i])
    return out


def noise_burst(dur: float, env=(0.001, 0.02, 0.1, 0.02), lowpass: float = 0.5, seed: int = 1) -> list[float]:
    n = int(dur * RATE)
    e = adsr(n, *env)
    rnd = Noise(seed)
    y, out = 0.0, []
    for i in range(n):
        y += lowpass * (rnd() - y)   # a one pole low pass: a smaller number is duller
        out.append(y * e[i])
    return out


def mix(*parts: list[float]) -> list[float]:
    n = max(len(p) for p in parts)
    return [sum(p[i] if i < len(p) else 0.0 for p in parts) for i in range(n)]


def seq(*parts: list[float], gap: float = 0.0) -> list[float]:
    out: list[float] = []
    for p in parts:
        out += p + [0.0] * int(gap * RATE)
    return out


def note(semitones: float, base: float = 261.63) -> float:
    return base * 2 ** (semitones / 12)


def chip_land(row: int) -> list[float]:
    """A soft wooden clack: a dull noise tick over a short decaying tone; the pitch rises one step each row (row 0 is the bottom)."""
    f = 220 * 2 ** (row / 12 * 2)   # two semitones a row
    return mix(noise_burst(0.025, (0.0005, 0.012, 0.0, 0.01), 0.35, seed=7 + row), [x * 0.8 for x in tone(f, 0.09, "sine", (0.001, 0.03, 0.15, 0.05))], [x * 0.3 for x in tone(f * 2.4, 0.04, "triangle", (0.001, 0.02, 0.0, 0.02))])


SOUNDS: dict[str, tuple[str, callable]] = {}


def sound(id_: str, what: str):
    def reg(fn):
        SOUNDS[id_] = (what, fn)
        return fn
    return reg


for r in range(6):
    SOUNDS[f"chip_land_{r + 1}"] = (f"a chip lands in row {r + 1}: a soft wooden clack, higher each row", (lambda r=r: chip_land(r)))


@sound("drop_whoosh", "a chip starts to fall: a quick falling whoosh")
def _():
    return noise_burst(0.14, (0.01, 0.06, 0.3, 0.06), 0.18, seed=21)


@sound("move_unit", "the robot's own move: a two note blip with a different (triangle) timbre")
def _():
    return seq(tone(note(7), 0.06, "triangle", (0.003, 0.03, 0.5, 0.02)), tone(note(12), 0.09, "triangle", (0.003, 0.04, 0.4, 0.04)))


@sound("win_fanfare", "a win: a short rising arpeggio")
def _():
    return seq(*(tone(note(s), 0.05, "triangle", (0.003, 0.02, 0.6, 0.02)) for s in (0, 4, 7)), tone(note(12), 0.1, "triangle", (0.003, 0.04, 0.5, 0.05)))


@sound("lose", "a loss: a soft descending three notes")
def _():
    return seq(*(tone(note(s), 0.08, "sine", (0.005, 0.03, 0.5, 0.04)) for s in (4, 0, -5)))


@sound("draw", "a draw: two level notes")
def _():
    return seq(tone(note(2), 0.08, "sine", (0.004, 0.03, 0.5, 0.03)), tone(note(2), 0.1, "sine", (0.004, 0.03, 0.5, 0.04)), gap=0.02)


@sound("illegal_thud", "an illegal move: a low short thud")
def _():
    return mix(tone(110, 0.1, "sine", (0.002, 0.04, 0.1, 0.05), slide=-30), noise_burst(0.02, (0.0005, 0.01, 0.0, 0.01), 0.1, seed=3))


@sound("tap_tick", "a menu or board tap: a tiny tick")
def _():
    return mix(noise_burst(0.006, (0.0003, 0.004, 0.0, 0.002), 0.6, seed=5), tone(1250, 0.03, "sine", (0.001, 0.01, 0.1, 0.015)))


@sound("flip", "a card flips: a quick rising sweep")
def _():
    return tone(500, 0.07, "triangle", (0.002, 0.03, 0.3, 0.03), slide=900)


@sound("slide", "a tile slides: a short soft scrape")
def _():
    return noise_burst(0.09, (0.01, 0.03, 0.3, 0.04), 0.25, seed=33)


@sound("pop", "something pops: a rising blip")
def _():
    return tone(380, 0.05, "sine", (0.001, 0.02, 0.1, 0.02), slide=700)


@sound("match_found", "a pair matches: two bright notes")
def _():
    return seq(tone(note(12), 0.07, "triangle"), tone(note(19), 0.14, "triangle", (0.004, 0.05, 0.5, 0.08)))


@sound("mine_flag", "a flag is planted: a small tick and a low blip")
def _():
    return seq(tone(note(-5), 0.05, "square", (0.002, 0.02, 0.2, 0.02)), tone(note(2), 0.06, "triangle"))


@sound("hangman_ok", "a right letter: a gentle high note")
def _():
    return tone(note(16), 0.12, "sine", (0.004, 0.05, 0.4, 0.06))


@sound("hangman_bad", "a wrong letter: a short low buzz")
def _():
    return tone(note(-12), 0.14, "square", (0.003, 0.05, 0.3, 0.06))


def normalize(x: list[float]) -> list[float]:
    pk = max((abs(v) for v in x), default=0.0)
    g = PEAK / pk if pk > 0 else 1.0
    out = [v * g for v in x]
    # a 2 ms fade at both ends so no sound starts or ends with a click
    f = min(len(out) // 2, int(0.002 * RATE))
    for i in range(f):
        out[i] *= i / max(1, f)
        out[-1 - i] *= i / max(1, f)
    return out


def pcm16(x: list[float]) -> bytes:
    return b"".join(struct.pack("<h", max(-32768, min(32767, round(v * 32767)))) for v in x)


def ulaw(x: list[float]) -> bytes:
    """8 kHz mu-law (G.711): halve the 16 kHz samples by averaging pairs, compress to one byte each."""
    half = [(x[i] + x[i + 1]) / 2 for i in range(0, len(x) - 1, 2)]
    out = bytearray()
    for v in half:
        s = max(-1.0, min(1.0, v))
        sign = 0x80 if s < 0 else 0
        m = int(abs(s) * 32635) + 132
        e = 7
        while e > 0 and not (m & (0x80 << e)):
            e -= 1
        q = (m >> (e + 3)) & 0x0F
        out.append(~(sign | (e << 4) | q) & 0xFF)
    return bytes(out)


def stats(x: list[float]) -> dict:
    pk = max(abs(v) for v in x)
    rms = math.sqrt(sum(v * v for v in x) / len(x))
    return {"peak_dbfs": round(20 * math.log10(pk), 1), "rms_dbfs": round(20 * math.log10(rms), 1), "clipped": sum(1 for v in x if abs(v) >= 0.999)}


def main(argv: list[str]) -> int:
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else ROOT / "docs" / "dev" / "game-sounds"
    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for id_, (what, fn) in SOUNDS.items():
        x = normalize(fn())
        pcm = pcm16(x)
        with wave.open(str(out / f"{id_}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(pcm)
        u = ulaw(x)
        (out / f"{id_}.ulaw").write_bytes(u)
        manifest.append({"id": id_, "what": what, "rate": RATE, "samples": len(x), "ms": round(len(x) * 1000 / RATE), "wav_bytes": 44 + len(pcm), "ulaw_bytes": len(u), "ulaw_rate": RATE // 2, **stats(x), "license": LICENSE_ID, "author": AUTHOR})
    (out / "manifest.json").write_text(json.dumps({"version": 1, "format": "mono, 16 kHz 16 bit WAV and 8 kHz mu-law raw", "level": "peak -10 dBFS", "sounds": manifest}, indent=1) + "\n")
    lines = ["# Game sounds: loudness report", "", "Made by `scripts/make-game-sounds.py`. Every sound is normalized to a peak of -10 dBFS (chime level) with a 2 ms fade at each end; none clips. Original work, CC0-1.0.", "",
             "| Sound | What | ms | WAV bytes | mu-law bytes | Peak dBFS | RMS dBFS |", "|---|---|---:|---:|---:|---:|---:|"]
    for m in manifest:
        lines.append(f"| `{m['id']}` | {m['what']} | {m['ms']} | {m['wav_bytes']:,} | {m['ulaw_bytes']:,} | {m['peak_dbfs']} | {m['rms_dbfs']} |")
    (out / "loudness.md").write_text("\n".join(lines) + "\n")
    if "--spectrogram" in argv:
        try:
            spectrogram_sheet(out, manifest)
        except ImportError:
            print("no numpy: spectrogram skipped")
    print(f"game sounds: {len(manifest)} sounds in {out}; total {sum(m['ulaw_bytes'] for m in manifest):,} bytes as mu-law, {sum(m['wav_bytes'] for m in manifest):,} as WAV")
    return 0


def spectrogram_sheet(out: Path, manifest: list[dict]) -> None:
    import struct as st
    import zlib

    import numpy as np

    rows = []
    for m in manifest:
        with wave.open(str(out / f"{m['id']}.wav")) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float)
        n, hop = 256, 64
        frames = [np.abs(np.fft.rfft(x[i : i + n] * np.hanning(n)))[:64] for i in range(0, max(1, len(x) - n), hop)]
        spec = np.log1p(np.array(frames).T)[::-1]
        spec = (255 * spec / max(1e-9, spec.max())).astype(np.uint8)
        img = np.zeros((64, 96), dtype=np.uint8)
        c = min(96, spec.shape[1])
        img[:, :c] = spec[:, :c]
        rows.append(img)
    cols = 4
    h = ((len(rows) + cols - 1) // cols) * 68
    sheet = np.full((h, cols * 100), 40, dtype=np.uint8)
    for i, im in enumerate(rows):
        sheet[(i // cols) * 68 + 2 : (i // cols) * 68 + 66, (i % cols) * 100 + 2 : (i % cols) * 100 + 98] = im
    raw = b"".join(b"\0" + bytes(r) for r in sheet)
    def chunk(t, d):
        c = st.pack(">I", len(d)) + t + d
        return c + st.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", st.pack(">IIBBBBB", sheet.shape[1], sheet.shape[0], 8, 0, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    (out / "spectrograms.png").write_bytes(png)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
