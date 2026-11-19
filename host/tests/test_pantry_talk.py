"""Riddles and trivia from the pantry library with no model (talk_fallback.py)."""

import random

from maipai_packages.pantry.library import Library
from maipai_packages.pantry.record import Record
from maipai_packages.pantry.talk_fallback import PantryTalk, matches


def make(tmp_path, records):
    lib = Library(tmp_path)
    lib.add(records)
    return PantryTalk(lib, rng=random.Random(1)), lib


def test_matches_whole_answer_among_words():
    assert matches("is it a Piano", "piano") and matches("PIANO", "piano")
    assert not matches("piano forte", "pia") and not matches("", "piano")


def test_riddle_right_scores_and_next_turn_asks_another(tmp_path):
    talk, _ = make(tmp_path, [Record("riddle", "en", "kid", "What has keys but opens no doors?", "piano"), Record("riddle", "en", "kid", "What has a face but no eyes?", "clock")])
    question, scored = talk.line("a", "riddles", "en", "go")
    assert "?" in question and scored is False
    asked = "piano" if "keys" in question else "clock"
    line, scored = talk.line("a", "riddles", "en", f"is it a {asked}")
    assert line.startswith("Right") and scored is True
    second, _ = talk.line("a", "riddles", "en", "yes")
    assert second != question  # never heard twice


def test_riddle_two_misses_reveal_the_answer(tmp_path):
    talk, _ = make(tmp_path, [Record("riddle", "en", "kid", "What has keys but opens no doors?", "piano")])
    talk.line("a", "riddles", "en", "go")
    assert talk.line("a", "riddles", "en", "dog")[0].startswith("Not quite. Try")
    assert talk.line("a", "riddles", "en", "cat")[0] == "The answer is piano."


def test_trivia_offers_three_choices_and_one_try(tmp_path):
    talk, _ = make(tmp_path, [Record("trivia", "en", "kid", "Which planet is red?", "Mars", "Venus|Saturn")])
    line, _ = talk.line("a", "trivia", "en", "go")
    assert all(x in line for x in ("Mars", "Venus", "Saturn"))
    assert talk.line("a", "trivia", "en", "venus") == ("Not quite. It is Mars.", False)


def test_adult_records_skipped_and_empty_library_says_so(tmp_path):
    talk, _ = make(tmp_path, [Record("riddle", "en", "adult", "A grown up riddle?", "x")])
    assert talk.line("a", "riddles", "en", "go")[0].startswith("I do not have any more")
    assert talk.line("a", "twenty_questions", "en", "go") is None


def test_turn_hook_plays_a_riddle_turn_when_the_model_is_out_of_reach(tmp_path):
    import asyncio
    from types import SimpleNamespace

    from maipai_body.bodies.stackchan.talk_games import TalkCommand, TalkGames
    from maipai_body.bodies.stackchan.turn import StackChanTurnBridge

    talk, _ = make(tmp_path, [Record("riddle", "en", "kid", "What has keys but opens no doors?", "piano")])
    games, said, notes = TalkGames(), [], []
    games.run(TalkCommand("start", "riddles", "en"), "unit-a")
    fake = SimpleNamespace(talk_fallback=talk, talk_games=games, _say=lambda p, b, c, line: said.append(line), _breaker=SimpleNamespace(note_speech=lambda: notes.append(1)))
    play = lambda text: asyncio.run(StackChanTurnBridge._pantry_game_turn(fake, "unit-a", SimpleNamespace(text=text), None, None, None))  # noqa: E731
    assert play("go") is True and "keys" in said[-1]
    assert play("piano") is True and said[-1].startswith("Right") and games.state("unit-a").score == 1
    games.run(TalkCommand("start", "twenty_questions", "en"), "unit-a")
    assert play("a dog") is False  # no library half: the usual offline line follows
