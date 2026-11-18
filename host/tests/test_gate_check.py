"""scripts/gate-check.py: the gate numbers in the script and in docs/dev/gate-numbers.md agree, and the verdict is strict."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("gate_check", ROOT / "scripts" / "gate-check.py")
gc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gc)

GOOD = {
    "face_move_fps": 44.7,
    "face_refresh_ms": 5,
    "picture_refresh_ms": 31,
    "wake_to_cue_median_ms": 22,
    "question_end_to_reply_median_ms": 6900,
    "question_end_to_reply_p95_ms": 20000,
}


def test_every_number_passes_when_inside_and_a_missing_one_fails():
    assert gc.verdict(GOOD)[1] is True
    missing = {k: v for k, v in GOOD.items() if k != "wake_to_cue_median_ms"}
    lines, ok = gc.verdict(missing)
    assert ok is False and any("not measured" in line for line in lines)
    assert gc.verdict({**GOOD, "face_move_fps": 20})[1] is False
    assert gc.verdict({**GOOD, "question_end_to_reply_p95_ms": 30000})[1] is False


def test_the_voice_trace_is_cut_into_rounds_at_the_wake_event():
    text = "\n".join(
        [
            "LAT: 1000 wake_evt",
            "LAT: 1020 listen_cue_queued",
            "LAT: 5000 inj_q_end",
            "LAT: 11000 tts_start",
            "LAT: 20000 wake_evt",
            "LAT: 20040 listen_cue_queued",
            "LAT: 24000 inj_q_end",
            "LAT: 33000 tts_start",
        ]
    )
    got = gc.voice_numbers(text)
    assert got["wake_to_cue_median_ms"] == 30 and got["question_end_to_reply_median_ms"] == 7500


def test_the_doc_lists_every_number_the_script_checks():
    doc = (ROOT / "docs" / "dev" / "gate-numbers.md").read_text().replace(",", "")
    for name, (cmp, limit, unit, _) in gc.GATES.items():
        forms = {f"{limit:g}", f"{limit / 1000:g} s"}  # milliseconds may be written as seconds
        assert any(f in doc for f in forms), (
            f"{name} limit {limit} is not in docs/dev/gate-numbers.md"
        )
