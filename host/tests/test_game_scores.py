"""Best scores per person: a finished game is filed under the named player or Someone; an early stop saves nothing; the person can be deleted."""

from __future__ import annotations

from maipai_body.game_scores import SOMEONE, ScoreBook


def test_a_finished_game_is_filed_under_someone_when_nobody_is_named(tmp_path):
    book = ScoreBook(tmp_path / "s.json")
    assert book.on_event("kitchen", "game_ended", {"game": "memory", "how": "finished", "score": 7})
    assert book.view("kitchen") == [{"person": SOMEONE, "games": [{"id": "memory", "scores": [7]}]}]


def test_a_named_player_gets_their_own_list_and_the_best_five_stay(tmp_path):
    names = {"who": "nadia"}
    book = ScoreBook(tmp_path / "s.json", player=lambda unit: names["who"])
    for score in (3, 9, 5, 7, 1, 8, 2):
        book.on_event("kitchen", "game_ended", {"game": "bopit", "how": "finished", "score": score})
    names["who"] = None
    book.on_event("kitchen", "game_ended", {"game": "bopit", "how": "finished", "score": 4})
    view = {v["person"]: v for v in book.view("kitchen")}
    assert view["nadia"]["games"] == [{"id": "bopit", "scores": [9, 8, 7, 5, 3]}]
    assert view[SOMEONE]["games"][0]["scores"] == [4]
    assert list(view)[-1] == SOMEONE, "Someone is listed last"


def test_a_game_stopped_early_or_a_bad_event_saves_nothing(tmp_path):
    book = ScoreBook(tmp_path / "s.json")
    assert not book.on_event("kitchen", "game_ended", {"game": "memory", "how": "stopped", "score": 5})
    assert not book.on_event("kitchen", "game_ended", {"game": "memory", "how": "finished", "score": "x"})
    assert not book.on_event("kitchen", "touch", {"game": "memory", "how": "finished", "score": 5})
    assert book.view("kitchen") == []


def test_units_are_separate_and_a_person_can_be_deleted(tmp_path):
    book = ScoreBook(tmp_path / "s.json", player=lambda unit: "iris")
    book.on_event("kitchen", "game_ended", {"game": "rps", "how": "finished", "score": 2})
    book.on_event("den", "game_ended", {"game": "rps", "how": "finished", "score": 3})
    assert book.view("den")[0]["games"][0]["scores"] == [3]
    assert book.forget("kitchen", "iris") and book.view("kitchen") == [] and book.view("den")
    assert not book.forget("kitchen", "iris")


def test_lower_is_better_sorts_the_other_way(tmp_path):
    book = ScoreBook(tmp_path / "s.json")
    for score in (30, 10, 20):
        book.on_event("k", "game_ended", {"game": "race", "how": "finished", "score": score}, lambda g: True)
    assert book.view("k")[0]["games"][0]["scores"] == [10, 20, 30]
