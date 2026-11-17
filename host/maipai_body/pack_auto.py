# ruff: noqa: E501
"""Which pack each unit should hold, worked out from the unit's own settings.

A person's explicit choice always wins (``packs.ActiveStore``). For the three managed types, with no explicit choice:

* ``language``: the screen-language pack of the face language (none for English, which is in the unit's image);
* ``filler``: the filler sounds, only when "While it thinks" is set to a phrase (a unit set to none or a tone holds no filler pack:
  the host sends only what is active, and the unit's flash cache and memory are small);
* ``phrase``: the offline phrases of the unit's language, preferring the pack made with the household's voice; none when the
  library has no set for that language (the unit then says the clips built into its image).

``PackService`` calls this on connect and when a setting that decides it changes, and sends or drops packs to match.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from maipai_body import faces as face_settings
from maipai_body import packs as packs_mod
from maipai_body import unit_prefs

logger = logging.getLogger("maipai_body.pack_auto")


class AutoPacks:
    def __init__(
        self,
        library: packs_mod.PackLibrary,
        get_saved: Callable[[str], dict[str, Any]],
        face_lang: Callable[[str], str] | None = None,
        voice: Callable[[], str] | None = None,
    ) -> None:
        self.library = library
        self._get_saved = get_saved
        self.face_lang = face_lang or (lambda _device_id: "en")
        self.voice = voice or (lambda: "")

    def language_of(self, device_id: str) -> str:
        try:
            code = str(self.face_lang(device_id) or "en").lower()
        except Exception:
            code = "en"
        return code if code in face_settings.LANGS else "en"

    def _pick(self, kind: str, lang: str, *, fallback_en: bool) -> str | None:
        listed = self.library.list(kind)
        voice = self.voice()
        for want in (lang, "en") if fallback_en and lang != "en" else (lang,):
            same = [p for p in listed if p.get("lang") == want]
            if not same:
                continue
            same.sort(key=lambda p: (0 if voice and p.get("voice") == voice else 1, p["id"]))
            return str(same[0]["id"])
        return None

    def __call__(self, device_id: str) -> dict[str, str | None]:
        lang = self.language_of(device_id)
        mode = unit_prefs.prefs_of(self._get_saved(device_id)).get("filler_mode", "tone")
        return {
            "language": self._pick("language", lang, fallback_en=False) if lang != "en" else None,
            "filler": self._pick("filler", lang, fallback_en=True) if mode == "phrase" else None,
            "phrase": self._pick("phrase", lang, fallback_en=False),
        }
