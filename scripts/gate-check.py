#!/usr/bin/env python3
"""Frame time and spoken-turn latency gate numbers, checked from what the bench agent measured (the memory numbers are checked by fw-stress.py).
Usage: gate-check.py [--voice-log LOG] [--move-fps N] [--face-refresh-ms N] [--picture-refresh-ms N]
  --voice-log: the log scripts/fw-voice-bench.py wrote (lines "LAT: <ms> <event>"); rounds are cut at each wake_evt.
  --move-fps: refreshes per second of `self.face.bench_run` workload move (patch H01 and V20 counters); --face-refresh-ms and --picture-refresh-ms:
  the milliseconds one face refresh and one full-screen picture refresh took (the same counters).
Exit 0 and "GATE PASS" only when every number the gate defines was given and is inside its floor: a number that was not measured fails, as the
memory gate fails when the host made no calls. The numbers and why: docs/dev/gate-numbers.md. Placement: Mac that holds the cable. Upstream: none."""

from __future__ import annotations

import argparse
import re
import statistics
import sys
from pathlib import Path

LAT = re.compile(r"LAT: (\d+) (\S+)")
# name: (comparison, limit, unit, source). "min" means the value must be at least the limit, "max" at most.
GATES = {
    "face_move_fps": (
        "min",
        30.0,
        "refreshes per second",
        "face keeps moving: the target of docs/design/picture-faces-2026-11-16.md (44.7 measured)",
    ),
    "face_refresh_ms": ("max", 8.0, "ms", "one face refresh draws in 3 to 7 ms measured"),
    "picture_refresh_ms": ("max", 40.0, "ms", "a full-screen picture flush measured 26 to 35 ms"),
    "wake_to_cue_median_ms": (
        "max",
        100.0,
        "ms",
        "wake event to the listening sound queued: 5 ms and 17 ms measured, unit side only",
    ),
    "question_end_to_reply_median_ms": (
        "max",
        8000.0,
        "ms",
        "end of the question to the first reply sound: 6.9 s median measured on a loaded Mac (provisional)",
    ),
    "question_end_to_reply_p95_ms": (
        "max",
        25000.0,
        "ms",
        "same, 95th percentile: 24.8 s measured (provisional)",
    ),
}


def voice_numbers(text: str) -> dict[str, float]:
    """From the trace of fw-voice-bench.py: per round (cut at wake_evt) the wake-to-cue time and the question-end-to-reply time."""
    cues: list[int] = []
    replies: list[int] = []
    wake = q_end = None
    cue_done = reply_done = False
    for line in text.splitlines():
        m = LAT.search(line)
        if not m:
            continue
        ms, name = int(m.group(1)), m.group(2)
        if name == "wake_evt":
            wake, q_end, cue_done, reply_done = ms, None, False, False
        elif name == "listen_cue_queued" and wake is not None and not cue_done:
            cues.append(ms - wake)
            cue_done = True
        elif name == "inj_q_end" and wake is not None:
            q_end = ms
        elif name == "tts_start" and q_end is not None and not reply_done:
            replies.append(ms - q_end)
            reply_done = True
    out: dict[str, float] = {}
    if cues:
        out["wake_to_cue_median_ms"] = statistics.median(cues)
    if replies:
        out["question_end_to_reply_median_ms"] = statistics.median(replies)
        out["question_end_to_reply_p95_ms"] = sorted(replies)[
            min(len(replies) - 1, int(0.95 * len(replies)))
        ]
    return out


def verdict(measured: dict[str, float]) -> tuple[list[str], bool]:
    lines, ok_all = [], True
    for name, (cmp, limit, unit, why) in GATES.items():
        if name not in measured:
            lines.append(
                f"  {name:34s} not measured  {cmp} {limit:g} {unit}  FAIL (a number that was not measured fails)"
            )
            ok_all = False
            continue
        value = measured[name]
        ok = value >= limit if cmp == "min" else value <= limit
        ok_all &= ok
        lines.append(
            f"  {name:34s} {value:>10.1f}  {cmp} {limit:g} {unit}  {'ok' if ok else 'FAIL'}"
        )
    return lines, ok_all


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--voice-log")
    p.add_argument("--move-fps", type=float)
    p.add_argument("--face-refresh-ms", type=float)
    p.add_argument("--picture-refresh-ms", type=float)
    a = p.parse_args(argv)
    measured: dict[str, float] = {}
    if a.voice_log:
        measured.update(voice_numbers(Path(a.voice_log).read_text(errors="replace")))
    for key, value in (
        ("face_move_fps", a.move_fps),
        ("face_refresh_ms", a.face_refresh_ms),
        ("picture_refresh_ms", a.picture_refresh_ms),
    ):
        if value is not None:
            measured[key] = value
    lines, ok = verdict(measured)
    print("\n".join(lines))
    print("GATE", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
