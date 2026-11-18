"""The memory notes package: plain per-person files, remember and forget on request, off by default."""

import datetime
import stat
import sys

import pytest

from maipai_packages.memory_notes import AdmissionError, Notes, NotesStore, check_note


@pytest.fixture
def notes(tmp_path):
    store = NotesStore(tmp_path / "notes", today=lambda: datetime.date(2026, 11, 18))
    return Notes(store, ["alex", "sam"], default_person="alex"), tmp_path / "notes"


def test_remember_writes_a_plain_readable_line_with_a_date_and_an_id(notes):
    n, folder = notes
    assert n.handle("Remember that I like oat milk", "alex") == "Okay, I will remember that."
    line = (folder / "alex.md").read_text().strip()
    assert line.startswith("- 2026-11-18 [") and line.endswith("] I like oat milk")
    assert (folder / "alex.md").stat().st_mode & 0o777 == 0o600


def test_notes_are_read_back_only_to_their_person(notes):
    n, _ = notes
    n.handle("remember my locker is number 12", "alex")
    n.handle("remember I am allergic to peanuts", "sam")
    assert "peanuts" not in n.context("alex") and "locker" in n.context("alex")
    assert "locker" not in n.context("sam") and "peanuts" in n.context("sam")
    assert n.context("a stranger") == "" and n.context(None) == n.context("alex")  # no speaker named: the default person only
    assert "peanuts" not in n.handle("what do you remember", "alex")


def test_household_notes_reach_every_listed_adult(notes):
    n, _ = notes
    n.handle("remember for everyone that the wifi guest name is cabin", "alex")
    assert "cabin" in n.context("sam") and "cabin" in n.context("alex")


def test_forget_removes_matching_notes_and_forget_everything_removes_the_file(notes):
    n, folder = notes
    n.handle("remember I like oat milk", "alex")
    n.handle("remember I like tea", "alex")
    assert n.handle("forget oat milk", "alex") == "Done. I forgot 1 thing."
    assert "oat milk" not in (folder / "alex.md").read_text() and "tea" in (folder / "alex.md").read_text()
    assert n.handle("forget everything about me", "alex").startswith("Done. I forgot 1")
    assert not (folder / "alex.md").exists()
    assert n.handle("forget the moon", "alex") == "I did not find that."


@pytest.mark.parametrize(
    "text",
    ["my password is hunter2", "card 4111 1111 1111 1111", "ssn 123-45-6789", "my pin is 4821", "x" * 301, "   "],
)
def test_credentials_numbers_and_oversize_text_are_not_stored(text):
    with pytest.raises(AdmissionError):
        check_note(text)


def test_a_refused_note_says_why_and_stores_nothing(notes):
    n, folder = notes
    reply = n.handle("remember my password is hunter2", "alex")
    assert "password manager" in reply and not (folder / "alex.md").exists()


def test_only_listed_adults_have_notes(tmp_path):
    n = Notes(NotesStore(tmp_path), ["alex"])  # no default person: an unknown speaker is not anyone
    assert "who is asking" in n.handle("remember I like tea", "kid")
    assert n.context("kid") == ""


def test_other_sentences_are_left_to_the_model(notes):
    n, _ = notes
    assert n.handle("what is the capital of France", "alex") is None
    assert n.handle("I will remember this day forever", "alex") is None


def test_a_person_name_cannot_escape_the_folder(tmp_path):
    store = NotesStore(tmp_path / "notes")
    with pytest.raises(AdmissionError):
        store.add("../evil", "x")


def test_it_is_off_costing_nothing_by_default():
    from maipai_body.config import RobotConfig

    assert RobotConfig().packages.memory_notes.enabled is False
    sys.modules.pop("maipai_packages.memory_notes", None)
    from maipai_body.brain.own_llm import OwnLLMBrain
    from maipai_body.config import LlmConfig

    assert OwnLLMBrain(LlmConfig()).memory is None


def test_a_notes_request_is_answered_without_a_model_call_and_notes_reach_the_prompt(notes):
    import json

    from maipai_body.brain.interface import TurnRequest
    from maipai_body.brain.own_llm import OwnLLMBrain
    from maipai_body.config import LlmConfig

    n, _ = notes

    class Session:
        def __init__(self):
            self.bodies = []

        def post(self, url, **kw):
            self.bodies.append(kw["json"])
            raise RuntimeError("no network in this test")

    session = Session()
    brain = OwnLLMBrain(LlmConfig(url="http://192.0.2.5:8080", model="m"), session=session)
    brain.memory = n
    events = list(brain.stream_turn(TurnRequest(text="remember I like oat milk", speaker_evidence={"person_id": "alex"})))
    assert events[0].reply_text == "Okay, I will remember that." and session.bodies == []
    list(brain.stream_turn(TurnRequest(text="what should I drink", speaker_evidence={"person_id": "alex"})))
    assert "oat milk" in json.dumps(session.bodies[0]["messages"][0])


def test_build_brain_switches_it_on_from_robot_toml(tmp_path):
    from maipai_body.config import RobotConfig, build_brain

    cfg = RobotConfig.model_validate(
        {"packages": {"memory_notes": {"enabled": True, "people": ["alex"], "default_person": "alex", "folder": str(tmp_path)}}}
    )
    assert build_brain(cfg).memory.people == ["alex"]
