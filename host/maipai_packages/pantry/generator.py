"""Generate (docs/design/content-pantry.md, section 6): ask the owner's model for batches of 20 records as JSON, then filter, dedupe and add them to the library.

Runs only when the host is idle and the model is reachable (the caller decides), never during a turn, and within a daily cap of model calls set by the owner.
A topic mix keeps a batch from repeating one theme. Every record is checked before it is kept: a model that goes away mid-run stops the run and keeps nothing unchecked."""

from __future__ import annotations

import json
import re

from maipai_packages.pantry.dedupe import dedupe
from maipai_packages.pantry.filter import Ask, ModelDown, filter_records
from maipai_packages.pantry.library import Library
from maipai_packages.pantry.record import TEXT_CAPS, Record

BATCH = 20
TOPICS = ("animals", "food", "space", "school", "nature", "music", "sports")
LANGUAGE_NAMES = {"en": "English", "es": "Spanish", "fr": "French", "de": "German", "pt": "Portuguese", "it": "Italian"}
SHAPE = {
    "joke": 'each object: {"text": "setup|punchline"} (one | between setup and punchline)',
    "riddle": 'each object: {"text": "the riddle question", "answer": "one short answer"}',
    "trivia": 'each object: {"text": "a question with one clear answer", "answer": "the right answer", "extra": "wrong one|another wrong one"}',
    "story": 'each object: {"text": "paragraph one|paragraph two|paragraph three"} (a short bedtime story, calm ending)',
}


def prompt_for(kind: str, language: str, rating: str, topic: str, n: int = BATCH) -> str:
    if kind not in SHAPE:
        raise ValueError(f"The host does not write {kind} records with the model. They ship in the built-in set.")
    return (
        f"Write {n} {kind}s for a family robot, in {LANGUAGE_NAMES.get(language, language)}, suitable for {'children' if rating == 'kid' else 'adults'}, about {topic}. "
        f"Reply with only a JSON array; {SHAPE[kind]}. Keep each text under {TEXT_CAPS[kind]} bytes and each answer under 40 bytes. No numbering, no commentary."
    )


def parse(reply: str, kind: str, language: str, rating: str) -> list[Record]:
    """The records in a model reply. Anything that is not a clean JSON array of objects gives nothing (the batch is lost, not guessed at)."""
    match = re.search(r"\[.*\]", reply, re.S)
    if not match:
        return []
    try:
        items = json.loads(match.group(0))
    except ValueError:
        return []
    out = []
    for item in items if isinstance(items, list) else []:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            out.append(Record(kind, language, rating, item["text"], str(item.get("answer", "") or ""), str(item.get("extra", "") or "")))
    return out


def generate(library: Library, ask: Ask, kind: str, language: str, *, rating: str = "kid", batches: int = 1, daily_cap: int = 200, adult_allowed: bool = False, seed: int = 0) -> dict:
    """Run up to ``batches`` batches. Returns {"added", "dropped": {reason: n}, "model_calls", "stopped"} and saves it as the library's last report."""
    summary = {"kind": kind, "language": language, "added": 0, "dropped": {}, "model_calls": 0, "stopped": ""}
    if kind not in SHAPE:
        summary["stopped"] = f"The model does not write {kind} records. They come with the built-in set."
        return summary
    for index in range(batches):
        topic = TOPICS[(seed + index) % len(TOPICS)]
        # one call for the batch plus about one per record for the filter: the daily cap counts them all
        if library.calls_today() + 1 + BATCH > daily_cap:
            summary["stopped"] = "the daily cap of model calls is reached"
            break
        calls = {"n": 0}

        def counted(prompt: str, _calls=calls) -> str:
            _calls["n"] += 1
            return ask(prompt)

        try:
            reply = counted(prompt_for(kind, language, rating, topic))
            candidates = parse(reply, kind, language, rating)
            kept, filtered = filter_records(candidates, counted, adult_allowed=adult_allowed)
        except ModelDown as down:
            summary["stopped"] = str(down)
            library.note_calls(calls["n"])
            summary["model_calls"] += calls["n"]
            break
        except Exception as error:  # the first call of the batch failed
            summary["stopped"] = f"The model did not answer ({type(error).__name__}). Try again later."
            library.note_calls(calls["n"])
            summary["model_calls"] += calls["n"]
            break
        known = library.records(kind, language)
        fresh, deduped = dedupe(kept, known, library.refused_ids())
        library.add(fresh)
        library.note_calls(calls["n"])
        summary["model_calls"] += calls["n"]
        summary["added"] += len(fresh)
        for reasons in (filtered.dropped, deduped.dropped):
            for why, count in reasons.items():
                summary["dropped"][why] = summary["dropped"].get(why, 0) + count
        if not candidates:
            summary["dropped"]["unreadable reply"] = summary["dropped"].get("unreadable reply", 0) + 1
    library.save_report(summary)
    return summary
