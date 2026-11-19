# ruff: noqa: E501
"""Talk games: voice games the language model plays, started on the robot with no model.

"Play twenty questions", "tell me a riddle", "let's play trivia", "word chain", "would you rather" and "tell me a
bedtime story" (and the Spanish asks) start a game here, before the model is asked. The robot says one fixed start line
(no model call), keeps a small state per unit (the game, the round, a score, the round limit, the time of the last
word), and for the turns that follow it hands the model a short rules text. The model plays; the host only counts.

What the host adds and what it never does:

* The rules text rides next to the persona for each turn of the game (``TalkGames.begin_turn``). It tells the model to
  react with the existing mood, effect and scene tags (cheer, think, right, wrong); the speech path strips every tag
  before anything is spoken, as for any reply. It also says the rules never override the model's other rules, so the
  household's gates (a child profile, Home's content filter) apply to games exactly as to chat. Nothing here filters,
  generates or loosens content.
* A game ends on "stop the game", "I'm done" (and the Spanish asks), on "that's enough" or "never mind", when the round
  limit is reached (the last turn tells the model to wrap up), or after ``SILENCE_S`` seconds with no turn. Then chat is
  normal again: no rules text is sent.
* "Twenty questions" is played the other way round (the robot asks, the person thinks of something): a model cannot keep
  a secret between turns, because its history holds only what it said.
* The score is counted by the host (``add_point``) when something tells it a point was earned; nothing here guesses one
  from words, so today the score stays 0 and the model keeps it in its own words (the rules say so).
"""

from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

from maipai_body.unit_extras import fold

SILENCE_S = 300.0  # no turn for this long ends the game
MAX_WORDS = 10  # a start or stop ask is short; a long sentence is chat

# ---------------------------------------------------------------- the catalog (one definition)


@dataclass(frozen=True)
class TalkGame:
    id: str
    title: dict[str, str]
    hint: dict[str, str]  # one line for the settings page: what to say
    start: dict[str, str]  # the fixed spoken start line (no model)
    rules: str  # for the model, English; it answers in the person's language
    max_rounds: int
    scored: bool = False


