#!/usr/bin/env python3
"""The offline mumble, reference implementation (patch UX16, spec docs/design/offline-mumble.md): one short note for every character of a caption, timed to the caption,
with the mouth levels that go with it. The same algorithm as firmware/main/hal/maipai_mumble_core.h (integer math, the same tables); host/tests/test_mumble.py compiles the C core
and checks that both give the same blips for the same text, in all six languages.
Usage: python3 scripts/virtual-unit/mumble.py --wav OUT.wav "text" [--ms 2500]     (a playable 8 kHz sample; no audio file is stored by the unit)
Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import math
import struct
import sys
import wave
from dataclasses import dataclass

FREQ = [round(196 * 2 ** (n / 12)) for n in range(-4, 41)]
SEMI_MIN, SEMI_MAX = -4, 40
PENTA = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21]
VOWEL_SEMI = [0, 4, 9, 2, 7]
VOWEL_MOUTH = [100, 60, 45, 85, 70]
SPACE, PAUSE, END, VOWEL, CONSONANT, DIGIT, OTHER, SILENT = range(8)


@dataclass
class Blip:
    t_ms: int
    dur_ms: int
    f0: int
    f1: int
    level: int
    mouth: int

    def as_tuple(self):
        return (self.t_ms, self.dur_ms, self.f0, self.f1, self.level, self.mouth)


def fold(c: int) -> int:
    if 65 <= c <= 90:
        return c + 32
    if 97 <= c <= 122:
        return c
    if 0xC0 <= c <= 0xFF and c not in (0xD7, 0xF7):
        l = c if c >= 0xE0 else c + 32
        if 0xE0 <= l <= 0xE6:
            return ord("a")
        if l == 0xE7:
            return ord("c")
        if 0xE8 <= l <= 0xEB:
            return ord("e")
        if 0xEC <= l <= 0xEF:
            return ord("i")
        if l == 0xF0:
            return ord("d")
        if l == 0xF1:
            return ord("n")
        if 0xF2 <= l <= 0xF6 or l == 0xF8:
            return ord("o")
        if 0xF9 <= l <= 0xFC:
            return ord("u")
        if l in (0xFD, 0xFF):
            return ord("y")
        if l == 0xDF:
            return ord("s")
        return 0
    if c == 0xDF:
        return ord("s")
    if c in (0x152, 0x153):
        return ord("o")
    return 0


def classify(c: int):
    """(class, letter number)"""
    if c in (32, 10, 9, 0xA0):
        return SPACE, 0
    if c in (ord(","), ord(";"), ord(":"), ord("-"), ord("("), ord(")"), ord('"'), ord("'"), 0x2014, 0x2013):
        return PAUSE, 0
    if c in (ord("."), ord("!"), ord("?"), 0x2026, 0xA1, 0xBF):
        return END, 0
    if 48 <= c <= 57:
        return DIGIT, c - 48
    f = fold(c)
    if f:
        return (VOWEL if chr(f) in "aeiou" else CONSONANT), f - 97
    if 0x370 <= c < 0xD800:
        return OTHER, c % 26
    return SILENT, 0


def freq(semi: int) -> int:
    return FREQ[max(SEMI_MIN, min(SEMI_MAX, semi)) - SEMI_MIN]


def vowel_index(letter: int) -> int:
    return {0: 0, 4: 1, 8: 2, 14: 3}.get(letter, 4)


def inflection(cps: list[int], i: int) -> int:
    remaining, end = 0, ""
    for c in cps[i + 1:]:
        k, _ = classify(c)
        if k == END:
            end = "?" if c in (ord("?"), 0xBF) else "!" if c in (ord("!"), 0xA1) else "."
            break
        if k in (VOWEL, CONSONANT, OTHER, DIGIT):
            remaining += 1
    if end == "?":
        return {0: 7, 1: 5, 2: 3}.get(remaining, 0)
    if end == "!":
        return 2 if remaining == 0 else 0
    if end == "." and remaining == 0:
        return -2
    return 0


def invalid_to_fffd(text: str) -> list[int]:
    return [ord(ch) for ch in text]


def blips(text: str, start_ms: int, end_ms: int) -> list[Blip]:
    cps = invalid_to_fffd(text)
    n = len(cps)
    if end_ms <= start_ms:
        end_ms = start_ms + 1
    span = end_ms - start_ms
    out = []
    for i, c in enumerate(cps):
        t0 = start_ms + span * i // n
        t1 = start_ms + span * (i + 1) // n
        slot = t1 - t0
        k, letter = classify(c)
        infl = inflection(cps, i) if k in (VOWEL, CONSONANT, OTHER, DIGIT) else 0
        b = Blip(t0, 0, 0, 0, 0, 0)
        if k == VOWEL:
            vi = vowel_index(letter)
            b = Blip(t0, slot * 9 // 10, freq(VOWEL_SEMI[vi] + infl), freq(VOWEL_SEMI[vi] + infl + 2), 100, VOWEL_MOUTH[vi])
        elif k in (CONSONANT, OTHER, DIGIT):
            semi = 12 + PENTA[(letter * 7) % 10]
            mouth = 10 if (k == CONSONANT and letter in (1, 12, 15)) else 30
            b = Blip(t0, slot * 6 // 10, freq(semi + infl), freq(semi + infl - 1), 55, mouth)
        out.append(b)
    return out


def mouth_schedule(blist: list[Blip], step_ms: int = 33) -> list[int]:
    """The face's speak level for each renderer frame (33 ms): the mouth of the blip sounding then, 0 in a rest."""
    if not blist:
        return []
    end = blist[-1].t_ms + max(1, blist[-1].dur_ms)
    levels = []
    for t in range(blist[0].t_ms, end + step_ms, step_ms):
        cur = 0
        for b in blist:
            if b.t_ms <= t < b.t_ms + max(b.dur_ms, 1):
                cur = b.mouth if b.dur_ms else 0
        levels.append(cur)
    return levels


