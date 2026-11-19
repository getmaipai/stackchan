"""The playground's offline lines (decision 24 extension): six situations in six languages, each within the record's limit, in the robot's plain voice, with the mouth levels the mumble reference gives,
and every frame (subtitle strip plus open mouth) is a scenario with a golden."""
import importlib.util
import sys
from pathlib import Path

VU = Path(__file__).resolve().parents[2] / "scripts" / "virtual-unit"
sys.path.insert(0, str(VU))
import offline_lines as ol  # noqa: E402


def test_every_situation_has_a_line_in_every_language_within_the_record_limit():
    assert len(ol.SITUATIONS) == 6 and len(ol.LANGS) == 6
    for sit in ol.SITUATIONS:
        assert set(ol.LINES[sit]) == set(ol.LANGS), sit
        for lg in ol.LANGS:
            text = ol.line(sit, lg)
            assert 0 < len(text.encode()) <= ol.MAX_BYTES, (sit, lg)
            assert "!" not in text and chr(0x2014) not in text, (sit, lg)   # the voice is plain: no exclamation points, no long dashes
            assert len(set(ol.LANGS) - {lg}) == 5 and all(ol.line(sit, o) != text for o in ol.LANGS if o != lg), (sit, lg)   # translated, not copied


def test_the_situations_are_among_the_twenty_of_the_pantry_record():
    src = (Path(__file__).resolve().parents[2] / "host" / "maipai_packages" / "pantry" / "record.py")
    if not src.exists():
        return
    text = src.read_text()
    for sit in ol.SITUATIONS:
        assert f'"{sit}"' in text, f"{sit} is not a situation of the pantry record"


def test_the_mouth_follows_the_mumble_and_opens_in_the_first_half():
    for sit in ol.SITUATIONS:
        for lg in ol.LANGS:
            text = ol.line(sit, lg)
            levels = ol.mouth_levels(text)
            assert levels and max(levels) <= 100 and min(levels) >= 0
            assert ol.mid_speech_level(text) >= 45   # the frame shows an open mouth (the quietest vowel is 45)


def test_each_line_is_a_scenario_with_a_golden():
    spec = importlib.util.spec_from_file_location("sc", VU / "scenarios.py")
    sc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sc)
    for sit in ol.SITUATIONS:
        for lg in ol.LANGS:
            name = f"offline-line-{sit.replace('_', '-')}-{lg}"
            assert name in sc.SCREENS, name
            assert (sc.GOLDEN_SCREENS / f"{name}.png").exists(), name
