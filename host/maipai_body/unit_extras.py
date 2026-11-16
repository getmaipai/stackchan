# ruff: noqa: E501
"""Per-unit extras the settings page edits and pushes to the unit (firmware patches U02 to U05, Train 4).

Four small services share one pattern: the host keeps the owner's choice in a small JSON file (so a
unit that is off still gets it later), checks it with the same rules the firmware uses, and sends it
through the unit's own tools.

* Word reactions (U02): a table of words that show a face, play a quiet sound, draw a face extra and
  optionally dance. The unit holds the table and matches the words; the page edits it.
* Clock and time zone (U03): the host sets the unit's clock (it never asks a public time server) and
  the zone is one of a short list.
* Network test (U04): the unit's own plain-words check of Wi-Fi, the link to this host and the
  private network, with the one thing to do about the first problem.
* Unit details (U05): the firmware version, release tag, image trust, slot and free memory.

``screen_text`` folds accents out of any text that is drawn on the unit's screen, because the screen
font has no accents.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import threading
import time
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from maipai_body.faces import CAPTION_SIZES, DECORATORS, FaceError, valid_colour
from maipai_body.hal.errors import BodyLost
from maipai_body.i18n import normalize

logger = logging.getLogger("maipai_body.unit_extras")

# ---------------------------------------------------------------------------------------------
# Messages. English and Spanish; the other page languages read English (their page words are in i18n).
# ---------------------------------------------------------------------------------------------

_MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "no_unit": "No unit is selected. Choose a unit, then try again.",
        "offline": "The unit is not connected. It is saved here and goes to the unit when it reconnects.",
        "refused": "The unit refused it: {why}. Fix that and try again.",
        "unreachable": "The unit is not connected, so it could not be asked. Check that it is on and near the router, then try again.",
        "old_firmware": "This unit's firmware does not have {what}. Update the unit's firmware, then try again.",
        "react_rows": "The reactions must be a list of at most {max} rows. Remove some rows and save again.",
        "react_row": "Row {n}: {why}. Fix that row and save again.",
        "react_phrase": "the words must be 2 to 23 letters or numbers",
        "react_face": "the face must be none, happy, sad, angry, doubtful or sleepy",
        "react_sound": "the sound must be none, success, popup, goodbye, charged, needs_you or vibration",
        "react_decor": "the face extra must be none or one of dizzy, heart, anger, tears, sparkles, stars, zzz",
        "react_dance": "the dance must be none, happy, robot, panic or look_around",
        "react_empty": "a reaction needs at least a face, a sound, a face extra or a dance",
        "react_dup": "those words are already in the table",
        "react_text": "write each reaction on one line as: words | face | sound | extra | dance",
        "zone": "The time zone {value!r} is not in the list. Pick a zone from the list.",
        "clock_set": "The clock is set from this computer.",
        "person_name": "A person needs a name of 1 to 24 letters, numbers or spaces. Type a name and save again.",
        "person_wake": "A wake phrase is 3 to 24 letters, numbers or spaces. Type a shorter or longer phrase, or leave it empty.",
        "person_many": "The list holds at most {max} people. Remove one, then add the new one.",
        "person_unknown": "That person is not in the list. Add them first.",
        "person_applied": "{name}'s face colour and caption size were sent to the unit.",
        "bad_file": "The file {path} could not be read. Fix or remove it; the built-in choices are used meanwhile.",
        "travel_key": "A Tailscale auth key is 16 to 200 letters, numbers or dashes with no spaces (it starts with tskey-). Paste the whole key and try again.",
        "travel_saved": "Saved on the unit. It joins Tailscale the next time it cannot reach your hub, then erases the key.",
        "travel_forgot": "The unit forgot its Tailscale key, the hub address and its place on your Tailscale network.",
        "travel_nothing": "Paste a Tailscale auth key or the hub's Tailscale address, or choose Forget the key.",
        "travel_peer": "The hub's Tailscale address looks like 100.x.x.x (four numbers with dots). Copy it from your Tailscale admin console and try again.",
        "travel_bad_key": "The unit did not accept that key. Make a new one-time key in your Tailscale admin console and paste it again.",
        "travel_not_built": "This unit's firmware was built without Tailscale. Update the firmware, then try again.",
        "travel_running": "The unit is joining Tailscale right now. Restart it first, then forget the key.",
    },
    "es": {
        "no_unit": "No hay ninguna unidad elegida. Elige una unidad y vuelve a intentarlo.",
        "offline": "La unidad no esta conectada. Se guarda aqui y llega a la unidad cuando se reconecte.",
        "refused": "La unidad lo rechazo: {why}. Corrigelo y vuelve a intentarlo.",
        "unreachable": "La unidad no esta conectada, asi que no se le pudo preguntar. Comprueba que este encendida y cerca del router, y vuelve a intentarlo.",
        "old_firmware": "El firmware de esta unidad no tiene {what}. Actualiza el firmware de la unidad y vuelve a intentarlo.",
        "react_rows": "Las reacciones deben ser una lista de {max} filas como maximo. Quita algunas filas y guarda otra vez.",
        "react_row": "Fila {n}: {why}. Corrige esa fila y guarda otra vez.",
        "react_phrase": "las palabras deben tener de 2 a 23 letras o numeros",
        "react_face": "la cara debe ser none, happy, sad, angry, doubtful o sleepy",
        "react_sound": "el sonido debe ser none, success, popup, goodbye, charged, needs_you o vibration",
        "react_decor": "el adorno debe ser none o uno de dizzy, heart, anger, tears, sparkles, stars, zzz",
        "react_dance": "el baile debe ser none, happy, robot, panic o look_around",
        "react_empty": "una reaccion necesita al menos una cara, un sonido, un adorno o un baile",
        "react_dup": "esas palabras ya estan en la tabla",
        "react_text": "escribe cada reaccion en una linea asi: palabras | cara | sonido | adorno | baile",
        "zone": "La zona horaria {value!r} no esta en la lista. Elige una zona de la lista.",
        "clock_set": "El reloj se puso con la hora de este ordenador.",
        "person_name": "Una persona necesita un nombre de 1 a 24 letras, numeros o espacios. Escribe un nombre y guarda otra vez.",
        "person_wake": "Una frase de llamada tiene de 3 a 24 letras, numeros o espacios. Escribe una frase mas corta o mas larga, o dejala vacia.",
        "person_many": "La lista tiene como maximo {max} personas. Quita una y anade la nueva.",
        "person_unknown": "Esa persona no esta en la lista. Anadela primero.",
        "person_applied": "El color de cara y el tamano de subtitulos de {name} se enviaron a la unidad.",
        "bad_file": "No se pudo leer el archivo {path}. Corrigelo o quitalo; mientras tanto se usan las opciones incluidas.",
        "travel_key": "Una clave de Tailscale tiene de 16 a 200 letras, numeros o guiones, sin espacios (empieza por tskey-). Pega la clave entera y vuelve a intentarlo.",
        "travel_saved": "Guardada en la unidad. Se une a Tailscale la proxima vez que no llegue a tu hub y despues borra la clave.",
        "travel_forgot": "La unidad olvido su clave de Tailscale, la direccion del hub y su lugar en tu red de Tailscale.",
        "travel_nothing": "Pega una clave de Tailscale o la direccion de Tailscale del hub, o elige Olvidar la clave.",
        "travel_peer": "La direccion de Tailscale del hub es como 100.x.x.x (cuatro numeros con puntos). Copiala de tu consola de Tailscale y vuelve a intentarlo.",
        "travel_bad_key": "La unidad no acepto esa clave. Crea una clave nueva de un solo uso en tu consola de Tailscale y pegala otra vez.",
        "travel_not_built": "El firmware de esta unidad se creo sin Tailscale. Actualiza el firmware y vuelve a intentarlo.",
        "travel_running": "La unidad se esta uniendo a Tailscale ahora. Reiniciala primero y luego olvida la clave.",
    },
}


class ExtrasError(ValueError):
    """A rejected setting. The message says what went wrong and what to do, in the page language."""


def say(lang: str | None, key: str, **values: object) -> str:
    code = normalize(lang)
    table = _MESSAGES.get(code) or _MESSAGES["en"]
    return (table.get(key) or _MESSAGES["en"][key]).format(**values)


# ---------------------------------------------------------------------------------------------
# Screen text: the unit's font has no accents.
# ---------------------------------------------------------------------------------------------

_LATIN1 = "aaaaaaaceeeeiiiidnooooo/ouuuuytsaaaaaaaceeeeiiiidnooooo/ouuuuyty"  # U+00C0 to U+00FF, as the firmware reads them


def fold(text: str) -> str:
    """Lower-case ASCII words, as the firmware folds text before it looks for a reaction.

    Accents come off (Latin-1 letters only: anything else is a gap), the sharp s is ``ss``, the ae
    ligature is ``ae``, an apostrophe vanishes and any other mark is a single space.
    """
    out: list[str] = []
    pending = False
    for ch in text or "":
        code = ord(ch)
        piece = ""
        if code < 0x80:
            if ch.isascii() and ch.isalnum():
                piece = ch.lower()
            elif ch == "'":
                continue
        elif 0xC0 <= code <= 0xFF:
            mapped = _LATIN1[code - 0xC0]
            if code in (0xDF,):
                piece = "ss"
            elif code in (0xC6, 0xE6):
                piece = "ae"
            elif mapped != "/":
                piece = mapped
        if not piece:
            if out:
                pending = True
            continue
        if pending:
            out.append(" ")
        pending = False
        out.append(piece)
    return "".join(out)


def screen_text(text: str) -> str:
    """Text for the unit's screen: accents removed, everything else kept (case and punctuation too)."""
    cleaned: list[str] = []
    for ch in text or "":
        if ch == "ß":
            cleaned.append("ss")
        elif ch in "æÆ":
            cleaned.append("ae" if ch == "æ" else "AE")
        elif ch in "øØ":
            cleaned.append("o" if ch == "ø" else "O")
        elif ch in "ðÐ":
            cleaned.append("d" if ch == "ð" else "D")
        elif ch in "þÞ":
            cleaned.append("th")
        elif ch == "¿" or ch == "¡":
            continue
        else:
            decomposed = unicodedata.normalize("NFKD", ch)
            base = "".join(c for c in decomposed if not unicodedata.combining(c))
            cleaned.append(base if base.isascii() else "")
    return "".join(cleaned)