def render(blist: list[Blip], rate: int = 8000, tail_ms: int = 120) -> list[int]:
    """16 bit samples: each blip a sine with a quarter triangle, 5 ms attack and a 15 ms fall, gliding from f0 to f1."""
    if not blist:
        return []
    total = (blist[-1].t_ms + blist[-1].dur_ms + tail_ms - blist[0].t_ms) * rate // 1000
    buf = [0.0] * total
    base = blist[0].t_ms
    for b in blist:
        if b.dur_ms == 0:
            continue
        s0 = (b.t_ms - base) * rate // 1000
        n = b.dur_ms * rate // 1000
        phase = 0.0
        for j in range(n):
            if s0 + j >= total:
                break
            f = b.f0 + (b.f1 - b.f0) * j / max(1, n)
            phase += 2 * math.pi * f / rate
            tri = 2 / math.pi * math.asin(math.sin(phase))
            att = min(1.0, j / max(1, 5 * rate // 1000))
            rel = min(1.0, (n - j) / max(1, 15 * rate // 1000))
            buf[s0 + j] += 0.45 * (b.level / 100) * att * rel * (math.sin(phase) * 0.8 + tri * 0.2)
    return [int(max(-1.0, min(1.0, v)) * 30000) for v in buf]


def write_wav(path: str, samples: list[int], rate: int = 8000) -> None:
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", s) for s in samples))


def main(argv: list[str]) -> int:
    if "--wav" not in argv:
        print("usage: mumble.py --wav OUT.wav \"text\" [--ms 2500]", file=sys.stderr)
        return 2
    out = argv[argv.index("--wav") + 1]
    ms = int(argv[argv.index("--ms") + 1]) if "--ms" in argv else 2500
    text = [a for a in argv if not a.startswith("--") and a != out and not a.isdigit()][-1]
    write_wav(out, render(blips(text, 0, ms)))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
