# ruff: noqa: E501
"""Talk games: voice games the model plays, started on the robot with no model (bodies/stackchan/talk_games.py)."""

from __future__ import annotations

import re

import pytest

from maipai_body import reply_tags
from maipai_body.bodies.stackchan import talk_games as tg
from maipai_body.bodies.stackchan.games import parse_ask
from maipai_body.bodies.stackchan.head_commands import parse_head_command
from maipai_body.speech.reply_stream import ReplyTagger, TagStripper

EM = chr(0x2014)  # written this way so the hygiene check never sees the character here
DEVICE = "00:11:22:33:44:55"

START_EN = {
    "twenty_questions": ["play twenty questions", "let's play twenty questions", "Play 20 questions!", "twenty questions", "can you play twenty questions with me", "StackChan, let's play a game of twenty questions"],
    "riddles": ["tell me a riddle", "give me a riddle", "can you tell me a riddle please", "a riddle", "another riddle", "let's play riddles"],
    "trivia": ["let's play trivia", "play trivia", "trivia", "quiz me", "I want to play a trivia game"],
    "word_chain": ["word chain", "play word chain", "let's play the word chain game", "I want to play word chain"],
    "would_you_rather": ["would you rather", "let's play would you rather", "play would you rather", "ask me a would you rather question"],
    "jokes": ["play jokes", "jokes", "joke time", "let's play the joke game"],
    "bedtime_story": ["tell me a bedtime story", "tell me a story", "read me a story", "story time", "can you tell me a story before bed", "I want a bedtime story"],
}
START_ES = {
    "twenty_questions": ["juguemos a veinte preguntas", "jugar a las veinte preguntas", "veinte preguntas", "20 preguntas"],
    "riddles": ["dime una adivinanza", "cuéntame una adivinanza", "una adivinanza", "juguemos a las adivinanzas"],
    "trivia": ["juguemos a la trivia", "jugar a trivia", "jugar al trivial"],
    "word_chain": ["cadena de palabras", "juguemos a las palabras encadenadas", "jugar a la cadena de palabras"],
    "would_you_rather": ["qué prefieres", "juguemos a qué prefieres", "pregúntame qué prefieres"],
    "jokes": ["juguemos a los chistes", "chistes", "hora de chistes"],
    "bedtime_story": ["cuéntame un cuento", "cuéntame un cuento para dormir", "léeme un cuento", "hora del cuento"],
}

CHAT = [
    "what is a riddle",
    "do you know any good riddles",
    "I told my sister a riddle yesterday",
    "who invented trivia",
    "tell me about the history of word chains in japan",
    "tell me a story about a dragon who loves pizza",
    "stop the game",  # not a start (and not an end unless a game is on)
    "I have twenty questions about space for you",
    "what's the weather",
    "play memory",
    "play a game",
    "tell me a joke",
    "",
    "   ",
]


@pytest.mark.parametrize(("game", "phrase"), [(g, p) for g, ps in START_EN.items() for p in ps])
def test_english_start_phrases_pick_their_game(game, phrase) -> None:
    command = tg.parse(phrase)
    assert command is not None and (command.kind, command.game, command.lang) == ("start", game, "en"), phrase


@pytest.mark.parametrize(("game", "phrase"), [(g, p) for g, ps in START_ES.items() for p in ps])
def test_spanish_start_phrases_pick_their_game_and_speak_spanish(game, phrase) -> None:
    command = tg.parse(phrase)
    assert command is not None and (command.kind, command.game, command.lang) == ("start", game, "es"), phrase
    line = tg.TalkGames().run(command, DEVICE)
    assert line == tg.get(game).start["es"]


@pytest.mark.parametrize("phrase", CHAT)
def test_ordinary_chat_is_not_a_game(phrase) -> None:
    assert tg.parse(phrase) is None, phrase
    assert tg.parse(phrase, active=False) is None


def test_a_long_sentence_is_never_a_start() -> None:
    assert tg.parse("tell me a riddle about the moon and the sea and the old house by the lake please") is None