# ---------------------------------------------------------------------------------------------
# Shared file store and tool call helpers
# ---------------------------------------------------------------------------------------------


def _config_dir() -> Path:
    return Path.home() / ".config" / "maipai"


class _JsonFile:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self.problem: str | None = None

    def read(self) -> dict[str, Any]:
        with self._lock:
            try:
                raw = json.loads(self.path.read_text())
            except FileNotFoundError:
                return {}
            except (OSError, ValueError):
                self.problem = say("en", "bad_file", path=self.path)
                logger.warning(self.problem)
                return {}
            return raw if isinstance(raw, dict) else {}

    def write(self, data: Mapping[str, Any]) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".extras-")
            try:
                with os.fdopen(fd, "w") as handle:
                    handle.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
                os.replace(tmp, self.path)
            except OSError:
                Path(tmp).unlink(missing_ok=True)
                raise


def _reply(result: object) -> dict[str, Any]:
    if isinstance(result, Mapping):
        return dict(result)
    if isinstance(result, (str, bytes)):
        try:
            parsed = json.loads(result)
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


class _Tools:
    """One call to a unit's tool with the same timeout and reply reading everywhere."""

    def __init__(self, call: Callable[..., object], timeout: float = 6.0) -> None:
        self._call = call
        self._timeout = timeout

    def __call__(self, unit_id: str, name: str, arguments: dict[str, object]) -> dict[str, Any]:
        return _reply(self._call(name, arguments, device_id=unit_id, timeout=self._timeout))