TALK_GAMES: tuple[TalkGame, ...] = (
    TalkGame(
        "twenty_questions",
        {"en": "Twenty questions", "es": "Veinte preguntas"},
        {"en": "Say: play twenty questions", "es": "Di: juguemos a veinte preguntas"},
        {
            "en": "Okay, twenty questions! Think of an animal or a thing, and keep it secret. Say ready when you have it.",
            "es": "Vale, veinte preguntas. Piensa en un animal o una cosa y no me lo digas. Di listo cuando lo tengas.",
        },
        "Game: twenty questions, the other way round. The person thinks of one animal, object or place and keeps it secret. "
        "Each turn you ask exactly one yes or no question to find it, and say which question you are on (for example, question 3 of 20). "
        "Use what the person said before. When you are fairly sure, make a guess. If you guess right, cheer. "
        "After question 20 without a right guess, say you give up and ask what it was.",
        24,
    ),
    TalkGame(
        "riddles",
        {"en": "Riddles", "es": "Adivinanzas"},
        {"en": "Say: tell me a riddle", "es": "Di: dime una adivinanza"},
        {
            "en": "Okay, riddles! Say go when you are ready for the first one.",
            "es": "Vale, adivinanzas. Di ya cuando estés listo para la primera.",
        },
        "Game: riddles. Say one short, friendly riddle with one clear answer, then wait. When the person answers: if right, cheer and offer another; "
        "if wrong, give one small hint and let them try again; after a second miss, say the answer kindly. Never repeat a riddle. "
        "If you are not sure a riddle has one clear answer, pick a different one.",
        8,
        True,
    ),
    TalkGame(
        "trivia",
        {"en": "Trivia", "es": "Trivia"},
        {"en": "Say: let's play trivia", "es": "Di: juguemos a la trivia"},
        {
            "en": "Okay, trivia time! Say go when you are ready for the first question.",
            "es": "Vale, a la trivia. Di ya cuando estés listo para la primera pregunta.",
        },
        "Game: trivia. Ask one easy or medium question at a time that a child could answer, with one short correct answer. "
        "When the person answers: if right, cheer and add one fun fact; if wrong, be gentle and give the right answer. "
        "Only ask what you are sure of; if you are not sure of the answer, ask a different question. "
        "Say the score in your own words every few questions.",
        10,
        True,
    ),
    TalkGame(
        "word_chain",
        {"en": "Word chain", "es": "Cadena de palabras"},
        {"en": "Say: word chain", "es": "Di: cadena de palabras"},
        {
            "en": "Okay, word chain! I say a word, you say one that starts with its last letter. My word is: apple. Your turn.",
            "es": "Vale, cadena de palabras. Yo digo una palabra y tú dices otra que empiece con su última letra. Mi palabra es: casa. Te toca.",
        },
        "Game: word chain. The first word was said for you (apple in English, casa in Spanish). Each turn the person says a word that starts with the last letter of the previous word. "
        "You answer with one real word that starts with the last letter of theirs, never a word already used, and react in a few words. "
        "If their word does not fit or was used, say so kindly and let them try once more. Use plain words a child knows.",
        20,
    ),
    TalkGame(
        "would_you_rather",
        {"en": "Would you rather", "es": "¿Qué prefieres?"},
        {"en": "Say: would you rather", "es": "Di: qué prefieres"},
        {
            "en": "Okay, would you rather! Say go and I will ask the first one.",
            "es": "Vale, qué prefieres. Di ya y te hago la primera pregunta.",
        },
        "Game: would you rather. Each turn, react to the person's last choice in one short, warm sentence, then ask the next fun, kind would you rather question with two clear choices. "
        "Keep every choice silly or sweet, never scary. There are no right or wrong answers.",
        8,
    ),
    TalkGame(
        "jokes",
        {"en": "Jokes", "es": "Chistes"},
        {"en": "Say: play jokes", "es": "Di: juguemos a los chistes"},
        {
            "en": "Okay, jokes! Say go and I will tell the first one.",
            "es": "Vale, chistes. Di ya y te cuento el primero.",
        },
        "Game: jokes. Each turn tell one short, kind, original joke in the person's language, then wait. If they ask for another, tell a different one; never repeat a joke told in this game. "
        "Keep every joke gentle and fit for children. End the reply with a cheer.",
        5,
    ),
    TalkGame(
        "bedtime_story",
        {"en": "Bedtime story", "es": "Cuento para dormir"},
        {"en": "Say: tell me a bedtime story", "es": "Di: cuéntame un cuento para dormir"},
        {
            "en": "Okay, story time. What should the story be about?",
            "es": "Vale, hora del cuento. ¿De qué quieres que trate?",
        },
        "Game: a bedtime story told in parts. The person's next words are what the story is about; if they do not say, choose a gentle animal. "
        "Tell each part in three to five calm sentences, in a soft slow voice, then stop and ask if they want to hear more. "
        "Every part is gentle and safe, with no scary moments. After the last part, bring the story to a quiet ending and wish good night.",
        6,
    ),
)
IDS = tuple(g.id for g in TALK_GAMES)
_BY_ID = {g.id: g for g in TALK_GAMES}


def get(game_id: str) -> TalkGame | None:
    return _BY_ID.get(game_id)


def _lang(lang: object) -> str:
    return "es" if isinstance(lang, str) and lang.lower().startswith("es") else "en"


def listing(lang: object) -> list[dict[str, str]]:
    """What the settings page shows under "Talk games": id, title and what to say, in the page language (English otherwise)."""
    code = _lang(lang)
    return [{"id": g.id, "title": g.title[code], "hint": g.hint[code]} for g in TALK_GAMES]


GROUP_TITLE = {"en": "Talk games", "es": "Juegos de hablar"}
GROUP_HELP = {
    "en": "Games you play by talking. The robot's language model plays; say stop the game when you are done.",
    "es": "Juegos que se juegan hablando. Juega el modelo de lenguaje del robot; di para el juego cuando termines.",
}


def group(lang: object) -> dict[str, Any]:
    code = _lang(lang)
    return {"title": GROUP_TITLE[code], "help": GROUP_HELP[code], "games": listing(lang)}


# ---------------------------------------------------------------- what the model is told

