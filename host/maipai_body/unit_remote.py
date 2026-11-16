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
HEAD_SPEED_MIN = 100  # the unit refuses a head speed below this (a refusal is an error, not a slow move)
HEAD_SPEED_MAX = 1000
FIND_VOLUME_SOURCE = 1  # play_sound find=1: the unit overrides mute for this chirp and raises a low volume
FIND_END = 2  # play_sound find=2: the find is over, the unit puts its volume back

_WORDS = {
    "en": {
        "bad_head": "The head can turn left and right up to {yaw} degrees and up and down from {low} to {high} degrees. Move the pad back inside that range.",
        "bad_text": "Type something to say, up to {max} characters, then press Speak.",
        "bad_dance": "That dance is not on the unit's list. Pick one from the list.",
        "bad_game": "That game is not on the unit's list. Pick one from the list.",
        "bad_sound": "That sound is not one the unit has. Pick a sound from the list.",
        "no_camera": "This unit has no camera tool yet. It needs the camera build.",
        "muted": "The unit is muted or in full quiet, so it cannot make a sound. Unmute it first.",
        "no_move": "The unit answered but its head did not move. It may be asleep, held, or on firmware that ignores head moves from this page. Wake it with a tap, then try again.",
        "no_state": "The unit did not confirm the change. Check that it is on and near the router, then try again.",
        "bad_value_mute": "Mute needs a yes or no. Press the button again.",
        "muted_now": "The unit is now muted.",
        "unmuted_now": "The unit is now unmuted.",
        "find_silent": "The unit did not make a sound. Its firmware may be older than the find feature: update the firmware, then try again.",
    },
    "es": {
        "bad_head": "La cabeza gira a izquierda y derecha hasta {yaw} grados y arriba y abajo de {low} a {high} grados. Vuelve a poner el panel dentro de ese rango.",
        "bad_text": "Escribe algo para decir, hasta {max} caracteres, y pulsa Hablar.",
        "bad_dance": "Ese baile no esta en la lista de la unidad. Elige uno de la lista.",
        "bad_game": "Ese juego no esta en la lista de la unidad. Elige uno de la lista.",
        "bad_sound": "Ese sonido no lo tiene la unidad. Elige un sonido de la lista.",
        "no_camera": "Esta unidad aun no tiene la herramienta de camara. Necesita la version con camara.",
        "muted": "La unidad esta silenciada o en silencio total, asi que no puede sonar. Quitale el silencio primero.",
        "no_move": "La unidad respondio pero la cabeza no se movio. Puede estar dormida, sujeta, o tener un firmware que ignora los movimientos de esta pagina. Despiertala con un toque y vuelve a intentarlo.",
        "no_state": "La unidad no confirmo el cambio. Comprueba que este encendida y cerca del router, y vuelve a intentarlo.",
        "bad_value_mute": "Silenciar necesita un si o un no. Pulsa el boton de nuevo.",
        "muted_now": "La unidad esta silenciada.",
        "unmuted_now": "La unidad ya no esta silenciada.",
        "find_silent": "La unidad no sono. Su firmware puede ser anterior a la funcion de buscar: actualizalo y vuelve a intentarlo.",
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
        speak: Callable[[str], bool] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        timeout: float = 4.0,
    ) -> None:
        self._call, self._photo, self._sleep, self._timeout = call, photo, sleep, timeout
        # The host's own text-to-speech through the voice link (the unit has no speak tool).
        self._speak = speak
        self._finders: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    @property
    def tool_call(self) -> Callable[..., object]:
        """The call used for unit tools (the remote cue goes through the same link)."""
        return self._call

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

    def _head(self, unit_id: str, yaw: float, pitch: float, lang: str | None, speed: int = 150) -> None:
        """One head move the person asked for: the unit is told so (source=user), so it does not
        treat it as an idle look and ignore it. Speed is clamped into the range the unit accepts."""
        speed = max(HEAD_SPEED_MIN, min(HEAD_SPEED_MAX, int(speed)))
        yaw = max(-HEAD_YAW_LIMIT_DEG, min(HEAD_YAW_LIMIT_DEG, int(round(yaw))))
        pitch = max(CENTRE_PITCH_DEG, min(HEAD_PITCH_MAX_DEG, int(round(pitch))))
        self._do(unit_id, "self.robot.set_head_angles", {"yaw": yaw, "pitch": pitch, "speed": speed, "source": "user"}, lang, "head movement")

    def _angles(self, unit_id: str) -> tuple[int, int] | None:
        """Where the head is now, or None when the unit cannot say."""
        try:
            reply = self._tool(unit_id, "self.robot.get_head_angles", {})
        except BodyLost:
            return None
        yaw, pitch = reply.get("yaw"), reply.get("pitch")
        if isinstance(yaw, (int, float)) and isinstance(pitch, (int, float)):
            return int(yaw), int(pitch)
        return None

    def _moved_to(self, unit_id: str, yaw: float, pitch: float, lang: str | None, *, start: tuple[int, int] | None, tolerance: int = 12) -> None:
        """Read the head back after a move. Raises a plain error when it neither arrived nor moved toward the target."""
        distance = max(abs(yaw - (start[0] if start else 0)), abs(pitch - (start[1] if start else 0)))
        self._sleep(min(1.6, 0.5 + distance * 0.012))
        now = self._angles(unit_id)
        if now is None:
            raise ExtrasError(_w(lang, "no_state"))
        if abs(now[0] - yaw) <= tolerance and abs(now[1] - pitch) <= tolerance:
            return
        if start is not None and (abs(now[0] - start[0]) > 3 or abs(now[1] - start[1]) > 3):
            return  # it is on its way: the unit is slower than the wait, not stuck
        raise ExtrasError(_w(lang, "no_move"))

    def _safe(self, unit_id: str, fn: Callable[[], None]) -> None:
        try:
            fn()
        except (ExtrasError, BodyLost):
            pass

    def _muted(self, unit_id: str) -> bool | None:
        """The unit's own mute, read from it (None when it cannot say)."""
        try:
            state = self._tool(unit_id, "self.privacy.get", {})
        except BodyLost:
            return None
        return bool(state.get("muted")) if "muted" in state else None

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
            "muted": self._muted(unit_id),
            "limits": {"yaw": HEAD_YAW_LIMIT_DEG, "pitch": [CENTRE_PITCH_DEG, HEAD_PITCH_MAX_DEG]},
        }

    # ---- actions ----

    def _played(self, unit_id: str) -> int | None:
        try:
            info = self._tool(unit_id, "self.audio.sound_info", {})
        except BodyLost:
            return None
        value = info.get("played")
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    def beep(self, unit_id: str, sound: object = "success", lang: str | None = None) -> dict[str, Any]:
        if sound not in EARCONS:
            raise ExtrasError(_w(lang, "bad_sound"))
        before = self._played(unit_id)
        reply = self._do(unit_id, "self.audio.play_sound", {"name": sound, "test": True}, lang, "sounds")
        if reply.get("played") is False or reply.get("muted") is True:
            raise ExtrasError(_w(lang, "muted"))
        if before is not None:
            self._sleep(0.3)
            after = self._played(unit_id)
            if after is not None and after <= before:
                raise ExtrasError(_w(lang, "muted"))
        return {"ok": True}

    def mute(self, unit_id: str, on: object, lang: str | None = None) -> dict[str, Any]:
        """Mute or unmute, then read the unit's own state back: the answer says what the unit now is."""
        if not isinstance(on, bool):
            raise ExtrasError(_w(lang, "bad_value_mute"))
        self._do(unit_id, "self.privacy.set", {"mute": 1 if on else 0}, lang, "mute")
        self._sleep(0.2)
        try:
            state = self._tool(unit_id, "self.privacy.get", {})
        except BodyLost:
            raise ExtrasError(_w(lang, "no_state")) from None
        if "muted" not in state or bool(state.get("muted")) != on:
            raise ExtrasError(_w(lang, "no_state"))
        return {"ok": True, "muted": on, "message": _w(lang, "muted_now" if on else "unmuted_now")}

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
        if self._speak is not None:
            if not self._speak(text.strip()):
                raise ExtrasError(
                    "It cannot speak right now: it is muted, in full quiet, or already talking. "
                    "Wait a moment, check the mute setting, then press Say again."
                )
            return {"ok": True}
        self._do(unit_id, "self.audio.speak", {"text": text.strip()}, lang, "speaking")
        return {"ok": True}

    def head(self, unit_id: str, yaw: object, pitch: object, lang: str | None = None) -> dict[str, Any]:
        for value in (yaw, pitch):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ExtrasError(_w(lang, "bad_head", yaw=HEAD_YAW_LIMIT_DEG, low=CENTRE_PITCH_DEG, high=HEAD_PITCH_MAX_DEG))
        if not -HEAD_YAW_LIMIT_DEG <= yaw <= HEAD_YAW_LIMIT_DEG or not CENTRE_PITCH_DEG <= pitch <= HEAD_PITCH_MAX_DEG:  # type: ignore[operator]
            raise ExtrasError(_w(lang, "bad_head", yaw=HEAD_YAW_LIMIT_DEG, low=CENTRE_PITCH_DEG, high=HEAD_PITCH_MAX_DEG))
        start = self._angles(unit_id)
        self._head(unit_id, yaw, pitch, lang)  # type: ignore[arg-type]
        self._moved_to(unit_id, yaw, pitch, lang, start=start)  # type: ignore[arg-type]
        return {"ok": True}

    def centre(self, unit_id: str, lang: str | None = None) -> dict[str, Any]:
        start = self._angles(unit_id)
        self._head(unit_id, 0, CENTRE_PITCH_DEG, lang)
        self._moved_to(unit_id, 0, CENTRE_PITCH_DEG, lang, start=start)
        return {"ok": True}

    def _return_to(self, unit_id: str, pose: tuple[int, int] | None, lang: str | None) -> None:
        yaw, pitch = pose if pose is not None else (0, CENTRE_PITCH_DEG)
        self._safe(unit_id, lambda: self._head(unit_id, yaw, pitch, lang))

    def _steps(self, unit_id: str, steps: list[tuple[float, float, int, float]], lang: str | None) -> tuple[int, int] | None:
        """Run head steps (yaw, pitch, speed, hold seconds), reading the head back after the first one."""
        start = self._angles(unit_id)
        for index, (yaw, pitch, speed, hold) in enumerate(steps):
            self._head(unit_id, yaw, pitch, lang, speed)
            if index == 0:
                self._moved_to(unit_id, yaw, pitch, lang, start=start)
            else:
                self._sleep(hold)
        return start

    def look_around(self, unit_id: str, lang: str | None = None) -> dict[str, Any]:
        start = self._angles(unit_id)
        try:
            self._steps(unit_id, [(-70, 25, 110, 0.9), (70, 25, 110, 1.2), (0, 25, 110, 0.9)], lang)
        finally:
            self._return_to(unit_id, start, lang)
        return {"ok": True}

    def nod(self, unit_id: str, lang: str | None = None) -> dict[str, Any]:
        """The firmware has no nod tool: three eased pitch steps up and back, then the start pose."""
        start = self._angles(unit_id) or (0, CENTRE_PITCH_DEG)
        up = min(HEAD_PITCH_MAX_DEG, start[1] + 20)
        low = max(CENTRE_PITCH_DEG, start[1])
        try:
            self._steps(unit_id, [(start[0], up, 220, 0.45), (start[0], low, 160, 0.45), (start[0], up - 6, 220, 0.4), (start[0], low, 160, 0.4)], lang)
        finally:
            self._return_to(unit_id, start, lang)
        return {"ok": True}

    def shake(self, unit_id: str, lang: str | None = None) -> dict[str, Any]:
        start = self._angles(unit_id) or (0, CENTRE_PITCH_DEG)
        pitch = max(CENTRE_PITCH_DEG, start[1])
        try:
            self._steps(
                unit_id,
                [(start[0] - 24, pitch, 220, 0.45), (start[0] + 24, pitch, 260, 0.5), (start[0] - 18, pitch, 260, 0.45), (start[0] + 18, pitch, 260, 0.45), (start[0], pitch, 160, 0.3)],
                lang,
            )
        finally:
            self._return_to(unit_id, start, lang)
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

    def _chirp(self, unit_id: str, lang: str | None) -> dict[str, Any]:
        """One find chirp. find=1 tells the unit this is the person locating it: the unit plays at an
        audible volume even when sounds or the mute are on (the speaker only; the microphone is never touched)."""
        return self._do(unit_id, "self.audio.play_sound", {"name": "exclamation", "test": True, "find": FIND_VOLUME_SOURCE}, lang, "sounds")

    def find(self, unit_id: str, on: object, lang: str | None = None) -> dict[str, Any]:
        with self._lock:
            old = self._finders.get(unit_id)
            if old is not None:
                old.set()
        if on is not True:
            self._safe(unit_id, lambda: self._led(unit_id, (0, 0, 0), lang))
            self._safe(unit_id, lambda: self._head(unit_id, 0, CENTRE_PITCH_DEG, lang))
            self._safe(unit_id, lambda: self._tool(unit_id, "self.audio.play_sound", {"name": "exclamation", "find": FIND_END}))
            return {"ok": True, "finding": False}
        # one round now, so a unit that is off (or cannot make the sound) is reported right away
        before = self._played(unit_id)
        reply = self._chirp(unit_id, lang)
        if reply.get("played") is False:
            raise ExtrasError(_w(lang, "find_silent"))
        if before is not None:
            self._sleep(0.3)
            after = self._played(unit_id)
            if after is not None and after <= before:
                raise ExtrasError(_w(lang, "find_silent"))
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
                self._safe(unit_id, lambda: self._chirp(unit_id, lang))
                swing = -swing
                stop.wait(1.6)
        finally:
            stop.set()
            self._safe(unit_id, lambda: self._led(unit_id, (0, 0, 0), lang))
            self._safe(unit_id, lambda: self._head(unit_id, 0, CENTRE_PITCH_DEG, lang))
            self._safe(unit_id, lambda: self._tool(unit_id, "self.audio.play_sound", {"name": "exclamation", "find": FIND_END}))