# ---------------------------------------------------------------------------------------------
# U02: word reactions
# ---------------------------------------------------------------------------------------------

_TRAVEL_KEY = re.compile(r"^[A-Za-z0-9\-]{16,200}$")
_TAILNET_ADDR = re.compile(r"^100\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
REACT_MAX = 40
REACT_FACES = ("none", "happy", "sad", "angry", "doubtful", "sleepy")
REACT_SOUNDS = ("none", "success", "popup", "goodbye", "charged", "needs_you", "vibration")
REACT_DANCES = ("none", "happy", "robot", "panic", "look_around")
REACT_DECORS = ("none", *DECORATORS)
REACT_MIN_PHRASE = 2
REACT_MAX_PHRASE = 23

# The built-in table. The firmware has the same rows in maipai_react_core.h; a test keeps them equal.
DEFAULT_REACTIONS: tuple[tuple[str, str, str, str, str], ...] = (
    ("hello", "happy", "", "sparkles", ""),
    ("thanks", "happy", "success", "sparkles", ""),
    ("thank you", "happy", "success", "sparkles", ""),
    ("love", "happy", "", "heart", "happy"),
    ("sorry", "sad", "", "", ""),
    ("good night", "sleepy", "goodbye", "zzz", ""),
    ("hola", "happy", "", "sparkles", ""),
    ("gracias", "happy", "success", "sparkles", ""),
    ("te quiero", "happy", "", "heart", "happy"),
    ("lo siento", "sad", "", "", ""),
    ("buenas noches", "sleepy", "goodbye", "zzz", ""),
    ("bonjour", "happy", "", "sparkles", ""),
    ("merci", "happy", "success", "sparkles", ""),
    ("je taime", "happy", "", "heart", "happy"),
    ("je t aime", "happy", "", "heart", "happy"),
    ("desole", "sad", "", "", ""),
    ("bonne nuit", "sleepy", "goodbye", "zzz", ""),
    ("hallo", "happy", "", "sparkles", ""),
    ("danke", "happy", "success", "sparkles", ""),
    ("ich liebe dich", "happy", "", "heart", "happy"),
    ("tut mir leid", "sad", "", "", ""),
    ("gute nacht", "sleepy", "goodbye", "zzz", ""),
    ("ola", "happy", "", "sparkles", ""),
    ("obrigado", "happy", "success", "sparkles", ""),
    ("obrigada", "happy", "success", "sparkles", ""),
    ("te amo", "happy", "", "heart", "happy"),
    ("desculpa", "sad", "", "", ""),
    ("boa noite", "sleepy", "goodbye", "zzz", ""),
    ("ciao", "happy", "", "sparkles", ""),
    ("grazie", "happy", "success", "sparkles", ""),
    ("ti voglio bene", "happy", "", "heart", "happy"),
    ("scusa", "sad", "", "", ""),
    ("buonanotte", "sleepy", "goodbye", "zzz", ""),
)


@dataclass(frozen=True)
class Reaction:
    say: str
    face: str = "none"
    sound: str = "none"
    decor: str = "none"
    dance: str = "none"

    def to_wire(self) -> dict[str, str]:
        return {
            "say": self.say,
            "face": self.face,
            "sound": "" if self.sound == "none" else self.sound,
            "decor": "" if self.decor == "none" else self.decor,
            "dance": "" if self.dance == "none" else self.dance,
        }

    def to_json(self) -> dict[str, str]:
        return {
            "say": self.say,
            "face": self.face,
            "sound": self.sound,
            "decor": self.decor,
            "dance": self.dance,
        }


def default_reactions() -> list[Reaction]:
    return [
        Reaction(r[0], r[1] or "none", r[2] or "none", r[3] or "none", r[4] or "none")
        for r in DEFAULT_REACTIONS
    ]


def clean_reactions(rows: object, lang: str | None = None) -> list[Reaction]:
    """The table checked with the firmware's own rules. Raises ``ExtrasError`` with the first problem."""
    if not isinstance(rows, (list, tuple)) or len(rows) > REACT_MAX:
        raise ExtrasError(say(lang, "react_rows", max=REACT_MAX))
    out: list[Reaction] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping):
            raise ExtrasError(say(lang, "react_row", n=index, why=say(lang, "react_text")))
        phrase = fold(str(row.get("say", "")))
        face = str(row.get("face") or "none")
        sound = str(row.get("sound") or "none")
        decor = str(row.get("decor") or "none")
        dance = str(row.get("dance") or "none")

        def fail(key: str, n: int = index) -> ExtrasError:
            return ExtrasError(say(lang, "react_row", n=n, why=say(lang, key)))

        if not REACT_MIN_PHRASE <= len(phrase) <= REACT_MAX_PHRASE:
            raise fail("react_phrase")
        if face not in REACT_FACES:
            raise fail("react_face")
        if sound not in REACT_SOUNDS:
            raise fail("react_sound")
        if decor not in REACT_DECORS:
            raise fail("react_decor")
        if dance not in REACT_DANCES:
            raise fail("react_dance")
        if face == sound == decor == dance == "none":
            raise fail("react_empty")
        if phrase in seen:
            raise fail("react_dup")
        seen.add(phrase)
        out.append(Reaction(phrase, face, sound, decor, dance))
    return out