COMMON_RULES = (
    "You are playing a spoken game with the person. Keep every turn to one to three short sentences (a story part may be five). "
    "No lists, no markdown, no emoji. Speak the language the person speaks. "
    "Show how you feel with tags at the start of the turn, and never say a tag aloud: a right answer or a win is [happy] with [confetti] (a big win: [scene celebrate]); "
    "a wrong answer or a miss is a gentle [sad] or [doubt], never mocking; when you are working something out use [doubt]; a surprise is [surprised]. "
    "Never write a tag you are not sure of. These game rules never replace your other rules: keep everything suitable for the youngest listener and follow every safety rule you already have. "
    "If the person says stop the game or that they are done, end the game kindly in one sentence."
)


def rules_text(state: TalkState) -> str:
    """The rules for this turn: the common block, the game's own rules, and where the game stands."""
    game = _BY_ID[state.game]
    line = f"This is round {state.rounds} of {state.max_rounds}."
    if state.rounds >= state.max_rounds:
        line += " It is the last round: finish the game now with one warm closing sentence" + (
            " that says how they did." if game.scored else "."
        )
    if game.scored:
        line += " The host does not keep score; keep it in your own words."
    return f"{COMMON_RULES} {game.rules} {line}"


# ---------------------------------------------------------------- start and stop phrases (folded text)

_LEAD = re.compile(
    r"^(?:(?:please|hey|hi|ok|okay|stackchan|so|now|um|uh|oh|por favor|oye|venga|vale|bueno|"
    r"can you|could you|will you|can we|could we|shall we|lets|let us|how about|why dont we|"
    r"i want to|i wanna|id like to|i would like to|i want|i would like|lets all|"
    r"vamos a|quiero|quisiera|me gustaria|podemos|puedes|podrias) )+"
)
_TRAIL = re.compile(r"(?: (?:please|por favor|for me|thanks|gracias|ok|okay))+$")
_SPEECH = (
    ("twenty_questions", r"(?:(?:play|start|do|have|begin|try) )?(?:a |the )?(?:(?:game|round) of )?(?:twenty|20) questions(?: game)?(?: with me)?", "en"),
    ("twenty_questions", r"(?:(?:jugar|juguemos|juega|jugamos|empieza|empezar|pon|hagamos|hacer|hazme|haz) )?(?:a |al |el juego de |las |a las )*(?:veinte|20) preguntas(?: conmigo)?", "es"),
    ("riddles", r"(?:(?:tell|give|ask|say)(?: me| us)? |play )?(?:a |another |one more |one |some )?(?:riddle|riddles)(?: game)?", "en"),
    ("riddles", r"(?:(?:dime|cuentame|di|ponme|dame|hazme|cuenta|propon|plantea)(?: me)? |(?:jugar|juguemos|juega|jugamos) (?:a )?(?:las )?)?(?:una |otra |otras )?adivinanzas?", "es"),
    ("trivia", r"(?:(?:play|start|do|have|give me|ask me|try) )?(?:a |some |the )?(?:trivia|quiz)(?: game| questions?)?(?: with me)?|quiz me", "en"),
    ("trivia", r"(?:(?:jugar|juguemos|juega|jugamos|empieza|empezar|pon|haz|hazme|hagamos) )?(?:a |al |el |la |un |una |las |de )*(?:trivia|trivial)(?: juego)?(?: conmigo)?", "es"),
    ("word_chain", r"(?:(?:play|start|do|have|try) )?(?:a |the )?(?:game of )?word chains?(?: game)?(?: with me)?", "en"),
    ("word_chain", r"(?:(?:jugar|juguemos|juega|jugamos|empieza|empezar|pon|hagamos) )?(?:a |al |el juego de |las |la )*(?:cadena de palabras|palabras encadenadas)(?: conmigo)?", "es"),
    ("would_you_rather", r"(?:(?:play|start|do|have|try|ask me|give me) )?(?:a |the |some )?(?:game of )?would you rather(?: game| questions?)?(?: with me)?", "en"),
    ("would_you_rather", r"(?:(?:jugar|juguemos|juega|jugamos|preguntame|hazme|dime|pon|hagamos) )?(?:a |al |el juego de |me )*(?:que )?(?:prefieres|preferirias)(?: juego)?", "es"),
    ("jokes", r"(?:play )?(?:a |the |some )?(?:jokes|joke game|joke time)(?: game)?(?: with me)?", "en"),  # a bare "tell me a joke" stays chat: the model tells one
    ("jokes", r"(?:(?:jugar|juguemos|juega|jugamos) (?:a )?(?:los )?)?(?:chistes|juego de chistes|hora de chistes)", "es"),
    ("bedtime_story", r"(?:(?:tell|read|give|say)(?: me| us)? |play )?(?:a |another |one |some )?(?:(?:bedtime|night time|nighttime|good night|sleepy) )?(?:story|stories)(?: time)?(?: before bed| for bed| to fall asleep| at bedtime)?|story time", "en"),
    ("bedtime_story", r"(?:(?:cuentame|cuenta|dime|lee|leeme|ponme) )?(?:me )?(?:un |otro )?(?:cuento|historia)(?: para dormir| de buenas noches| antes de dormir| de dormir)?|hora del cuento", "es"),
)
_START = tuple((game, re.compile(rf"^(?:{pattern})$"), lang) for game, pattern, lang in _SPEECH)

