# ruff: noqa: E501
"""Voice games with no model: "play a game", "I'm bored", "another one", "what games do you have", in every shipped language.

Fixed phrases, like the other voice commands. The robot picks among the games installed on THIS robot (the unit's own list, decision 17),
never the one it just played and not the last three while others remain, weighted by what the person plays and by whether a model is
available for the talk games. A game that exists but is not installed is named plainly and left as a notice on the dashboard
("Install X?"), never installed on its own. Full quiet refuses; a muted robot plays silently (the unit does that); a locked robot or a child
refuses. Everything is per robot (decision 16).
"""

from __future__ import annotations

import json
import os
import random
import tempfile
import threading
from collections import deque
from collections.abc import Callable
from pathlib import Path

from maipai_body.unit_extras import fold

# ---------------------------------------------------------------- the phrases (folded: lower case, no accents, no punctuation)

RANDOM = {
    "en": ("play a game", "lets play", "let's play", "play something", "pick a game", "im bored", "i am bored", "surprise me", "lets play a game", "can we play a game"),
    "es": ("juega a algo", "jugamos", "juguemos", "juguemos a algo", "estoy aburrido", "estoy aburrida", "elige un juego", "sorprendeme", "quiero jugar", "jugamos a un juego"),
    "fr": ("jouons", "jouons a un jeu", "on joue", "je mennuie", "je m ennuie", "choisis un jeu", "joue a un jeu", "surprends moi", "on joue a un jeu"),
    "de": ("lass uns spielen", "spielen wir", "mir ist langweilig", "spiel ein spiel", "such ein spiel aus", "ueberrasch mich", "lass uns ein spiel spielen"),
    "pt": ("vamos brincar", "vamos jogar", "estou entediado", "estou entediada", "escolhe um jogo", "joga um jogo", "me surpreenda", "vamos jogar um jogo"),
    "it": ("giochiamo", "facciamo un gioco", "mi annoio", "scegli un gioco", "giochiamo a qualcosa", "sorprendimi", "giochiamo a un gioco"),
}
ANOTHER = {
    "en": ("another one", "another game", "play something else", "something else", "play a different game", "next game", "play another game"),
    "es": ("otro", "otro juego", "juega a otra cosa", "algo diferente", "otro mas", "juega a otro"),
    "fr": ("un autre", "un autre jeu", "autre chose", "joue a autre chose", "encore un autre"),
    "de": ("noch eins", "ein anderes spiel", "etwas anderes", "spiel etwas anderes", "noch ein spiel"),
    "pt": ("outro", "outro jogo", "joga outra coisa", "algo diferente", "mais um"),
    "it": ("un altro", "un altro gioco", "qualcos altro", "gioca a qualcos altro", "ancora uno"),
}
LIST = {
    "fr": ("quels jeux as tu", "quels jeux tu as", "liste des jeux", "tes jeux"),
    "de": ("welche spiele hast du", "welche spiele gibt es", "deine spiele", "liste der spiele"),
    "pt": ("que jogos tens", "que jogos tu tens", "quais jogos voce tem", "lista de jogos"),
    "it": ("quali giochi hai", "che giochi hai", "elenco dei giochi", "i tuoi giochi"),
}
# What a person may call each game in the languages the games table does not already name (folded).
EXTRA_ALIASES = {
    "memory": ("memoire", "jeu de memoire", "gedaechtnis", "gedaechtnisspiel", "jogo da memoria", "memoria colori", "gioco della memoria"),
    "whack": ("tape taupe", "taupe", "maulwurf", "hau den maulwurf", "bate toupeira", "acchiappa la talpa", "talpa"),
    "tictactoe": ("morpion", "tic tac toe", "tris", "drei gewinnt", "jogo da velha", "galo"),
    "bopit": ("fais le", "mach es", "faz isso", "fallo"),
    "rps": ("pierre feuille ciseaux", "schere stein papier", "pedra papel tesoura", "sasso carta forbici"),
    "eightball": ("boule magique", "magische kugel", "bola magica", "palla magica"),
    "dice": ("des", "wuerfel", "dados", "dadi", "pile ou face", "kopf oder zahl", "cara ou coroa", "testa o croce"),
}

