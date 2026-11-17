#!/usr/bin/env python3
"""Voice path bench for a BENCH image on the USB cable (needs the serial tools and trace points of patches V01 and L06).

  fw-voice-bench.py ROUNDS [LOG]     reset the unit, wait, then ROUNDS times: inject the wake phrase and a question, read the trace

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


def main() -> int:
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    out = sys.argv[2] if len(sys.argv) > 2 else "fw-voice-bench.log"
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