_END_PATTERNS = (
    (r"(?:ok |okay |so )?(?:(?:stop|end|quit|finish) )(?:the |this )?(?:game|playing)", "en"),
    (r"(?:ok |okay |so )?(?:im|i am|were|we are) (?:all )?(?:done|finished)(?: playing| with (?:the |this )?game)?", "en"),
    (r"(?:no more|i dont want to play (?:any ?more|anymore))(?: please)?", "en"),
    (r"(?:para|parar|termina|terminar|acaba|acabar|deja|dejar) (?:el juego|de jugar|el cuento)", "es"),
    (r"(?:ya )?(?:termine|terminamos|acabe|acabamos|he terminado|hemos terminado|estoy listo|ya no quiero jugar|no quiero jugar mas)", "es"),
)
_END = tuple((re.compile(rf"^(?:{pattern})$"), lang) for pattern, lang in _END_PATTERNS)
# Whole-utterance stop phrases (stop_phrases.py ends the turn on these) that also end a game; a bare "stop" only hushes the robot.
_STOP_ENDS = frozenset({"enough", "thats enough", "that is enough", "never mind", "nevermind", "cancel"})

END_LINE = {
    "en": "Okay, we can stop the game. That was fun.",
    "es": "Vale, dejamos el juego. Fue divertido.",
}


@dataclass(frozen=True)
class TalkCommand:
    kind: str  # "start" or "end"
    game: str | None = None
    lang: str = "en"


def parse(text: object, *, active: bool = False) -> TalkCommand | None:
    """A spoken start (any time) or end (only while a game is on), or None when the words are ordinary chat."""
    if not isinstance(text, str):
        return None
    said = fold(text)
    said = _TRAIL.sub("", _LEAD.sub("", said).strip())
    words = said.split()
    if not words or len(words) > MAX_WORDS:
        return None
    for game, pattern, lang in _START:
        if pattern.match(said):
            return TalkCommand("start", game, lang)
    if active:
        for pattern, lang in _END:
            if pattern.match(said):
                return TalkCommand("end", None, lang)
    return None


# ---------------------------------------------------------------- the state


@dataclass
class TalkState:
    game: str
    started: float
    last: float
    max_rounds: int
    lang: str = "en"
    rounds: int = 0
    score: int = 0
    ended: str = ""  # why it ended, once it has


