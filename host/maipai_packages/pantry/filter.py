"""Filter (docs/design/content-pantry.md, section 6): what the host is willing to store and tell later. Cheapest check first; anything not a clear pass is dropped, never edited.

This curates content the host keeps. It is not a chat filter and changes nothing about the own-LLM brain, which adds none (decision 13).
The model is a plain function ``ask(prompt) -> text`` so tests use a fake and the host passes the owner's own model."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from maipai_packages.pantry.record import Record, RecordError, check, normalize

Ask = Callable[[str], str]

# Words a kid shelf never holds, per language (a first, cheap pass; the model pass follows). Whole words after normalizing.
KID_BLOCK = {
    "en": "kill killed murder dead death die dying blood gun shoot shot sex sexy naked drunk beer wine vodka whiskey drug drugs weed cocaine stupid idiot hate suicide ghost demon",
    "es": "matar matado asesinato muerto muerte morir sangre pistola disparo sexo desnudo borracho cerveza vino vodka droga drogas estupido idiota odio suicidio fantasma demonio",
    "fr": "tuer tue meurtre mort mourir sang pistolet sexe nu ivre biere vin vodka drogue stupide idiot haine suicide fantome demon",
    "de": "toten getotet mord tot tod sterben blut pistole sex nackt betrunken bier wein wodka droge dumm idiot hass selbstmord geist damon",
    "pt": "matar morto assassinato morte morrer sangue arma tiro sexo nu bebado cerveja vinho vodka droga estupido idiota odio suicidio fantasma demonio",
    "it": "uccidere ucciso omicidio morto morte morire sangue pistola sparo sesso nudo ubriaco birra vino vodka droga stupido idiota odio suicidio fantasma demone",
}
FRESH_WORDS = re.compile(r"\b(latest|current|currently|today|tonight|this year|last year|recent|recently|now|newest|2024|2025|2026)\b", re.I)
LATIN = re.compile(r"[A-Za-zÀ-ſ]")


class ModelDown(RuntimeError):
    """The model could not be asked. Nothing unchecked is kept; the run stops and tries again later."""


@dataclass
class Report:
    kept: int = 0
    dropped: dict[str, int] = field(default_factory=dict)

    def drop(self, why: str) -> None:
        self.dropped[why] = self.dropped.get(why, 0) + 1


def _words(record: Record) -> set[str]:
    return set(normalize(" ".join((record.text, record.answer, record.extra))).split())


def _yes(reply: str) -> bool:
    return normalize(reply).split()[:1] in (["yes"], ["si"], ["oui"], ["ja"], ["sim"], ["s"])


def _ask(ask: Ask, prompt: str) -> str:
    try:
        return ask(prompt)
    except Exception as error:
        raise ModelDown(f"The model did not answer ({type(error).__name__}). The filter stops; unchecked records are not kept.") from error


def _language_ok(record: Record) -> bool:
    letters = len(LATIN.findall(record.text))
    return letters >= 0.8 * max(1, len(re.sub(r"[\s\d\W]", "", record.text)))  # the shelf languages all use the Latin alphabet


def filter_records(candidates: list[Record], ask: Ask, *, adult_allowed: bool = False) -> tuple[list[Record], Report]:
    """Records that pass shape, rating, facts and riddle checks, with a report of what was dropped and why."""
    report, kept = Report(), []
    for original in candidates:
        try:
            record = check(original)
        except RecordError:
            report.drop("shape")
            continue
        if not _language_ok(record):
            report.drop("wrong language")
            continue
        if record.rating == "adult" and not adult_allowed:
            report.drop("adult not allowed")
            continue
        if record.rating == "kid":
            if _words(record) & set(KID_BLOCK.get(record.language, KID_BLOCK["en"]).split()):
                report.drop("not for kids (word list)")
                continue
            if not _yes(_ask(ask, f"Is this suitable for a six year old? Answer only yes or no.\n\n{record.text}\n{record.answer}")):
                report.drop("not for kids (model)")
                continue
        if record.kind == "trivia":
            if FRESH_WORDS.search(record.text):
                report.drop("time-bound fact")
                continue
            got = normalize(_ask(ask, f"Answer in a few words, no explanation:\n{record.text}"))
            want = normalize(record.answer)
            if not want or (want not in got and got not in want):
                report.drop("fact not confirmed")
                continue
        if record.kind == "riddle":
            second = normalize(_ask(ask, f"Riddle: {record.text}\nThe intended answer is: {record.answer}\nIs there a different, equally good answer? Reply with it, or reply none."))
            if second and second.split()[:1] != ["none"] and normalize(record.answer) not in second:
                report.drop("riddle has two answers")
                continue
        kept.append(record)
        report.kept += 1
    return kept, report
