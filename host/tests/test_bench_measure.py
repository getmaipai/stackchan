import json
import struct
import wave

import pytest

from maipai_body.measure.bench import (
    analyze_frames,
    analyze_recording,
    compare,
    run_sim,
    script_path,
)


def _wav(path, silent_frames):
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(48000)
        samples = []
        for i in range(200):
            active = not any(a <= i < b for a, b in silent_frames)
            samples.extend([12000 if active else 0] * 480)
        stream.writeframes(struct.pack("<" + "h" * len(samples), *samples))


def test_script_has_twenty_expected_turns():
    script = json.loads(script_path().read_text())
    assert len(script) == 20
    assert [
        sum(row["kind"] == kind for row in script) for kind in ("short", "medium", "interrupt")
    ] == [10, 5, 5]
    assert all("interrupt_after_s" in row for row in script if row["kind"] == "interrupt")


def test_recording_finds_known_gap(tmp_path):
    path = tmp_path / "known.wav"
    _wav(path, [(50, 63)])
    rows = analyze_recording(path, question_end_s=0)
    assert len(rows) == 1
    assert rows[0]["stutter_count"] == 1
    assert rows[0]["longest_gap_s"] == pytest.approx(0.13)
    assert rows[0]["time_question_end_to_first_sound_s"] == pytest.approx(0)


def test_frames_reports_median_p95_and_drops(tmp_path):
    path = tmp_path / "frames.txt"
    path.write_text("0\n0.0083333\n0.0166666\n0.0500000\n")
    result = analyze_frames(path)
    assert result["median_ms"] == pytest.approx(8.3333)
    assert result["p95_ms"] == pytest.approx(33.3334)
    assert result["dropped_frames"] == 3


def test_compare_pass_and_fail():
    baseline = {
        "measures": {
            key: {"median": 10}
            for key in (
                "time_to_first_audio_ms",
                "stutter_count",
                "longest_gap_ms",
                "wake_cue_delay_ms",
                "stop_delay_ms",
            )
        }
    }
    improved = {
        "measures": {
            key: {"median": value} for key, value in zip(baseline["measures"], (9, 8, 7, 10, 10))
        }
    }
    assert compare(improved, baseline)[1]
    assert not compare(baseline, improved)[1]
    missing = {"measures": dict(improved["measures"])}
    missing["measures"]["wake_cue_delay_ms"] = {"median": None}
    assert not compare(missing, baseline)[1]


def test_sim_runs_twenty_turns():
    result = run_sim(delay=0)
    assert len(result["turns"]) == 20
    assert "time_to_first_audio_ms" in result["measures"]
