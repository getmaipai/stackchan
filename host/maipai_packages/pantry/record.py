"""The pantry record (docs/design/content-pantry.md, section 2): one thing the robot can say, with the rules that keep it small and stable.

The id is the first 8 bytes of SHA-256 over kind, language, normalized text and answer, so the same joke has the same id on every host and a deleted
record stays deleted. Length caps keep one record on the unit's screen and inside the shelf budget."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import asdict, dataclass

KINDS = ("joke", "riddle", "trivia", "story", "object", "line")  # object: a twenty questions object (docs/design/twenty-questions-library.md); kind byte 4 on a shelf
RATINGS = ("kid", "adult")
# The situations a canned offline line answers (docs/design/content-pantry.md, "Lines by situation"). A `line` record's extra is one of these tags.
SITUATIONS = (
    "greeting_morning", "greeting_day", "greeting_evening", "goodnight", "touch_head", "touch_face", "pick_up", "put_down", "shaken", "loud_noise",
    "wake_heard_offline", "cannot_reach_home", "back_online", "timer_done", "battery_low", "thanks", "bored", "sleepy", "happy", "curious",
)
TEXT_CAPS = {"joke": 160, "riddle": 140, "trivia": 140, "story": 1600, "object": 24, "line": 100}  # bytes of UTF-8
ANSWER_CAP = 40
EXTRA_CAP = 80  # two wrong answers split by "|"
_PUNCT = re.compile(r"[^\w\s|]", re.UNICODE)
_SPACE = re.compile(r"\s+")


class RecordError(ValueError):
    """A record that cannot be kept. The message says what is wrong in plain words (it goes to the dedupe and filter reports)."""


def normalize(text: str) -> str:
    """Lowercase, fold accents, drop punctuation, collapse space: what two spellings of the same line have in common."""
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    return _SPACE.sub(" ", _PUNCT.sub(" ", folded)).strip()


@dataclass(frozen=True)
class Record:
    kind: str
    language: str
    rating: str
    text: str
    answer: str = ""
    extra: str = ""

    @property
    def id(self) -> bytes:
        digest = hashlib.sha256("\x1f".join((self.kind, self.language, normalize(self.text), normalize(self.answer))).encode("utf-8")).digest()
        return digest[:8]

    @property
    def id_hex(self) -> str:
        return self.id.hex()

    def to_json(self) -> dict:
        return {"id": self.id_hex, **asdict(self)}

    @staticmethod
    def from_json(data: dict) -> Record:
        return Record(str(data["kind"]), str(data["language"]), str(data["rating"]), str(data["text"]), str(data.get("answer", "")), str(data.get("extra", "")))


def check(record: Record) -> Record:
    """The shape rules: kind, rating, caps, no control characters, the fields each kind needs. Returns the record or raises RecordError."""
    if record.kind not in KINDS:
        raise RecordError(f"The kind {record.kind!r} is not one of {', '.join(KINDS)}.")
    if record.rating not in RATINGS:
        raise RecordError(f"The rating {record.rating!r} is not kid or adult.")
    if not re.fullmatch(r"[a-z]{2}", record.language):
        raise RecordError("The language must be a two letter code such as en or es.")
    for name, value in (("text", record.text), ("answer", record.answer), ("extra", record.extra)):
        if any(ord(ch) < 32 and ch not in "\n" for ch in value):
            raise RecordError(f"The {name} has a control character.")
    text = record.text.strip()
    if not text:
        raise RecordError("The text is empty.")
    if len(text.encode("utf-8")) > TEXT_CAPS[record.kind]:
        raise RecordError(f"The {record.kind} text is over {TEXT_CAPS[record.kind]} bytes.")
    if len(record.answer.encode("utf-8")) > ANSWER_CAP:
        raise RecordError(f"The answer is over {ANSWER_CAP} bytes.")
    if len(record.extra.encode("utf-8")) > EXTRA_CAP:
        raise RecordError(f"The wrong answers are over {EXTRA_CAP} bytes.")
    if record.kind == "joke" and text.count("|") != 1:
        raise RecordError("A joke is a setup and a punchline split by one |.")
    if record.kind in ("riddle", "trivia") and not record.answer.strip():
        raise RecordError(f"A {record.kind} needs an answer.")
    if record.kind == "trivia" and record.extra.count("|") != 1:
        raise RecordError("A trivia question needs two wrong answers split by one |.")
    if record.kind == "object":
        if record.answer.strip() not in ("animal", "thing"):
            raise RecordError("An object's answer is its group, animal or thing.")
        if not re.fullmatch(r"[01]{12}", record.extra.strip()):
            raise RecordError("An object's extra is the 12 answers to the 12 questions, each 0 or 1.")
    if record.kind == "line":
        if record.extra.strip() not in SITUATIONS:
            raise RecordError(f"A line's extra is its situation, one of {', '.join(SITUATIONS)}.")
        if record.answer:
            raise RecordError("A line has no answer.")
        if record.rating != "kid":
            raise RecordError("Every line is rated kid.")
    if record.kind in ("joke", "story") and (record.answer or record.extra):
        raise RecordError(f"A {record.kind} has no answer.")
    return Record(record.kind, record.language, record.rating, text, record.answer.strip(), record.extra.strip())
