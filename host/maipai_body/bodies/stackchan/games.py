# ruff: noqa: E501
"""The unit's games, the host side (firmware patch G01).

The unit plays the games itself (color memory, whack-a-mole, tic-tac-toe, a game called "do it" that gets faster each round, rock paper
scissors, the magic 8 ball and dice and coin): the screen, the
touches, the tones, the rules and the best scores are the firmware's, so a game works with Home
down. This module is what only the host adds:

* the names a person says for each game, in English and Spanish, and the spoken asks that start,
  stop or list them ("play memory", "juega a los topos", "stop the game", "what games do you
  have");
* the hub's device commands ``game_start``, ``game_list``, ``game_stop`` and ``game_scores``, each
  answering ``{ok, ...}`` or ``{ok: False, error}`` in plain words, through the unit's own
  ``self.game.*`` tools;
* the view the settings page shows: every game and its best scores.

Rules: a game never starts in full quiet (the unit refuses it and says so); a muted unit plays it
with no sound; a stopped game saves nothing. The firmware table and the names here are kept equal
by a test.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from maipai_body.hal.errors import BodyLost
from maipai_body.i18n import normalize
from maipai_body.unit_extras import fold

logger = logging.getLogger("maipai_body.bodies.stackchan.games")


@dataclass(frozen=True)
class Game:
    id: str
    title: dict[str, str]
    # What a person may call it, already folded to lower-case ASCII words (see unit_extras.fold).
    aliases: tuple[str, ...]
    lower_is_better: bool
    unit: dict[str, str]  # what the score counts, for the settings page


GAMES: tuple[Game, ...] = (
    Game(
        "memory",
        {"en": "Color Memory", "es": "Memoria de colores"},
        (
            "memory",
            "color memory",
            "color memory",
            "simon",
            "memoria",
            "memoria de colores",
            "juego de memoria",
            "colores",
        ),
        False,
        {"en": "rounds", "es": "rondas"},
    ),
    Game(
        "whack",
        {"en": "Whack-a-Mole", "es": "Atrapa topos"},
        (
            "whack",
            "whack a mole",
            "whackamole",
            "mole",
            "moles",
            "atrapa topos",
            "atrapa el topo",
            "topo",
            "topos",
            "golpea topos",
        ),
        False,
        {"en": "moles", "es": "topos"},
    ),
    Game(
        "tictactoe",
        {"en": "Tic-Tac-Toe", "es": "Tres en raya"},
        (
            "tictactoe",
            "tic tac toe",
            "tic tac",
            "noughts and crosses",
            "naughts and crosses",
            "tres en raya",
            "tres en linea",
            "el gato",
            "gato",
        ),
        False,
        {"en": "points", "es": "puntos"},
    ),
    Game(
        "bopit",
        {"en": "Do It", "es": "Hazlo"},
        (
            "bopit",
            "do it",
            "do it game",
            "tap swipe shake",
            "hazlo",
            "haz lo que digo",
        ),
        False,
        {"en": "rounds", "es": "rondas"},
    ),
    Game(
        "rps",
        {"en": "Rock Paper Scissors", "es": "Piedra papel tijera"},
        (
            "rps",
            "rock paper scissors",
            "rock paper or scissors",
            "rock scissors paper",
            "roshambo",
            "piedra papel tijera",
            "piedra papel o tijera",
            "piedra papel y tijera",
            "pptj",
        ),
        False,
        {"en": "matches won", "es": "partidas ganadas"},
    ),
    Game(
        "eightball",
        {"en": "Magic 8-Ball", "es": "Bola 8 magica"},
        (
            "eightball",
            "magic 8 ball",
            "magic eight ball",
            "8 ball",
            "eight ball",
            "bola 8",
            "bola 8 magica",
            "bola magica",
        ),
        False,
        {"en": "questions", "es": "preguntas"},
    ),
    Game(
        "dice",
        {"en": "Dice and Coin", "es": "Dados y moneda"},
        (
            "dice",
            "dice and coin",
            "a dice",
            "a die",
            "coin flip",
            "coin",
            "dados",
            "dado",
            "dados y moneda",
            "moneda",
        ),
        False,
        {"en": "rolls", "es": "tiradas"},
    ),
)
IDS = tuple(g.id for g in GAMES)

_START = (
    "play",
    "start",
    "lets play",
    "juega",
    "jugar",
    "juguemos",
    "jugamos",
    "pon",
    "empieza",
    "empezar",
    "quiero jugar",
)
_STOP = (
    "stop the game",
    "stop game",
    "stop playing",
    "end the game",
    "quit the game",
    "quit game",
    "im done playing",
    "para el juego",
    "parar el juego",
    "deja de jugar",
    "termina el juego",
    "acaba el juego",
)
_LIST = (
    "what games",
    "which games",
    "list games",
    "list the games",
    "games do you have",
    "games can you play",
    "games can we play",
    "que juegos",
    "cuales juegos",
    "lista de juegos",
    "lista los juegos",
)
# Short asks that start a game by themselves, with no word like "play" ("roll a dice", "flip a coin"), in English and Spanish.
_DIRECT = (
    ("roll a dice", "dice"),
    ("roll a die", "dice"),
    ("roll the dice", "dice"),
    ("roll the die", "dice"),
    ("roll some dice", "dice"),
    ("roll dice", "dice"),
    ("throw the dice", "dice"),
    ("flip a coin", "dice"),
    ("toss a coin", "dice"),
    ("flip the coin", "dice"),
    ("coin flip", "dice"),
    ("heads or tails", "dice"),
    ("tira un dado", "dice"),
    ("tira los dados", "dice"),
    ("lanza un dado", "dice"),
    ("lanza una moneda", "dice"),
    ("tira una moneda", "dice"),
    ("cara o cruz", "dice"),
    ("ask the magic 8 ball", "eightball"),
    ("ask the magic eight ball", "eightball"),
    ("pregunta a la bola 8", "eightball"),
    ("pregunta a la bola magica", "eightball"),
)
_SCORES = (
    "best score",
    "high score",
    "my score",
    "mejor puntuacion",
    "mejores puntuaciones",
    "puntuacion mas alta",
    "mis puntos",
)


def find_game(text: object) -> Game | None:
    """The game a person named, or None. Matches the id, the title and every alias, English or Spanish."""
    if not isinstance(text, str):
        return None
    words = fold(text)
    if not words:
        return None
    best: tuple[int, Game] | None = None
    for game in GAMES:
        names = {fold(game.id), fold(game.title["en"]), fold(game.title["es"]), *game.aliases}
        for name in names:
            # the whole name must appear as whole words
            if f" {name} " in f" {words} ":
                score = len(name)
                if best is None or score > best[0]:
                    best = (score, game)
    return best[1] if best else None


def parse_ask(text: object) -> tuple[str, str | None] | None:
    """A spoken ask about games: ("start", id), ("stop", None), ("list", None), ("scores", id or None), or None.

    Only phrases that are plainly about games count; the words "stop" or "list" alone mean something
    else to the rest of the unit, so they are not taken here (the stop word has its own path).
    """
    if not isinstance(text, str):
        return None
    said = fold(text)
    if not said:
        return None
    if any(p in said for p in _STOP):
        return ("stop", None)
    if any(p in said for p in _LIST):
        return ("list", None)
    for phrase, game_id in _DIRECT:
        if f" {phrase} " in f" {said} ":
            return ("start", game_id)
    game = find_game(said)
    if any(p in said for p in _SCORES):
        return ("scores", game.id if game else None)
    if game is not None and any(f" {p} " in f" {said} " for p in _START):
        return ("start", game.id)
    from maipai_body.bodies.stackchan import game_voice

    if game_voice.parse_list(said):
        return ("list", None)
    parsed = game_voice.parse_random(said)
    if parsed is not None:
        return (parsed[0], None)
    # a game named in French, German, Portuguese or Italian, started with their word for play
    for gid, names in game_voice.EXTRA_ALIASES.items():
        if any(f" {n} " in f" {said} " for n in names) and any(f" {p} " in f" {said} " for p in ("joue a", "joue", "spiel", "spielen", "vamos jogar", "joga", "gioca", "giochiamo a", "jouons a", "brincar")):
            return ("start", gid)
    return None


_SPANISH_WORDS = frozenset(
    "juega jugar juguemos jugamos quiero deja termina acaba que cuales lista mejor puntuacion puntuaciones "
    "topo topos memoria colores pon empieza para el los las tres raya linea gato hazlo piedra papel tijera dados dado moneda bola magica cara cruz tira lanza".split()
)


def _spanish(text: str) -> bool:
    words = set(fold(text).split())
    return len(words & (_SPANISH_WORDS - {"para", "el", "los", "las", "lista"})) > 0


_LINES = {
    "en": {
        "start": "Okay, let's play {title}.",
        "stopped": "Okay, I stopped the game.",
        "none_playing": "No game is playing right now.",
        "no_scores": "There is no best score for {title} yet.",
        "best": "Your best in {title} is {best} {unit}.",
        "list": "I have {names}.",
    },
    "es": {
        "start": "Vale, a jugar a {title}.",
        "stopped": "Vale, detuve el juego.",
        "none_playing": "Ahora no hay ningun juego en marcha.",
        "no_scores": "Todavia no hay mejor puntuacion en {title}.",
        "best": "Tu mejor en {title} es {best} {unit}.",
        "list": "Tengo {names}.",
    },
}

_PLAIN = {
    "en": {
        "no_game": "I do not know that game. Ask for memory, whack-a-mole, tic-tac-toe, do it, rock paper scissors, magic 8 ball or dice.",
        "unreachable": "I could not reach my body to do that. Check that it is on, then ask again.",
        "old_firmware": "This unit's firmware has no games. Update the unit's firmware, then ask again.",
        "none": "No scores yet. Play a game and the best ones show here.",
    },
    "es": {
        "no_game": "No conozco ese juego. Pide memoria, atrapa topos, tres en raya, hazlo, piedra papel tijera, bola 8 magica o dados.",
        "unreachable": "No pude llegar a mi cuerpo para hacerlo. Comprueba que este encendido y pidelo otra vez.",
        "old_firmware": "El firmware de esta unidad no tiene juegos. Actualizalo y pidelo otra vez.",
        "none": "Todavia no hay puntuaciones. Juega y las mejores se muestran aqui.",
    },
}


def _say(lang: str | None, key: str) -> str:
    table = _PLAIN.get(normalize(lang)) or _PLAIN["en"]
    return table.get(key) or _PLAIN["en"][key]


def _reply(result: object) -> dict[str, Any]:
    if isinstance(result, dict):
        return result
    if isinstance(result, (str, bytes)):
        try:
            parsed = json.loads(result)
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


class GameService:
    """Starts, stops and lists the unit's games through its ``self.game.*`` tools.

    ``call`` is the unit client's tool call (name, arguments); it may raise ``BodyLost`` when the
    unit is not connected.
    """

    def __init__(
        self,
        call: Callable[[str, dict[str, object]], object],
        *,
        language: str = "en",
        picker: Any = None,
        notices: Any = None,
        unit: Callable[[], str] = lambda: "",
        refusal: Callable[[], str | None] = lambda: None,
        model_ready: Callable[[], bool] = lambda: False,
        start_talk: Callable[[str, str], str] | None = None,
    ) -> None:
        self._call = call
        self._language = language
        # The voice games with no model (game_voice.py): `picker` chooses among the games on this robot, `notices` leaves "Install X?" on the
        # dashboard, `refusal()` answers "quiet", "locked" or "child" when a game must not start, `start_talk(id, lang)` starts a model game.
        self._picker, self._notices, self._unit, self._refusal, self._model_ready, self._start_talk = picker, notices, unit, refusal, model_ready, start_talk

    def _tool(
        self,
        name: str,
        arguments: dict[str, object],
        lang: str | None,
        *,
        needs_ok: bool = False,
    ) -> dict[str, Any]:
        """One tool call. A unit that does not answer is "unreachable"; one that has no such tool is old firmware.

        ``needs_ok``: the tool cannot fail on a unit that has it (list, scores), so any not-ok answer
        means the firmware has no games. For start and stop a not-ok answer is the unit's own plain
        sentence (full quiet, an update, another game running) and is passed on.
        """
        try:
            reply = _reply(self._call(name, arguments))
        except BodyLost:
            return {"ok": False, "error": _say(lang or self._language, "unreachable")}
        if reply.get("isError") and reply.get("ok") is not True:  # the unit refused the call: say so in plain words, never stay silent
            return {"ok": False, "error": _say(lang or self._language, "unreachable")}
        if not reply or (needs_ok and reply.get("ok") is not True):
            return {"ok": False, "error": _say(lang or self._language, "old_firmware")}
        return reply

    def start(self, name: object, lang: str | None = None) -> dict[str, Any]:
        game = find_game(name)
        if game is None:
            return {"ok": False, "error": _say(lang or self._language, "no_game")}
        reply = self._tool("self.game.start", {"name": game.id}, lang)
        return {**reply, "game": game.id} if reply.get("ok") is True else reply

    def stop(self, lang: str | None = None) -> dict[str, Any]:
        return self._tool("self.game.stop", {}, lang)

    def list(self, lang: str | None = None) -> dict[str, Any]:
        reply = self._tool("self.game.list", {}, lang, needs_ok=True)
        if reply.get("ok") is not True:
            return reply
        code = normalize(lang or self._language)
        rows = []
        for item in reply.get("games", []):
            known = next((g for g in GAMES if g.id == item.get("id")), None)
            rows.append(
                {
                    "id": item.get("id"),
                    "title": (known.title.get(code) or known.title["en"])
                    if known
                    else item.get("title"),
                    "lower_is_better": bool(item.get("lower_is_better")),
                    "unit": (known.unit.get(code) or known.unit["en"]) if known else "",
                    "scores": [s for s in item.get("scores", []) if isinstance(s, int)][:5],
                }
            )
        return {"ok": True, "playing": bool(reply.get("playing")), "games": rows}

    def scores(self, name: object, lang: str | None = None) -> dict[str, Any]:
        game = find_game(name)
        if game is None:
            return {"ok": False, "error": _say(lang or self._language, "no_game")}
        return self._tool("self.game.scores", {"name": game.id}, lang, needs_ok=True)

    def ask(self, text: object, lang: str | None = None) -> dict[str, Any] | None:
        """Answer a spoken ask about games, or None when the words are not about games."""
        parsed = parse_ask(text)
        if parsed is None:
            return None
        kind, game_id = parsed
        if kind == "start":
            return self.start(game_id, lang)
        if kind == "stop":
            return self.stop(lang)
        if kind == "scores":
            return self.scores(game_id, lang) if game_id else self.list(lang)
        return self.list(lang)

    def spoken(self, ask: tuple[str, str | None], text: str = "") -> str:
        """Do a parsed spoken ask and answer the short line to say, in the language the person used."""
        kind, game_id = ask
        from maipai_body.bodies.stackchan import game_voice

        phrase_lang = (game_voice.parse_random(text) or (None, None))[1] or game_voice.parse_list(text)
        lang = phrase_lang or ("es" if _spanish(text) else self._language if self._language in game_voice.LINES else "en")
        game = next((g for g in GAMES if g.id == game_id), None)
        title = game.title.get(lang) or game.title["en"] if game else ""
        if kind in ("random", "another", "start"):
            blocked = self._refusal() if self._refusal else None
            if blocked in ("quiet", "locked", "child"):
                return game_voice.say(lang, blocked)
        if kind in ("random", "another"):
            return self._random(lang)
        if kind == "start":
            installed = self._installed_ids()
            if installed is not None and game is not None and game.id not in installed:
                if self._notices is not None:
                    self._notices.add(self._unit(), "game", title, f"game/{game.id}")
                return game_voice.say(lang, "not_installed", title=title)
            result = self.start(game_id, lang)
            if result.get("ok") is True:
                if self._picker is not None and game_id:
                    self._picker.note_played(self._unit(), game_id)
                return (_LINES.get(lang) or _LINES["en"])["start"].format(title=title)
            return str(result.get("error", ""))
        if kind == "stop":
            result = self.stop(lang)
            if result.get("ok") is not True:
                return str(result.get("error", ""))
            return _LINES[lang]["stopped" if result.get("was") else "none_playing"]
        if kind == "scores" and game is not None:
            result = self.scores(game_id, lang)
            if result.get("ok") is not True:
                return str(result.get("error", ""))
            scores = [n for n in result.get("scores", []) if isinstance(n, int)]
            if not scores:
                return _LINES[lang]["no_scores"].format(title=title)
            return _LINES[lang]["best"].format(title=title, best=scores[0], unit=game.unit[lang])
        listing = self.list(lang)
        if listing.get("ok") is not True:
            return str(listing.get("error", ""))
        names = [g["title"] for g in listing["games"]]
        if not names:
            return game_voice.say(lang, "none")
        return game_voice.say(lang, "list", names=game_voice.join_names(lang, names))

    def _installed_ids(self) -> list[str] | None:
        """The ids of the games on this robot (its own list), or None when the robot cannot say."""
        listing = self.list(self._language)
        if listing.get("ok") is not True:
            return None
        self._playing = bool(listing.get("playing"))
        return [str(g["id"]) for g in listing["games"] if g.get("id")]

    def _random(self, lang: str) -> str:
        """Pick a game from the ones installed on this robot, never the one just played, and start it."""
        from maipai_body.bodies.stackchan import game_voice, talk_games

        installed = self._installed_ids()
        if not installed:
            return game_voice.say(lang, "none")
        picker = self._picker or game_voice.GamePicker()
        self._picker = picker
        talk = [f"talk:{g}" for g in talk_games.IDS] if (self._model_ready() and self._start_talk is not None) else []
        unit = self._unit()
        choice = picker.pick(unit, installed + talk)
        if choice is None:
            return game_voice.say(lang, "none")
        if choice.startswith("talk:"):
            picker.note_played(unit, choice)
            line = self._start_talk(choice[5:], lang) if self._start_talk else ""
            return line or game_voice.say(lang, "none")
        if getattr(self, "_playing", False):
            self.stop(lang)  # "another one" ends the game that is on first
        result = self.start(choice, lang)
        if result.get("ok") is not True:
            return str(result.get("error", ""))
        picker.note_played(unit, choice)
        game = next((g for g in GAMES if g.id == choice), None)
        return game_voice.say(lang, "random", title=(game.title.get(lang) or game.title["en"]) if game else choice)

    def handlers(self) -> dict[str, Callable[[dict], dict]]:
        """The hub's device commands for games: each answers {ok, ...} or {ok: False, error}."""

        def guarded(fn: Callable[[dict], dict]) -> Callable[[dict], dict]:
            def run(payload: dict) -> dict:
                try:
                    return fn(payload)
                except Exception as exc:  # the unit is away or answered oddly
                    logger.warning("game command failed", exc_info=True)
                    return {
                        "ok": False,
                        "error": _say(self._language, "unreachable"),
                        "detail": type(exc).__name__,
                    }

            return run

        return {
            "game_start": guarded(lambda p: self.start(p.get("name"), p.get("lang"))),
            "game_stop": guarded(lambda p: self.stop(p.get("lang"))),
            "game_list": guarded(lambda p: self.list(p.get("lang"))),
            "game_scores": guarded(lambda p: self.scores(p.get("name"), p.get("lang"))),
        }


__all__ = ["GAMES", "IDS", "Game", "GameService", "find_game", "parse_ask"]
