"""Voice benchmark helpers for repeatable scripts and recordings."""

from __future__ import annotations

import json
import math
import statistics
import time
import wave
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np


def script_path() -> Path:
    return Path(__file__).resolve().parents[2] / "bench" / "script-20.json"


def quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"median": None, "p95": None}
    ordered = sorted(values)
    return {
        "median": statistics.median(ordered),
        "p95": ordered[math.ceil(0.95 * len(ordered)) - 1],
    }


def analyse_recording(
    path: str | Path, threshold: float = 0.012, question_end_s: float = 0.0
) -> list[dict[str, Any]]:
    """Split mono/stereo 48 kHz PCM recordings into active segments and report silence gaps."""
    with wave.open(str(path), "rb") as source:
        rate, channels, width = source.getframerate(), source.getnchannels(), source.getsampwidth()
        if rate != 48000 or channels not in (1, 2) or width not in (1, 2, 3, 4):
            raise ValueError("Recording must be 48 kHz mono or stereo PCM WAV.")
        raw = source.readframes(source.getnframes())
    if width == 2:
        samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768
    elif width == 1:
        samples = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128) / 128
    elif width == 4:
        samples = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648
    else:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        vals = (
            b[:, 0].astype(np.int32)
            | b[:, 1].astype(np.int32) << 8
            | b[:, 2].astype(np.int32) << 16
        )
        vals = np.where(vals & 0x800000, vals - 0x1000000, vals)
        samples = vals.astype(np.float32) / 8388608
    mono = samples.reshape(-1, channels).mean(axis=1)
    window = 480  # 10 ms energy windows
    count = len(mono) // window
    rms = np.sqrt(np.mean(mono[: count * window].reshape(count, window) ** 2, axis=1))
    active = rms > threshold
    # Bridge brief consonant-level drops; gaps are evaluated from the resulting segments.
    segments: list[list[int]] = []
    for i in np.flatnonzero(active):
        if not segments or i - segments[-1][-1] > 2:
            segments.append([int(i), int(i)])
        else:
            segments[-1][-1] = int(i)
    segments = [s for s in segments if s[1] - s[0] >= 5]
    replies: list[list[list[int]]] = []
    for segment in segments:
        if not replies or (segment[0] - replies[-1][-1][1] - 1) * 0.01 > 1.2:
            replies.append([segment])
        else:
            replies[-1].append(segment)
    out = []
    for reply in replies:
        gaps = [(b[0] - a[1] - 1) * 0.01 for a, b in zip(reply, reply[1:])]
        out.append(
            {
                "start_s": reply[0][0] * 0.01,
                "end_s": (reply[-1][1] + 1) * 0.01,
                "time_question_end_to_first_sound_s": reply[0][0] * 0.01 - question_end_s,
                "gaps_over_80ms": [gap for gap in gaps if gap > 0.08],
                "longest_gap_s": max((gap for gap in gaps if gap > 0.08), default=0.0),
                "stutter_count": sum(gap > 0.08 for gap in gaps),
            }
        )
    return out


def analyse_frames(path: str | Path) -> dict[str, float | int]:
    stamps = [float(line.strip()) for line in Path(path).read_text().splitlines() if line.strip()]
    if len(stamps) < 2 or any(b <= a for a, b in zip(stamps, stamps[1:])):
        raise ValueError("Provide at least two strictly increasing frame timestamps.")
    intervals = [(b - a) * 1000 for a, b in zip(stamps, stamps[1:])]
    return {
        "median_ms": statistics.median(intervals),
        "p95_ms": sorted(intervals)[math.ceil(0.95 * len(intervals)) - 1],
        "dropped_frames": sum(max(0, round(value / (1000 / 120)) - 1) for value in intervals),
    }


def run_sim(
    script: Path | None = None, *, firmware: str = "sim", delay: float = 0.01
) -> dict[str, Any]:
    turns = json.loads((script or script_path()).read_text())
    results = []
    for turn in turns:
        start = time.monotonic()
        time.sleep(delay)
        first = time.monotonic()
        results.append(
            {
                "id": turn["id"],
                "kind": turn["kind"],
                "prompt": turn["prompt"],
                "time_to_first_audio_ms": (first - start) * 1000,
                "stutter_count": 0,
                "longest_gap_ms": 0,
                "stop_delay_ms": delay * 1000 if turn["kind"] == "interrupt" else None,
                "wake_cue_delay_ms": None,
                "clock": "time.monotonic",
            }
        )
    measures = {}
    for key in (
        "time_to_first_audio_ms",
        "stutter_count",
        "longest_gap_ms",
        "stop_delay_ms",
        "wake_cue_delay_ms",
    ):
        measures[key] = quantiles([float(t[key]) for t in results if t[key] is not None])
    now = date.today().isoformat()
    return {
        "firmware": firmware,
        "date": now,
        "clock": "time.monotonic",
        "host_estimates": ["time_to_first_audio_ms", "stop_delay_ms"],
        "recording_required": ["stutter_count", "longest_gap_ms", "wake_cue_delay_ms"],
        "hardware": "simulated",
        "host": "simulated",
        "model": "fake",
        "speech_model": "fake",
        "measures": measures,
        "turns": results,
    }


def markdown_table(data: dict[str, Any]) -> str:
    rows = ["| Measure | Median | p95 |", "|---|---:|---:|"]
    for name, vals in data["measures"].items():
        rows.append(f"| {name} | {vals['median']} | {vals['p95']} |")
    rows.extend(
        [
            "",
            "## All turns",
            "",
            "| Turn | Kind | First audio ms | Stutters | Longest gap ms | "
            "Stop delay ms | Wake cue ms |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for turn in data["turns"]:
        rows.append(
            "| {id} | {kind} | {time_to_first_audio_ms} | {stutter_count} | "
            "{longest_gap_ms} | {stop_delay_ms} | {wake_cue_delay_ms} |".format(**turn)
        )
    return "\n".join(rows)


def compare(a: dict[str, Any], b: dict[str, Any]) -> tuple[str, bool]:
    metrics = (
        "time_to_first_audio_ms",
        "stutter_count",
        "longest_gap_ms",
        "wake_cue_delay_ms",
        "stop_delay_ms",
    )
    rows = ["| Measure | A median | B median |", "|---|---:|---:|"]
    verdict = True
    for metric in metrics:
        av, bv = a["measures"][metric]["median"], b["measures"][metric]["median"]
        rows.append(f"| {metric} | {av} | {bv} |")
        if av is None or bv is None:
            verdict = False
            continue
        verdict &= av < bv if metric in metrics[:3] else av <= bv
    return "\n".join(rows), verdict
