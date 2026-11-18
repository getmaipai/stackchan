#!/usr/bin/env python3
"""Voice path bench for a BENCH image on the USB cable (needs the serial tools and trace points of patches V01 and L06).

  fw-voice-bench.py --noise [ROUNDS] [LOG]   room noise from this Mac (afplay), wake only, nobody talks: fails when noise holds listening open
  fw-voice-bench.py ROUNDS [LOG] [--gate]     (--gate exits 1 when a spoken turn got no reply or a host error line appeared)
  reset the unit, wait, then ROUNDS times: inject the wake phrase and a question, read the trace

Intent: put numbers on the voice path so a memory change can be judged against another image: wake event to listening sound
queued (ms), output gaps and slow outputs per minute of speech, replies that started, the lowest free stack of the audio
tasks, and one camera frame (photo tool). Run it against two images and compare the printed lines.
Placement: Mac that holds the cable (development only). Needs the host on the unit's link for the reply to speak.
Upstream: none.
"""

from __future__ import annotations

import importlib.util
import os
import re
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fw_serial", os.path.join(HERE, "fw-serial.py"))
fw_serial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fw_serial)  # type: ignore[union-attr]

LAT = re.compile(r"LAT: (\d+) (\S+)(.*)")

# Serial lines that mean the host or the link failed during a spoken turn (--gate fails on any of them).
HOST_ERRORS = [
    r"Failed to receive server hello",
    r"TIMEOUT inject",
    r"WebSocket (?:error|disconnected)",
    r"Server timeout",
    r"stt[_ ](?:error|failed)",
    r"tts[_ ](?:error|failed)",
    r"Guru Meditation",
    r"task_wdt: Task watchdog",
]


def gate_verdict(text: str, rounds: int, replies: int) -> list[str]:
    """Why a spoken-turn gate fails, in plain words; empty when it passes. `replies` counts tts_start trace points."""
    failures = []
    if replies < rounds:
        failures.append(f"only {replies} of {rounds} spoken turns got a reply that started; check the host's speech address and the listening guard")
    for pattern in HOST_ERRORS:
        hits = re.findall(pattern, text)
        if hits:
            failures.append(f"{len(hits)} serial line(s) match {pattern!r}; open the log and read the lines before the first one")
    resets = len(re.findall(r"rst:0x", text))
    if resets > 1:
        failures.append(f"{resets - 1} unexpected reset(s) during the run")
    return failures


GUARD_LINE = re.compile(r"State guard returning listening to idle after (\d+) seconds")


def noise_verdict(held_seconds: list[int], cap_s: int = 60) -> list[str]:
    """Why the noisy-room listening check fails, in plain words; empty when it passes.
    held_seconds: how long each listening turn stayed open before the state guard ended it, with room noise playing and nobody talking."""
    if not held_seconds:
        return ["no 'State guard returning listening to idle' line was read: the unit never started or never ended a listening turn"]
    failures = []
    over = [h for h in held_seconds if h > cap_s + 1]
    if over:
        failures.append(f"{len(over)} turn(s) stayed open past the {cap_s} s cap (longest {max(over)} s)")
    long_ones = [h for h in held_seconds if h > 20]
    if len(long_ones) * 2 > len(held_seconds):
        failures.append(f"room noise kept more than half of the {len(held_seconds)} turns open longer than 20 s (median {sorted(held_seconds)[len(held_seconds) // 2]} s): raise the voice threshold or shorten the window")
    return failures


def noise_run(rounds: int, out: str) -> int:
    """--noise ROUNDS: pink noise from this Mac's speaker (macOS afplay and ffmpeg), wake only, nobody talking; reads how long each turn stays open."""
    import subprocess
    import tempfile

    wav = os.path.join(tempfile.mkdtemp(), "noise.wav")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "anoisesrc=color=pink:amplitude=0.4:duration=75:sample_rate=16000",
                    "-af", "lowpass=f=3500,highpass=f=60", wav], check=True)
    s = fw_serial.open_port()
    log = open(out, "w")
    held: list[int] = []
    for _ in range(rounds):
        player = subprocess.Popen(["afplay", wav])
        try:
            fw_serial.call(s, "self.bench.inject", {"q": 0, "wake": 1}, wait=10.0, on_line=lambda t: log.write(t + "\n"))
        except TimeoutError:
            log.write("TIMEOUT inject\n")
        t_end = time.time() + 70
        while time.time() < t_end:
            raw = s.readline()
            if raw:
                text = raw.decode("utf8", "replace").strip()
                log.write(text + "\n")
                m = GUARD_LINE.search(text)
                if m:
                    held.append(int(m.group(1)))
                    break
        player.terminate()
        time.sleep(5)
    failures = noise_verdict(held)
    print(f"noise rounds {rounds}: turns ended after {held} s")
    for f in failures:
        print(f"GATE FAIL: {f}")
    print("GATE " + ("FAIL" if failures else "PASS"))
    return 1 if failures else 0


