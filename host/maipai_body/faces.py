# ruff: noqa: E501
"""Face settings per unit, and how they reach the unit (firmware patches F01 to F06).

The face is neutral by default: white on black, the classic look, no captions, no time-of-day
change, no clock by itself. Style, color, captions, the time-of-day schedule, the thinking tone,
the language of the clock face and the clock are saved settings. This module holds them per unit
(keyed by the unit's Device-Id), checks them with the same rules the firmware uses, and sends them
through the unit's ``self.face.*`` tools. The unit keeps its own copy in its flash, so the face
looks right with this host off; the host copy is what the settings page shows and what it pushes
again after a reconnect or a unit reset.

The functions at the bottom (``settings_view``, ``apply_settings``) are what the settings page
calls; the page itself lives elsewhere.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from maipai_body.hal.errors import BodyLost
from maipai_body.i18n import normalize
from maipai_body.spelling_aliases import to_unit_keys, upgrade_keys

logger = logging.getLogger("maipai_body.faces")

# The face styles (firmware patch X02). Big eyes is the default. Stock is the original M5 face as shipped.
STYLES = (
    "big_eyes",
    "eyes_only",
    "stock",
    "classic",
    "minimal",
)
DEFAULT_STYLE = "big_eyes"
# Styles that were offered before patch X02. A saved or sent one is Big eyes now (never an error), so an old setting migrates.
DROPPED_STYLES = ("round", "cat", "robot", "sleepy", "retro_pixel", "heart_eyes")
NEW_LOOK_STYLES = ("eyes_only", "stock")  # firmware before patch X01 does not draw these two
CAPTION_SIZES = ("small", "medium", "large")
# Face decorators (firmware patch U01): small drawn extras shown for a few seconds. One list, here.
DECORATORS = ("dizzy", "heart", "anger", "tears", "sparkles", "stars", "zzz")  # sweat and shy were dropped (patch X02)
DECOR_MIN_S = 1
DECOR_MAX_S = 60
DECOR_DEFAULT_S = 6
# The decorator that goes with a logical face, for a caller that wants the extra (never required).
DECORATOR_FOR_FACE = {
    "sad": "tears",
    "dizzy": "dizzy",
    "love": "heart",
    "angry": "anger",
    "sleepy": "zzz",
    "excited": "sparkles",
    "joy": "sparkles",
}
PALETTE = ("mint", "sky", "amber", "rose", "lilac", "lime", "coral")
CLOCK_STYLES = ("digits", "ring")
LANGS = ("en", "es", "fr", "de", "pt", "it")  # screen words; the host page has the same six
BANDS = ("morning", "day", "evening", "night")
DEFAULT_HOURS = (6, 9, 18, 21)
MAX_CLOCK_IDLE_S = 3600
MAX_SHOW_CLOCK_S = 3600
MIN_LUMA = 60  # of 255: a color darker than this cannot be seen on the black screen
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_NEED = {  # firmware feature word a setting needs; a unit without it ignores the setting
    "background": "background",
    "emotion_tint": "tint",
    "captions": "captions",
    "tod": "tod",
    "tod_hours": "tod",
    "clock_style": "clock",
    "clock_idle_s": "clock",
    "clock24": "clock",
    "thinking_tone": "thinking",
    "caption_size": "packs",
}

# Plain words, English and Spanish: what went wrong, then what to do.
_MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "style": "The face style {value!r} does not exist. Choose big_eyes, eyes_only, stock, classic or minimal.",
        "bright": "That screen color is too bright for white eyes to show. Choose a darker color.",
        "caption_size": "The caption size {value!r} does not exist. Choose small, medium or large.",
        "decor": "The face extra {value!r} does not exist. Choose dizzy, heart, anger, tears, sparkles, stars or zzz.",
        "decor_seconds": "A face extra can show for 1 to 60 seconds. Type a number in that range.",
        "color": "The color {value!r} is not one I know. Choose none, a name (mint, sky, amber, rose, lilac, lime, coral) or a code like #40c0ff.",
        "dark": "That color is too dark to see on the black screen. Choose a lighter color.",
        "hours": "The day bands must be four hours from 0 to 23 that rise: morning, day, evening, night. Fix the hours and save again.",
        "lang": "The language {value!r} is not supported. Choose en, es, fr, de, pt or it.",
        "clock_style": "The clock style {value!r} does not exist. Choose digits or ring.",
        "clock_idle": "The idle time for the clock must be 0 (never) to 3600 seconds. Type a number in that range.",
        "flag": "{field} must be on or off. Turn it on or off and save again.",
        "unknown": "{field} is not a face setting. Remove it and save again.",
        "seconds": "The clock can show for 1 to 3600 seconds, or 0 to hide it. Type a number in that range.",
        "no_feature": "This unit's firmware does not have {what}. Update the unit's firmware, then try again.",
        "offline": "The unit is not connected. The setting is saved here and goes to the unit when it reconnects.",
        "refused": "The unit refused the face setting: {why}. Fix that and save again.",
        "no_unit": "No unit is selected. Choose a unit, then try again.",
        "bad_file": "The face settings file {path} could not be read. Fix or remove it; the plain face is used meanwhile.",
    },
    "es": {
        "style": "El estilo de cara {value!r} no existe. Elige big_eyes, eyes_only, stock, classic o minimal.",
        "bright": "Ese color de pantalla es demasiado claro para que se vean los ojos blancos. Elige un color mas oscuro.",
        "caption_size": "El tamano de subtitulos {value!r} no existe. Elige small, medium o large.",
        "decor": "El adorno de cara {value!r} no existe. Elige dizzy, heart, anger, tears, sparkles, stars o zzz.",
        "decor_seconds": "Un adorno de cara puede verse de 1 a 60 segundos. Escribe un numero en ese rango.",
        "color": "No conozco el color {value!r}. Elige none, un nombre (mint, sky, amber, rose, lilac, lime, coral) o un codigo como #40c0ff.",
        "dark": "Ese color es demasiado oscuro para verse en la pantalla negra. Elige un color mas claro.",
        "hours": "Las franjas del dia son cuatro horas de 0 a 23 que suben: manana, dia, tarde, noche. Corrige las horas y guarda otra vez.",
        "lang": "El idioma {value!r} no esta disponible. Elige en, es, fr, de, pt o it.",
        "clock_style": "El estilo de reloj {value!r} no existe. Elige digits o ring.",
        "clock_idle": "El tiempo de reposo del reloj va de 0 (nunca) a 3600 segundos. Escribe un numero en ese rango.",
        "flag": "{field} debe estar activado o desactivado. Cambialo y guarda otra vez.",
        "unknown": "{field} no es un ajuste de la cara. Quitalo y guarda otra vez.",
        "seconds": "El reloj puede verse de 1 a 3600 segundos, o 0 para ocultarlo. Escribe un numero en ese rango.",
        "no_feature": "El firmware de esta unidad no tiene {what}. Actualiza el firmware de la unidad y vuelve a intentarlo.",
        "offline": "La unidad no esta conectada. El ajuste se guarda aqui y llega a la unidad cuando se reconecte.",
        "refused": "La unidad rechazo el ajuste de la cara: {why}. Corrigelo y guarda otra vez.",
        "no_unit": "No hay ninguna unidad elegida. Elige una unidad y vuelve a intentarlo.",
        "bad_file": "No se pudo leer el archivo de ajustes de la cara {path}. Corrigelo o quitalo; mientras tanto se usa la cara simple.",
    },
}

_FEATURE_WORDS = {
    "en": {
        "captions": "captions",
        "tod": "time-of-day faces",
        "clock": "a clock face",
        "thinking": "the thinking cue",
        "timers": "timer countdowns",
        "config": "face settings",
        "packs": "the extra face styles and caption sizes",
        "looks": "the eyes-only and stock face styles",
        "background": "a screen color",
        "tint": "the emotion colors",
        "decor": "face extras",
        "langs6": "screen words in French, German, Portuguese and Italian",
    },
    "es": {
        "captions": "subtitulos",
        "tod": "caras segun la hora",
        "clock": "cara de reloj",
        "thinking": "la senal de pensar",
        "timers": "cuentas atras de temporizadores",
        "config": "ajustes de la cara",
        "packs": "los estilos de cara extra y los tamanos de subtitulos",
        "looks": "los estilos de cara solo ojos y original",
        "background": "un color de pantalla",
        "tint": "los colores de las emociones",
        "decor": "adornos de cara",
        "langs6": "las palabras en pantalla en frances, aleman, portugues e italiano",
    },
}


class FaceError(ValueError):
    """A rejected face setting. The message says what went wrong and what to do, in the page language."""


def _say(lang: str | None, key: str, **values: object) -> str:
    """A message in the page language; a language with no table of its own (fr, de, pt, it) reads English."""
    code = normalize(lang)
    table = _MESSAGES.get(code) or _MESSAGES["en"]
    return (table.get(key) or _MESSAGES["en"][key]).format(**values)


def _feature_word(lang: str | None, name: str) -> str:
    words = _FEATURE_WORDS.get(normalize(lang)) or _FEATURE_WORDS["en"]
    return words.get(name) or _FEATURE_WORDS["en"][name]


def luma(red: int, green: int, blue: int) -> int:
    return (red * 30 + green * 59 + blue * 11) // 100


def valid_color(value: str) -> str | None:
    """None when the color is fine, otherwise "color" (unknown) or "dark" (too dark to see)."""
    if value == "none" or value in PALETTE:
        return None
    if not _HEX.match(value):
        return "color"
    red, green, blue = (int(value[i : i + 2], 16) for i in (1, 3, 5))
    return "dark" if luma(red, green, blue) < MIN_LUMA else None


MAX_BG_LUMA = 100  # of 255: a screen color brighter than this hides the white eyes


def valid_background(value: str) -> str | None:
    """None when the screen color is fine, otherwise "color" (unknown) or "bright" (hides the white eyes)."""
    if value == "none" or value in PALETTE:
        return None
    if not _HEX.match(value):
        return "color"
    red, green, blue = (int(value[i : i + 2], 16) for i in (1, 3, 5))
    return "bright" if luma(red, green, blue) > MAX_BG_LUMA else None


@dataclass(frozen=True)
class FaceConfig:
    """One unit's face settings. The defaults are the neutral, plain face."""

    style: str = DEFAULT_STYLE
    color: str = "none"  # the eye color: none is white, a palette name, or #rrggbb
    background: str = "none"  # the screen color: none is black, a palette name (dimmed), or a dark #rrggbb
    emotion_tint: bool = True  # the eyes lean a little toward a color per emotion
    captions: bool = False
    tod: bool = False
    tod_hours: tuple[int, int, int, int] = DEFAULT_HOURS
    thinking_tone: bool = True
    lang: str = "en"
    clock24: bool = False
    clock_style: str = "digits"
    clock_idle_s: int = 0
    caption_size: str = "medium"

    def to_wire(self) -> dict[str, Any]:
        """The JSON object ``self.face.set_config`` takes (the unit's own key spelling)."""
        return to_unit_keys(self.to_json())

    def to_json(self) -> dict[str, Any]:
        """The saved and page form, with the host's key names."""
        return {
            "style": self.style,
            "color": self.color.lower(),
            "background": self.background.lower(),
            "emotion_tint": self.emotion_tint,
            "captions": self.captions,
            "tod": self.tod,
            "tod_hours": list(self.tod_hours),
            "thinking_tone": self.thinking_tone,
            "lang": self.lang,
            "clock24": self.clock24,
            "clock_style": self.clock_style,
            "clock_idle_s": self.clock_idle_s,
            "caption_size": self.caption_size,
        }


