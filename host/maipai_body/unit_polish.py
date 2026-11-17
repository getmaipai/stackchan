# ruff: noqa: E501
"""The newer unit features, built once and shared by the voice path and the settings page.

Emotion faces and overlay tags (reply_tags.py), the listening and look choices (unit_prefs.py), the pack library
(packs.py) and the filler sounds (fillers.py) all need the same three things: a way to call a unit tool, one
cache of which optional tools each unit has, and the per-unit settings. ``Polish`` holds them together so the two
sides see the same state.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from maipai_body import command_bus as bus_mod
from maipai_body import fillers as fillers_mod
from maipai_body import (
    language_packs,
    pack_auto,
    phrase_packs,
    reply_tags,
    scenes,
    swipe_pages,
    unit_lock,
    unit_prefs,
)
from maipai_body import overlays as overlays_mod
from maipai_body import packs as packs_mod
from maipai_body.unit_tools import ToolProbe, unwrap

logger = logging.getLogger("maipai_body.unit_polish")


class Polish:
    def __init__(
        self,
        call: Callable[..., object],
        get: Callable[[str], dict[str, Any]],
        put: Callable[[str, dict[str, Any]], dict[str, Any]],
        *,
        library: packs_mod.PackLibrary | None = None,
        active: packs_mod.ActiveStore | None = None,
        synth: Callable[[str], tuple[Any, int]] | None = None,
        tool_list: Callable[[str], set[str] | None] | None = None,
        data_dir: Path | None = None,
        tone_on_unit: Callable[[str], bool] | None = None,
        face_lang: Callable[[str], str] | None = None,
        voice: Callable[[], str] | None = None,
        background: bool = True,
    ) -> None:
        self.get = get
        self.probe = ToolProbe(call, tool_list=tool_list)
        if library is None and data_dir is not None:
            library = packs_mod.PackLibrary(data_dir / "packs", filler_root=data_dir / "fillers")
        if active is None and data_dir is not None:
            active = packs_mod.ActiveStore(data_dir / "packs-active.json")
        self.library = library or packs_mod.PackLibrary()
        self.active = active or packs_mod.ActiveStore()
        self.prefs = unit_prefs.PrefsService(self.probe, get, put)
        self.pages = swipe_pages.SwipePagesService(self.probe, get, put)  # swipe pages and the control sheet (firmware patches P10 to P13)
        self.lock = unit_lock.LockService(self.probe)  # the passcode lock: forwards to the unit, never keeps the code
        self.overlays = overlays_mod.OverlayDirector(self.probe)
        # One command bus for every source that decorates the unit (command_bus.py): the model's tags, the settings page, Home.
        # ``gate_state`` says what outranks decoration (``attach`` fills it from the turn bridge); ``ring`` is the ring light's sink
        # (``ring(device_id, color_or_off, seconds) -> bool``; None until the ring standard has a scene row, so a scene's light is skipped);
        # ``mood_sink(device_id, mood)`` draws a mood the settings page's Test asked for.
        self.scenes = scenes.SceneBook(get, put)
        self.gate_state: Callable[[str], bus_mod.Gate] = lambda _device_id: bus_mod.Gate()
        self.ring: Callable[[str, str, float], bool] | None = None
        self.mood_sink: Callable[[str, str], object] | None = None
        self.bus = bus_mod.CommandBus(
            {
                "fx.set": lambda d, a: self.overlays.set(d, a["name"], a["intensity"], a["seconds"]),
                "fx.clear": lambda d, a: self.overlays.clear(d),
                "light.look": self._light,
                "sound.play": self._sound,
            },
            gate=lambda device_id: self.gate_state(device_id),
            scenes=self.scenes,
        )
        # The packs the unit's own settings call for (language, "While it thinks", voice) are chosen here, not only by a person's
        # click: see pack_auto.py. Setting changes reach the unit in the background so a save never waits on a pack push.
        self.auto = pack_auto.AutoPacks(self.library, get, face_lang, voice)
        self.packs = packs_mod.PackService(self.probe, self.library, self.active, auto=self.auto)
        self.generator = fillers_mod.FillerGenerator(synth, self.library)
        self.phrases = phrase_packs.PhraseGenerator(synth, self.library)
        self._background = background
        self._threads: list[threading.Thread] = []
        try:
            language_packs.install(self.library)  # the five shipped screen-language packs: a few hundred bytes each
        except Exception:
            logger.warning("the screen-language packs could not be put in the pack library", exc_info=True)
        self.prefs.after_save = self.on_prefs_saved
        self.player = fillers_mod.FillerPlayer(self.library, self.active, self.probe, tone_on_unit=tone_on_unit)

    def turn_prefs(self, device_id: str) -> dict[str, Any]:
        """What the voice path reads each turn."""
        return unit_prefs.prefs_of(self.get(device_id))

    def _light(self, device_id: str, args: dict[str, Any]) -> bool:
        if self.ring is None:
            return False
        return bool(self.ring(device_id, args["color"], args["seconds"]))

    def _sound(self, device_id: str, args: dict[str, Any]) -> bool:
        return unwrap(self.probe.call(device_id, "self.audio.play_sound", {"name": args["name"]})).get("ok") is True

    def attach(self, bridge: Any) -> None:
        """Give the turn bridge its hooks, and the command bus the bridge's gates (privacy, sleep, a child, a remote cue)."""
        bridge.prefs_for = self.turn_prefs
        bridge.overlay_director = self.overlays
        bridge.filler_player = self.player
        bridge.command_bus = self.bus
        self.gate_state = lambda device_id: bus_mod.Gate(
            muted=bridge.muted_reason() is not None,
            blocked=bool(bridge.decoration_blocked()),
            remote=bool(bridge.remote_active(device_id)),
            child=bool(bridge.child_present(device_id)),
        )
        self.mood_sink = lambda _device_id, mood: bridge.show_mood(reply_tags.MOOD_CUE[mood])

    def scene_test(self, device_id: str, name: object, lang: str | None = None) -> dict[str, Any]:
        """The settings page's Test: the owner asks for a scene (or ``off``) on this unit. Loud about what it did not do."""
        if name == "off":
            result = self.bus.send(device_id, bus_mod.Command("scene.clear", source="owner"))
        elif name in reply_tags.SCENE_NAMES:
            result = self.bus.send(device_id, bus_mod.Command("scene.set", {"name": name}, source="owner"))
        else:
            raise scenes.SceneError(scenes.say(lang, "unknown", names=", ".join(reply_tags.SCENE_NAMES)))
        mood = result.mood if name != "off" else None
        if mood and self.mood_sink is not None:
            self.mood_sink(device_id, mood)
        skipped = [n for n, r in result.parts if not r.shown and n != "face.mood"]
        return {"ok": result.ok, "shown": [n for n, r in result.parts if r.shown], "skipped": skipped, "mood": mood}

    def bind_faces(self, faces: Any) -> None:
        """Take the unit's screen language from the face settings, and follow its changes (a new language sends its pack)."""
        self.auto.face_lang = lambda device_id: faces.config(device_id).lang
        if self.on_face_saved not in faces.listeners:
            faces.listeners.append(self.on_face_saved)

    def _run(self, work: Callable[[], None]) -> None:
        if not self._background:
            work()
            return
        thread = threading.Thread(target=work, name="unit-packs", daemon=True)
        self._threads = [t for t in self._threads if t.is_alive()] + [thread]
        thread.start()

    def join(self, timeout: float = 10.0) -> None:
        """Wait for background pack work (tests and shutdown)."""
        for thread in list(self._threads):
            thread.join(timeout)

    def sync_types(self, device_id: str, kinds: tuple[str, ...]) -> None:
        self._run(lambda: self.packs.sync_types(device_id, kinds))

    def on_prefs_saved(self, device_id: str, values: dict[str, Any]) -> None:
        """A unit setting was saved: "While it thinks" decides whether the unit holds the filler pack."""
        if "filler_mode" in values:
            self.sync_types(device_id, ("filler",))

    def on_face_saved(self, device_id: str, keys: set[str]) -> None:
        """The face settings changed: a new screen language sends its words (and drops the old language's pack), and the phrase and
        filler sets follow the language."""
        if "lang" in keys:
            self.sync_types(device_id, ("language", "phrase", "filler"))

    def make_fillers(self, device_id: str, voice: str, lang: str) -> dict[str, Any]:
        """Make the filler sounds for a voice and send them when they are done (when "While it thinks" is on phrase)."""
        return self.generator.start(voice, lang, on_done=lambda _info: self.sync_types(device_id, ("filler",)))

    def make_phrases(self, device_id: str, voice: str, lang: str) -> dict[str, Any]:
        """Make the offline phrases for a voice and send them when they are done."""
        return self.phrases.start(voice, lang, on_done=lambda _info: self.sync_types(device_id, ("phrase",)))

    def on_connect(self, device_id: str) -> None:
        """A unit connected: forget what we knew of its tools, then send what it is due."""
        self.probe.forget(device_id)
        for step in (self.prefs.sync, self.pages.sync, self.packs.sync):
            try:
                step(device_id)
            except Exception:
                logger.debug("unit features not synced to %s", device_id[-5:], exc_info=True)