def test_every_game_has_start_phrases_lines_rules_and_a_round_limit_in_both_languages() -> None:
    assert set(START_EN) == set(START_ES) == set(tg.IDS)
    for game in tg.TALK_GAMES:
        assert set(game.title) == set(game.hint) == set(game.start) == {"en", "es"}
        assert game.rules.strip() and 3 <= game.max_rounds <= 30
        for text in (*game.title.values(), *game.hint.values(), *game.start.values(), game.rules):
            assert EM not in text and text.strip()


def test_start_phrases_do_not_collide_with_the_unit_games_or_head_commands() -> None:
    for phrases in (*START_EN.values(), *START_ES.values()):
        for phrase in phrases:
            assert parse_ask(phrase) is None, phrase
            assert parse_head_command(phrase) is None or tg.parse(phrase) is not None


# ---------------------------------------------------------------- state machine


class Clock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def start(games: tg.TalkGames, phrase: str = "play trivia") -> str:
    command = games.parse(phrase, DEVICE)
    assert command is not None and command.kind == "start"
    return games.run(command, DEVICE)


def test_start_says_a_fixed_line_and_creates_the_state() -> None:
    games = tg.TalkGames(clock=Clock())
    assert not games.active(DEVICE)
    line = start(games)
    assert line == tg.get("trivia").start["en"]
    state = games.state(DEVICE)
    assert (state.game, state.rounds, state.score, state.max_rounds) == ("trivia", 0, 0, tg.get("trivia").max_rounds)
    assert games.status(DEVICE) == {"playing": True, "game": "trivia", "round": 0, "max_rounds": 10, "score": 0}


def test_starting_asks_no_model_and_a_second_start_replaces_the_game() -> None:
    games = tg.TalkGames(clock=Clock())
    start(games, "play trivia")
    games.begin_turn(DEVICE)
    start(games, "tell me a riddle")
    state = games.state(DEVICE)
    assert state.game == "riddles" and state.rounds == 0


def test_each_model_turn_counts_a_round_and_carries_the_rules() -> None:
    games = tg.TalkGames(clock=Clock())
    start(games, "let's play riddles")
    first = games.begin_turn(DEVICE)
    assert "Game: riddles" in first and "round 1 of 8" in first and tg.COMMON_RULES in first
    second = games.begin_turn(DEVICE)
    assert "round 2 of 8" in second
    assert games.state(DEVICE).rounds == 2


def test_no_game_means_no_rules_and_nothing_changes_for_chat() -> None:
    games = tg.TalkGames(clock=Clock())
    assert games.begin_turn(DEVICE) is None
    assert games.parse("stop the game", DEVICE) is None  # falls through to the unit's own game stop


def test_the_round_limit_wraps_up_on_the_last_turn_then_chat_is_normal() -> None:
    games = tg.TalkGames(clock=Clock())
    start(games, "would you rather")
    limit = tg.get("would_you_rather").max_rounds
    for n in range(1, limit):
        text = games.begin_turn(DEVICE)
        assert f"round {n} of {limit}" in text and "last round" not in text
    last = games.begin_turn(DEVICE)
    assert f"round {limit} of {limit}" in last and "last round" in last
    assert not games.active(DEVICE)
    assert games.begin_turn(DEVICE) is None


@pytest.mark.parametrize(
    ("phrase", "lang"),
    [
        ("stop the game", "en"),
        ("stop playing", "en"),
        ("I'm done", "en"),
        ("ok I am done playing", "en"),
        ("end the game", "en"),
        ("no more", "en"),
        ("para el juego", "es"),
        ("deja de jugar", "es"),
        ("ya terminé", "es"),
        ("ya no quiero jugar", "es"),
    ],
)
def test_ending_phrases_end_the_game_with_a_fixed_line(phrase, lang) -> None:
    games = tg.TalkGames(clock=Clock())
    start(games)
    command = games.parse(phrase, DEVICE)
    assert command is not None and command.kind == "end" and command.lang == lang
    assert games.run(command, DEVICE) == tg.END_LINE[lang]
    assert not games.active(DEVICE) and games.begin_turn(DEVICE) is None


def test_an_answer_that_only_mentions_done_does_not_end_the_game() -> None:
    games = tg.TalkGames(clock=Clock())
    start(games)
    for answer in ("I'm done with my homework", "is the answer Paris", "stop signs are red", "the answer is four"):
        assert games.parse(answer, DEVICE) is None, answer