def _flag(field: str, value: object, lang: str | None) -> bool:
    if isinstance(value, bool):
        return value
    raise FaceError(_say(lang, "flag", field=field))


def clean(base: FaceConfig, values: Mapping[str, Any], lang: str | None = None) -> FaceConfig:
    """``base`` with ``values`` applied, every field checked with the firmware's own rules.

    Nothing is changed unless every field is valid (the same all-or-nothing rule the unit uses).
    ``lang`` picks the language of the error message; it defaults to the config's own language.
    """
    values = upgrade_keys(values)  # older pages and files use the old key name
    say_lang = lang or values.get("lang") or base.lang
    out = base
    for field, value in values.items():
        if field == "style":
            if value in DROPPED_STYLES:
                value = DEFAULT_STYLE  # a style that was dropped: Big eyes
            if value not in STYLES:
                raise FaceError(_say(say_lang, "style", value=value))
            out = replace(out, style=value)
        elif field == "background":
            if not isinstance(value, str):
                raise FaceError(_say(say_lang, "color", value=value))
            problem = valid_background(value if value in PALETTE or value == "none" else value.lower())
            if problem is not None:
                raise FaceError(_say(say_lang, problem, value=value))
            out = replace(out, background=value.lower())
        elif field == "color":
            if not isinstance(value, str):
                raise FaceError(_say(say_lang, "color", value=value))
            problem = valid_color(value if value in PALETTE or value == "none" else value.lower())
            if problem is not None:
                raise FaceError(_say(say_lang, problem, value=value))
            out = replace(out, color=value.lower())
        elif field in ("captions", "tod", "thinking_tone", "clock24", "emotion_tint"):
            out = replace(out, **{field: _flag(field, value, say_lang)})
        elif field == "tod_hours":
            hours = _hours(value)
            if hours is None:
                raise FaceError(_say(say_lang, "hours"))
            out = replace(out, tod_hours=hours)
        elif field == "lang":
            if value not in LANGS:
                raise FaceError(_say(say_lang, "lang", value=value))
            out = replace(out, lang=value)
        elif field == "clock_style":
            if value not in CLOCK_STYLES:
                raise FaceError(_say(say_lang, "clock_style", value=value))
            out = replace(out, clock_style=value)
        elif field == "caption_size":
            if value not in CAPTION_SIZES:
                raise FaceError(_say(say_lang, "caption_size", value=value))
            out = replace(out, caption_size=value)
        elif field == "clock_idle_s":
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= MAX_CLOCK_IDLE_S
            ):
                raise FaceError(_say(say_lang, "clock_idle"))
            out = replace(out, clock_idle_s=value)
        else:
            raise FaceError(_say(say_lang, "unknown", field=field))
    return out


