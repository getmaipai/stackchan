"""Twenty questions from the library with no model (docs/design/twenty-questions-library.md)."""

import random

import pytest
from maipai_packages.pantry.library import Library
from maipai_packages.pantry.record import Record, RecordError, check
from maipai_packages.pantry.talk_fallback import PantryTalk
from maipai_packages.pantry.twenty_fallback import QUESTIONS, TwentyQuestions, read_answer


def table(n=40):
    """n objects with spread out answers, like a real table (neighbors one bit apart would make a wrong answer unfixable)."""
    rng, seen, out = random.Random(7), [], []
    while len(out) < n:
        key = "".join(rng.choice("01") for _ in range(12))
        if all(sum(a != b for a, b in zip(key, other)) >= 3 for other in seen):
            seen.append(key)
            out.append(Record("object", "en", "kid", f"thing {len(out)}", "thing", key))
    return out


def play(objects, target, wrong_at=None, seed=1):
    engine = TwentyQuestions(random.Random(seed))
    game = engine.new(objects, 1.0)
    line, asked = engine.turn(game, "en", "ready"), 0
    while not game.done:
        if game.stage == "guessing":
            if line == f"Is it {target.text}?" or line == f"Hmm. Then is it {target.text}?":
                line = engine.turn(game, "en", "yes")
            else:
                line = engine.turn(game, "en", "no")
            continue
        q = QUESTIONS["en"].index(line)
        truth = target.extra[q] == "1"
        if wrong_at == asked:
            truth = not truth
        asked += 1
        line = engine.turn(game, "en", "yes" if truth else "no")
    return line, asked


def test_the_12_questions_exist_in_six_languages():
    assert all(len(q) == 12 for q in QUESTIONS.values()) and set(QUESTIONS) == {"en", "es", "fr", "de", "pt", "it"}


def test_object_record_shape_rules():
    assert check(Record("object", "en", "kid", "a cat", "animal", "110110000100")).kind == "object"
    for bad in (Record("object", "en", "kid", "a cat", "plant", "110110000100"), Record("object", "en", "kid", "a cat", "animal", "1101"), Record("object", "en", "kid", "x" * 30, "animal", "110110000100")):
        with pytest.raises(RecordError):
            check(bad)


@pytest.mark.parametrize("answer,expected", [("yes", "yes"), ("Sí", "yes"), ("nope", "no"), ("I do not know", "unknown"), ("maybe", "unknown"), ("banana", "")])
def test_read_answer(answer, expected):
    assert read_answer(answer) == expected


def test_a_known_table_is_solved_for_every_target():
    objects = table(40)
    for target in objects:
        line, asked = play(objects, target)
        assert line.startswith("I got it") and asked <= 12, (target.text, line)


def test_one_wrong_answer_is_forgiven_for_most_targets():
    objects = table(40)
    wins = sum(play(objects, t, wrong_at=3)[0].startswith("I got it") for t in objects)
    assert wins >= 36, wins


def test_too_small_a_library_says_so_and_through_the_talk_hook(tmp_path):
    lib = Library(tmp_path)
    talk = PantryTalk(lib, rng=random.Random(1))
    assert talk.line("a", "twenty_questions", "en", "ready")[0].startswith("I do not have enough")
    lib.add(table(30))
    line, scored = talk.line("a", "twenty_questions", "en", "ready", 5.0)
    assert line in QUESTIONS["en"] and scored is False
    ended = False
    for _ in range(40):
        talk.line("a", "twenty_questions", "en", "no", 5.0)
        if talk.done("a"):
            ended = True
            break
    assert ended


def test_the_shipped_english_table_is_solved_for_almost_every_target():
    """The built-in objects, played honestly for each one: the robot names it within the question limit and two guesses."""
    import json
    from pathlib import Path

    rows = json.loads((Path(__file__).resolve().parents[1] / "maipai_packages" / "pantry" / "seed" / "en-object.json").read_text(encoding="utf-8"))
    objects = [Record.from_json(r) for r in rows]
    won = sum(play(objects, target, seed=i)[0].startswith("I got it") for i, target in enumerate(objects))
    assert won == len(objects), f"{won} of {len(objects)}"
