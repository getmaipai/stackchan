# ruff: noqa: E501
"""The passcode lock, host side (design note lock-and-radio-2026-11-17, section 1).

The unit enforces the lock by itself, even with the host off. This module is only the settings page's and the voice command's way to
ask the unit: it checks what a person typed, forwards it once, and turns the unit's answer into a plain sentence. The unit tools:

    self.lock.status {}                              -> {"ok": true, "has_code": bool, "locked": bool, "auto_minutes": N}
    self.lock.set    {"code": "1234", "current"?: "0000"} -> {"ok": true} or {"ok": false, "reason": "bad_code" | "wrong_current" | "current_needed" | "locked"}
    self.lock.clear  {"current": "1234"}             -> {"ok": true} or {"ok": false, "reason": "wrong_current" | "no_code"}
    self.lock.now    {}                              -> {"ok": true, "locked": true} or {"ok": false, "reason": "no_code"}
    self.lock.config {"auto_minutes": N}             -> {"ok": true, "auto_minutes": N} or {"ok": false, "reason": "bad_minutes"}

THE HOST NEVER KEEPS THE CODE. It goes from the page's request to the unit tool call and nowhere else: not to disk, not to a log, not into
a response, an event, an error sentence, a settings file or a dump. Every sentence this module returns is a fixed one from ``SAY`` or
``REASONS``; none is built from what was typed or from the text of an exception. The auto lock minutes are not saved on the host either:
the unit is the authority and ``view`` asks it. A spoken code is never accepted anywhere (``bodies/stackchan/lock_voice.py`` handles only
the word "lock").

While the unit is locked it refuses set, clear and config with ``locked``; no remote command clears or bypasses a lock.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from maipai_body.unit_tools import ToolProbe, is_unknown_tool, unwrap

logger = logging.getLogger("maipai_body.unit_lock")

CODE_MIN, CODE_MAX = 4, 6
AUTO_MINUTES = (0, 1, 15)  # 0 is off; the unit accepts only these (an older saved 5, 30 or 60 still loads on the unit and is shown as it is)
_CODE = re.compile(
    rf"[0-9]{{{CODE_MIN},{CODE_MAX}}}"
)  # ASCII digits only: \d would also match other scripts

# The unit's refusal reasons (the firmware's words) and the plain sentence for each: what went wrong, what to do.
REASONS: dict[str, tuple[str, str]] = {
    "bad_code": (
        "The code must be 4 to 6 digits, with nothing else. Type digits only and try again.",
        "El código debe tener de 4 a 6 dígitos, sin nada más. Escribe solo dígitos e inténtalo de nuevo.",
    ),
    "wrong_current": (
        "The current code is not right. Type the current code again, or unlock the robot with its keypad.",
        "El código actual no es correcto. Escribe el código actual de nuevo, o desbloquea el robot con su teclado.",
    ),
    "current_needed": (
        "The robot already has a code. Type the current code to change it.",
        "El robot ya tiene un código. Escribe el código actual para cambiarlo.",
    ),
    "locked": (
        "The robot is locked. Unlock it with the code on the robot's keypad, then try again.",
        "El robot está bloqueado. Desbloquéalo con el código en el teclado del robot y inténtalo de nuevo.",
    ),
    "no_code": (
        "The robot has no code. Set a code first.",
        "El robot no tiene código. Primero crea un código.",
    ),
    "bad_minutes": (
        "Choose Off, 1, 5, 15, 30 or 60 minutes.",
        "Elige Desactivado, 1, 5, 15, 30 o 60 minutos.",
    ),
}

SAY: dict[str, tuple[str, str]] = {
    "mismatch": (
        "The two codes are not the same. Type the same code in both boxes.",
        "Los dos códigos no son iguales. Escribe el mismo código en las dos casillas.",
    ),
    "bad_current": (
        "The current code is 4 to 6 digits. Type it again, digits only.",
        "El código actual tiene de 4 a 6 dígitos. Escríbelo de nuevo, solo dígitos.",
    ),
    "need_current": (
        "Type the current code to remove it. If you forgot it, use the robot's reset.",
        "Escribe el código actual para quitarlo. Si lo olvidaste, usa el reinicio del robot.",
    ),
    "bad_minutes": REASONS["bad_minutes"],
    "offline": (
        "The robot is not connected. Turn it on and try again.",
        "El robot no está conectado. Enciéndelo e inténtalo de nuevo.",
    ),
    "coming": (
        "The passcode lock comes with the next unit update.",
        "El bloqueo con código llega con la próxima actualización de la unidad.",
    ),
    "refused": (
        "The robot did not accept that. Try again.",
        "El robot no lo aceptó. Inténtalo de nuevo.",
    ),
    "code_set": ("Code saved on the robot.", "Código guardado en el robot."),
    "code_removed": (
        "Code removed. The robot no longer locks.",
        "Código quitado. El robot ya no se bloquea.",
    ),
    "locked_now": ("The robot is locked.", "El robot está bloqueado."),
    "auto_saved": ("Auto lock saved.", "Bloqueo automático guardado."),
}

# What the firmware core must say for these tables to be right: a test compares them with the core when one exists.
TABLE: dict[str, Any] = {
    "code_min": CODE_MIN,
    "code_max": CODE_MAX,
    "auto_minutes": list(AUTO_MINUTES),
    "reasons": sorted(REASONS),
    "tools": [
        "self.lock.status",
        "self.lock.set",
        "self.lock.clear",
        "self.lock.now",
        "self.lock.config",
    ],
}


def _lang(lang: str | None) -> int:
    return 1 if (lang or "").lower().startswith("es") else 0


def say(lang: str | None, key: str) -> str:
    return SAY[key][_lang(lang)]


def reason_text(lang: str | None, reason: object) -> str:
    """The plain sentence for a unit reason; any other word is the generic refusal (never the unit's own text)."""
    if isinstance(reason, str) and reason in REASONS:
        return REASONS[reason][_lang(lang)]
    return say(lang, "refused")


def valid_code(code: object) -> bool:
    """Exactly 4 to 6 ASCII digits in a string: no spaces, no letters, no number type (a number loses its leading zeros)."""
    return isinstance(code, str) and _CODE.fullmatch(code) is not None


def valid_minutes(minutes: object) -> bool:
    return isinstance(minutes, int) and not isinstance(minutes, bool) and minutes in AUTO_MINUTES


def _failed(lang: str | None, text: str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "error": text, **extra}


class LockService:
    def __init__(self, probe: ToolProbe) -> None:
        self.probe = probe

    # ---- one forwarded call ------------------------------------------------------------------------------------

    def _ask(
        self, device_id: str, tool: str, arguments: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        """("reply", the unit's answer), ("offline", {}) or ("coming", {}). The arguments may hold a code: they are handed to the unit
        call and dropped; nothing here logs them, and a failure is logged by its class name only (never its text)."""
        try:
            have = self.probe.has(device_id, "lock")
        except Exception as exc:  # a probe that fails is an unreachable unit; the text of the exception is never used
            logger.warning("the lock probe failed (%s)", type(exc).__name__)
            return "offline", {}
        if have is None:
            return "offline", {}
        if have is False:
            return "coming", {}
        try:
            reply = unwrap(self.probe.call(device_id, tool, arguments))
        except Exception as exc:  # BodyLost, OSError, TimeoutError or anything the link raises: logged without its text
            logger.warning("the lock call %s failed (%s)", tool, type(exc).__name__)
            return "offline", {}
        if is_unknown_tool(reply):
            return "coming", {}
        return "reply", reply

    def _answer(
        self, lang: str | None, kind: str, reply: dict[str, Any], done: str, **extra: Any
    ) -> dict[str, Any]:
        if kind == "offline":
            return _failed(lang, say(lang, "offline"), offline=True)
        if kind == "coming":
            return _failed(lang, say(lang, "coming"), pending=True)
        if reply.get("ok") is True:
            return {"ok": True, "message": say(lang, done), **extra}
        reason = reply.get("reason")
        return _failed(
            lang, reason_text(lang, reason), reason=reason if reason in REASONS else "refused"
        )

    # ---- the page ----------------------------------------------------------------------------------------------

    def view(self, device_id: str, lang: str | None = None) -> dict[str, Any]:
        """What the Security section shows. The unit answers; nothing is read from the host's settings and nothing is invented when
        the unit cannot be reached (the fields are None and ``reachable`` is False)."""
        base: dict[str, Any] = {
            "has_code": None,
            "locked": None,
            "auto_minutes": None,
            "status": "unknown",
            "auto_options": list(AUTO_MINUTES),
            "limits": {"min": CODE_MIN, "max": CODE_MAX},
            "unit_ready": False,
            "reachable": False,
            "message": "",
        }
        kind, reply = self._ask(device_id, "self.lock.status", {})
        if kind == "offline":
            return {**base, "message": say(lang, "offline")}
        if kind == "coming":
            return {**base, "reachable": True, "message": say(lang, "coming")}
        if (
            reply.get("ok") is not True
            or not isinstance(reply.get("has_code"), bool)
            or not isinstance(reply.get("locked"), bool)
        ):
            return {**base, "reachable": True, "unit_ready": True, "message": say(lang, "refused")}
        minutes = reply.get("auto_minutes")
        has_code, locked = reply["has_code"], reply["locked"]
        return {
            **base,
            "has_code": has_code,
            "locked": locked,
            "auto_minutes": minutes if valid_minutes(minutes) else None,
            "status": "locked" if locked else ("unlocked" if has_code else "none"),
            "unit_ready": True,
            "reachable": True,
        }

    def set_code(
        self,
        device_id: str,
        code: object,
        confirm: object = None,
        current: object = None,
        lang: str | None = None,
    ) -> dict[str, Any]:
        """Set a code, or change it (the unit wants ``current`` when it already has one). Every check that needs no unit runs first."""
        if not valid_code(code):
            return _failed(lang, reason_text(lang, "bad_code"), reason="bad_code")
        if confirm is not None and confirm != code:
            return _failed(lang, say(lang, "mismatch"), reason="mismatch")
        arguments: dict[str, Any] = {"code": code}
        if current not in (None, ""):
            if not valid_code(current):
                return _failed(lang, say(lang, "bad_current"), reason="wrong_current")
            arguments["current"] = current
        kind, reply = self._ask(device_id, "self.lock.set", arguments)
        return self._answer(lang, kind, reply, "code_set")

    def clear_code(
        self, device_id: str, current: object, lang: str | None = None
    ) -> dict[str, Any]:
        if current in (None, ""):
            return _failed(lang, say(lang, "need_current"), reason="current_needed")
        if not valid_code(current):
            return _failed(lang, say(lang, "bad_current"), reason="wrong_current")
        kind, reply = self._ask(device_id, "self.lock.clear", {"current": current})
        return self._answer(lang, kind, reply, "code_removed")

    def lock_now(self, device_id: str, lang: str | None = None) -> dict[str, Any]:
        kind, reply = self._ask(device_id, "self.lock.now", {})
        return self._answer(lang, kind, reply, "locked_now")

    def set_auto(self, device_id: str, minutes: object, lang: str | None = None) -> dict[str, Any]:
        if not valid_minutes(minutes):
            return _failed(lang, say(lang, "bad_minutes"), reason="bad_minutes")
        kind, reply = self._ask(device_id, "self.lock.config", {"auto_minutes": minutes})
        return self._answer(lang, kind, reply, "auto_saved", auto_minutes=minutes)
