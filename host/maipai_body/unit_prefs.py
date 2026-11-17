# ruff: noqa: E501
"""The newer per-unit choices: emotion faces, overlays, the listening cues, "While it thinks", look effects.

One table says every key, its allowed values, its default, and whether the unit applies it itself. The page
saves them in the host's own unit settings now (the host half works at once: tags, fillers, overlays); the keys
the *unit* applies are also sent in one tool call when the unit has it, and the page says "coming with the next
unit update" while it does not:

    self.prefs.get  {}                       -> {"ok": true, ...}   (also the probe)
    self.prefs.set  {"json": "{...}"}        -> {"ok": true}        (only the unit's keys, JSON text)
    self.listen.test {}                      -> {"ok": true}        (plays the enabled listening cues)
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any

from maipai_body.hal.errors import BodyLost
from maipai_body.spelling_aliases import to_unit_keys, upgrade_keys
from maipai_body.unit_tools import ToolProbe, dumps, is_unknown_tool, unwrap

logger = logging.getLogger("maipai_body.unit_prefs")

_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")

# key: (kind, allowed or range, default, applied by the unit)
PREFS: dict[str, tuple[str, Any, Any, bool]] = {
    "emotion_faces": ("bool", None, True, False),
    "overlays_enabled": ("bool", None, True, False),
    "filler_mode": ("enum", ("none", "tone", "phrase"), "tone", False),
    "filler_wait_s": ("float", (0.2, 1.5), 0.4, False),
    "listen_sound": ("enum", ("off", "chime", "mm"), "chime", True),
    "listen_light": ("enum", ("off", "dim", "normal"), "normal", True),
    "listen_light_color": ("color", None, "#40c0ff", True),
    "listen_face": ("bool", None, True, True),
    "fx_crt": ("bool", None, False, True),
    "fx_color_mode": ("enum", ("normal", "mono", "warm", "cool"), "normal", True),
    "fx_night_dim": ("bool", None, False, True),
    "fx_glow": ("bool", None, False, True),
    "speech_bubble": ("bool", None, False, True),
    "thinking_dots": ("bool", None, True, True),
}
UNIT_KEYS = tuple(k for k, spec in PREFS.items() if spec[3])
DEFAULTS: dict[str, Any] = {k: spec[2] for k, spec in PREFS.items()}

SAY: dict[str, tuple[str, str]] = {
    "soon": (
        "Saved. This unit gets the setting with its next update; nothing was sent yet.",
        "Guardado. Esta unidad recibe el ajuste con su próxima actualización; todavía no se envió nada.",
    ),
    "sent": ("Saved and sent to the unit.", "Guardado y enviado a la unidad."),
    "kept": (
        "Saved. The unit is not connected; it gets the setting when it connects.",
        "Guardado. La unidad no está conectada; recibe el ajuste cuando se conecte.",
    ),
    "test_soon": (
        "The listening test comes with the next unit update.",
        "La prueba de escucha llega con la próxima actualización de la unidad.",
    ),
    "test_ok": ("The unit played its listening cues.", "La unidad reprodujo sus señales de escucha."),
    "offline": (
        "The unit is not connected. Turn it on and try again.",
        "La unidad no está conectada. Enciéndela e inténtalo de nuevo.",
    ),
    "all_off": (
        "All three listening cues are off. People near the robot will not see or hear when it listens.",
        "Las tres señales de escucha están apagadas. Quien esté cerca del robot no verá ni oirá cuándo escucha.",
    ),
}


def say(lang: str | None, code: str) -> str:
    english, spanish = SAY[code]
    return spanish if (lang or "").lower().startswith("es") else english


def clean(values: dict[str, Any], error: type[Exception]) -> dict[str, Any]:
    """The known keys of ``values`` checked and normalized; ``error`` is raised with a plain message."""
    out: dict[str, Any] = {}
    for key, value in upgrade_keys(values).items():  # an older page or file may send the old spelling
        spec = PREFS.get(key)
        if spec is None:
            continue
        kind, allowed, _default, _unit = spec
        label = key.replace("_", " ")
        if kind == "bool":
            if not isinstance(value, bool):
                raise error(f"{label} must be on or off. Choose on or off and save again.")
        elif kind == "enum":
            if value not in allowed:
                raise error(f"{label} must be one of {', '.join(allowed)}. Pick one and save again.")
        elif kind == "float":
            low, high = allowed
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
                raise error(f"{label} must be a number from {low} to {high}. Pick a number in that range.")
            value = round(float(value), 2)
        elif kind == "color":
            if not (isinstance(value, str) and _COLOR.match(value)):
                raise error("The light color must be a code like #40c0ff. Pick a color and save again.")
            value = value.lower()
        out[key] = value
    return out


def prefs_of(saved: dict[str, Any]) -> dict[str, Any]:
    """Every pref with its saved value or its default."""
    saved = upgrade_keys(saved)
    return {k: saved.get(k, d) for k, d in DEFAULTS.items()}


class PrefsService:
    def __init__(self, probe: ToolProbe, get: Callable[[str], dict[str, Any]], put: Callable[[str, dict[str, Any]], dict[str, Any]]) -> None:
        self.probe, self._get, self._put = probe, get, put

    def view(self, device_id: str, lang: str | None = None) -> dict[str, Any]:
        values = prefs_of(self._get(device_id))
        ready = self.probe.has(device_id, "prefs")
        all_off = values["listen_sound"] == "off" and values["listen_light"] == "off" and not values["listen_face"]
        return {
            "values": values,
            "unit_keys": list(UNIT_KEYS),
            "unit_ready": ready is True,
            "reachable": ready is not None,
            "features": {
                "overlay": self.probe.has(device_id, "overlay") is True,
                "pack": self.probe.has(device_id, "pack") is True,
                "filler": self.probe.has(device_id, "filler") is True,
                "prefs": ready is True,
            },
            "notice": say(lang, "all_off") if all_off else "",
        }

    def save(self, device_id: str, values: dict[str, Any], lang: str | None = None) -> dict[str, Any]:
        merged = self._put(device_id, values)
        mine = [k for k in UNIT_KEYS if k in upgrade_keys(values)]
        if not mine:
            return {"ok": True, "pushed": None, "message": ""}
        return self._send(device_id, merged, lang, mine)

    def _send(self, device_id: str, saved: dict[str, Any], lang: str | None, keys: list[str] | None = None) -> dict[str, Any]:
        """Send the unit's keys a person has chosen (``keys``, or every unit key saved so far), never a default.

        A key the person never touched is left off the call: the unit keeps its own default for it (the speech bubble
        follows the Stock style until a person chooses), so sending the host's default would overwrite that choice."""
        saved = upgrade_keys(saved)
        chosen = [k for k in (upgrade_keys(dict.fromkeys(keys)) if keys is not None else UNIT_KEYS) if k in saved]
        if not chosen:
            return {"ok": True, "pushed": None, "message": ""}
        have = self.probe.has(device_id, "prefs")
        if have is None:
            return {"ok": True, "pushed": False, "pending": False, "message": say(lang, "kept")}
        if have is False:
            return {"ok": True, "pushed": False, "pending": True, "message": say(lang, "soon")}
        payload = to_unit_keys({k: saved[k] for k in chosen})  # the unit's own key spelling
        try:
            reply = unwrap(self.probe.call(device_id, "self.prefs.set", {"json": dumps(payload)}))
        except (BodyLost, OSError, TimeoutError):
            return {"ok": True, "pushed": False, "pending": False, "message": say(lang, "kept")}
        if reply.get("ok") is not True:
            return {"ok": True, "pushed": False, "pending": is_unknown_tool(reply), "message": say(lang, "soon")}
        return {"ok": True, "pushed": True, "pending": False, "message": say(lang, "sent")}

    def test_listen(self, device_id: str, lang: str | None = None) -> dict[str, Any]:
        try:
            reply = unwrap(self.probe.call(device_id, "self.listen.test", {}))
        except (BodyLost, OSError, TimeoutError):
            return {"ok": False, "message": say(lang, "offline")}
        if is_unknown_tool(reply):
            return {"ok": False, "pending": True, "message": say(lang, "test_soon")}
        return {"ok": reply.get("ok") is True, "message": say(lang, "test_ok")}

    def sync(self, device_id: str) -> None:
        """When a unit connects: ask afresh which tools it has, then send its keys if it can take them."""
        self.probe.forget(device_id)
        try:
            self._send(device_id, self._get(device_id), None)
        except Exception:
            logger.debug("unit preferences not sent to %s", device_id[-5:], exc_info=True)
