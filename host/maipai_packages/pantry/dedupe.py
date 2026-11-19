"""Dedupe (docs/design/content-pantry.md, section 6): the same line twice, or the same idea in other words, is kept once.

Order: exact id, then near duplicates inside a kind and language by token-set similarity of 0.7 or more, and for riddles and trivia the same answer with a
similar question. The report says how many were dropped and why, for the dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field

from maipai_packages.pantry.record import Record, normalize

SIMILAR = 0.7
SAME_ANSWER_SIMILAR = 0.5  # a riddle or trivia with the same answer needs less in common to be the same question


def tokens(text: str) -> frozenset[str]:
    return frozenset(t for t in normalize(text).split() if len(t) > 1)


def similarity(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass
class Report:
    kept: int = 0
    dropped: dict[str, int] = field(default_factory=dict)

    def drop(self, why: str) -> None:
        self.dropped[why] = self.dropped.get(why, 0) + 1


def dedupe(candidates: list[Record], known: list[Record], refused_ids: set[bytes] = frozenset()) -> tuple[list[Record], Report]:
    """The candidates that are new against what is known (the library, the shelf, the heard history) and against each other."""
    report = Report()
    seen_ids = {r.id for r in known} | set(refused_ids)
    pool = [(r, tokens(r.text), normalize(r.answer)) for r in known]
    out: list[Record] = []
    for record in candidates:
        if record.id in refused_ids:
            report.drop("refused before")
            continue
        if record.id in seen_ids:
            report.drop("exact duplicate")
            continue
        toks, answer = tokens(record.text), normalize(record.answer)
        twin = False
        for other, other_toks, other_answer in pool:
            if other.kind != record.kind or other.language != record.language:
                continue
            score = similarity(toks, other_toks)
            if score >= SIMILAR or (answer and answer == other_answer and score >= SAME_ANSWER_SIMILAR):
                twin = True
                break
        if twin:
            report.drop("near duplicate")
            continue
        out.append(record)
        seen_ids.add(record.id)
        pool.append((record, toks, answer))
        report.kept += 1
    return out, report
