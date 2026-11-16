# ruff: noqa: E501
"""The Remote page: things you ask the selected unit to do right now.

Each action uses a tool the firmware already has. A unit that is off is not an error to hide: the page says so
in plain words. Timed actions (flash, look around, find my robot) run on the host and always leave the unit
centred with the lights off.
"""

from __future__ import annotations

import base64
import threading
import time
from collections.abc import Callable, Mapping
from typing import Any

from maipai_body.bodies.stackchan.games import GAMES
from maipai_body.bodies.stackchan.profile import (
    CENTRE_PITCH_DEG,
    HEAD_PITCH_MAX_DEG,
    HEAD_YAW_LIMIT_DEG,
)
from maipai_body.bodies.stackchan.sounds import EARCONS
from maipai_body.hal.errors import BodyLost
from maipai_body.i18n import normalize
from maipai_body.unit_extras import ExtrasError, _reply, say

LED_MAX = 168
FIND_SECONDS = 90
BUILTIN_DANCES = ("happy", "robot", "panic", "look_around", "sway", "nod_yes", "shake_no", "wiggle", "bow", "groove")
MAX_SAY = 200

_WORDS = {
    "en": {
        "bad_head": "The head can turn left and right up to {yaw} degrees and up and down from {low} to {high} degrees. Move the pad back inside that range.",
        "bad_text": "Type something to say, up to {max} characters, then press Speak.",
        "bad_dance": "That dance is not on the unit's list. Pick one from the list.",
        "bad_game": "That game is not on the unit's list. Pick one from the list.",
        "bad_sound": "That sound is not one the unit has. Pick a sound from the list.",
        "no_camera": "This unit has no camera tool yet. It needs the camera build.",
        "muted": "The unit is muted or in full quiet, so it cannot make a sound. Unmute it first.",
    },
    "es": {
        "bad_head": "La cabeza gira a izquierda y derecha hasta {yaw} grados y arriba y abajo de {low} a {high} grados. Vuelve a poner el panel dentro de ese rango.",
        "bad_text": "Escribe algo para decir, hasta {max} caracteres, y pulsa Hablar.",
        "bad_dance": "Ese baile no esta en la lista de la unidad. Elige uno de la lista.",
        "bad_game": "Ese juego no esta en la lista de la unidad. Elige uno de la lista.",
        "bad_sound": "Ese sonido no lo tiene la unidad. Elige un sonido de la lista.",
        "no_camera": "Esta unidad aun no tiene la herramienta de camara. Necesita la version con camara.",
        "muted": "La unidad esta silenciada o en silencio total, asi que no puede sonar. Quitale el silencio primero.",
    },
}


def _w(lang: str | None, key: str, **values: object) -> str:
    table = _WORDS.get(normalize(lang)) or _WORDS["en"]
    return (table.get(key) or _WORDS["en"][key]).format(**values)