def main() -> int:
    if "--noise" in sys.argv[1:]:
        rest = [a for a in sys.argv[1:] if a != "--noise"]
        return noise_run(int(rest[0]) if rest else 5, rest[1] if len(rest) > 1 else "fw-voice-noise.log")
    args = [a for a in sys.argv[1:] if a != "--gate"]
    gate = "--gate" in sys.argv[1:]
    rounds = int(args[0]) if len(args) > 0 else 6
    out = args[1] if len(args) > 1 else "fw-voice-bench.log"
    log = open(out, "w")
    lines: list[tuple[float, str]] = []

    def keep(text: str) -> None:
        lines.append((time.time(), text))
        log.write(text + "\n")
        log.flush()

    s = fw_serial.open_port()
    t_end = time.time() + 50
    while time.time() < t_end:  # boot and settle; keep every line
        raw = s.readline()
        if raw:
            keep(raw.decode("utf8", "replace").strip())
    started = time.time()
    cues, gaps, slow, replies = [], 0, 0, 0
    for r in range(rounds):
        mark = len(lines)
        try:
            fw_serial.call(s, "self.bench.inject", {"q": 1 + (r % 5), "wake": 1}, wait=10.0, on_line=keep)
        except TimeoutError:
            keep("TIMEOUT inject")
        t_end = time.time() + 28
        while time.time() < t_end:
            raw = s.readline()
            if raw:
                keep(raw.decode("utf8", "replace").strip())
        wake = cue = None
        for _, text in lines[mark:]:
            m = LAT.search(text)
            if not m:
                continue
            ms, name, rest = int(m.group(1)), m.group(2), m.group(3)
            if name == "wake_evt" and wake is None:
                wake = ms
            elif name == "listen_cue_queued" and cue is None and wake is not None:
                cue = ms
            elif name == "gap":
                gaps += 1
            elif name == "slow_out":
                slow += 1
            elif name == "tts_start":
                replies += 1
        if wake is not None and cue is not None:
            cues.append(cue - wake)
    photo = "not run"
    try:
        reply = fw_serial.call(s, "self.camera.take_photo", {"question": "what is in front of you"}, wait=40.0, on_line=keep)
        photo = str(reply)[:160]
    except Exception as exc:  # noqa: BLE001 - the bench prints what happened
        photo = f"error: {exc}"
    minutes = max((time.time() - started) / 60.0, 0.01)
    text = "\n".join(t for _, t in lines)
    stk = re.findall(r"SystemInfo: stk(.*)", text)
    audio = {}
    if stk:
        for name, val in re.findall(r"(audio_input|audio_output|opus_codec|audio_afe|main|ws_reconnect)=(\d+)", stk[-1]):
            audio[name] = int(val)
    print(f"rounds {rounds}, {minutes:.1f} min after the settle")
    print(f"  wake event to listening sound queued (ms): {cues if cues else 'none read'}"
          + (f", median {statistics.median(cues):.0f}" if cues else ""))
    print(f"  output gaps {gaps}, slow outputs {slow}, replies that started {replies}, per minute: gaps {gaps / minutes:.2f}, slow {slow / minutes:.2f}")
    print(f"  lowest free stack (last stk line): {audio}")
    print(f"  resets {len(re.findall(r'rst:0x', text))} (1 is the start), task_wdt {len(re.findall('task_wdt: Task watchdog', text))}, panics {len(re.findall('Guru Meditation|abort[(][)] was called', text))}")
    print(f"  camera frame: {photo}")
    if gate:
        failures = gate_verdict(text, rounds, replies)
        for f in failures:
            print(f"GATE FAIL: {f}")
        print("GATE " + ("FAIL" if failures else "PASS"))
        return 1 if failures else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
