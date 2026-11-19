# ruff: noqa: E501
"""Twenty questions with no model (docs/design/twenty-questions-library.md): the person thinks of an animal or a thing, the robot asks up to 12 fixed yes or no
questions and narrows the library's ``object`` records, then guesses. No model, no generated text: every line is fixed and comes from this table."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

from maipai_packages.pantry.record import Record, normalize

QUESTIONS = {
    "en": ["Is it alive?", "Does it live in water?", "Can it fly?", "Does it have four legs?", "Does it have fur or feathers?", "Do people eat it?", "Is it found in a house?",
           "Is it made of metal or plastic?", "Is it bigger than a chair?", "Does it make a sound?", "Is it a toy, or used to play?", "Do you wear it or carry it?"],
    "es": ["¿Está vivo?", "¿Vive en el agua?", "¿Puede volar?", "¿Tiene cuatro patas?", "¿Tiene pelo o plumas?", "¿La gente se lo come?", "¿Se encuentra en una casa?",
           "¿Es de metal o de plástico?", "¿Es más grande que una silla?", "¿Hace algún sonido?", "¿Es un juguete, o sirve para jugar?", "¿Te lo pones o lo llevas contigo?"],
    "fr": ["Est-ce vivant ?", "Est-ce que ça vit dans l'eau ?", "Est-ce que ça peut voler ?", "Est-ce que ça a quatre pattes ?", "Est-ce que ça a des poils ou des plumes ?", "Est-ce que les gens le mangent ?",
           "Est-ce qu'on en trouve dans une maison ?", "Est-ce en métal ou en plastique ?", "Est-ce plus grand qu'une chaise ?", "Est-ce que ça fait un bruit ?", "Est-ce un jouet, ou pour jouer ?", "Est-ce qu'on le porte ou l'emporte ?"],
    "de": ["Lebt es?", "Lebt es im Wasser?", "Kann es fliegen?", "Hat es vier Beine?", "Hat es Fell oder Federn?", "Essen Menschen es?", "Gibt es das in einem Haus?",
           "Ist es aus Metall oder Plastik?", "Ist es größer als ein Stuhl?", "Macht es ein Geräusch?", "Ist es ein Spielzeug, oder spielt man damit?", "Trägt man es am Körper oder bei sich?"],
    "pt": ["Está vivo?", "Vive na água?", "Pode voar?", "Tem quatro patas?", "Tem pelo ou penas?", "As pessoas comem isso?", "Encontra-se numa casa?",
           "É de metal ou de plástico?", "É maior que uma cadeira?", "Faz algum som?", "É um brinquedo, ou serve para brincar?", "Veste-se ou leva-se consigo?"],
    "it": ["È vivo?", "Vive nell'acqua?", "Può volare?", "Ha quattro zampe?", "Ha il pelo o le piume?", "Le persone lo mangiano?", "Si trova in una casa?",
           "È di metallo o di plastica?", "È più grande di una sedia?", "Fa un suono?", "È un giocattolo, o serve per giocare?", "Lo si indossa o lo si porta con sé?"],
}
LINES = {
    "en": {"none": "I do not have enough things to guess from, so we will stop here.", "say": "Please say yes, no, or I do not know.", "guess": "Is it {name}?",
           "win": "I got it. That was fun.", "second": "Hmm. Then is it {name}?", "giveup": "I give up. What was it?"},
    "es": {"none": "No tengo suficientes cosas para adivinar, así que paramos aquí.", "say": "Por favor di sí, no, o no sé.", "guess": "¿Es {name}?",
           "win": "Lo adiviné. Fue divertido.", "second": "Mmm. Entonces, ¿es {name}?", "giveup": "Me rindo. ¿Qué era?"},
    "fr": {"none": "Je n'ai pas assez de choses pour deviner, alors on s'arrête là.", "say": "Dis oui, non, ou je ne sais pas.", "guess": "Est-ce {name} ?",
           "win": "J'ai trouvé. C'était amusant.", "second": "Hmm. Alors, est-ce {name} ?", "giveup": "Je donne ma langue au chat. C'était quoi ?"},
    "de": {"none": "Ich kenne nicht genug Dinge zum Raten, also hören wir hier auf.", "say": "Bitte sag ja, nein oder ich weiß nicht.", "guess": "Ist es {name}?",
           "win": "Ich hab es. Das hat Spaß gemacht.", "second": "Hmm. Dann ist es {name}?", "giveup": "Ich gebe auf. Was war es?"},
    "pt": {"none": "Não tenho coisas suficientes para adivinhar, então vamos parar aqui.", "say": "Por favor diz sim, não, ou não sei.", "guess": "É {name}?",
           "win": "Acertei. Foi divertido.", "second": "Hmm. Então é {name}?", "giveup": "Desisto. O que era?"},
    "it": {"none": "Non ho abbastanza cose per indovinare, quindi ci fermiamo qui.", "say": "Per favore dì sì, no, o non lo so.", "guess": "È {name}?",
           "win": "Ho indovinato. È stato divertente.", "second": "Hmm. Allora è {name}?", "giveup": "Mi arrendo. Cos'era?"},
}
YES = {"yes", "yeah", "yep", "yup", "sure", "correct", "right", "si", "claro", "oui", "ja", "sim", "certo", "exacto", "exacte"}
NO = {"no", "nope", "nah", "non", "nein", "nao", "never"}
UNKNOWN = {"maybe", "unsure", "dunno", "idk", "perhaps", "quizas", "peutetre", "vielleicht", "talvez", "forse"}
UNKNOWN_PHRASES = ("not sure", "dont know", "do not know", "no se", "je ne sais pas", "ich weiss nicht", "nao sei", "non lo so", "no idea")
MIN_OBJECTS = 10
MAX_QUESTIONS = 12
TOLERANCE = 1  # one answer that disagrees is forgiven: people answer the same question differently


def read_answer(heard: str) -> str:
    """``yes``, ``no``, ``unknown`` or ``""`` (not an answer). Accents are folded, so "sí" and "si" are the same."""
    said = normalize(heard)
    if any(phrase in said for phrase in UNKNOWN_PHRASES):
        return "unknown"
    words = set(said.split())
    if words & UNKNOWN:
        return "unknown"
    yes, no = bool(words & YES), bool(words & NO)
    if yes and not no:
        return "yes"
    if no and not yes:
        return "no"
    return ""


@dataclass
class _Game:
    objects: list[Record]
    game_started: float
    answers: dict[int, bool] = field(default_factory=dict)
    skipped: set[int] = field(default_factory=set)  # asked, and the person did not know
    asked: int | None = None  # the question waiting for an answer
    guessed: list[bytes] = field(default_factory=list)
    stage: str = "asking"  # asking, guessing
    done: bool = False


def _mismatches(record: Record, answers: dict[int, bool]) -> int:
    return sum(1 for q, yes in answers.items() if (record.extra[q] == "1") != yes)


class TwentyQuestions:
    """One unit's games, played from the library's ``object`` records."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()

    def new(self, objects: list[Record], game_started: float) -> _Game | None:
        return _Game(objects, game_started) if len(objects) >= MIN_OBJECTS else None

    def _alive(self, game: _Game) -> list[Record]:
        return [r for r in game.objects if _mismatches(r, game.answers) <= TOLERANCE]

    def _next_question(self, game: _Game, candidates: list[Record]) -> int | None:
        left = [q for q in range(12) if q not in game.answers and q not in game.skipped]
        if not left:
            return None

        def balance(q: int) -> float:
            return abs(sum(1 for r in candidates if r.extra[q] == "1") / max(1, len(candidates)) - 0.5)

        return min(left, key=lambda q: (balance(q), q))

    def _best(self, game: _Game, candidates: list[Record]) -> Record | None:
        pool = [r for r in candidates if r.id not in game.guessed]
        if not pool:
            return None
        best = min(_mismatches(r, game.answers) for r in pool)
        return self._rng.choice([r for r in pool if _mismatches(r, game.answers) == best])

    def turn(self, game: _Game, lang: str, heard: str) -> str:
        words = LINES.get(lang, LINES["en"])
        questions = QUESTIONS.get(lang, QUESTIONS["en"])
        if game.stage == "guessing":
            answer = read_answer(heard)
            if answer == "yes":
                game.done = True
                return words["win"]
            if answer == "":
                return words["say"]
            return self._guess(game, lang, second=True)
        if game.asked is not None:
            answer = read_answer(heard)
            if answer == "":
                return words["say"]
            if answer == "unknown":
                game.skipped.add(game.asked)
            else:
                game.answers[game.asked] = answer == "yes"
        candidates = self._alive(game)
        nxt = None if len(candidates) <= 1 or len(game.answers) >= MAX_QUESTIONS else self._next_question(game, candidates)
        if nxt is None:
            return self._guess(game, lang)
        game.asked = nxt
        return questions[nxt]

    def _guess(self, game: _Game, lang: str, second: bool = False) -> str:
        words = LINES.get(lang, LINES["en"])
        record = self._best(game, self._alive(game) or game.objects)
        if record is None or (second and len(game.guessed) >= 2):
            game.done = True
            return words["giveup"]
        game.guessed.append(record.id)
        game.stage = "guessing"
        return words["second" if second else "guess"].format(name=record.text)
