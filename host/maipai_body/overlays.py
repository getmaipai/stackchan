# ruff: noqa: E501
"""Overlays on the unit's screen (rain, snow, confetti...): one director, one tool pair.

The unit draws; the host only says which overlay, how strong, and for how long:

    self.overlay.set    {"name": "rain", "intensity": "light|normal|heavy", "seconds": 8}
    self.overlay.clear  {}

The names and the tag grammar are in :mod:`maipai_body.reply_tags`. Every trigger goes through
:class:`OverlayDirector`: a reply tag, the settings Remote page, and (later) host events. A unit without the
overlay tools (checked with :class:`~maipai_body.unit_tools.ToolProbe`) is skipped quietly: the reply still
speaks and nothing is shown or logged above debug.
"""

from __future__ import annotations

import logging
from typing import Any

from maipai_body import reply_tags
from maipai_body.unit_tools import ToolProbe

logger = logging.getLogger("maipai_body.overlays")

SAY: dict[str, tuple[str, str]] = {
    "unknown": (
        "That overlay is not known. Choose one of: {names}.",
        "No conozco esa superposición. Elige una de: {names}.",
    ),
    "soon": (
        "This unit cannot draw overlays yet. They come with the next unit update; nothing was sent.",
        "Esta unidad todavía no puede dibujar superposiciones. Llegan con la próxima actualización de la unidad; no se envió nada.",
    ),
    "offline": (
        "The unit is not connected. Turn it on and try again.",
        "La unidad no está conectada. Enciéndela e inténtalo de nuevo.",
    ),
    "seconds": (
        "The time must be from 1 to {max} seconds. Choose a number in that range.",
        "El tiempo debe ser de 1 a {max} segundos. Elige un número en ese rango.",
    ),
}


class OverlayError(ValueError):
    pass


def say(lang: str | None, code: str, **values: object) -> str:
    english, spanish = SAY[code]
    return (spanish if (lang or "").lower().startswith("es") else english).format(**values)


class OverlayDirector:
    """Shows and clears overlays on a unit. ``set`` and ``clear`` never raise for a missing tool."""

    def __init__(self, probe: ToolProbe) -> None:
        self.probe = probe

    def supported(self, device_id: str) -> bool | None:
        return self.probe.has(device_id, "overlay")

    def set(self, device_id: str, name: str, intensity: str = reply_tags.DEFAULT_INTENSITY, seconds: float = reply_tags.DEFAULT_SECONDS) -> bool:
        """Start an overlay. True when the unit took it; False when skipped (no tool, offline, refused)."""
        if self.supported(device_id) is not True:
            logger.debug("overlay %s skipped: the unit has no overlay tool (yet)", name)
            return False
        seconds = max(1, min(reply_tags.MAX_SECONDS, int(round(seconds))))
        try:
            reply = self.probe.call(device_id, "self.overlay.set", {"name": name, "intensity": intensity, "seconds": seconds})
        except Exception:
            logger.debug("overlay %s not sent", name, exc_info=True)
            return False
        return reply.get("ok") is True

    def clear(self, device_id: str) -> bool:
        if self.supported(device_id) is not True:
            return False
        try:
            return self.probe.call(device_id, "self.overlay.clear", {}).get("ok") is True
        except Exception:
            logger.debug("overlay clear not sent", exc_info=True)
            return False

    # ---- the settings Remote page: loud about what it did not do ------------------------------

    def remote_set(self, device_id: str, name: object, intensity: object, seconds: object, lang: str | None = None) -> dict[str, Any]:
        text = str(name).strip()
        tag = reply_tags.parse_tag(text if ":" in text or "=" in text else f"overlay:{text}")  # "love" is also a mood: the page means the overlay
        if tag.kind != "overlay":
            raise OverlayError(say(lang, "unknown", names=", ".join(reply_tags.OVERLAYS)))
        level = intensity if intensity in reply_tags.INTENSITIES else tag.intensity
        if seconds in (None, ""):
            seconds = reply_tags.DEFAULT_SECONDS
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not 1 <= seconds <= reply_tags.MAX_SECONDS:
            raise OverlayError(say(lang, "seconds", max=reply_tags.MAX_SECONDS))
        have = self.supported(device_id)
        if have is None:
            raise OverlayError(say(lang, "offline"))
        if have is False:
            return {"ok": False, "pending": True, "message": say(lang, "soon")}
        ok = self.set(device_id, tag.name, level, seconds)
        return {"ok": ok, "name": tag.name, "intensity": level, "seconds": int(seconds)}

    def remote_clear(self, device_id: str, lang: str | None = None) -> dict[str, Any]:
        have = self.supported(device_id)
        if have is None:
            raise OverlayError(say(lang, "offline"))
        if have is False:
            return {"ok": False, "pending": True, "message": say(lang, "soon")}
        return {"ok": self.clear(device_id)}