def _hours(value: object) -> tuple[int, int, int, int] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    if any(isinstance(h, bool) or not isinstance(h, int) for h in value):
        return None
    morning, day, evening, night = value
    if not (0 <= morning < day < evening < night <= 23):
        return None
    return (morning, day, evening, night)


def from_stored(raw: object) -> FaceConfig:
    """A config read back from the saved file; anything unusable falls back to the plain face."""
    if not isinstance(raw, Mapping):
        return FaceConfig()
    try:
        return clean(
            FaceConfig(), {k: v for k, v in upgrade_keys(raw).items() if k in FaceConfig.__dataclass_fields__}
        )
    except FaceError:
        return FaceConfig()


def band_for_hour(config: FaceConfig, hour: int, minute: int = 0) -> str:
    """The time-of-day band at a local time (what the unit draws), "day" while the setting is off."""
    if not config.tod or not (0 <= hour <= 23 and 0 <= minute <= 59):
        return "day"
    morning, day, evening, night = config.tod_hours
    if hour >= night or hour < morning:
        return "night"
    if hour >= evening:
        return "evening"
    if hour >= day:
        return "day"
    return "morning"


def default_path() -> Path:
    return Path.home() / ".config" / "maipai" / "stackchan-faces.json"


class FaceStore:
    """Face settings per unit, kept in one small JSON file keyed by Device-Id."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path if path is not None else default_path()
        self._lock = threading.Lock()
        self._units: dict[str, FaceConfig] | None = None
        self.problem: str | None = None  # a plain line when the file could not be read

    def _load(self) -> dict[str, FaceConfig]:
        if self._units is not None:
            return self._units
        units: dict[str, FaceConfig] = {}
        try:
            raw = json.loads(self.path.read_text())
        except FileNotFoundError:
            raw = {}
        except (OSError, ValueError):
            self.problem = _say("en", "bad_file", path=self.path)
            logger.warning(self.problem)
            raw = {}
        if isinstance(raw, Mapping):
            for unit_id, stored in raw.items():
                if isinstance(unit_id, str):
                    units[unit_id] = from_stored(stored)
        self._units = units
        return units

    def get(self, unit_id: str) -> FaceConfig:
        with self._lock:
            return self._load().get(unit_id, FaceConfig())

    def known(self) -> list[str]:
        with self._lock:
            return sorted(self._load())

    def set(self, unit_id: str, config: FaceConfig) -> None:
        with self._lock:
            units = self._load()
            units[unit_id] = config
            self._write(units)

    def reset(self, unit_id: str) -> FaceConfig:
        plain = FaceConfig()
        self.set(unit_id, plain)
        return plain

    def _write(self, units: Mapping[str, FaceConfig]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({k: v.to_json() for k, v in sorted(units.items())}, indent=2) + "\n"
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".faces-")
        try:
            with os.fdopen(fd, "w") as handle:
                handle.write(payload)
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


class FaceService:
    """Sets, saves and pushes one unit's face settings.

    ``call`` is the voice server's ``call_device_tool(name, arguments, device_id=..., timeout=...)``
    and may raise ``BodyLost`` while the unit is not connected; the saved setting is then pushed
    by ``sync`` when the unit comes back.
    """

    def __init__(
        self,
        call: Callable[..., object],
        store: FaceStore | None = None,
        *,
        timeout: float = 5.0,
    ) -> None:
        self._call = call
        self.store = store if store is not None else FaceStore()
        self._timeout = timeout
        self._features: dict[str, set[str]] = {}
        self._pending: set[str] = set()
        self._lock = threading.Lock()

    # ---- reading ----

    def config(self, unit_id: str) -> FaceConfig:
        if not unit_id:
            raise FaceError(_say("en", "no_unit"))
        return self.store.get(unit_id)

    def features(self, unit_id: str) -> set[str] | None:
        """The face features the unit's firmware has, as last read back; None until known."""
        with self._lock:
            known = self._features.get(unit_id)
            return None if known is None else set(known)

    def pending(self, unit_id: str) -> bool:
        with self._lock:
            return unit_id in self._pending

    # ---- the unit's tools ----

    def _tool(self, unit_id: str, name: str, arguments: dict[str, object]) -> dict[str, Any]:
        return _reply(self._call(name, arguments, device_id=unit_id, timeout=self._timeout))

    def push(self, unit_id: str, lang: str | None = None) -> dict[str, Any]:
        """Send the saved settings to the unit. Returns {"ok": True, "pushed": bool, "message": str}.

        A unit that is not connected is not an error: the setting stays saved and goes out on ``sync``.
        """
        config = self.config(unit_id)
        say_lang = lang or config.lang
        try:
            reply = self._tool(
                unit_id, "self.face.set_config", {"config": json.dumps(config.to_wire())}
            )
        except BodyLost:
            with self._lock:
                self._pending.add(unit_id)
            return {"ok": True, "pushed": False, "message": _say(say_lang, "offline")}
        if reply.get("ok") is False:
            why = str(reply.get("error", "no reason given"))
            with self._lock:
                self._pending.add(unit_id)
            raise FaceError(_say(say_lang, "refused", why=why))
        self._remember_features(unit_id, reply)
        with self._lock:
            self._pending.discard(unit_id)
        return {"ok": True, "pushed": True, "message": ""}

    def sync(self, unit_id: str) -> dict[str, Any]:
        """Call when a unit connects or reports a reset: push what this host has saved, if it differs.

        A unit whose own settings already match is left alone (no flash write for nothing).
        """
        saved = self.config(unit_id)
        try:
            reply = self._tool(unit_id, "self.face.get_config", {})
        except BodyLost:
            return {"ok": True, "pushed": False, "message": ""}
        if reply.get("ok") is False:
            # An older firmware has no face tools: remember that so the page can say so.
            with self._lock:
                self._features[unit_id] = set()
            return {"ok": True, "pushed": False, "message": ""}
        self._remember_features(unit_id, reply)
        if _wire_equal(saved, reply):
            with self._lock:
                self._pending.discard(unit_id)
            return {"ok": True, "pushed": False, "message": ""}
        return self.push(unit_id)

    def _remember_features(self, unit_id: str, reply: Mapping[str, Any]) -> None:
        features = reply.get("features")
        if isinstance(features, list):
            with self._lock:
                self._features[unit_id] = {f for f in features if isinstance(f, str)}

    # ---- changing ----

    def update(
        self, unit_id: str, values: Mapping[str, Any], lang: str | None = None
    ) -> dict[str, Any]:
        """Check, save and push a partial change. Nothing is saved unless every field is valid."""
        before = self.config(unit_id)
        after = clean(before, values, lang)
        self.store.set(unit_id, after)
        result = self.push(unit_id, lang)
        result["config"] = after.to_json()
        result["unsupported"] = self.unsupported(unit_id, values, lang)
        return result

    def reset(self, unit_id: str, lang: str | None = None) -> dict[str, Any]:
        """Back to the plain face."""
        self.config(unit_id)
        self.store.reset(unit_id)
        result = self.push(unit_id, lang)
        result["config"] = FaceConfig().to_json()
        return result

    def unsupported(
        self, unit_id: str, values: Mapping[str, Any], lang: str | None = None
    ) -> list[str]:
        """Plain lines for each changed setting the unit's firmware does not have (empty while unknown)."""
        known = self.features(unit_id)
        if known is None:
            return []
        say_lang = normalize(lang or self.config(unit_id).lang)
        lines: list[str] = []
        for field, value in values.items():
            need = _NEED.get(field)
            if field == "style" and value in NEW_LOOK_STYLES:
                need = "looks"  # the eyes-only and stock styles are firmware patch X01
            elif field == "lang" and value not in ("en", "es"):
                need = "langs6"
            if need is not None and need not in known:
                lines.append(_say(say_lang, "no_feature", what=_feature_word(say_lang, need)))
        return lines

    # ---- the cues the host can start ----

    def show_clock(
        self, unit_id: str, seconds: int = 30, lang: str | None = None
    ) -> dict[str, Any]:
        """Show the clock face for ``seconds`` (1 to 3600), or 0 to go back to the face."""
        say_lang = lang or self.config(unit_id).lang
        if (
            isinstance(seconds, bool)
            or not isinstance(seconds, int)
            or not 0 <= seconds <= MAX_SHOW_CLOCK_S
        ):
            raise FaceError(_say(say_lang, "seconds"))
        self._require(unit_id, "clock", say_lang)
        reply = self._tool(unit_id, "self.face.show_clock", {"seconds": seconds})
        if reply.get("ok") is False:
            raise FaceError(
                _say(say_lang, "refused", why=str(reply.get("error", "no reason given")))
            )
        return {"ok": True}

    def thinking(self, unit_id: str, on: bool, lang: str | None = None) -> dict[str, Any]:
        """Start or end the thinking cue (dots and a quiet tone)."""
        say_lang = lang or self.config(unit_id).lang
        self._require(unit_id, "thinking", say_lang)
        reply = self._tool(unit_id, "self.face.thinking", {"on": bool(on)})
        if reply.get("ok") is False:
            raise FaceError(
                _say(say_lang, "refused", why=str(reply.get("error", "no reason given")))
            )
        return {"ok": True}

    def decorate(
        self,
        unit_id: str,
        name: str,
        seconds: int = DECOR_DEFAULT_S,
        lang: str | None = None,
    ) -> dict[str, Any]:
        """Draw a face extra (dizzy, heart, anger, tears, sparkles, stars, zzz) for a few seconds.

        ``name`` ``none`` ends the current one. The unit refuses it while a mute, vision-off or quiet
        look or a ringing timer shows, and says why; the refusal comes back as a ``FaceError``.
        """
        say_lang = lang or self.config(unit_id).lang
        if name != "none" and name not in DECORATORS:
            raise FaceError(_say(say_lang, "decor", value=name))
        if (
            isinstance(seconds, bool)
            or not isinstance(seconds, int)
            or not DECOR_MIN_S <= seconds <= DECOR_MAX_S
        ):
            raise FaceError(_say(say_lang, "decor_seconds"))
        self._require(unit_id, "decor", say_lang)
        reply = self._tool(unit_id, "self.face.decorate", {"name": name, "seconds": seconds})
        if reply.get("ok") is False:
            raise FaceError(
                _say(say_lang, "refused", why=str(reply.get("error", "no reason given")))
            )
        return {"ok": True}

    def extra_for_face(self, unit_id: str, logical_face: str) -> bool:
        """Best effort: draw the extra that goes with a logical face, if it has one. Never raises."""
        name = DECORATOR_FOR_FACE.get(logical_face)
        if name is None:
            return False
        try:
            self.decorate(unit_id, name)
        except (BodyLost, FaceError, OSError, TimeoutError):
            logger.debug("face extra skipped for unit %s", unit_id[-5:], exc_info=True)
            return False
        return True

    def handlers(self) -> dict[str, Callable[[dict], dict]]:
        """Hub device commands for the face extras: ``face_decorate`` and one entry per extra."""

        def run(unit_id: object, name: object, seconds: object) -> dict:
            try:
                if not isinstance(unit_id, str) or not unit_id:
                    raise FaceError(_say("en", "no_unit"))
                return self.decorate(
                    unit_id, str(name), DECOR_DEFAULT_S if seconds is None else seconds
                )  # type: ignore[arg-type]
            except FaceError as error:
                return {"ok": False, "error": str(error)}
            except BodyLost:
                return {
                    "ok": False,
                    "error": "I could not reach my body to do that. Check that it is on, then ask again.",
                }

        table: dict[str, Callable[[dict], dict]] = {
            "face_decorate": lambda p: run(p.get("unit"), p.get("name", "none"), p.get("seconds")),
            "face_decorators": lambda _p: {"ok": True, "decorators": list(DECORATORS)},
        }
        for decor in DECORATORS:
            table[f"face_{decor}"] = lambda p, decor=decor: run(
                p.get("unit"), decor, p.get("seconds")
            )
        return table

    def _require(self, unit_id: str, feature: str, lang: str) -> None:
        known = self.features(unit_id)
        if known is not None and feature not in known:
            raise FaceError(_say(lang, "no_feature", what=_feature_word(lang, feature)))