def reactions_to_text(rows: list[Reaction]) -> str:
    return "\n".join(f"{r.say} | {r.face} | {r.sound} | {r.decor} | {r.dance}" for r in rows)


def reactions_from_text(text: str, lang: str | None = None) -> list[Reaction]:
    """One reaction per line: ``words | face | sound | extra | dance`` (missing columns mean none)."""
    rows: list[dict[str, str]] = []
    for number, line in enumerate((text or "").splitlines(), start=1):
        if not line.strip():
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) > 5 or not cells[0]:
            raise ExtrasError(say(lang, "react_row", n=number, why=say(lang, "react_text")))
        cells += [""] * (5 - len(cells))
        rows.append(dict(zip(("say", "face", "sound", "decor", "dance"), cells, strict=True)))
    return clean_reactions(rows, lang)


class ReactionStore:
    """The owner's reaction table per unit (Device-Id); a unit with none saved uses the built-in table."""

    def __init__(self, path: Path | None = None) -> None:
        self._file = _JsonFile(path or _config_dir() / "stackchan-reactions.json")

    @property
    def problem(self) -> str | None:
        return self._file.problem

    def get(self, unit_id: str) -> list[Reaction] | None:
        raw = self._file.read().get(unit_id)
        if raw is None:
            return None
        try:
            return clean_reactions(raw)
        except ExtrasError:
            return None

    def set(self, unit_id: str, rows: list[Reaction]) -> None:
        data = self._file.read()
        data[unit_id] = [r.to_json() for r in rows]
        self._file.write(data)

    def reset(self, unit_id: str) -> None:
        data = self._file.read()
        if unit_id in data:
            del data[unit_id]
            self._file.write(data)


# ---------------------------------------------------------------------------------------------
# U03: clock and time zone
# ---------------------------------------------------------------------------------------------