def test_enough_and_never_mind_end_a_game_but_a_bare_stop_only_hushes() -> None:
    games = tg.TalkGames(clock=Clock())
    start(games)
    assert games.on_stop_phrase(DEVICE, "stop") is False and games.active(DEVICE)
    assert games.on_stop_phrase(DEVICE, "That's enough!") is True and not games.active(DEVICE)
    start(games)
    assert games.on_stop_phrase(DEVICE, "never mind") is True and not games.active(DEVICE)
    assert games.on_stop_phrase(DEVICE, "never mind") is False  # nothing to end


def test_a_long_silence_ends_the_game() -> None:
    clock = Clock()
    games = tg.TalkGames(clock=clock, silence_s=300.0)
    start(games)
    clock.t += 299
    assert games.active(DEVICE)
    games.begin_turn(DEVICE)  # a turn restarts the silence timer
    clock.t += 299
    assert games.active(DEVICE)
    clock.t += 2
    assert not games.active(DEVICE)
    assert games.begin_turn(DEVICE) is None


def test_games_are_kept_per_unit() -> None:
    games = tg.TalkGames(clock=Clock())
    start(games, "play trivia")
    assert games.active(DEVICE) and not games.active("aa:bb:cc:dd:ee:ff")
    assert games.begin_turn("aa:bb:cc:dd:ee:ff") is None


def test_a_point_is_counted_only_when_a_source_says_so() -> None:
    games = tg.TalkGames(clock=Clock())
    assert games.add_point(DEVICE) == 0
    start(games, "play trivia")
    games.begin_turn(DEVICE)
    assert games.state(DEVICE).score == 0  # nothing guesses one from words
    assert games.add_point(DEVICE) == 1 and games.add_point(DEVICE) == 2
    assert "keep it in your own words" in games.begin_turn(DEVICE)


def test_a_status_hook_hears_start_and_end_and_never_breaks_a_game() -> None:
    seen: list = []

    def hook(device_id, state):
        seen.append((device_id, None if state is None else state.game))
        raise RuntimeError("a status hook must not break the game")

    games = tg.TalkGames(clock=Clock(), on_change=hook)
    start(games)
    games.end(DEVICE)
    assert seen == [(DEVICE, "trivia"), (DEVICE, None)]


# ---------------------------------------------------------------- prompt injection


def _tags_in(text: str) -> list[str]:
    return re.findall(r"\[([^\]]+)\]", text)


def test_the_rules_only_name_tags_the_host_understands() -> None:
    for game in tg.TALK_GAMES:
        state = tg.TalkState(game.id, 0.0, 0.0, game.max_rounds, rounds=1)
        for inner in _tags_in(tg.rules_text(state)):
            assert reply_tags.parse_tag(inner).kind != "unknown", (game.id, inner)
    state = tg.TalkState("trivia", 0.0, 0.0, 10, rounds=1)
    text = tg.rules_text(state)
    for needed in ("[happy]", "[confetti]", "[scene celebrate]", "[sad]", "[doubt]", "[surprised]"):
        assert needed in text  # cheer, think, right and wrong
    assert "never say a tag aloud" in text and "never replace your other rules" in text and "safety rule" in text


class FakeInner:
    def __init__(self) -> None:
        self.calls: list = []

    def stream(self, text, **kwargs):
        self.calls.append((text, kwargs))
        return iter(())

    def cancel(self, turn_id):
        return True


def test_own_model_gets_the_rules_as_instructions_next_to_the_persona() -> None:
    inner = FakeInner()
    turn = tg.GameTurn(inner, "RULES", persona_path=True)
    list(turn.stream("my answer", conversation_id="c"))
    assert inner.calls == [("my answer", {"instructions": "RULES", "conversation_id": "c"})]
    assert turn.cancel("t") is True


def test_the_home_turn_gets_the_rules_in_front_of_the_words() -> None:
    inner = FakeInner()
    list(tg.GameTurn(inner, "RULES", persona_path=False).stream("my answer", present=None))
    text, kwargs = inner.calls[0]
    assert text == "[Game rules for this turn: RULES] my answer" and kwargs == {"present": None}