_OPTIONAL_WIRE = {  # keys older firmware does not report; the saved value being the plain one counts as equal
    "caption_size": "medium",
    "background": "none",
    "emotion_tint": True,
}


def _wire_equal(config: FaceConfig, reply: Mapping[str, Any]) -> bool:
    """Whether the unit's read-back already holds what the host saved."""
    wire = config.to_wire()
    for key, value in wire.items():
        if key not in reply:
            if key in _OPTIONAL_WIRE and value == _OPTIONAL_WIRE[key]:
                continue  # an older unit does not report it, and the saved value is the plain one
            return False
        got = reply[key]
        if key == "tod_hours":
            if list(got) != list(value):
                return False
        elif got != value:
            return False
    return True


# ---- for the settings page ----


def settings_view(service: FaceService, unit_id: str, lang: str | None = None) -> dict[str, Any]:
    """Everything the page needs to draw the face section for one unit."""
    config = service.config(unit_id)
    say_lang = normalize(lang or config.lang)
    known = service.features(unit_id)
    return {
        "unit": unit_id,
        "values": config.to_json(),
        "choices": {
            "style": list(STYLES),
            "color": ["none", *PALETTE],
            "background": ["none", *PALETTE],
            "clock_style": list(CLOCK_STYLES),
            "caption_size": list(CAPTION_SIZES),
            "decorators": list(DECORATORS),
            "lang": list(LANGS),
            "bands": list(BANDS),
        },
        "limits": {
            "clock_idle_s": [0, MAX_CLOCK_IDLE_S],
            "show_clock_s": [0, MAX_SHOW_CLOCK_S],
            "decor_s": [DECOR_MIN_S, DECOR_MAX_S],
        },
        "features": None if known is None else sorted(known),
        "unavailable": []
        if known is None
        else [
            _feature_word(say_lang, name)
            for name in ("captions", "tod", "clock", "thinking", "timers", "packs", "decor", "looks", "background", "tint")
            if name not in known
        ],
        "pending": service.pending(unit_id),
        "problem": service.store.problem,
    }