# The firmware's list, west to east (maipai_tz_core.h); a test keeps them equal. id, label.
ZONES: tuple[tuple[str, str], ...] = (
    ("pacific_honolulu", "Honolulu"),
    ("america_anchorage", "Anchorage"),
    ("america_los_angeles", "Los Angeles"),
    ("america_denver", "Denver"),
    ("america_phoenix", "Phoenix"),
    ("america_chicago", "Chicago"),
    ("america_mexico_city", "Mexico City"),
    ("america_new_york", "New York"),
    ("america_bogota", "Bogota"),
    ("america_halifax", "Halifax"),
    ("america_sao_paulo", "Sao Paulo"),
    ("atlantic_azores", "Azores"),
    ("utc", "UTC"),
    ("europe_london", "London"),
    ("europe_lisbon", "Lisbon"),
    ("europe_paris", "Paris"),
    ("europe_berlin", "Berlin"),
    ("europe_madrid", "Madrid"),
    ("europe_rome", "Rome"),
    ("europe_athens", "Athens"),
    ("africa_cairo", "Cairo"),
    ("europe_moscow", "Moscow"),
    ("asia_dubai", "Dubai"),
    ("asia_karachi", "Karachi"),
    ("asia_kolkata", "Delhi"),
    ("asia_dhaka", "Dhaka"),
    ("asia_bangkok", "Bangkok"),
    ("asia_shanghai", "Beijing"),
    ("asia_tokyo", "Tokyo"),
    ("australia_sydney", "Sydney"),
    ("pacific_auckland", "Auckland"),
)
ZONE_IDS = tuple(z[0] for z in ZONES)


def zone_iana(zone_id: str) -> str:
    """``america_new_york`` is ``America/New_York``."""
    if zone_id == "utc":
        return "UTC"
    region, _, rest = zone_id.partition("_")
    return f"{region.capitalize()}/{'_'.join(w.capitalize() for w in rest.split('_'))}"


def _offsets(info: Any = None) -> tuple[int, int]:
    """UTC offsets in seconds on 15 January and 15 July; ``None`` means this computer's own zone rules."""

    def at(month: int) -> int:
        stamp = datetime(2026, month, 15, 12, tzinfo=UTC).astimezone(info)
        delta = stamp.utcoffset()
        return int(delta.total_seconds()) if delta else 0

    return at(1), at(7)


def guess_zone(local: Any = None) -> str | None:
    """The listed zone whose winter and summer offsets match this computer's, or None."""
    want = _offsets(local)  # no argument: this computer's own rules, summer time included
    for zone_id in ZONE_IDS:
        try:
            if _offsets(ZoneInfo(zone_iana(zone_id))) == want:
                return zone_id
        except ZoneInfoNotFoundError:
            continue
    return None


class ClockStore:
    def __init__(self, path: Path | None = None) -> None:
        self._file = _JsonFile(path or _config_dir() / "stackchan-clock.json")

    def get(self, unit_id: str) -> str | None:
        value = self._file.read().get(unit_id)
        return value if value in ZONE_IDS else None

    def set(self, unit_id: str, zone: str) -> None:
        data = self._file.read()
        data[unit_id] = zone
        self._file.write(data)


# ---------------------------------------------------------------------------------------------
# The facade the settings page and the connect event use
# ---------------------------------------------------------------------------------------------