class UnitRemote:
    def __init__(
        self,
        call: Callable[..., object],
        *,
        photo: Callable[[str], bytes | None] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        timeout: float = 4.0,
    ) -> None:
        self._call, self._photo, self._sleep, self._timeout = call, photo, sleep, timeout
        self._finders: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    # ---- plumbing ----

    def _tool(self, unit_id: str, name: str, arguments: dict[str, object]) -> dict[str, Any]:
        return _reply(self._call(name, arguments, device_id=unit_id, timeout=self._timeout))

    def _do(self, unit_id: str, name: str, arguments: dict[str, object], lang: str | None, what: str) -> dict[str, Any]:
        try:
            reply = self._tool(unit_id, name, arguments)
        except BodyLost:
            raise ExtrasError(say(lang, "unreachable")) from None
        if reply.get("ok") is False:
            why = str(reply.get("error", "no reason given"))
            if "nknown tool" in why:
                raise ExtrasError(say(lang, "old_firmware", what=what))
            raise ExtrasError(say(lang, "refused", why=why))
        return reply

    def _led(self, unit_id: str, rgb: tuple[int, int, int], lang: str | None) -> None:
        self._do(unit_id, "self.robot.set_led_color", {"red": rgb[0], "green": rgb[1], "blue": rgb[2]}, lang, "the light ring")

    def _head(self, unit_id: str, yaw: float, pitch: float, lang: str | None, speed: int = 120) -> None:
        self._do(unit_id, "self.robot.set_head_angles", {"yaw": yaw, "pitch": pitch, "speed": speed}, lang, "head movement")

    def _safe(self, unit_id: str, fn: Callable[[], None]) -> None:
        try:
            fn()
        except (ExtrasError, BodyLost):
            pass

    # ---- what the page needs to draw ----

    def view(self, unit_id: str, lang: str | None = None) -> dict[str, Any]:
        dances: list[dict[str, Any]] = []
        reachable = True
        try:
            reply = self._tool(unit_id, "self.robot.dance_list", {})
            raw = reply.get("dances") or reply.get("list") or []
            for item in raw if isinstance(raw, list) else []:
                if isinstance(item, str):
                    dances.append({"name": item})
                elif isinstance(item, Mapping) and isinstance(item.get("name"), str):
                    dances.append({"name": item["name"], "seconds": item.get("seconds", item.get("length"))})
        except BodyLost:
            reachable = False
        if reachable and not dances:
            dances = [{"name": n} for n in BUILTIN_DANCES[:4]]
        return {
            "ok": True,
            "reachable": reachable,
            "dances": dances,
            "games": [{"id": g.id, "title": g.title.get(normalize(lang)) or g.title["en"]} for g in GAMES],
            "sounds": list(EARCONS),
            "photo": self._photo is not None,
            "finding": unit_id in self._finders and not self._finders[unit_id].is_set(),
            "limits": {"yaw": HEAD_YAW_LIMIT_DEG, "pitch": [CENTRE_PITCH_DEG, HEAD_PITCH_MAX_DEG]},
        }

    # ---- actions ----

    def beep(self, unit_id: str, sound: object = "success", lang: str | None = None) -> dict[str, Any]:
        if sound not in EARCONS:
            raise ExtrasError(_w(lang, "bad_sound"))
        reply = self._do(unit_id, "self.audio.play_sound", {"sound": sound}, lang, "sounds")
        if reply.get("played") is False or reply.get("muted") is True:
            raise ExtrasError(_w(lang, "muted"))
        return {"ok": True}

    def flash(self, unit_id: str, colour: object = None, lang: str | None = None) -> dict[str, Any]:
        rgb = (0, 126, 168)
        if isinstance(colour, str) and len(colour) == 7 and colour.startswith("#"):
            try:
                rgb = tuple(int(colour[i : i + 2], 16) * LED_MAX // 255 for i in (1, 3, 5))  # type: ignore[assignment]
            except ValueError:
                pass
        try:
            for _ in range(3):
                self._led(unit_id, rgb, lang)
                self._sleep(0.25)
                self._led(unit_id, (0, 0, 0), lang)
                self._sleep(0.2)
        finally:
            self._safe(unit_id, lambda: self._led(unit_id, (0, 0, 0), lang))
        return {"ok": True}

    def say(self, unit_id: str, text: object, lang: str | None = None) -> dict[str, Any]:
        if not isinstance(text, str) or not text.strip() or len(text.strip()) > MAX_SAY:
            raise ExtrasError(_w(lang, "bad_text", max=MAX_SAY))
        self._do(unit_id, "self.audio.speak", {"text": text.strip()}, lang, "speaking")
        return {"ok": True}

    def head(self, unit_id: str, yaw: object, pitch: object, lang: str | None = None) -> dict[str, Any]:
        for value in (yaw, pitch):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ExtrasError(_w(lang, "bad_head", yaw=HEAD_YAW_LIMIT_DEG, low=CENTRE_PITCH_DEG, high=HEAD_PITCH_MAX_DEG))
        if not -HEAD_YAW_LIMIT_DEG <= yaw <= HEAD_YAW_LIMIT_DEG or not CENTRE_PITCH_DEG <= pitch <= HEAD_PITCH_MAX_DEG:  # type: ignore[operator]
            raise ExtrasError(_w(lang, "bad_head", yaw=HEAD_YAW_LIMIT_DEG, low=CENTRE_PITCH_DEG, high=HEAD_PITCH_MAX_DEG))
        self._head(unit_id, yaw, pitch, lang)  # type: ignore[arg-type]
        return {"ok": True}

    def centre(self, unit_id: str, lang: str | None = None) -> dict[str, Any]:
        self._head(unit_id, 0, CENTRE_PITCH_DEG, lang)
        return {"ok": True}

    def look_around(self, unit_id: str, lang: str | None = None) -> dict[str, Any]:
        try:
            for yaw in (-70, 70, 0):
                self._head(unit_id, yaw, 25, lang, 90)
                self._sleep(0.8)
        finally:
            self._safe(unit_id, lambda: self._head(unit_id, 0, CENTRE_PITCH_DEG, lang))
        return {"ok": True}

    def nod(self, unit_id: str, lang: str | None = None) -> dict[str, Any]:
        self._do(unit_id, "self.robot.nod", {}, lang, "nodding")
        return {"ok": True}

    def shake(self, unit_id: str, lang: str | None = None) -> dict[str, Any]:
        try:
            for yaw in (-25, 25, -25, 25, 0):
                self._head(unit_id, yaw, CENTRE_PITCH_DEG + 10, lang, 300)
                self._sleep(0.3)
        finally:
            self._safe(unit_id, lambda: self._head(unit_id, 0, CENTRE_PITCH_DEG, lang))
        return {"ok": True}

    def dance(self, unit_id: str, name: object, lang: str | None = None) -> dict[str, Any]:
        known = {d["name"] for d in self.view(unit_id, lang)["dances"]}
        if not isinstance(name, str) or (known and name not in known):
            raise ExtrasError(_w(lang, "bad_dance"))
        reply = self._do(unit_id, "self.robot.dance", {"name": name}, lang, "dancing")
        if reply.get("result") is False:
            raise ExtrasError(_w(lang, "bad_dance"))
        return {"ok": True}

    def stop_dance(self, unit_id: str, lang: str | None = None) -> dict[str, Any]:
        self._do(unit_id, "self.robot.stop_dance", {}, lang, "dancing")
        return {"ok": True}

    def game(self, unit_id: str, name: object, lang: str | None = None) -> dict[str, Any]:
        from maipai_body.bodies.stackchan.games import GameService

        service = GameService(lambda tool, args: self._tool(unit_id, tool, args), language=normalize(lang))
        try:
            result = service.start(name, lang)
        except BodyLost:
            raise ExtrasError(say(lang, "unreachable")) from None
        if result.get("ok") is not True:
            raise ExtrasError(str(result.get("error") or _w(lang, "bad_game")))
        return {"ok": True}

    def photo(self, unit_id: str, lang: str | None = None) -> dict[str, Any]:
        if self._photo is None:
            raise ExtrasError(_w(lang, "no_camera"))
        try:
            data = self._photo(unit_id)
        except BodyLost:
            raise ExtrasError(say(lang, "unreachable")) from None
        if not data:
            raise ExtrasError(_w(lang, "no_camera"))
        kind = "png" if data[:4] == b"\x89PNG" else "jpeg"
        return {"ok": True, "image": f"data:image/{kind};base64," + base64.b64encode(data).decode("ascii")}

    # ---- find my robot: chirp, flash and wiggle until stopped ----

    def find(self, unit_id: str, on: object, lang: str | None = None) -> dict[str, Any]:
        with self._lock:
            old = self._finders.get(unit_id)
            if old is not None:
                old.set()
        if on is not True:
            self._safe(unit_id, lambda: self._led(unit_id, (0, 0, 0), lang))
            self._safe(unit_id, lambda: self._head(unit_id, 0, CENTRE_PITCH_DEG, lang))
            return {"ok": True, "finding": False}
        # one round now, so a unit that is off is reported right away
        self._do(unit_id, "self.audio.play_sound", {"sound": "needs_you"}, lang, "sounds")
        stop = threading.Event()
        with self._lock:
            self._finders[unit_id] = stop
        threading.Thread(target=self._find_loop, args=(unit_id, stop, lang), daemon=True, name="find-my-robot").start()
        return {"ok": True, "finding": True}

    def _find_loop(self, unit_id: str, stop: threading.Event, lang: str | None) -> None:
        deadline = time.monotonic() + FIND_SECONDS
        swing = 25
        try:
            while not stop.is_set() and time.monotonic() < deadline:
                self._safe(unit_id, lambda: self._led(unit_id, (168, 40, 0), lang))
                self._safe(unit_id, lambda: self._head(unit_id, swing, CENTRE_PITCH_DEG + 10, lang, 300))
                stop.wait(0.4)
                self._safe(unit_id, lambda: self._led(unit_id, (0, 0, 0), lang))
                self._safe(unit_id, lambda: self._tool(unit_id, "self.audio.play_sound", {"sound": "needs_you"}))
                swing = -swing
                stop.wait(1.2)
        finally:
            stop.set()
            self._safe(unit_id, lambda: self._led(unit_id, (0, 0, 0), lang))
            self._safe(unit_id, lambda: self._head(unit_id, 0, CENTRE_PITCH_DEG, lang))