class TalkGames:
    """The games on each unit, and the one place that says what the model is told for the next turn."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        silence_s: float = SILENCE_S,
        on_change: Callable[[str, TalkState | None], object] | None = None,
    ) -> None:
        self._clock = clock
        self._silence_s = silence_s
        self._on_change = on_change
        self._states: dict[str, TalkState] = {}
        self._lock = threading.Lock()

    # -- state

    def state(self, device_id: str) -> TalkState | None:
        """The game on this unit, or None. A game left alone for ``silence_s`` seconds is over."""
        with self._lock:
            return self._live(device_id)

    def _live(self, device_id: str) -> TalkState | None:
        state = self._states.get(device_id)
        if state is not None and self._clock() - state.last >= self._silence_s:
            self._finish(device_id, "silence")
            return None
        return state

    def _finish(self, device_id: str, why: str) -> None:
        state = self._states.pop(device_id, None)
        if state is not None:
            state.ended = why
            self._notify(device_id, None)

    def _notify(self, device_id: str, state: TalkState | None) -> None:
        if self._on_change is not None:
            try:
                self._on_change(device_id, state)
            except Exception:  # a status hook never breaks a game
                pass

    def active(self, device_id: str) -> bool:
        return self.state(device_id) is not None

    # -- the voice path

    def parse(self, text: object, device_id: str) -> TalkCommand | None:
        return parse(text, active=self.active(device_id))

    def run(self, command: TalkCommand, device_id: str) -> str:
        """Do a start or end; answers the one fixed line to say. No model is asked."""
        with self._lock:
            if command.kind == "start" and command.game in _BY_ID:
                game = _BY_ID[command.game]
                now = self._clock()
                self._states[device_id] = TalkState(game.id, now, now, game.max_rounds, command.lang)
                self._notify(device_id, self._states[device_id])
                return game.start[_lang(command.lang)]
            if command.kind == "end":
                self._finish(device_id, "asked")
                return END_LINE[_lang(command.lang)]
        return ""

    def on_stop_phrase(self, device_id: str, text: object) -> bool:
        """A whole-utterance stop phrase such as "that's enough" ends a game too (a bare "stop" only hushes the robot)."""
        said = fold(text) if isinstance(text, str) else ""
        if said not in _STOP_ENDS:
            return False
        with self._lock:
            if self._live(device_id) is None:
                return False
            self._finish(device_id, "stopped")
            return True

    def begin_turn(self, device_id: str) -> str | None:
        """A turn for the model is starting: count the round and answer the rules text, or None when no game is on.

        The turn that reaches the round limit still gets its rules (with the order to wrap up); the game is over after it."""
        with self._lock:
            state = self._live(device_id)
            if state is None:
                return None
            state.rounds += 1
            state.last = self._clock()
            text = rules_text(state)
            if state.rounds >= state.max_rounds:
                self._finish(device_id, "rounds")
            return text

    def add_point(self, device_id: str) -> int:
        """One point for the person, when a source says so (nothing guesses one from words)."""
        with self._lock:
            state = self._live(device_id)
            if state is None:
                return 0
            state.score += 1
            return state.score

    def end(self, device_id: str, why: str = "ended") -> bool:
        with self._lock:
            had = device_id in self._states
            self._finish(device_id, why)
            return had

    def status(self, device_id: str) -> dict[str, Any]:
        """For the settings page: what is on, the round and the limit."""
        state = self.state(device_id)
        if state is None:
            return {"playing": False}
        return {"playing": True, "game": state.game, "round": state.rounds, "max_rounds": state.max_rounds, "score": state.score}


# ---------------------------------------------------------------- handing the rules to the model


class GameTurn:
    """A turn client for one turn of a game: the same ``stream`` and ``cancel`` as the one it wraps, plus the rules.

    The unit's own model (a ``BrainTurn``) takes them next to its persona, as a system instruction. Home's turn client has no
    such field, so the rules go in front of the person's words in brackets (Home's own filters see the whole message). """

    def __init__(self, inner: Any, rules: str, *, persona_path: bool) -> None:
        self._inner = inner
        self._rules = rules
        self._persona_path = persona_path

    def stream(self, text: str, **kwargs: Any) -> Iterator[Any]:
        if self._persona_path:
            return self._inner.stream(text, instructions=self._rules, **kwargs)
        return self._inner.stream(f"[Game rules for this turn: {self._rules}] {text}", **kwargs)

    def cancel(self, turn_id: str) -> bool:
        return bool(self._inner.cancel(turn_id))

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


__all__ = [
    "END_LINE",
    "IDS",
    "SILENCE_S",
    "TALK_GAMES",
    "GameTurn",
    "TalkCommand",
    "TalkGame",
    "TalkGames",
    "TalkState",
    "get",
    "group",
    "listing",
    "parse",
    "rules_text",
]
