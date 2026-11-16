# ruff: noqa: E501
"""The everyday device controls on the settings page: volume, brightness, light ring, mute, head idle motion,
battery, the home overview and the two-step reset. Each one goes to the unit through a tool the firmware already
has; the host keeps the last value it set so the page can show it again (the unit has no read-back for these).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

from maipai_body.hal.errors import BodyLost
from maipai_body.i18n import normalize
from maipai_body.unit_extras import ExtrasError, _reply, say

LED_MAX = 168  # the ring's own limit per channel (self.robot.set_led_color)
RESET_WORD = "RESET"

_WORDS: dict[str, dict[str, str]] = {
    "en": {
        "bad_value": "{field} is not a value the unit accepts. Move the control back into its range and try again.",
        "reset_word": "To reset the unit, type the word RESET in the box first. A reset erases the unit's saved Wi-Fi and settings.",
        "no_reset": "This unit's firmware has no reset command yet. Update the unit's firmware, or reset it over USB.",
        "reset_done": "The unit is resetting. It restarts, then needs its Wi-Fi set up again.",
    },
    "es": {
        "bad_value": "{field} no es un valor que acepte la unidad. Devuelve el control a su rango y vuelve a intentarlo.",
        "reset_word": "Para reiniciar la unidad de fabrica, escribe primero la palabra RESET en el cuadro. Un reinicio borra el Wi-Fi y los ajustes guardados de la unidad.",
        "no_reset": "El firmware de esta unidad aun no tiene el comando de reinicio. Actualiza el firmware o reinicia la unidad por USB.",
        "reset_done": "La unidad se esta reiniciando. Despues hay que volver a configurar su Wi-Fi.",
    },
}


def _words(lang: str | None, key: str, **values: object) -> str:
    table = _WORDS.get(normalize(lang)) or _WORDS["en"]
    return (table.get(key) or _WORDS["en"][key]).format(**values)


def hex_to_rgb(colour: str) -> tuple[int, int, int]:
    """``#40c0ff`` as three ring channels, scaled from 255 down to the ring's own 168."""
    raw = [int(colour[i : i + 2], 16) for i in (1, 3, 5)]
    return (raw[0] * LED_MAX // 255, raw[1] * LED_MAX // 255, raw[2] * LED_MAX // 255)


class UnitDevice:
    def __init__(self, call: Callable[..., object], *, timeout: float = 4.0) -> None:
        self._call, self._timeout = call, timeout

    def _tool(self, unit_id: str, name: str, arguments: dict[str, object]) -> dict[str, Any]:
        return _reply(self._call(name, arguments, device_id=unit_id, timeout=self._timeout))

    def _check(self, reply: Mapping[str, Any], lang: str | None) -> None:
        if reply.get("ok") is False:
            why = str(reply.get("error", "no reason given"))
            if "nknown tool" in why:
                raise ExtrasError(say(lang, "old_firmware", what="this control"))
            raise ExtrasError(say(lang, "refused", why=why))

    def overview(self, unit_id: str, lang: str | None = None) -> dict[str, Any]:
        """What the home page shows: battery, privacy switches and room light, each None when the unit cannot say."""
        out: dict[str, Any] = {"ok": True, "reachable": True, "battery": None, "privacy": None, "light": None}
        try:
            battery = self._tool(unit_id, "self.battery.get_status", {})
            if battery.get("ok") is not False and "percent" in battery:
                out["battery"] = {"percent": battery.get("percent"), "charging": bool(battery.get("charging"))}
            privacy = self._tool(unit_id, "self.privacy.get", {})
            if "muted" in privacy:
                out["privacy"] = {
                    "mute": bool(privacy.get("muted")),
                    "vision_off": bool(privacy.get("vision_off", privacy.get("vision"))),
                    "quiet": bool(privacy.get("quiet")),
                }
            light = self._tool(unit_id, "self.screen.get_ambient_light", {})
            lux = light.get("lux", light.get("value"))
            if isinstance(lux, (int, float)) and not isinstance(lux, bool):
                out["light"] = lux
        except BodyLost:
            out["reachable"] = False
        return out

    def set_volume(self, unit_id: str, value: object, lang: str | None = None) -> dict[str, Any]:
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
            raise ExtrasError(_words(lang, "bad_value", field="Volume"))
        return self._send(unit_id, "self.audio_speaker.set_volume", {"volume": value}, lang)

    def set_brightness(self, unit_id: str, value: object, lang: str | None = None) -> dict[str, Any]:
        if isinstance(value, bool) or not isinstance(value, int) or not 10 <= value <= 100:
            raise ExtrasError(_words(lang, "bad_value", field="Brightness"))
        return self._send(unit_id, "self.screen.set_brightness", {"brightness": value}, lang)

    def set_idle_motion(self, unit_id: str, value: object, lang: str | None = None) -> dict[str, Any]:
        if not isinstance(value, bool):
            raise ExtrasError(_words(lang, "bad_value", field="Idle motion"))
        return self._send(unit_id, "self.robot.set_idle_motion", {"enabled": value}, lang)

    def set_led(self, unit_id: str, colour: object, lang: str | None = None) -> dict[str, Any]:
        if colour == "off":
            red = green = blue = 0
        elif isinstance(colour, str) and len(colour) == 7 and colour.startswith("#"):
            try:
                red, green, blue = hex_to_rgb(colour)
            except ValueError:
                raise ExtrasError(_words(lang, "bad_value", field="Colour")) from None
        else:
            raise ExtrasError(_words(lang, "bad_value", field="Colour"))
        return self._send(unit_id, "self.robot.set_led_color", {"red": red, "green": green, "blue": blue}, lang)

    def set_privacy(self, unit_id: str, name: str, value: object, lang: str | None = None) -> dict[str, Any]:
        if name not in {"mute", "vision_off", "quiet"} or not isinstance(value, bool):
            raise ExtrasError(_words(lang, "bad_value", field=name))
        return self._send(unit_id, "self.privacy.set", {name: 1 if value else 0}, lang)

    def reset(self, unit_id: str, confirm: object, lang: str | None = None) -> dict[str, Any]:
        """Factory reset. Two steps: the page shows the warning, and the person types the word."""
        if confirm != RESET_WORD:
            raise ExtrasError(_words(lang, "reset_word"))
        try:
            reply = self._tool(unit_id, "self.system.reset", {"confirm": RESET_WORD})
        except BodyLost:
            raise ExtrasError(say(lang, "unreachable")) from None
        if reply.get("ok") is False:
            raise ExtrasError(_words(lang, "no_reset"))
        return {"ok": True, "message": _words(lang, "reset_done")}

    def _send(self, unit_id: str, name: str, arguments: dict[str, object], lang: str | None) -> dict[str, Any]:
        """Send one setting. A unit that is off is not an error: the choice is saved and the page says so."""
        try:
            reply = self._tool(unit_id, name, arguments)
        except BodyLost:
            return {"ok": True, "pushed": False, "message": say(lang, "offline")}
        self._check(reply, lang)
        return {"ok": True, "pushed": True, "message": ""}


def encode(value: object) -> bytes:
    return json.dumps(value).encode()