class UnitExtras:
    """Reactions, clock, network test and unit details for every unit, through the unit's own tools."""

    def __init__(
        self,
        call: Callable[..., object],
        *,
        reactions: ReactionStore | None = None,
        clock: ClockStore | None = None,
        now: Callable[[], float] = time.time,
        local_zone: Callable[[], str | None] = guess_zone,
        timeout: float = 6.0,
    ) -> None:
        self._tool = _Tools(call, timeout)
        self.reactions = reactions or ReactionStore()
        self.clock = clock or ClockStore()
        self._now = now
        self._local_zone = local_zone

    # ---- word reactions ----

    def reactions_view(self, unit_id: str) -> dict[str, Any]:
        saved = self.reactions.get(unit_id)
        rows = saved if saved is not None else default_reactions()
        return {
            "unit": unit_id,
            "builtin": saved is None,
            "rows": [r.to_json() for r in rows],
            "text": reactions_to_text(rows),
            "choices": {
                "face": list(REACT_FACES),
                "sound": list(REACT_SOUNDS),
                "decor": list(REACT_DECORS),
                "dance": list(REACT_DANCES),
            },
            "limits": {"rows": REACT_MAX, "phrase": [REACT_MIN_PHRASE, REACT_MAX_PHRASE]},
            "problem": self.reactions.problem,
        }

    def save_reactions(
        self, unit_id: str, body: Mapping[str, Any], lang: str | None = None
    ) -> dict[str, Any]:
        """Check, save and push. ``body`` has ``rows`` (a list) or ``text`` (one reaction per line)."""
        if not unit_id:
            raise ExtrasError(say(lang, "no_unit"))
        rows = (
            reactions_from_text(str(body["text"]), lang)
            if "text" in body
            else clean_reactions(body.get("rows"), lang)
        )
        self.reactions.set(unit_id, rows)
        return {"ok": True, **self._push_reactions(unit_id, rows, lang)}

    def reset_reactions(self, unit_id: str, lang: str | None = None) -> dict[str, Any]:
        if not unit_id:
            raise ExtrasError(say(lang, "no_unit"))
        self.reactions.reset(unit_id)
        try:
            reply = self._tool(unit_id, "self.reaction.reset", {})
        except BodyLost:
            return {"ok": True, "pushed": False, "message": say(lang, "offline")}
        if reply.get("ok") is False:
            raise ExtrasError(say(lang, "refused", why=str(reply.get("error", "no reason given"))))
        return {"ok": True, "pushed": True, "message": ""}

    def _push_reactions(
        self, unit_id: str, rows: list[Reaction], lang: str | None
    ) -> dict[str, Any]:
        try:
            reply = self._tool(
                unit_id,
                "self.reaction.set_table",
                {"table": json.dumps([r.to_wire() for r in rows])},
            )
        except BodyLost:
            return {"pushed": False, "message": say(lang, "offline")}
        if reply.get("ok") is False:
            raise ExtrasError(say(lang, "refused", why=str(reply.get("error", "no reason given"))))
        return {"pushed": True, "message": ""}

    # ---- clock and zone ----

    def clock_view(self, unit_id: str) -> dict[str, Any]:
        saved = self.clock.get(unit_id)
        guess = self._local_zone()
        return {
            "unit": unit_id,
            "zone": saved or guess or "utc",
            "saved": saved is not None,
            "guess": guess,
            "zones": [{"id": i, "label": label} for i, label in ZONES],
        }

    def save_zone(self, unit_id: str, zone: object, lang: str | None = None) -> dict[str, Any]:
        if not unit_id:
            raise ExtrasError(say(lang, "no_unit"))
        if zone not in ZONE_IDS:
            raise ExtrasError(say(lang, "zone", value=zone))
        self.clock.set(unit_id, str(zone))
        return {"ok": True, **self._push_clock(unit_id, lang)}

    def set_clock_now(self, unit_id: str, lang: str | None = None) -> dict[str, Any]:
        """The page's button: set the unit's clock and zone from this computer."""
        if not unit_id:
            raise ExtrasError(say(lang, "no_unit"))
        result = self._push_clock(unit_id, lang)
        if result.get("pushed"):
            result["message"] = say(lang, "clock_set")
        return {"ok": True, **result}

    def _push_clock(self, unit_id: str, lang: str | None) -> dict[str, Any]:
        zone = self.clock.get(unit_id) or self._local_zone()
        try:
            if zone:
                reply = self._tool(unit_id, "self.clock.set_zone", {"zone": zone})
                if reply.get("ok") is False:
                    raise ExtrasError(
                        say(lang, "refused", why=str(reply.get("error", "no reason given")))
                    )
            reply = self._tool(unit_id, "self.clock.set", {"epoch": int(self._now())})
        except BodyLost:
            return {"pushed": False, "message": say(lang, "offline")}
        if reply.get("ok") is False:
            raise ExtrasError(say(lang, "refused", why=str(reply.get("error", "no reason given"))))
        return {"pushed": True, "message": "", "zone": zone, "local": reply.get("local", "")}

    # ---- network test and details ----

    def network_test(self, unit_id: str, lang: str | None = None) -> dict[str, Any]:
        """The unit's own check, in plain words. A unit that cannot be asked says so and what to do."""
        if not unit_id:
            raise ExtrasError(say(lang, "no_unit"))
        try:
            reply = self._tool(unit_id, "self.network.test", {})
        except BodyLost:
            return {
                "ok": False,
                "summary": say(lang, "unreachable"),
                "fix": say(lang, "unreachable"),
                "steps": [],
            }
        if reply.get("ok") is not True:
            return {
                "ok": False,
                "summary": say(lang, "old_firmware", what="the network test"),
                "fix": say(lang, "old_firmware", what="the network test"),
                "steps": [],
            }
        return reply

    def details(self, unit_id: str, lang: str | None = None) -> dict[str, Any]:
        if not unit_id:
            raise ExtrasError(say(lang, "no_unit"))
        try:
            reply = self._tool(unit_id, "self.version.get", {})
        except BodyLost:
            return {"ok": False, "error": say(lang, "unreachable")}
        if reply.get("ok") is not True:
            return {"ok": False, "error": say(lang, "old_firmware", what="the details page")}
        return reply

    # ---- travel key (firmware TN01 to TN06): the unit joins the private network from another Wi-Fi ----

    def travel_view(self, unit_id: str, lang: str | None = None) -> dict[str, Any]:
        """What the unit says about Tailscale, in plain fields. The key is never part of the answer."""
        if not unit_id:
            raise ExtrasError(say(lang, "no_unit"))
        try:
            reply = self._tool(unit_id, "self.tailnet.status", {})
        except BodyLost:
            return {"ok": False, "available": None, "error": say(lang, "unreachable")}
        if reply.get("ok") is False or ("state" not in reply and "enabled" not in reply):
            return {"ok": False, "available": False, "error": say(lang, "old_firmware", what="Tailscale")}
        shown = {k: v for k, v in reply.items() if k not in {"key", "authkey", "auth_key", "ok"}}
        state = str(shown.get("state", "off"))
        phase = {"connected": "connected", "connecting": "connecting", "registering": "connecting", "reconnecting": "connecting", "error": "error", "waiting_wifi": "waiting", "idle": "waiting"}.get(state, "off")
        if not shown.get("enabled") and phase == "waiting":
            phase = "off"
        if shown.get("compiled") is False:
            phase = "off"
        last = "refusal" if shown.get("refusal") else ("key" if phase == "error" and not shown.get("joined") else ("error" if phase == "error" else ""))
        return {
            "ok": True,
            "available": shown.get("compiled") is not False,
            **shown,
            "phase": phase,
            "route": shown.get("route", "home"),
            "last_error": last,
            "ready_to_use": bool(shown.get("key_saved") or shown.get("joined")) and bool(shown.get("peer_saved")),
        }

    def travel_set(
        self, unit_id: str, values: Mapping[str, Any], lang: str | None = None
    ) -> dict[str, Any]:
        """Send the Tailscale key (``key``), the hub's address (``peer``), on or off (``enabled``) or ``forget``.

        The host never stores the key and never echoes it."""
        if not unit_id:
            raise ExtrasError(say(lang, "no_unit"))
        key = values.get("key")
        peer = values.get("peer")
        arguments: dict[str, object] = {}
        forget = values.get("forget") is True
        if forget:
            arguments["forget"] = True
        else:
            if isinstance(key, str) and key.strip():
                if not _TRAVEL_KEY.match(key.strip()):
                    raise ExtrasError(say(lang, "travel_key"))
                arguments["key"] = key.strip()
                arguments["enabled"] = True
            if isinstance(peer, str) and peer.strip():
                if not _TAILNET_ADDR.match(peer.strip()):
                    raise ExtrasError(say(lang, "travel_peer"))
                arguments["peer"] = peer.strip()
                arguments.setdefault("enabled", True)
            if isinstance(values.get("enabled"), bool):
                arguments["enabled"] = values["enabled"]
            if not arguments:
                raise ExtrasError(say(lang, "travel_nothing"))
        try:
            reply = self._tool(unit_id, "self.tailnet.set", arguments)
        except BodyLost:
            raise ExtrasError(say(lang, "unreachable")) from None
        if reply.get("ok") is False:
            why = str(reply.get("error", "no reason given"))
            table = {"bad_key": "travel_bad_key", "bad_address": "travel_peer", "not_compiled": "travel_not_built", "running_restart_first": "travel_running"}
            if why in table:
                raise ExtrasError(say(lang, table[why]))
            if "nknown tool" in why:
                raise ExtrasError(say(lang, "old_firmware", what="Tailscale"))
            raise ExtrasError(say(lang, "refused", why=why.replace(str(key or "\0"), "the key")))
        if forget:
            return {"ok": True, "message": say(lang, "travel_forgot")}
        if "key" in arguments or "peer" in arguments:
            return {"ok": True, "message": say(lang, "travel_saved")}
        return {"ok": True, "message": ""}

    # ---- games (firmware patch G01) ----

    def games(self, unit_id: str, lang: str | None = None) -> dict[str, Any]:
        """Every game on the unit and its best scores, as data and as lines of plain words for the page."""
        from maipai_body.bodies.stackchan.games import GameService

        if not unit_id:
            raise ExtrasError(say(lang, "no_unit"))
        service = GameService(
            lambda name, args: self._tool(unit_id, name, args), language=normalize(lang)
        )
        view = service.list(lang)
        if view.get("ok") is not True:
            return {"ok": False, "error": view.get("error", ""), "lines": [view.get("error", "")]}
        none = "ninguna todavia" if normalize(lang) == "es" else "none yet"
        lines = []
        for game in view["games"]:
            best = ", ".join(str(n) for n in game["scores"]) or none
            lines.append(f"{game['title']}: {best} {game['unit'] if game['scores'] else ''}".rstrip())
        return {**view, "lines": lines}

    # ---- the connect event ----

    def sync(self, unit_id: str) -> None:
        """When a unit connects: set its clock and zone, and send the owner's reactions if there are any."""
        try:
            self._push_clock(unit_id, None)
        except (ExtrasError, OSError, TimeoutError):
            logger.debug("clock not sent to unit %s", unit_id[-5:], exc_info=True)
        saved = self.reactions.get(unit_id)
        if saved is None:
            return
        try:
            reply = self._tool(unit_id, "self.reaction.get_table", {})
            if (
                reply.get("ok") is True
                and reply.get("builtin") is False
                and _same_rows(reply.get("table"), saved)
            ):
                return
            self._push_reactions(unit_id, saved, None)
        except (BodyLost, ExtrasError, OSError, TimeoutError):
            logger.debug("reactions not sent to unit %s", unit_id[-5:], exc_info=True)