LINES = {
    "en": {
        "random": "Okay, let's play {title}.",
        "none": "I have no games on this robot yet. Ask on the dashboard to add some.",
        "not_installed": "{title} is not on this robot. I left a note on your dashboard so you can add it.",
        "quiet": "I am in full quiet, so I cannot start a game now.",
        "locked": "The robot is locked, so I cannot start a game.",
        "child": "I will not start that game right now.",
        "list": "I have {names}.",
    },
    "es": {
        "random": "Vale, a jugar a {title}.",
        "none": "Todavía no tengo juegos en este robot. Pídelo en el panel para añadir algunos.",
        "not_installed": "{title} no está en este robot. Dejé un aviso en tu panel para que lo añadas.",
        "quiet": "Estoy en silencio total, así que ahora no puedo empezar un juego.",
        "locked": "El robot está bloqueado, así que no puedo empezar un juego.",
        "child": "Ahora no voy a empezar ese juego.",
        "list": "Tengo {names}.",
    },
    "fr": {
        "random": "D'accord, on joue à {title}.",
        "none": "Je n'ai pas encore de jeux sur ce robot. Demande sur le tableau de bord d'en ajouter.",
        "not_installed": "{title} n'est pas sur ce robot. J'ai laissé une note sur ton tableau de bord pour l'ajouter.",
        "quiet": "Je suis en silence total, donc je ne peux pas lancer de jeu maintenant.",
        "locked": "Le robot est verrouillé, donc je ne peux pas lancer de jeu.",
        "child": "Je ne vais pas lancer ce jeu maintenant.",
        "list": "J'ai {names}.",
    },
    "de": {
        "random": "Okay, wir spielen {title}.",
        "none": "Auf diesem Roboter sind noch keine Spiele. Füge auf dem Dashboard welche hinzu.",
        "not_installed": "{title} ist nicht auf diesem Roboter. Ich habe einen Hinweis auf dein Dashboard gelegt, damit du es hinzufügen kannst.",
        "quiet": "Ich bin im Ruhemodus, deshalb kann ich jetzt kein Spiel starten.",
        "locked": "Der Roboter ist gesperrt, deshalb kann ich kein Spiel starten.",
        "child": "Dieses Spiel starte ich jetzt nicht.",
        "list": "Ich habe {names}.",
    },
    "pt": {
        "random": "Certo, vamos jogar {title}.",
        "none": "Ainda não tenho jogos neste robô. Peça no painel para adicionar alguns.",
        "not_installed": "{title} não está neste robô. Deixei um aviso no seu painel para você adicionar.",
        "quiet": "Estou em silêncio total, então não posso começar um jogo agora.",
        "locked": "O robô está bloqueado, então não posso começar um jogo.",
        "child": "Não vou começar esse jogo agora.",
        "list": "Tenho {names}.",
    },
    "it": {
        "random": "Va bene, giochiamo a {title}.",
        "none": "Non ho ancora giochi su questo robot. Chiedi sulla dashboard di aggiungerne.",
        "not_installed": "{title} non è su questo robot. Ho lasciato un avviso sulla tua dashboard per aggiungerlo.",
        "quiet": "Sono in silenzio totale, quindi ora non posso iniziare un gioco.",
        "locked": "Il robot è bloccato, quindi non posso iniziare un gioco.",
        "child": "Non avvio quel gioco adesso.",
        "list": "Ho {names}.",
    },
}
AND = {"en": "and", "es": "y", "fr": "et", "de": "und", "pt": "e", "it": "e"}
HISTORY = 3


def match_language(text: object, table: dict[str, tuple[str, ...]]) -> str | None:
    """The language whose whole-utterance phrase this is, or None. Whole utterance (after a polite lead), so 'play a game of memory' is not a random ask."""
    if not isinstance(text, str):
        return None
    said = " ".join(fold(text).split())
    for lead in ("please ", "hey ", "oye ", "por favor ", "bitte ", "s il te plait ", "per favore ", "por favor "):
        if said.startswith(lead):
            said = said[len(lead):]
    for lang, phrases in table.items():
        if said in phrases:
            return lang
    return None


def parse_random(text: object) -> tuple[str, str] | None:
    """("random"|"another", language) for a fixed phrase, or None."""
    lang = match_language(text, RANDOM)
    if lang:
        return "random", lang
    lang = match_language(text, ANOTHER)
    if lang:
        return "another", lang
    return None


def parse_list(text: object) -> str | None:
    return match_language(text, LIST)


def say(lang: str | None, key: str, **values: str) -> str:
    table = LINES.get(lang or "en") or LINES["en"]
    return (table.get(key) or LINES["en"][key]).format(**values)


def join_names(lang: str, names: list[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + f" {AND.get(lang, 'and')} " + names[-1]


# ---------------------------------------------------------------- the picker


class GamePicker:
    """Chooses the next game for one robot: never the one just played, not the last three while others remain, weighted by plays."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
        self._history: dict[str, deque[str]] = {}
        self._plays: dict[str, dict[str, int]] = {}
        self._lock = threading.Lock()

    def note_played(self, unit: str, game_id: str) -> None:
        with self._lock:
            self._history.setdefault(unit, deque(maxlen=HISTORY)).append(game_id)
            plays = self._plays.setdefault(unit, {})
            plays[game_id] = plays.get(game_id, 0) + 1

    def last(self, unit: str) -> str | None:
        with self._lock:
            history = self._history.get(unit)
            return history[-1] if history else None

    def pick(self, unit: str, installed: list[str], *, talk_ready: Callable[[str], bool] = lambda gid: True) -> str | None:
        """A game id from the installed ones, or None when there is nothing to pick."""
        with self._lock:
            history = list(self._history.get(unit, ()))
            plays = dict(self._plays.get(unit, {}))
        usable = [g for g in installed if talk_ready(g)]
        if not usable:
            return None
        pool = [g for g in usable if g != (history[-1] if history else None)]
        if not pool:
            return usable[0]  # only one game exists: it may repeat
        fresh = [g for g in pool if g not in history]
        pool = fresh or pool
        weights = [1.0 + 0.5 * min(plays.get(g, 0), 6) for g in pool]
        return self._rng.choices(pool, weights=weights, k=1)[0]


# ---------------------------------------------------------------- dashboard notices: "Install X?" (never automatic)


class InstallNotices:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()

    def _load(self) -> dict:
        try:
            data = json.loads(self.path.read_text())
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def add(self, unit: str, kind: str, name: str, item_id: str) -> None:
        with self._lock:
            data = self._load()
            rows = data.setdefault(unit, [])
            if not any(r.get("id") == item_id for r in rows):
                rows.append({"kind": kind, "name": name, "id": item_id})
                self.path.parent.mkdir(parents=True, exist_ok=True)
                fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".notices-")
                with os.fdopen(fd, "w") as handle:
                    handle.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
                os.chmod(tmp, 0o600)
                os.replace(tmp, self.path)

    def get(self, unit: str) -> list[dict]:
        with self._lock:
            return list(self._load().get(unit, []))

    def clear(self, unit: str, item_id: str) -> None:
        with self._lock:
            data = self._load()
            data[unit] = [r for r in data.get(unit, []) if r.get("id") != item_id]
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".notices-")
            with os.fdopen(fd, "w") as handle:
                handle.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.path)
