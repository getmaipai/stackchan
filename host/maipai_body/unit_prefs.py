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
    # Captions are OFF unless a person turns them on, except the Stock style, whose own bubble became the subtitles (unit patch FI05;
    # the unit's mp_captions_mode and settings_ui.py agree).
    "captions_mode": ("enum", ("off", "subtitles", "banner"), "off", True),
    "top_bar": ("enum", ("hidden", "always"), "hidden", True),
    # Turn toward faces (the unit's own seeker, firmware patches S10 and NX06): off, only after it is spoken to ("talk"), or also when
    # something moves while the unit is awake ("always", the default since NX06; one camera frame a second with the camera cue, at most four
    # turns a minute, never locked, carried or at night); the flash key is 13 characters.
    "turn_to_faces": ("enum", ("off", "talk", "always"), "always", True),
    # The banner row shows the heard, listening and thinking states as an icon and a word (firmware patch UI04). Off by default: the
    # sound and the light of the listening cues (listen_sound, listen_light) still signal the same states.
    "status_icons": ("bool", None, False, True),
    # The offline mumble (firmware patch SF87): a caption sentence with no voice is mumbled by the unit when this is on. Off by default.
    "mumble": ("bool", None, False, True),
}

FACE_OWNERS = ("robot", "hub", "off")  # who turns toward faces: this robot (default), the Home hub, nobody
DEFAULT_FACE_OWNER = "robot"
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


def own_owner(saved: dict[str, Any]) -> str:
    """Who turns toward faces for this unit: "robot" (default), "hub" or "off"."""
    owner = saved.get("face_owner", DEFAULT_FACE_OWNER)
    return owner if owner in FACE_OWNERS else DEFAULT_FACE_OWNER


def effective_turn_to_faces(saved: dict[str, Any]) -> str:
    """The value the unit gets, first match wins (firmware patch NX06):

    1. "Who turns toward faces: off" switches the unit's seeker off whatever was chosen (the choice itself is kept and comes back when the
       owner is set to the robot again);
    2. a person's own "off" stays off;
    3. the "Look for faces" switch, once a person has used it: on is "always" (it also searches when something moves), off is "talk"
       (only after the wake word);
    4. the person's own choice, else the default, "always"."""
    if own_owner(saved) == "off":
        return "off"
    value = saved.get("turn_to_faces", DEFAULTS["turn_to_faces"])
    if value not in PREFS["turn_to_faces"][1]:
        value = DEFAULTS["turn_to_faces"]
    if value == "off":
        return "off"
    look = saved.get("look_faces")
    if isinstance(look, bool):
        return "always" if look else "talk"
    return value


def prefs_of(saved: dict[str, Any]) -> dict[str, Any]:
    """Every pref with its saved value or its default."""
    saved = upgrade_keys(saved)
    return {k: saved.get(k, d) for k, d in DEFAULTS.items()}


class PrefsService:
    def __init__(self, probe: ToolProbe, get: Callable[[str], dict[str, Any]], put: Callable[[str, dict[str, Any]], dict[str, Any]]) -> None:
        self.probe, self._get, self._put = probe, get, put
        self.after_save: Callable[[str, dict[str, Any]], None] | None = None  # set by Polish: a setting that decides a pack changed

    def view(self, device_id: str, lang: str | None = None) -> dict[str, Any]:
        values = prefs_of(self._get(device_id))
        ready = self.probe.has(device_id, "prefs")
        all_off = values["listen_sound"] == "off" and values["listen_light"] == "off" and not values["listen_face"]
        return {
            "values": values,
            "saved": sorted(upgrade_keys(self._get(device_id))),  # keys a person chose (the page shows the Stock captions default for the rest)
            "unit_keys": list(UNIT_KEYS),
            "unit_ready": ready is True,
            "reachable": ready is not None,
            "features": {
                "overlay": self.probe.has(device_id, "overlay") is True,
                "pack": self.probe.has(device_id, "pack") is True,
                "filler": self.probe.has(device_id, "filler") is True,
                "prefs": ready is True,
                "look": self.probe.has(device_id, "look") is True,
            },
            "face_owner": own_owner(self._get(device_id)),
            "look": self.look_status(device_id) if callable(getattr(self, "look_status", None)) else {},  # set by _wire_look_owner
            "notice": say(lang, "all_off") if all_off else "",
        }

    def save(self, device_id: str, values: dict[str, Any], lang: str | None = None) -> dict[str, Any]:
        merged = self._put(device_id, values)
        if self.after_save is not None:
            try:
                self.after_save(device_id, dict(upgrade_keys(values)))
            except Exception:
                logger.debug("pack follow-up after a settings save failed", exc_info=True)
        mine = [k for k in UNIT_KEYS if k in upgrade_keys(values)]
        if "look_faces" in values and "turn_to_faces" not in mine:
            mine.append("turn_to_faces")  # the "Look for faces" switch is the unit's seeker mode too (effective_turn_to_faces)
        if not mine:
            return {"ok": True, "pushed": None, "message": ""}
        return self._send(device_id, merged, lang, mine)

    def _send(self, device_id: str, saved: dict[str, Any], lang: str | None, keys: list[str] | None = None) -> dict[str, Any]:
        """Send the unit's keys a person has chosen (``keys``, or every unit key saved so far), never a default.

        A key the person never touched is left off the call: the unit keeps its own default for it (the speech bubble
        follows the Stock style until a person chooses), so sending the host's default would overwrite that choice."""
        saved = upgrade_keys(saved)
        if keys is not None and "turn_to_faces" in keys and "turn_to_faces" not in saved:
            saved = {**saved, "turn_to_faces": effective_turn_to_faces(saved)}  # a switch decides it, the person never chose the mode itself
        chosen = [k for k in (upgrade_keys(dict.fromkeys(keys)) if keys is not None else UNIT_KEYS) if k in saved]
        if own_owner(saved) == "off" and "turn_to_faces" not in chosen and keys is None:
            chosen.append("turn_to_faces")  # the unit must hear "off" even when the person never chose a value
        if "turn_to_faces" in chosen:
            saved = {**saved, "turn_to_faces": effective_turn_to_faces(saved)}
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

    def resend_look(self, device_id: str, lang: str | None = None) -> dict[str, Any]:
        """The owner of face seeking changed: send the unit the value it is due now (off, or the person's choice again)."""
        saved = self._get(device_id)
        return self._send(device_id, {**saved, "turn_to_faces": saved.get("turn_to_faces", DEFAULTS["turn_to_faces"])}, lang, ["turn_to_faces"])

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