def test_the_rules_reach_the_models_system_message_and_only_for_that_turn(monkeypatch) -> None:
    from maipai_body.brain.interface import TurnRequest
    from maipai_body.brain.own_llm import OwnLLMBrain
    from maipai_body.config import LlmConfig

    sent: list = []

    class Response:
        status_code = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def raise_for_status(self):
            return None

        def iter_lines(self, **kw):
            yield 'data: {"choices":[{"delta":{"content":"[happy] Yes!"}}]}'
            yield "data: [DONE]"

    class Session:
        def post(self, url, json=None, **kw):
            sent.append(json)
            return Response()

    brain = OwnLLMBrain(LlmConfig(url="http://llm.example.com", model="m", persona="PERSONA"), session=Session())
    list(brain.stream_turn(TurnRequest(text="hi", conversation_id="c", instructions="GAME RULES")))
    list(brain.stream_turn(TurnRequest(text="hi again", conversation_id="c")))
    assert sent[0]["messages"][0]["content"] == "PERSONA\n\nGAME RULES"
    assert sent[1]["messages"][0]["content"] == "PERSONA"  # the next turn carries no rules


def test_the_persons_words_never_start_or_change_a_game_through_the_rules() -> None:
    # The rules text is built only from the catalog and counters; nothing the person said can reach it.
    games = tg.TalkGames(clock=Clock())
    start(games, "play trivia")
    text = games.begin_turn(DEVICE)
    games2 = tg.TalkGames(clock=Clock())
    start(games2, "play trivia")
    assert games2.begin_turn(DEVICE) == text


# ---------------------------------------------------------------- nothing is spoken as a tag


MODEL_REPLIES = [
    "[happy] [confetti] That is right! Paris is the capital of France.",
    "[sad] Not this time. The answer was four. [doubt] Want to try another?",
    "[scene celebrate] [happy] You won the game!",
    "[doubt] Hmm, is it a big animal? Question 3 of 20.",
    "[sleepy] [scene bedtime] Once upon a time, a little fox found a star. Do you want to hear more?",
    "[surprised] [sound:success] Wow, you got it!",
]


@pytest.mark.parametrize("reply", MODEL_REPLIES)
def test_no_reply_tag_is_spoken_whole_or_one_character_at_a_time(reply) -> None:
    for chunks in ([reply], list(reply)):
        stripper = TagStripper()
        spoken = "".join(stripper.feed(c) for c in chunks) + stripper.flush()
        assert "[" not in spoken and "]" not in spoken
        tagger = ReplyTagger()
        items = tagger.feed(reply) + tagger.flush()
        said = " ".join(getattr(i, "text", "") or "" for i in items)
        assert "[" not in said and "scene" not in said.lower().split() and "confetti" not in said.lower().split()
    stripper = TagStripper()
    spoken = stripper.feed(reply) + stripper.flush()
    assert spoken.strip() and spoken.lstrip()[0] not in "[]"
    assert not re.search(r"\b(scene|confetti|celebrate|bedtime|sound)\b", spoken.lower())


def test_the_start_and_end_lines_hold_no_bracket_and_no_dash() -> None:
    for game in tg.TALK_GAMES:
        for text in game.start.values():
            assert "[" not in text and "]" not in text and EM not in text
    for text in tg.END_LINE.values():
        assert "[" not in text and EM not in text


# ---------------------------------------------------------------- the settings page list


def test_the_settings_page_lists_talk_games_as_their_own_group_in_english_and_spanish() -> None:
    en, es = tg.group("en"), tg.group("es")
    assert en["title"] == "Talk games" and es["title"] != en["title"]
    assert [g["id"] for g in en["games"]] == list(tg.IDS) == [g["id"] for g in es["games"]]
    assert en["games"][0]["title"] == "Twenty questions" and es["games"][0]["title"] == "Veinte preguntas"
    assert tg.group("fr") == en and tg.group(None) == en  # other languages read English, as other lists do


def test_the_games_route_returns_the_talk_group_apart_from_the_unit_games(tmp_path) -> None:
    from maipai_body.settings_sim import KITCHEN, build

    backend, _units = build(tmp_path)
    import json

    status, _, body = backend.route_get(f"/api/stackchan/unit/{KITCHEN}/games", "es", True)
    data = json.loads(body)
    assert status == 200 and data["talk"]["title"] == tg.GROUP_TITLE["es"]
    assert len(data["talk"]["games"]) == len(tg.TALK_GAMES)
    assert all(row["id"] not in {x["id"] for x in data.get("games", [])} for row in data["talk"]["games"])


