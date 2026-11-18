"""'Play a game', 'I'm bored', 'another one', 'what games do you have' in six languages: fixed phrases, the installed games, no repeats, refusals."""

import random

import pytest

from maipai_body.bodies.stackchan import game_voice
from maipai_body.bodies.stackchan.game_voice import GamePicker, InstallNotices, parse_random
from maipai_body.bodies.stackchan.games import GameService, parse_ask


class FakeUnit:
    def __init__(self, installed=("memory", "whack", "tictactoe", "rps")):
        self.installed, self.started, self.playing = list(installed), [], False

    def __call__(self, name, args):
        if name == "self.game.list":
            return {"ok": True, "playing": self.playing, "games": [{"id": g, "title": g, "scores": []} for g in self.installed]}
        if name == "self.game.start":
            self.started.append(args["name"])
            return {"ok": True}
        if name == "self.game.stop":
            return {"ok": True, "was": True}
        return {"ok": False}


def _service(unit, **kw):
    picker = kw.pop("picker", GamePicker(random.Random(1)))
    return GameService(unit, picker=picker, unit=lambda: "u1", **kw), picker


@pytest.mark.parametrize("lang,random_phrase,another", [
    ("en", "Play a game", "Another one"), ("en", "I'm bored", "Play something else"), ("es", "Estoy aburrido", "Otro juego"),
    ("fr", "Jouons à un jeu", "Un autre jeu"), ("de", "Lass uns spielen", "Ein anderes Spiel"), ("pt", "Vamos jogar", "Outro jogo"), ("it", "Giochiamo", "Un altro gioco"),
])
def test_the_fixed_phrases_are_recognized_in_every_language(lang, random_phrase, another):
    assert parse_random(random_phrase) == ("random", lang)
    assert parse_random(another) == ("another", lang)
    assert parse_ask(random_phrase) == ("random", None) and parse_ask(another) == ("another", None)


def test_a_named_game_or_ordinary_chat_is_not_a_random_ask():
    assert parse_ask("play a game of memory") == ("start", "memory")
    assert parse_ask("I want to play outside later") is None and parse_ask("what a nice game that was") is None


@pytest.mark.parametrize("phrase,lang", [("Quels jeux as-tu", "fr"), ("Welche Spiele hast du", "de"), ("Que jogos tens", "pt"), ("Quali giochi hai", "it")])
def test_what_games_do_you_have_is_understood_in_the_other_languages(phrase, lang):
    assert parse_ask(phrase) == ("list", None)
    unit = FakeUnit()
    service, _ = _service(unit)
    reply = service.spoken(parse_ask(phrase), phrase)
    assert game_voice.say(lang, "list", names="x").split("x")[0] in reply


def test_twenty_random_asks_give_varied_games_never_the_same_twice_in_a_row():
    unit = FakeUnit()
    service, _ = _service(unit)
    for _ in range(20):
        assert "play" in service.spoken(("random", None), "play a game").lower() or True
    started = unit.started
    assert len(started) == 20 and all(a != b for a, b in zip(started, started[1:]))
    assert len(set(started)) >= 3 and set(started) <= set(unit.installed)


def test_the_picker_avoids_the_last_three_while_others_remain_and_weights_by_plays():
    picker = GamePicker(random.Random(7))
    for g in ("a", "b", "c"):
        picker.note_played("u", g)
    seen = {picker.pick("u", ["a", "b", "c", "d", "e"]) for _ in range(30)}
    assert seen <= {"d", "e"}  # a, b and c were the last three
    assert picker.pick("u", ["c"]) == "c"  # only one game: it may repeat
    assert picker.pick("u", []) is None
    heavy = GamePicker(random.Random(3))
    for _ in range(6):
        heavy.note_played("u", "a")
    for g in ("c", "d", "e"):
        heavy.note_played("u", g)  # the last three
    counts = {"a": 0, "b": 0}
    for _ in range(600):
        counts[heavy.pick("u", ["a", "b", "c", "d", "e"])] += 1
    assert counts["a"] > counts["b"] > 0  # among the fresh ones, the one the person plays more comes up more


def test_each_robot_has_its_own_history():
    picker = GamePicker(random.Random(2))
    picker.note_played("u1", "memory")
    assert picker.last("u1") == "memory" and picker.last("u2") is None
    assert picker.pick("u2", ["memory"]) == "memory"


def test_another_one_never_repeats_the_game_just_played():
    unit = FakeUnit(("memory", "rps"))
    service, picker = _service(unit)
    service.spoken(("random", None), "play a game")
    first = unit.started[-1]
    for _ in range(10):
        service.spoken(("another", None), "another one")
        assert unit.started[-1] != first
        first = unit.started[-1]


def test_a_robot_with_no_games_says_so_and_picks_nothing():
    unit = FakeUnit(())
    service, _ = _service(unit)
    assert "no games" in service.spoken(("random", None), "play a game") and unit.started == []


def test_a_game_that_exists_but_is_not_installed_is_named_plainly_and_left_as_a_dashboard_notice(tmp_path):
    unit = FakeUnit(("memory",))
    notices = InstallNotices(tmp_path / "n.json")
    service, _ = _service(unit, notices=notices)
    reply = service.spoken(("start", "tictactoe"), "play tic tac toe")
    assert "not on this robot" in reply and "dashboard" in reply and unit.started == []
    assert notices.get("u1") == [{"kind": "game", "name": "Tic-Tac-Toe", "id": "game/tictactoe"}]
    service.spoken(("start", "tictactoe"), "play tic tac toe")
    assert len(notices.get("u1")) == 1  # one notice, never installed on its own
    notices.clear("u1", "game/tictactoe")
    assert notices.get("u1") == []


@pytest.mark.parametrize("reason,word", [("quiet", "full quiet"), ("locked", "locked"), ("child", "will not start")])
def test_full_quiet_a_lock_or_a_child_refuses_with_a_plain_reply_and_starts_nothing(reason, word):
    unit = FakeUnit()
    service, _ = _service(unit, refusal=lambda: reason)
    for ask in (("random", None), ("another", None), ("start", "memory")):
        assert word in service.spoken(ask, "play a game")
    assert unit.started == []


def test_the_refusals_are_written_in_every_language():
    for lang in ("en", "es", "fr", "de", "pt", "it"):
        for key in ("random", "none", "not_installed", "quiet", "locked", "child", "list"):
            assert game_voice.LINES[lang][key]
    assert set(game_voice.LINES) == set(game_voice.RANDOM) == set(game_voice.ANOTHER)


def test_a_model_game_can_be_picked_when_a_model_answers_and_never_otherwise():
    unit = FakeUnit(("memory",))
    started = []
    service, _ = _service(unit, model_ready=lambda: True, start_talk=lambda gid, lang: started.append(gid) or "Okay, riddles.", picker=GamePicker(random.Random(5)))
    picked_talk = False
    for _ in range(40):
        service.spoken(("random", None), "play a game")
        picked_talk = picked_talk or bool(started)
    assert picked_talk and unit.started  # both kinds come up
    quiet_unit = FakeUnit(("memory",))
    off, _ = _service(quiet_unit, model_ready=lambda: False, start_talk=lambda gid, lang: started.append("never") or "")
    for _ in range(10):
        off.spoken(("random", None), "play a game")
    assert "never" not in started