def _same_rows(wire: object, rows: list[Reaction]) -> bool:
    if not isinstance(wire, list) or len(wire) != len(rows):
        return False
    for got, want in zip(wire, rows, strict=True):
        if not isinstance(got, Mapping) or dict(got) != want.to_json():
            return False
    return True


def sync_on_connect(extras: UnitExtras, unit_id: str) -> None:
    """Session listener: never raises."""
    try:
        extras.sync(unit_id)
    except Exception:
        logger.warning(
            "could not send the clock and reactions to unit %s", unit_id[-5:], exc_info=True
        )


def offline_call(*_args: object, **_kwargs: object) -> object:
    raise BodyLost("No unit is connected to this process.")


# ---------------------------------------------------------------------------------------------
# U06: per-person choices
# ---------------------------------------------------------------------------------------------

PEOPLE_MAX = 12
_NAME = re.compile(r"^[^\W_][\w .'-]{0,23}$", re.UNICODE)
_WAKE = re.compile(r"^[A-Za-z0-9 ]{3,24}$")


def person_id(name: str) -> str:
    """A short ASCII id from a name: ``Nova B.`` is ``nova-b``."""
    slug = re.sub(r"[^a-z0-9]+", "-", screen_text(name).lower()).strip("-")
    return slug or "person"