def test_the_page_script_draws_the_talk_group() -> None:
    from maipai_body import settings_ui

    assert "g.d.talk" in settings_ui.JS and "talkCard" in settings_ui.JS


# ---------------------------------------------------------------- the voice path (turn bridge)


def test_the_bridge_routes_a_talk_game_start_locally_and_wraps_the_next_turn(monkeypatch) -> None:
    from maipai_body.bodies.stackchan.turn import StackChanTurnBridge

    bridge = StackChanTurnBridge.__new__(StackChanTurnBridge)
    bridge.talk_games = tg.TalkGames(clock=Clock())
    bridge.volume_control = bridge.brightness_control = bridge.head_control = bridge.alarm_control = None
    route = bridge._route_of("let's play trivia", "speech", DEVICE)
    assert route[0] == "local command" and "talk game" in route[1]
    assert bridge._route_of("what is the capital of france", "speech", DEVICE)[0] == "chat"
    bridge.talk_games.run(bridge.talk_games.parse("let's play trivia", DEVICE), DEVICE)
    # while a game is on, "stop the game" is a local command too
    assert bridge._route_of("stop the game", "speech", DEVICE)[0] == "local command"


def _say_all(monkeypatch, utterances, games):
    """Run one turn per utterance through the real bridge with the stock fakes; answers (turns the model got, lines spoken)."""
    import asyncio

    import maipai_body.bodies.stackchan.turn as turn_module
    from maipai_body.speech.stt_stream import SttStreamResult
    from tests.test_stackchan_turn import (  # type: ignore[import-not-found]
        FakeCapture,
        FakePlayback,
        FakeServer,
        FakeTts,
        FakeTurn,
        InlineExecutor,
        Link,
        Offline,
    )

    heard = iter(utterances)

    class Stt:
        def __init__(self, base, cookie):
            pass

        def run(self, capture, **kwargs):
            return SttStreamResult(kind="final", text=next(heard))

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    server = FakeServer()
    server._loop = loop
    FakeTurn.streams = []
    FakeTts.sentences = []
    monkeypatch.setattr(turn_module, "StackChanAudioPlayback", FakePlayback)
    bridge = turn_module.StackChanTurnBridge(
        server, Link(), Offline(), stt_factory=Stt, turn_factory=FakeTurn, tts_factory=FakeTts, side_executor=InlineExecutor()
    )
    bridge.talk_games = games
    per_turn = []
    for _ in utterances:
        before = len(FakeTurn.streams)
        said_before = len(FakeTts.sentences)
        loop.run_until_complete(bridge._run("session", DEVICE, FakeCapture()))
        per_turn.append((FakeTurn.streams[before:], FakeTts.sentences[said_before:]))
    loop.close()
    return per_turn


def test_a_whole_game_through_the_bridge_start_no_model_rules_on_turns_stop_then_plain_chat(monkeypatch) -> None:
    games = tg.TalkGames(clock=Clock())
    turns = _say_all(
        monkeypatch,
        ["let's play trivia", "go", "four", "stop the game", "what is the weather"],
        games,
    )
    start_streams, start_said = turns[0]
    assert start_streams == [] and start_said == [tg.get("trivia").start["en"]]  # the start asks no model
    (go_stream,), _ = turns[1]
    assert go_stream[0].startswith("[Game rules for this turn: ") and go_stream[0].endswith("] go")
    assert "round 1 of 10" in go_stream[0]
    (four_stream,), _ = turns[2]
    assert "round 2 of 10" in four_stream[0]
    stop_streams, stop_said = turns[3]
    assert stop_streams == [] and stop_said == [tg.END_LINE["en"]]  # the end asks no model either
    (chat_stream,), _ = turns[4]
    assert chat_stream[0] == "what is the weather"  # normal chat: no rules, no brackets
    assert not games.active(DEVICE)


def test_the_bridge_without_talk_games_is_unchanged(monkeypatch) -> None:
    turns = _say_all(monkeypatch, ["let's play trivia"], None)
    (stream,), _ = turns[0]
    assert stream[0] == "let's play trivia"
