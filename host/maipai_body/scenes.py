# ruff: noqa: E501
"""Scenes: one named preset that sets the whole look (docs/design/llm-display-control-2026-11-17.md section 8.6a).

A scene is a row of this table: an optional mood, an optional effect (with its strength), an optional ring color, an optional
quiet sound and a hold time. It is a source's request (the model's ``[scene rainy_day]`` tag, a Home event, the owner's Test
button), never a guess from words. :meth:`SceneBook.expand` turns it into the ordinary catalog commands (``face.mood``,
``fx.set``, ``light.look``, ``sound.play``) and the command bus (command_bus.py) checks each one as if it had been sent alone:
permission, gates, priority and the model's limits. A scene row has no field for a body move, a photo or a privacy change, and
saving a row rejects any other key, so a scene can never carry one.

The names are in :mod:`maipai_body.reply_tags` (``SCENE_NAMES``); the values are here, once. The owner may change a scene's values
for one unit on the settings page; the choice is saved in that unit's settings under ``scenes`` and an untouched scene keeps
the shipped values.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from maipai_body import reply_tags

FIELDS: tuple[str, ...] = ("mood", "fx", "level", "light", "sound", "hold_s")
HOLD_RANGE = (3, 120)
SETTINGS_KEY = "scenes"

# name: mood, effect, effect strength, ring color, sound, hold seconds. "" means "none of that". The ring colors are the closed palette
# of the seam (no red); the sounds are the quiet ones.
DEFAULT_SCENES: dict[str, dict[str, Any]] = {
    "rainy_day": {"mood": "neutral", "fx": "rain", "level": "normal", "light": "blue", "sound": "", "hold_s": 20},
    "snowy_day": {"mood": "neutral", "fx": "snow", "level": "normal", "light": "cyan", "sound": "", "hold_s": 20},
    "sunny_day": {"mood": "happy", "fx": "sun", "level": "normal", "light": "amber", "sound": "", "hold_s": 20},
    "bedtime": {"mood": "sleepy", "fx": "stars", "level": "light", "light": "amber", "sound": "", "hold_s": 20},
    "party": {"mood": "happy", "fx": "disco", "level": "normal", "light": "magenta", "sound": "popup", "hold_s": 20},
    "birthday": {"mood": "happy", "fx": "balloons", "level": "normal", "light": "magenta", "sound": "success", "hold_s": 20},
    "cozy": {"mood": "love", "fx": "hearts", "level": "light", "light": "amber", "sound": "", "hold_s": 20},
    "spooky": {"mood": "surprised", "fx": "fog", "level": "normal", "light": "magenta", "sound": "", "hold_s": 20},
    "focus": {"mood": "neutral", "fx": "", "level": "normal", "light": "cyan", "sound": "", "hold_s": 20},
    "celebrate": {"mood": "happy", "fx": "celebrate", "level": "normal", "light": "white", "sound": "success", "hold_s": 20},
}

SAY: dict[str, tuple[str, str]] = {
    "unknown": (
        "That scene is not known. Choose one of: {names}.",
        "No conozco esa escena. Elige una de: {names}.",
    ),
    "bad_field": (
        "A scene can only set: {names}. Remove the other fields and try again.",
        "Una escena solo puede ajustar: {names}. Quita los demás campos e inténtalo de nuevo.",
    ),
    "bad_value": (
        "{field} cannot be {value}. Choose one of: {names}.",
        "{field} no puede ser {value}. Elige uno de: {names}.",
    ),
    "hold": (
        "The hold time must be from {low} to {high} seconds. Choose a number in that range.",
        "El tiempo debe ser de {low} a {high} segundos. Elige un número en ese rango.",
    ),
}


class SceneError(ValueError):
    pass


def say(lang: str | None, code: str, **values: object) -> str:
    english, spanish = SAY[code]
    return (spanish if (lang or "").lower().startswith("es") else english).format(**values)


def options() -> dict[str, list[str]]:
    """What each field may be (the settings page builds its choices from this, so the page cannot drift)."""
    return {
        "mood": ["", *reply_tags.MOODS],
        "fx": ["", *reply_tags.OVERLAYS],
        "level": list(reply_tags.INTENSITIES),
        "light": ["", *reply_tags.LIGHT_COLORS],
        "sound": ["", *reply_tags.MODEL_SOUNDS],
    }


def clean_row(row: object, lang: str | None = None) -> dict[str, Any]:
    """A scene row checked against the lists. Raises :class:`SceneError` with a plain message; never returns a partial row."""
    if not isinstance(row, dict):
        raise SceneError(say(lang, "bad_field", names=", ".join(FIELDS)))
    extra = [k for k in row if k not in FIELDS]
    if extra:
        raise SceneError(say(lang, "bad_field", names=", ".join(FIELDS)))
    out: dict[str, Any] = {}
    choices = options()
    for field in FIELDS:
        if field == "hold_s":
            value = row.get(field, 20)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not HOLD_RANGE[0] <= value <= HOLD_RANGE[1]:
                raise SceneError(say(lang, "hold", low=HOLD_RANGE[0], high=HOLD_RANGE[1]))
            out[field] = int(round(value))
            continue
        value = row.get(field, reply_tags.DEFAULT_INTENSITY if field == "level" else "")
        if value not in choices[field]:
            raise SceneError(say(lang, "bad_value", field=field, value=repr(value), names=", ".join(c or "none" for c in choices[field])))
        out[field] = value
    return out


class SceneBook:
    """The scene table for each unit: the shipped rows with the unit's own changes on top. ``get`` and ``put`` are the unit store's."""

    def __init__(
        self,
        get: Callable[[str], dict[str, Any]],
        put: Callable[[str, dict[str, Any]], dict[str, Any]],
    ) -> None:
        self._get, self._put = get, put

    def table(self, device_id: str) -> dict[str, dict[str, Any]]:
        """Every scene's row (shipped, or the unit's own when it has one that still checks out)."""
        saved = self._get(device_id).get(SETTINGS_KEY)
        saved = saved if isinstance(saved, dict) else {}
        table: dict[str, dict[str, Any]] = {}
        for name in reply_tags.SCENE_NAMES:
            row = dict(DEFAULT_SCENES[name])
            if name in saved:
                try:
                    row = clean_row(saved[name])
                except SceneError:
                    pass  # a damaged saved row never breaks a reply: the shipped row is used
            table[name] = row
        return table

    def row(self, device_id: str, name: str) -> dict[str, Any] | None:
        return self.table(device_id).get(name)

    def view(self, device_id: str) -> dict[str, Any]:
        saved = self._get(device_id).get(SETTINGS_KEY)
        saved = saved if isinstance(saved, dict) else {}
        table = self.table(device_id)
        return {
            "scenes": [{"name": n, **row, "changed": row != DEFAULT_SCENES[n]} for n, row in table.items()],
            "defaults": {n: dict(r) for n, r in DEFAULT_SCENES.items()},
            "options": options(),
            "hold": list(HOLD_RANGE),
            "saved": sorted(n for n in saved if n in reply_tags.SCENE_NAMES),
        }

    def save(self, device_id: str, name: object, row: object, lang: str | None = None) -> dict[str, Any]:
        if name not in reply_tags.SCENE_NAMES:
            raise SceneError(say(lang, "unknown", names=", ".join(reply_tags.SCENE_NAMES)))
        clean = clean_row(row, lang)
        saved = self._get(device_id).get(SETTINGS_KEY)
        saved = dict(saved) if isinstance(saved, dict) else {}
        saved[str(name)] = clean
        self._put(device_id, {SETTINGS_KEY: saved})
        return {"ok": True, **self.view(device_id)}

    def reset(self, device_id: str, name: object, lang: str | None = None) -> dict[str, Any]:
        if name not in reply_tags.SCENE_NAMES:
            raise SceneError(say(lang, "unknown", names=", ".join(reply_tags.SCENE_NAMES)))
        saved = self._get(device_id).get(SETTINGS_KEY)
        saved = dict(saved) if isinstance(saved, dict) else {}
        saved.pop(str(name), None)
        self._put(device_id, {SETTINGS_KEY: saved})
        return {"ok": True, **self.view(device_id)}

    def expand(self, device_id: str, name: str) -> list[tuple[str, dict[str, Any]]]:
        """The catalog commands a scene stands for, as (command, arguments). Empty for an unknown name."""
        row = self.row(device_id, name)
        if row is None:
            return []
        parts: list[tuple[str, dict[str, Any]]] = []
        if row["mood"]:
            parts.append(("face.mood", {"mood": row["mood"]}))
        if row["fx"]:
            parts.append(("fx.set", {"name": row["fx"], "intensity": row["level"], "seconds": row["hold_s"]}))
        if row["light"]:
            parts.append(("light.look", {"color": row["light"], "seconds": row["hold_s"]}))
        if row["sound"]:
            parts.append(("sound.play", {"name": row["sound"]}))
        return parts

    def expand_off(self) -> list[tuple[str, dict[str, Any]]]:
        """``[scene off]``: the effect and the ring color end (a sound already played cannot be taken back, and the face keeps its mood)."""
        return [("fx.clear", {}), ("light.look", {"color": reply_tags.LIGHT_OFF})]
