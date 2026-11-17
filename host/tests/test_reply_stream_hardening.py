# ruff: noqa: E501
"""The parser never speaks a long bracket run or JSON (docs/design/llm-display-control-2026-11-17.md section 8.4).

Cases: runs of 59, 60, 61, 90 and 91 characters; JSON; nested brackets; the same text fed whole, in random pieces and one
character at a time; and a fuzz over a small alphabet of the characters that matter. The invariants hold for every input:
no exception, the same output however the stream is cut, no ``[`` followed by more than 60 characters on its line, and no
``{"`` run in what is spoken.
"""

from __future__ import annotations

import logging
import random

import pytest

from maipai_body.speech.reply_stream import MAX_TAG_CHARS, ReplyTagger, TagStripper


def strip(chunks):
    stripper = TagStripper()
    out = "".join(stripper.feed(c) for c in chunks) + stripper.flush()
    return out, stripper


def whole(text):
    return strip([text])


def by_char(text):
    return strip(list(text))


def by_random(text, rng):
    pieces, i = [], 0
    while i < len(text):
        n = rng.randint(1, 9)
        pieces.append(text[i : i + n])
        i += n
    return strip(pieces)


def run_of(total_with_brackets: int) -> str:
    return "[" + "a" * (total_with_brackets - 2) + "]"


@pytest.mark.parametrize("total", [59, 60, 61, 62, 90, 91, 200])
def test_a_bracket_run_of_any_length_is_never_spoken(total):
    text = f"Hello {run_of(total)} there."
    for out in (whole(text)[0], by_char(text)[0]):
        assert out == "Hello  there."


def test_a_long_run_is_dropped_counted_and_logged_without_its_words(caplog):
    caplog.set_level(logging.INFO, logger="maipai_body.speech.reply_stream")
    secret = "x" * 80
    out, stripper = whole(f"Hi [{secret}] there.")
    assert out == "Hi  there." and stripper.dropped == 1
    assert "dropped from speech" in caplog.text and secret not in caplog.text


def test_a_long_run_that_never_closes_is_dropped_to_the_newline():
    text = "Intro [" + "word " * 30 + "\nNext line is spoken."
    out, stripper = whole(text)
    assert out == "Intro \nNext line is spoken." and stripper.dropped == 1
    assert by_char(text)[0] == out


def test_a_long_run_that_never_closes_is_dropped_at_the_end_of_the_stream():
    out, stripper = whole("Intro [" + "word " * 30)
    assert out == "Intro " and stripper.dropped == 1


def test_a_short_open_bracket_is_still_plain_text_and_tag_letters_are_dropped():
    assert whole("a [2")[0] == "a [2"
    assert whole("Fine [mood")[0] == "Fine "
    assert whole("a [2 and more\nnext")[0] == "a [2 and more\nnext"


def test_json_is_never_spoken_in_any_shape():
    for text in (
        'Sure. {"type": "text", "body": "hello"} Done.',
        'Sure. [{"type": "text", "body": "this is a long card payload that goes past the limit"}] Done.',
        'Sure. {"a": {"b": [1, 2, {"c": 3}]}} Done.',
        "Sure. [[1, 2], [3, 4], [5, 6], [7, 8], [9, 10], [11, 12], [13, 14], [15, 16]] Done.",
    ):
        for out in (whole(text)[0], by_char(text)[0]):
            assert out == "Sure.  Done." and '"' not in out, text


def test_braces_that_are_not_json_are_plain_text():
    assert whole("Use {curly} braces, and {x=1}.")[0] == "Use {curly} braces, and {x=1}."
    assert whole("An unfinished { brace")[0] == "An unfinished { brace"


def test_a_short_json_array_tag_is_a_tag_and_not_spoken():
    out, stripper = whole('Hi [{"a":1}] there.')
    assert out == "Hi  there." and stripper.tags == ['{"a":1}']


def test_nested_brackets_inside_a_short_tag_close_together():
    out, stripper = whole("Hi [mood [x]] there.")
    assert out == "Hi  there." and stripper.tags == ["mood [x]"]


def test_a_long_run_gives_no_cue_and_no_speech_in_the_tagger():
    tagger = ReplyTagger()
    items = list(tagger.feed("[happy] Fine. [" + "z" * 100 + "] Bye. "))
    items += tagger.flush()
    assert [i.text for i in items if i.text] == ["Fine.", "Bye."]
    assert [(c.kind, c.name) for i in items for c in i.cues] == [("mood", "happy")]


ALPHABET = ["[", "]", "{", "}", '"', "\n", " ", "a", "b", "happy", "scene ", "rain", ":", "\\", ".", "\U0001f600", "(", ")", "*"]


def invariants(out: str, text: str = "") -> None:
    """``text`` is the input: JSON is checked on inputs without brackets, because removing a tag that sits inside a brace run can
    leave the two characters ``{"`` side by side in the speech of text that was never JSON to begin with."""
    for line in out.split("\n"):
        i = line.find("[")
        while i != -1:
            assert len(line) - i <= MAX_TAG_CHARS + 1, (line, i)
            i = line.find("[", i + 1)
    if "[" not in text:
        assert '{"' not in out and '{ "' not in out


def test_fuzz_the_output_is_the_same_however_the_stream_is_cut_and_never_breaks_the_rules():
    rng = random.Random(20261117)
    for _ in range(1500):
        text = "".join(rng.choice(ALPHABET) for _ in range(rng.randint(0, 220)))
        out, stripper = whole(text)
        invariants(out, text)
        single = by_char(text)
        assert single[0] == out, repr(text)
        assert by_random(text, rng)[0] == out, repr(text)
        assert single[1].tags == stripper.tags


def test_fuzz_long_runs_always_drop():
    rng = random.Random(7)
    for _ in range(300):
        body = "".join(rng.choice("abcdef ,:") for _ in range(rng.randint(61, 150)))
        text = f"x [{body}] y"
        assert whole(text)[0] == "x  y"
        assert by_char(text)[0] == "x  y"


def test_cutting_the_tagger_stream_anywhere_gives_the_same_cues_and_sentences():
    text = "[happy] [scene rainy_day] It is wet. [rain]Pour[/rain] now. [sound:success] [light:blue 5] Bye. [unknown] Done."

    def run(chunks):
        tagger = ReplyTagger()
        items = []
        for c in chunks:
            items += tagger.feed(c)
        items += tagger.flush()
        return [(i.text, tuple((c.kind, c.name, c.intensity, c.seconds) for c in i.cues)) for i in items]

    expected = run([text])
    assert run(list(text)) == expected
    for cut in range(1, len(text)):
        assert run([text[:cut], text[cut:]]) == expected, cut


def test_a_tag_inside_braces_is_still_a_tag():
    out, stripper = whole("Use {a [happy] b} here.")
    assert out == "Use {a  b} here." and stripper.tags == ["happy"]