def apply_settings(
    service: FaceService, unit_id: str, values: Mapping[str, Any], lang: str | None = None
) -> dict[str, Any]:
    """The page's save button: validate, save, push. Raises ``FaceError`` with a plain message."""
    return service.update(unit_id, values, lang)


# ---- for the turn loop and the connect event ----


def offline_call(*_args: object, **_kwargs: object) -> object:
    """A ``call`` for a process with no unit link (the dashboard, the CLI): the unit counts as offline."""
    raise BodyLost("No unit is connected to this process.")


def turn_cue(service: FaceService, devices: Callable[[], list[str]], state: str) -> None:
    """Start or end the thinking cue on every connected unit as a turn moves.

    ``state`` is a turn state from the turn sink: ``thinking`` starts the cue; ``speaking`` and
    ``settle`` end it (the unit also ends it on any other emotion or after 45 s). A cue never fails
    the turn: a unit that is gone or has old firmware is skipped and logged once at debug level.
    """
    if state == "thinking":
        on = True
    elif state in {"speaking", "settle"}:
        on = False
    else:
        return
    for unit_id in devices():
        try:
            service.thinking(unit_id, on)
        except (BodyLost, FaceError, OSError, TimeoutError):
            logger.debug("thinking cue skipped for unit %s", unit_id[-5:], exc_info=True)


def sync_on_connect(service: FaceService, unit_id: str) -> None:
    """Session listener: push the saved face settings when a unit connects, never raising."""
    try:
        service.sync(unit_id)
    except Exception:
        logger.warning(
            "could not send the face settings to unit %s; they go out when it reconnects",
            unit_id[-5:],
            exc_info=True,
        )