@dataclass(frozen=True)
class Person:
    id: str
    name: str
    colour: str = "none"
    caption_size: str = "medium"
    wake_phrase: str = ""

    def to_json(self) -> dict[str, str]:
        return {
            "id": self.id,
            "name": self.name,
            "colour": self.colour,
            "caption_size": self.caption_size,
            "wake_phrase": self.wake_phrase,
        }


def clean_person(values: Mapping[str, Any], lang: str | None = None) -> Person:
    """A person from the page's fields, every one checked. Raises ``ExtrasError`` or ``FaceError``."""
    name = str(values.get("name", "")).strip()
    if not _NAME.match(name):
        raise ExtrasError(say(lang, "person_name"))
    colour = str(values.get("colour", "none") or "none").strip()
    key = colour if colour == "none" or not colour.startswith("#") else colour.lower()
    problem = valid_colour(key)
    if problem is not None:
        from maipai_body.faces import _say as face_say

        raise FaceError(face_say(lang, problem, value=colour))
    size = str(values.get("caption_size", "medium") or "medium")
    if size not in CAPTION_SIZES:
        from maipai_body.faces import _say as face_say

        raise FaceError(face_say(lang, "caption_size", value=size))
    wake = " ".join(str(values.get("wake_phrase", "") or "").split())
    if wake and not _WAKE.match(wake):
        raise ExtrasError(say(lang, "person_wake"))
    return Person(person_id(str(values.get("id") or name)), name, key, size, wake)


class PeopleStore:
    """The people this unit's owner customises: a name, a face colour, a caption size and a wake phrase."""

    def __init__(self, path: Path | None = None) -> None:
        self._file = _JsonFile(path or _config_dir() / "stackchan-people.json")

    @property
    def problem(self) -> str | None:
        return self._file.problem

    def all(self) -> list[Person]:
        raw = self._file.read().get("people", [])
        people: list[Person] = []
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, Mapping):
                    try:
                        people.append(clean_person(item))
                    except (ExtrasError, FaceError):
                        continue
        return people[:PEOPLE_MAX]

    def save(self, person: Person, lang: str | None = None) -> list[Person]:
        people = [p for p in self.all() if p.id != person.id]
        if len(people) >= PEOPLE_MAX:
            raise ExtrasError(say(lang, "person_many", max=PEOPLE_MAX))
        people.append(person)
        people.sort(key=lambda p: p.name.lower())
        self._file.write({"people": [p.to_json() for p in people]})
        return people

    def remove(self, pid: str) -> list[Person]:
        people = [p for p in self.all() if p.id != pid]
        self._file.write({"people": [p.to_json() for p in people]})
        return people


def apply_person(
    faces: Any, unit_id: str, person: Person, lang: str | None = None
) -> dict[str, Any]:
    """Send a person's face colour and caption size to a unit (the face service pushes it)."""
    result = faces.update(
        unit_id, {"colour": person.colour, "caption_size": person.caption_size}, lang
    )
    result["message"] = result.get("message") or say(lang, "person_applied", name=person.name)
    return result
