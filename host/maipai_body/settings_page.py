# ruff: noqa: E501
"""The core settings page: one small local page, no Home, no household data.

``SettingsBackend`` holds the logic (testable with no server); ``render_page`` makes the HTML.
The dashboard server routes /settings and /api/stackchan/settings* to it, local administrator only.
"""

from __future__ import annotations

import base64
import html
import json
import threading
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from maipai_body.first_run_name import DEFAULT_NAME
from maipai_body import character_pack as character_pack_mod
from maipai_body import faces as face_settings
from maipai_body import overlays as overlays_mod
from maipai_body import packs as packs_mod
from maipai_body import phrase_packs as phrase_packs_mod
from maipai_body import picture_faces as picture_mod
from maipai_body import remote_activity as activity_mod
from maipai_body import scenes as scenes_mod
from maipai_body import unit_device as device_mod
from maipai_body import unit_extras as extras_mod
from maipai_body import unit_remote as remote_mod
from maipai_body.bodies.stackchan import updater
from maipai_body.i18n import catalog, normalize, t
from maipai_body.picture_faces_page import pictures_js
from maipai_body.unit_polish import Polish
from maipai_body.unit_settings import SettingsError, UnitSettingsStore

Live = Callable[[str], dict[str, Any]]


def _remote_forced_off() -> bool:
    """robot.toml [remote] enabled = false keeps remote access off whatever the page says."""
    try:
        from maipai_body.config import load_config

        return load_config().remote.enabled is False
    except Exception:
        return False


class SettingsBackend:
    def __init__(
        self,
        *,
        devices: Callable[[], dict[str, Any]],
        store: UnitSettingsStore | None = None,
        live: Live | None = None,
        host_address: str = "",
        update_source: str | Path | None = None,
        public_key: str | Path | None = None,
        push: updater.OtaPush | None = None,
        preset: str = "core",
        language: str = "en",
        faces: face_settings.FaceService | None = None,
        extras: extras_mod.UnitExtras | None = None,
        people: extras_mod.PeopleStore | None = None,
        pictures: picture_mod.PictureService | None = None,
        device: device_mod.UnitDevice | None = None,
        remote: remote_mod.UnitRemote | None = None,
        polish: Polish | None = None,
        activity: activity_mod.RemoteActivity | None = None,
        link: Any = None,
    ) -> None:
        self.installed: Any = None  # installed_set.InstalledSets: the 'On my robot' page (set by the host)
        self.installed_units: Callable[[], list[dict[str, Any]]] = lambda: []
        self.health: Callable[[], dict[str, Any]] | None = None  # the host's health document (health.py); set by the host
        self.brain_setup: Any = None  # brain_setup.controller.BrainSetup: the Brain page (set by the host)
        self.pair_code: Callable[[], str] | None = None  # mints a pairing code (set by the host)
        self.pair_exchange: Any = None  # the voice server (waiting_exchanges, approve_exchange); set by the host
        self.wakeword: Any = None  # the wake word maker package (set by the host only when switched on)
        self.phone_link: Callable[[], dict[str, Any]] | None = None  # {"lan", "base", "token"} for the phone login link
        self._link = link  # the encrypted robot link's policy (xiaozhi/link_security.py); no keys leave it
        self.devices, self.store = devices, store or UnitSettingsStore()
        self.live = live or (lambda _device_id: {})
        self.host_address = host_address
        self.update_source, self.public_key = update_source, public_key
        self.push, self.preset, self.language = push, preset, normalize(language)
        self._faces = faces
        self._extras = extras
        self._people = people
        self._pictures = pictures
        self._device = device
        self._remote = remote
        self._polish = polish
        self._activity = activity
        if polish is not None and faces is not None:
            polish.bind_faces(faces)  # the unit's screen language decides its language pack

    @property
    def pictures(self) -> picture_mod.PictureService:
        """The owner's picture faces. Without a live link a unit counts as offline: the pictures are saved and go to
        the unit when the host next sees it connect."""
        if self._pictures is None:
            self._pictures = picture_mod.PictureService(face_settings.offline_call)
        return self._pictures

    @property
    def device(self) -> device_mod.UnitDevice:
        """The everyday controls. Without a live link a unit counts as offline."""
        if self._device is None:
            self._device = device_mod.UnitDevice(extras_mod.offline_call)
        return self._device

    @property
    def remote(self) -> remote_mod.UnitRemote:
        """The Remote page's actions. Without a live link a unit counts as offline."""
        if self._remote is None:
            self._remote = remote_mod.UnitRemote(extras_mod.offline_call)
        return self._remote

    @property
    def polish(self) -> Polish:
        """Emotion faces, overlays, listening cues, packs and fillers. Without a live link a unit counts as offline."""
        if self._polish is None:
            self._polish = Polish(
                extras_mod.offline_call, self.store.get, self.store.update, data_dir=Path(self.store.path).parent, background=False
            )
            self._polish.bind_faces(self.faces)
        return self._polish

    @property
    def activity(self) -> activity_mod.RemoteActivity:
        """The remote cue, the remote settings and the remote activity log. Files sit next to the unit settings."""
        if self._activity is None:
            folder = Path(self.store.path).parent
            self._activity = activity_mod.RemoteActivity(
                self.remote.tool_call,
                self.polish.probe,
                activity_mod.RemoteStore(folder / "remote-access.json", forced_off=_remote_forced_off),
                activity_mod.RemoteLog(folder / "remote-activity.jsonl"),
            )
        if self._activity.bind_marker is None:
            self._activity.bind_marker = self.remote.set_marker  # patch TC01: a controller's tool calls carry its cue
        return self._activity

    @property
    def extras(self) -> extras_mod.UnitExtras:
        """Reactions, clock, network test and details. Without a live link a unit counts as offline."""
        if self._extras is None:
            self._extras = extras_mod.UnitExtras(extras_mod.offline_call)
        return self._extras

    @property
    def people(self) -> extras_mod.PeopleStore:
        if self._people is None:
            self._people = extras_mod.PeopleStore()
        return self._people

    @property
    def faces(self) -> face_settings.FaceService:
        """The face settings of every unit. Without a live link a unit counts as offline: a change
        is saved and goes to the unit when the host next sees it connect."""
        if self._faces is None:
            self._faces = face_settings.FaceService(face_settings.offline_call)
        return self._faces

    def state(self, lang: str | None = None) -> dict[str, Any]:
        units = []
        for device_id in sorted(self.devices()):
            own = self.store.get(device_id)
            live = self.live(device_id)
            wifi = live.get("wifi_configured")
            try:
                color = self.faces.config(device_id).color
            except face_settings.FaceError:
                color = "none"
            units.append(
                {
                    "device_id": device_id,
                    "name": own.get("name", DEFAULT_NAME),
                    "wifi": "unknown" if wifi is None else ("set" if wifi else "unset"),
                    "persona": own.get("persona", ""),
                    "llm": own.get("llm", {"url": "", "model": "", "api_key_env": ""}),
                    "alarms": own.get("alarms", []),
                    "volume_cap": own.get("volume_cap", 100),
                    "speech_speed": own.get("speech_speed", 1.0),
                    "speech_pitch": own.get("speech_pitch", 0),
                    "muted": own.get("muted", bool(live.get("muted", False))),
                    "idle_movement": own.get("idle_movement", "off"),
                    "ignore_noise": own.get("ignore_noise", "medium"),
                    "look_speaker": own.get("look_speaker", False),
                    "look_faces": own.get("look_faces", False),
                    "look_on_wake": own.get("look_on_wake", True),
                    "face_owner": own.get("face_owner", "robot"),
                    "wait_after_talking": own.get("wait_after_talking", "quick"),
                    "firmware_version": live.get("firmware_version"),
                    "online": live.get("online"),
                    "color": color,
                }
            )
        online = [u["device_id"] for u in units if u["online"]]
        default = units[0]["device_id"] if len(units) == 1 else (online[0] if online else None)
        return {
            "default_unit": default or (units[0]["device_id"] if units else None),
            "host_address": self.host_address,
            "language": normalize(lang or self.language),
            "update_source_set": bool(self.update_source),
            "host_version": _host_version(),
            "units": units,
        }

    def save(self, device_id: str, values: dict[str, Any]) -> dict[str, Any]:
        if device_id not in self.devices():
            raise SettingsError("That unit is not paired. Pair it first, then open its settings.")
        saved = self.store.update(device_id, values)
        self._notify_saved(device_id, values)
        return saved

    def _notify_saved(self, device_id: str, values: dict[str, Any]) -> None:
        """Tell the running host a setting changed (idle movement, noise level) so it acts at once."""
        hook = getattr(self, "on_saved", None)
        if hook is not None:
            try:
                hook(device_id, values)
            except Exception:  # a hook must never fail a save
                logging.getLogger(__name__).warning("settings hook failed", exc_info=True)

    def update(self, device_id: str, lang: str | None = None, *, dry_run: bool = True) -> str:
        """The Update button: check the signed release. It only checks (dry run) unless the caller
        passes dry_run=False after the person confirmed; then it pushes over the air, which needs
        the host's push (a unit that is online). Without one, the refusal says what to do."""
        lang = normalize(lang or self.language)
        folder = updater.read_source(self.update_source)
        if folder is None:
            raise updater.UpdateRefused(t(lang, "settings.update.none"))
        release = updater.load_release(
            folder, public_key=self.public_key, preset=self.preset, lang=lang
        )
        unit_version = self.live(device_id).get("firmware_version")
        try:
            return updater.update_over_air(
                release,
                device_id=device_id,
                unit_version=unit_version,
                push=self.push,
                dry_run=dry_run,
                lang=lang,
            )
        except updater.UpdateRefused as error:
            if unit_version and not updater.is_newer(release.version, unit_version):
                raise updater.UpdateRefused(t(lang, "settings.update.current")) from error
            raise

    # -- face settings (faces.py): one section per unit on the page ----------------------------

    def _face_unit(self, device_id: str) -> None:
        if device_id not in self.devices():
            raise face_settings.FaceError(
                "That unit is not paired. Pair it first, then open its face settings."
            )

    def _faces_get(self, device_id: str, lang: str) -> tuple[int, str, bytes]:
        try:
            self._face_unit(device_id)
            view = face_settings.settings_view(self.faces, device_id, lang)
            return 200, JSON, json.dumps(view).encode()
        except face_settings.FaceError as error:
            return 400, JSON, json.dumps({"error": str(error)}).encode()

    def _faces_post(self, rest: str, body: dict[str, Any], lang: str) -> tuple[int, dict[str, Any]]:
        """Save and send one unit's face settings. ``.../reset`` goes back to the plain face."""
        values = {k: v for k, v in body.items() if k not in {"lang", "confirm", "screen_lang"}}
        if "screen_lang" in body:
            values["lang"] = body[
                "screen_lang"
            ]  # the words on the unit's screen, not the page language
        try:
            if rest.endswith("/reset"):
                device_id = rest[: -len("/reset")]
                self._face_unit(device_id)
                return 200, self.faces.reset(device_id, lang)
            self._face_unit(rest)
            return 200, face_settings.apply_settings(self.faces, rest, values, lang)
        except face_settings.FaceError as error:
            return 400, {"error": str(error)}

    # -- unit extras (unit_extras.py): reactions, clock, network test, details, face extras, people ----

    def _unit_known(self, device_id: str) -> None:
        if device_id not in self.devices():
            raise extras_mod.ExtrasError(
                "That unit is not paired. Pair it first, then open its settings."
            )

    _DEVICE_KEYS = ("volume", "brightness", "idle_motion", "idle_movement", "look_speaker", "look_faces", "look_on_wake", "dance_to_music", "face_owner", "led", "mute", "vision_off", "quiet")

    def _saved_device(self, device_id: str) -> dict[str, Any]:
        own = self.store.get(device_id)
        return {
            "volume": own.get("volume", 70),
            "brightness": own.get("brightness", 100),
            "idle_motion": own.get("idle_motion", True),
            "idle_movement": own.get("idle_movement", "off"),
            "look_speaker": own.get("look_speaker", False),
            "look_faces": own.get("look_faces", False),
            "look_on_wake": own.get("look_on_wake", True),
            "dance_to_music": own.get("dance_to_music", False),
            "dance_status": self._dance_status(device_id),
            "face_owner": own.get("face_owner", "robot"),
            "led": own.get("led", "off"),
        }

    def _dance_status(self, device_id: str) -> str:
        """The plain state of "Dance to music" for the page: off, waiting, listening, dancing, paused or unsupported (see music_dance_wiring.status_code)."""
        hook = getattr(self, "music_status", None)
        saved = bool(self.store.get(device_id).get("dance_to_music", False))
        if hook is None:
            return "waiting" if saved else "off"
        try:
            return str(hook(saved))
        except Exception:
            return "waiting" if saved else "off"

    def _device_post(self, device_id: str, values: dict[str, Any], lang: str) -> dict[str, Any]:
        """One everyday control: send it to the unit, then keep the value here so the page can show it again."""
        keys = [k for k in values if k in self._DEVICE_KEYS]
        if len(keys) != 1 or len(values) != 1:
            raise extras_mod.ExtrasError(device_mod._words(lang, "bad_value", field=", ".join(values) or "(none)"))
        key, value = keys[0], values[keys[0]]
        try:
            if key == "volume":
                result = self.device.set_volume(device_id, value, lang)
            elif key == "brightness":
                result = self.device.set_brightness(device_id, value, lang)
            elif key == "dance_to_music":
                if not isinstance(value, bool):
                    raise SettingsError("Dance to music must be on or off. Choose on or off and save again.")
                self.store.update(device_id, {key: value})
                self._notify_saved(device_id, {key: value})  # app.py turns the music dance controller on or off
                return {"ok": True, key: value, "status": self._dance_status(device_id)}
            elif key in ("look_speaker", "look_faces", "look_on_wake"):
                self.store.update(device_id, {key: value})
                self._notify_saved(device_id, {key: value})
                return {"ok": True, key: value}
            elif key == "face_owner":
                if value not in ("robot", "hub", "off"):
                    raise SettingsError("Who turns toward faces must be this robot, my Home hub or off. Pick one and save again.")
                self.store.update(device_id, {"face_owner": value})
                self._notify_saved(device_id, {"face_owner": value})
                pushed = self.polish.prefs.resend_look(device_id, lang)  # the unit hears "off", or its own choice again
                return {"ok": True, "face_owner": value, "pushed": pushed.get("pushed"), "pending": bool(pushed.get("pending")), "message": pushed.get("message", "")}
            elif key == "idle_movement":
                # The host decides every idle head move from this level (power_idle and the looks
                # in app.py); the unit's own flag follows it, so nothing here talks to the unit.
                self.store.update(device_id, {"idle_movement": value})
                self._notify_saved(device_id, {"idle_movement": value})
                return {"ok": True, "idle_movement": value}
            elif key == "idle_motion":
                result = self.device.set_idle_motion(device_id, value, lang)
                self._notify_saved(device_id, {"idle_motion": value})
            elif key == "led":
                result = self.device.set_led(device_id, value, lang)
            else:
                result = self.device.set_privacy(device_id, key, value, lang)
        except SettingsError as error:
            raise extras_mod.ExtrasError(str(error)) from error
        keep = {"mute": "muted"}.get(key, key)
        if keep in {"volume", "brightness", "idle_motion", "led", "muted"}:
            self.store.update(device_id, {keep: value})
        return result

    def _remote_post(self, device_id: str, values: dict[str, Any], lang: str, controller: dict[str, Any] | None = None) -> dict[str, Any]:
        """One Remote button, after the robot has shown who is acting (see remote_activity.py)."""
        do = str(values.get("do"))
        return self.activity.act(device_id, do, values, lambda: self._remote_dispatch(device_id, values, lang), lang, controller=controller)

    def _remote_dispatch(self, device_id: str, values: dict[str, Any], lang: str) -> dict[str, Any]:
        """One Remote button: ``{"do": "beep" | "flash" | "find" | "say" | "head" | "center" | "look" | "nod" | "shake" | "dance" | "stop_dance" | "game" | "photo", ...}``."""
        remote = self.remote
        do = values.get("do")
        if do == "beep":
            return remote.beep(device_id, values.get("sound", "success"), lang)
        if do == "flash":
            return remote.flash(device_id, values.get("color", values.get("colour")), lang)  # "colour": older page
        if do == "find":
            return remote.find(device_id, values.get("on"), lang)
        if do == "say":
            return remote.say(device_id, values.get("text"), lang)
        if do == "head":
            return remote.head(device_id, values.get("yaw"), values.get("pitch"), lang)
        if do == "center":
            return remote.center(device_id, lang)
        if do == "look":
            return remote.look_around(device_id, lang)
        if do == "nod":
            return remote.nod(device_id, lang)
        if do == "shake":
            return remote.shake(device_id, lang)
        if do == "mute":
            return remote.mute(device_id, values.get("on"), lang)
        if do == "dance":
            return remote.dance(device_id, values.get("name"), lang)
        if do == "stop_dance":
            return remote.stop_dance(device_id, lang)
        if do == "game":
            return remote.game(device_id, values.get("name"), lang)
        if do == "photo":
            return remote.photo(device_id, lang)
        if do == "overlay":
            return self.polish.overlays.remote_set(device_id, values.get("name"), values.get("intensity"), values.get("seconds"), lang)
        if do == "overlay_clear":
            return self.polish.overlays.remote_clear(device_id, lang)
        if do == "scene":
            return self.polish.scene_test(device_id, values.get("name"), lang)
        raise extras_mod.ExtrasError(device_mod._words(lang, "bad_value", field=str(do)))

    def _cue_view(self, device_id: str, lang: str) -> dict[str, Any]:
        state = self.activity.state(lang, unit_id=device_id)
        return {"cue": state["cue"], "cue_note": state["cue_note"], "speaking": state["speaking"]}

    def _access_get(self, lang: str) -> tuple[int, str, bytes]:
        return 200, JSON, json.dumps(self.activity.state(lang)).encode()

    def _access_post(self, rest: str, body: dict[str, Any], local_admin: bool, lang: str) -> tuple[int, dict[str, Any]]:
        """POST /api/stackchan/remote-access[/pair|allow|revoke|act]. Pairing and acting are the only routes a
        paired controller (not this machine's page) may call; they refuse everything unless access is on."""
        values = {k: v for k, v in body.items() if k not in {"lang", "confirm"}}
        activity = self.activity
        try:
            if rest == "pair":
                if not activity.store.settings()["enabled"]:
                    raise extras_mod.ExtrasError(activity_mod._w(lang, "off"))
                return 200, {"ok": True, **activity.store.pair(values.get("label"), lang)}
            if rest == "act":
                controller = activity.store.find(values.get("token"))
                if controller is None:
                    raise extras_mod.ExtrasError(activity_mod._w(lang, "no_controller"))
                if controller.get("status") != "paired":
                    raise extras_mod.ExtrasError(activity_mod._w(lang, "pending"))
                unit = str(values.get("unit", ""))
                self._unit_known(unit)
                acting = {k: v for k, v in values.items() if k not in {"token", "unit"}}
                return 200, self._remote_post(unit, acting, lang, controller)
            if not local_admin:
                return 403, {"error": t(lang, "settings.local_only")}
            if rest == "":
                return 200, {"ok": True, **activity.store.update(values, lang)}
            if rest in {"allow", "revoke"}:
                getattr(activity.store, rest)(values.get("id"), lang)
                return 200, {"ok": True, "controllers": activity.store.controllers()}
        except (extras_mod.ExtrasError, SettingsError) as error:
            return 400, {"error": str(error)}
        return 404, {"error": "not found"}

    def _people_view(self) -> dict[str, Any]:
        return {
            "people": [p.to_json() for p in self.people.all()],
            "choices": {
                "color": ["none", *face_settings.PALETTE],
                "caption_size": list(face_settings.CAPTION_SIZES),
            },
            "limits": {"people": extras_mod.PEOPLE_MAX},
            "problem": self.people.problem,
        }

    def _unit_get(self, rest: str, lang: str) -> tuple[int, str, bytes]:
        """GET /api/stackchan/unit/<id>/(reactions|clock|details|games)."""
        device_id, _, what = rest.rpartition("/")
        try:
            self._unit_known(device_id)
            if what == "reactions":
                body = self.extras.reactions_view(device_id)
            elif what == "clock":
                body = self.extras.clock_view(device_id)
            elif what == "details":
                body = self.extras.details(device_id, lang)
            elif what == "games":
                body = self.extras.games(device_id, lang)
            elif what == "pictures":
                body = self.pictures.view(device_id, lang)
            elif what == "remote":
                body = {**self.remote.view(device_id, lang), **self._cue_view(device_id, lang)}
            elif what == "overview":
                body = {**self.device.overview(device_id, lang), "saved": self._saved_device(device_id)}
            elif what == "travel":
                body = self.extras.travel_view(device_id, lang)
            elif what == "prefs":
                body = self.polish.prefs.view(device_id, lang)
            elif what == "pages":
                body = self.polish.pages.view(device_id, lang)
            elif what == "link":
                if self._link is None:
                    return 404, JSON, json.dumps({"error": "not found"}).encode()
                body = self._link.view(device_id)
            elif what == "lock":
                body = self.polish.lock.view(device_id, lang)
            elif what == "scenes":
                body = self.polish.scenes.view(device_id)
            elif what == "packs":
                body = self.polish.packs.view(device_id, lang)
            elif what == "fillers":
                body = self._fillers_view(device_id)
            elif what == "phrases":
                body = self._phrases_view(device_id)
            else:
                return 404, JSON, json.dumps({"error": "not found"}).encode()
            return 200, JSON, json.dumps(body).encode()
        except (
            extras_mod.ExtrasError,
            face_settings.FaceError,
            picture_mod.PictureError,
            packs_mod.PackError,
            overlays_mod.OverlayError,
            scenes_mod.SceneError,
            SettingsError,
        ) as error:
            return 400, JSON, json.dumps({"error": str(error)}).encode()

    def _fillers_view(self, device_id: str) -> dict[str, Any]:
        polish = self.polish
        return {
            "packs": polish.library.list("filler"),
            "active": polish.active.get(device_id).get("filler"),
            "status": dict(polish.generator.status),
            "can_make": polish.generator.synth is not None,
        }

    def _phrases_view(self, device_id: str) -> dict[str, Any]:
        """The offline phrases of this unit: the packs in the library, the one it should hold, what the unit says it holds."""
        polish = self.polish
        wanted = polish.packs.wanted(device_id).get("phrase")
        unit = polish.packs.unit_state(device_id).get("phrase", {}) if polish.probe.has(device_id, "pack") is True else {}
        return {
            "packs": polish.library.list("phrase"),
            "wanted": wanted,
            "unit": unit,
            "languages": phrase_packs_mod.languages(),
            "status": dict(polish.phrases.status),
            "can_make": polish.phrases.synth is not None,
        }

    def _polish_post(self, device_id: str, action: str, values: dict[str, Any], lang: str) -> tuple[int, dict[str, Any]]:
        """POST /api/stackchan/unit/<id>/<prefs|listen-test|packs/activate|packs/sync|fillers/generate|phrases/generate>."""
        polish = self.polish
        if action == "prefs":
            return 200, polish.prefs.save(device_id, values, lang)
        if action in {"pages", "pages/show", "pages/tiles"}:
            if action == "pages":
                reply = polish.pages.save(device_id, values, lang)
            elif action == "pages/show":
                reply = polish.pages.show(device_id, str(values.get("name") or ""), lang)
            else:
                reply = polish.pages.push_tiles(device_id, values.get("tiles"), lang)
            return (400 if reply.get("ok") is False and "error" in reply else 200), reply
        if action in {"lock", "lock/clear", "lock/now", "lock/auto"}:
            # The code goes from this request to the unit tool and nowhere else: it is never logged, stored or echoed (unit_lock.py).
            if action == "lock":
                reply = polish.lock.set_code(device_id, values.get("code"), values.get("confirm_code"), values.get("current"), lang)
            elif action == "lock/clear":
                reply = polish.lock.clear_code(device_id, values.get("current"), lang)
            elif action == "lock/now":
                reply = polish.lock.lock_now(device_id, lang)
            else:
                reply = polish.lock.set_auto(device_id, values.get("auto_minutes"), lang)
            return (400 if reply.get("ok") is False else 200), reply
        if action == "scenes":
            if values.get("reset") is True:
                return 200, polish.scenes.reset(device_id, values.get("name"), lang)
            return 200, polish.scenes.save(device_id, values.get("name"), {k: v for k, v in values.items() if k != "name"}, lang)
        if action == "listen-test":
            return 200, polish.prefs.test_listen(device_id, lang)
        if action == "packs/activate":
            return 200, polish.packs.activate(device_id, values.get("type"), values.get("pack_id"), lang)
        if action == "fillers/generate":
            voice = str(values.get("voice") or "default")[:40]
            return 200, polish.make_fillers(device_id, voice, str(values.get("lang") or lang))
        if action == "phrases/generate":
            voice = str(values.get("voice") or "default")[:40]
            return 200, polish.make_phrases(device_id, voice, str(values.get("for_lang") or lang))  # "lang" is the page's language, not the pack's
        if action == "packs/sync":
            return 200, {"ok": True, "done": polish.packs.sync_types(device_id, packs_mod.MANAGED)}
        return 404, {"error": "not found"}

    def _packs_post(self, action: str, values: dict[str, Any], lang: str) -> tuple[int, dict[str, Any]]:
        """POST /api/stackchan/packs/<import|export|delete>."""
        service = self.polish.packs
        if action == "import":
            return 200, service.import_pack(values.get("b64"), lang)
        if action == "export":
            return 200, service.export_pack(values.get("pack_id"), lang)
        if action == "delete":
            return 200, service.delete_pack(values.get("pack_id"), lang)
        return 404, {"error": "not found"}

    def _pictures_post(
        self, device_id: str, action: str, values: dict[str, Any], lang: str
    ) -> tuple[int, dict[str, Any]]:
        """POST /api/stackchan/unit/<id>/pictures/<add|remove|options|send|clear>."""
        self._unit_known(device_id)
        service = self.pictures
        if action == "add":
            try:
                raw = base64.b64decode(str(values.get("rgba_b64", "")), validate=True)
                width, height = int(values.get("width", 0)), int(values.get("height", 0))
                index = int(values.get("index", 0))
            except (ValueError, TypeError):
                raise picture_mod.PictureError(
                    picture_mod.say(lang, "bad_picture"), "bad_picture"
                ) from None
            return 200, service.add_picture(
                device_id, str(values.get("slot", "")), index, width, height, raw, lang
            )
        if action == "remove":
            index = values.get("index")
            return 200, service.remove_picture(
                device_id,
                str(values.get("slot", "")),
                index if isinstance(index, int) else None,
                lang,
            )
        if action == "options":
            overlay = values.get("overlay")
            fps = values.get("fps")
            return 200, service.set_options(
                device_id,
                mode=values.get("mode"),
                fps=fps if isinstance(fps, int) and not isinstance(fps, bool) else None,
                overlay=overlay if isinstance(overlay, dict) else None,
                lang=lang,
            )
        if action == "import-character":
            return character_pack_mod.import_for_page(service, device_id, values.get("b64"), lang)
        if action == "send":
            return 200, service.send(device_id, lang)
        if action == "clear":
            return 200, service.clear_all(device_id, lang)
        return 404, {"error": "not found"}

    def _unit_post(self, rest: str, body: dict[str, Any], lang: str) -> tuple[int, dict[str, Any]]:
        """POST /api/stackchan/unit/<id>/<action>, and the people routes."""
        values = {k: v for k, v in body.items() if k not in {"lang", "confirm"}}
        try:
            if rest == "people" or rest.startswith("people/"):
                return self._people_post(rest, values, lang)
            for polish_action in ("prefs", "scenes", "pages", "pages/show", "pages/tiles", "lock", "lock/clear", "lock/now", "lock/auto", "listen-test", "packs/activate", "packs/sync", "fillers/generate", "phrases/generate"):
                if rest.endswith("/" + polish_action):
                    device_id = rest[: -len(polish_action) - 1]
                    self._unit_known(device_id)
                    return self._polish_post(device_id, polish_action, values, lang)
            if rest.endswith("/link") and self._link is not None:
                device_id = rest[: -len("/link")]
                self._unit_known(device_id)
                try:
                    return 200, {**self._link.set_mode(device_id, values.get("mode")), "message": "Saved."}
                except ValueError as error:
                    return 400, {"error": str(error)}
            if "/pictures/" in rest:
                device_id, _, action = rest.partition("/pictures/")
                return self._pictures_post(device_id, action, values, lang)
            device_id, _, action = rest.rpartition("/")
            if action == "reset" and device_id.endswith("/reactions"):
                device_id = device_id[: -len("/reactions")]
                self._unit_known(device_id)
                return 200, self.extras.reset_reactions(device_id, lang)
            self._unit_known(device_id)
            if action == "reactions":
                return 200, self.extras.save_reactions(device_id, values, lang)
            if action == "clock":
                if values.get("sync") is True:
                    return 200, self.extras.set_clock_now(device_id, lang)
                return 200, self.extras.save_zone(device_id, values.get("zone"), lang)
            if action == "network-test":
                result = self.extras.network_test(device_id, lang)
                return 200, {**result, "message": result.get("summary", "")}
            if action == "remote":
                return 200, self._remote_post(device_id, values, lang)
            if action == "device":
                return 200, self._device_post(device_id, values, lang)
            if action == "reset":
                return 200, self.device.reset(device_id, values.get("confirm_word"), lang)
            if action == "travel":
                return 200, self.extras.travel_set(device_id, values, lang)
            if action == "decorate":
                seconds = values.get("seconds", face_settings.DECOR_DEFAULT_S)
                return 200, self.faces.decorate(
                    device_id, str(values.get("name", "none")), seconds, lang
                )
            return 404, {"error": "not found"}
        except (
            extras_mod.ExtrasError,
            face_settings.FaceError,
            picture_mod.PictureError,
            packs_mod.PackError,
            overlays_mod.OverlayError,
            scenes_mod.SceneError,
            SettingsError,
        ) as error:
            return 400, {"error": str(error)}

    def _people_post(
        self, rest: str, values: dict[str, Any], lang: str
    ) -> tuple[int, dict[str, Any]]:
        if rest == "people":
            person = extras_mod.clean_person(values, lang)
            self.people.save(person, lang)
            return 200, self._people_view()
        parts = rest.split("/")  # people/<id>/remove  or  people/<id>/use/<unit>
        pid = parts[1] if len(parts) > 1 else ""
        if len(parts) == 3 and parts[2] == "remove":
            self.people.remove(pid)
            return 200, self._people_view()
        if len(parts) == 4 and parts[2] == "use":
            person = next((p for p in self.people.all() if p.id == pid), None)
            if person is None:
                raise extras_mod.ExtrasError(extras_mod.say(lang, "person_unknown"))
            self._unit_known(unquote(parts[3]))
            return 200, extras_mod.apply_person(self.faces, unquote(parts[3]), person, lang)
        return 404, {"error": "not found"}

    # -- routes shared by every server that hosts the page ------------------------------------

    def _wakeword_post(self, action: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """clip | train | install | clear, for the wake word maker package. A message is plain words; nothing is logged."""
        import base64
        import binascii

        word = str(body.get("word", ""))
        try:
            if action == "clip":
                try:
                    wav = base64.b64decode(str(body.get("wav_b64", "")), validate=True)
                except (binascii.Error, ValueError):
                    return 400, {"error": "The recording did not arrive whole. Try recording again."}
                count = self.wakeword.store.add_clip(word, str(body.get("kind", "")), wav)
                return 200, {"count": count, **self.wakeword.state(word)}
            if action == "train":
                return 200, self.wakeword.train(word)
            if action == "install":
                return 200, {"installed": self.wakeword.install(word)}
            if action == "clear":
                self.wakeword.store.clear(word)
                return 200, self.wakeword.state(word)
        except ValueError as error:  # ClipError is a ValueError
            return 400, {"error": str(error)}
        return 404, {"error": "not found"}

    def _phone_link_view(self) -> dict[str, Any]:
        """The address and QR code that log a phone in to this page (host computer only)."""
        info = self.phone_link() if self.phone_link else {"lan": False}
        if not info.get("lan"):
            return {
                "enabled": False,
                "note": "The page is for this computer only. To open it from a phone, set lan = true under [settings] in robot.toml and restart the host.",
            }
        import io

        import segno

        url = f"{info['base']}/settings?token={info['token']}"
        out = io.BytesIO()
        segno.make(url, error="m").save(out, kind="svg", xmldecl=False, nl=False, scale=6, border=2)
        return {"enabled": True, "url": url, "svg": out.getvalue().decode("ascii")}

    def route_get(self, path: str, lang: str, local_admin: bool) -> tuple[int, str, bytes] | None:
        """(status, content type, body) for a settings GET, or None when it is not a settings path."""
        if path.startswith(FACES):
            if not local_admin:
                return 403, JSON, json.dumps({"error": t(lang, "settings.local_only")}).encode()
            return self._faces_get(unquote(path[len(FACES) :]), lang)
        if path == PACKS:
            if not local_admin:
                return 403, JSON, json.dumps({"error": t(lang, "settings.local_only")}).encode()
            return 200, JSON, json.dumps(self.polish.packs.library_view()).encode()
        if path == WAKEWORD or path.startswith(WAKEWORD + "/"):
            if self.wakeword is None:
                return 200, JSON, json.dumps({"enabled": False}).encode()
            if local_admin is not True:
                return 403, JSON, json.dumps({"error": t(lang, "settings.local_only")}).encode()
            word = unquote(path[len(WAKEWORD) + 1 :])
            try:
                return 200, JSON, json.dumps(self.wakeword.state(word)).encode()
            except ValueError as error:
                return 400, JSON, json.dumps({"error": str(error)}).encode()
        if (path == INSTALLED_PAGE or path == INSTALLED or path.startswith(INSTALLED + "/")) and self.installed is not None:
            if local_admin is not True:
                return 403, JSON, json.dumps({"error": t(lang, "settings.local_only")}).encode()
            if path == INSTALLED_PAGE:
                from maipai_body.installed_page import render_installed_page

                return 200, "text/html; charset=utf-8", render_installed_page()
            if path == INSTALLED:
                return 200, JSON, json.dumps({"units": self.installed_units()}).encode()
            return 200, JSON, json.dumps(self.installed.view(unquote(path[len(INSTALLED) + 1 :]))).encode()
        if path in (HEALTH_PAGE, HEALTH) and self.health is not None:
            if local_admin is not True:
                return 403, JSON, json.dumps({"error": t(lang, "settings.local_only")}).encode()
            from maipai_body import health as health_mod

            doc = self.health()
            if path == HEALTH_PAGE:
                return 200, "text/html; charset=utf-8", health_mod.render_page(doc)
            return 200, JSON, json.dumps(doc).encode()
        if path in (BRAIN_PAGE, BRAIN) and self.brain_setup is not None:
            if local_admin is not True:
                return 403, JSON, json.dumps({"error": t(lang, "settings.local_only")}).encode()
            if path == BRAIN_PAGE:
                from maipai_body.brain_page import render_brain_page

                return 200, "text/html; charset=utf-8", render_brain_page()
            return 200, JSON, json.dumps(self.brain_setup.view()).encode()
        if path == PAIR_WAITING:
            if local_admin is not True:
                return 403, JSON, json.dumps({"error": t(lang, "settings.local_only")}).encode()
            waiting = self.pair_exchange.waiting_exchanges() if self.pair_exchange else []
            return 200, JSON, json.dumps({"waiting": waiting}).encode()
        if path == PHONE_LINK:
            if local_admin is not True:
                return 403, JSON, json.dumps({"error": t(lang, "settings.local_only")}).encode()
            return 200, JSON, json.dumps(self._phone_link_view()).encode()
        if path == ACCESS:
            if local_admin is not True:
                return 403, JSON, json.dumps({"error": t(lang, "settings.local_only")}).encode()
            return self._access_get(lang)
        if path.startswith(UNIT) or path == PEOPLE:
            if not local_admin:
                return 403, JSON, json.dumps({"error": t(lang, "settings.local_only")}).encode()
            if path == PEOPLE:
                return 200, JSON, json.dumps(self._people_view()).encode()
            return self._unit_get(unquote(path[len(UNIT) :]), lang)
        if path != "/settings" and not path.startswith("/api/stackchan/settings"):
            return None
        if not local_admin:
            return 403, JSON, json.dumps({"error": t(lang, "settings.local_only")}).encode()
        if path == "/settings":
            return 200, "text/html; charset=utf-8", render_page(lang)
        if path == "/api/stackchan/settings":
            return 200, JSON, json.dumps(self.state(lang)).encode()
        return 404, JSON, json.dumps({"error": "not found"}).encode()

    def _installed_post(self, rest: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """`<unit>/choose` saves Automatic or a custom set that fits and starts sending it; `<unit>/retry` tries again now."""
        unit, _, action = unquote(rest).partition("/")
        if action == "choose":
            try:
                chosen = body.get("chosen") if isinstance(body.get("chosen"), dict) else None
                view = self.installed.choose(unit, str(body.get("mode", "")), chosen)
            except ValueError as error:
                return 400, {"error": str(error)}
            threading.Thread(target=self.installed.reconcile, args=(unit,), name="installed-set-apply", daemon=True).start()
            return 200, view
        if action == "retry":
            threading.Thread(target=self.installed.reconcile, args=(unit,), name="installed-set-apply", daemon=True).start()
            return 200, {"ok": True}
        return 404, {"error": "not found"}

    def _brain_post(self, action: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """The Brain page's buttons: test an address, apply a mode, install, stop and remove the local stack."""
        setup = self.brain_setup
        if action == "test":
            return 200, setup.test(str(body.get("kind", "")), str(body.get("url", "")), str(body.get("model", "")), str(body.get("api_key", "")))
        if action == "apply":
            result = setup.apply(str(body.get("mode", "")), body)
            return (200 if result.get("ok") else 400), result
        if action == "install":
            result = setup.install(str(body.get("choice", "")))
            return (200 if result.get("ok") else 400), result
        if action == "stop":
            setup.installer.stop()
            return 200, {"ok": True}
        if action == "remove":
            return 200, setup.remove()
        return 404, {"error": "not found"}

    def route_post(
        self, path: str, body: dict[str, Any], local_admin: bool
    ) -> tuple[int, dict[str, Any]] | None:
        """(status, JSON payload) for a settings POST, or None when it is not a settings path.

        The update route checks the release and changes nothing unless the body says
        ``"confirm": true``."""
        prefix = "/api/stackchan/settings/"
        if path.startswith(WAKEWORD + "/"):
            if self.wakeword is None:
                return None
            if local_admin is not True:
                return 403, {"error": t(normalize(str(body.get("lang", "")) or self.language), "settings.local_only")}
            return self._wakeword_post(path[len(WAKEWORD) + 1 :], body)
        if path.startswith(INSTALLED + "/") and self.installed is not None:
            if local_admin is not True:
                return 403, {"error": t(normalize(str(body.get("lang", "")) or self.language), "settings.local_only")}
            return self._installed_post(path[len(INSTALLED) + 1 :], body)
        if path.startswith(BRAIN + "/") and self.brain_setup is not None:
            if local_admin is not True:
                return 403, {"error": t(normalize(str(body.get("lang", "")) or self.language), "settings.local_only")}
            return self._brain_post(path[len(BRAIN) + 1 :], body)
        if path == PAIR_CODE_ENTRY and self.pair_exchange is not None:
            if local_admin is not True:
                return 403, {"error": t(normalize(str(body.get("lang", "")) or self.language), "settings.local_only")}
            from maipai_body.bodies.stackchan.xiaozhi.link_exchange import ExchangeError

            try:
                self.pair_exchange.approve_exchange(
                    str(body.get("device_id", "")), str(body.get("code", "")).strip(), str(body.get("_source", "")), True
                )  # only an admin (this host, or a signed-in session) reaches this route; the server sets _source
            except ExchangeError as error:
                return 400, {"error": str(error)}
            return 200, {"ok": True, "message": "Paired. The robot now uses an encrypted link."}
        if path == PAIRING_CODE and self.pair_code is not None:
            if local_admin is not True:
                return 403, {"error": t(normalize(str(body.get("lang", "")) or self.language), "settings.local_only")}
            if self.pair_code is None:
                return None  # not a page route on this host: the dashboard's own route answers
            return 200, {"code": self.pair_code(), "minutes": 10}
        if not path.startswith(prefix) and not path.startswith((FACES, UNIT, PEOPLE, PACKS, ACCESS)):
            return None
        lang = normalize(str(body.get("lang", "")) or self.language)
        if path == ACCESS or path.startswith(ACCESS + "/"):
            return self._access_post(path[len(ACCESS) + 1 :], body, local_admin is True, lang)
        if not local_admin:
            return 403, {"error": t(lang, "settings.local_only")}
        host_only = path.endswith("/update") or "/lock" in path
        if host_only and local_admin is not True:
            return 403, {"error": t(lang, "settings.local_only")}
        if path.startswith(FACES):
            return self._faces_post(unquote(path[len(FACES) :]), body, lang)
        if path.startswith(PACKS + "/"):
            values = {k: v for k, v in body.items() if k not in {"lang", "confirm"}}
            try:
                return self._packs_post(path[len(PACKS) + 1 :], values, lang)
            except packs_mod.PackError as error:
                return 400, {"error": str(error)}
        if path.startswith(UNIT):
            return self._unit_post(unquote(path[len(UNIT) :]), body, lang)
        if path == PEOPLE or path.startswith(PEOPLE + "/"):
            return self._unit_post(unquote(path[len("/api/stackchan/") :]), body, lang)
        rest = path[len(prefix) :]
        try:
            if rest.endswith("/update"):
                device_id = unquote(rest[: -len("/update")])
                try:
                    message = self.update(device_id, lang, dry_run=body.get("confirm") is not True)
                except updater.UpdateRefused as error:
                    return 422, {"error": str(error)}
                return 200, {"message": message}
            body = {k: v for k, v in body.items() if k not in {"lang", "confirm"}}
            return 200, self.save(unquote(rest), body)
        except SettingsError as error:
            return 400, {"error": str(error)}


def _host_version() -> str:
    try:
        from importlib.metadata import version

        return version("maipai-bot")
    except Exception:
        return ""


JSON = "application/json"
TOKEN_ACCESS = "token"  # a settings-token login: the settings pages, not the controls that stay on the host computer
FACES = "/api/stackchan/faces/"
UNIT = "/api/stackchan/unit/"
PEOPLE = "/api/stackchan/people"
PACKS = "/api/stackchan/packs"
ACCESS = "/api/stackchan/remote-access"
PAIRING_CODE = "/api/stackchan/pairings/code"
PHONE_LINK = "/api/stackchan/phone-link"
PAIR_WAITING = "/api/stackchan/pairings/waiting"
PAIR_CODE_ENTRY = "/api/stackchan/pairings/code-entry"
BRAIN = "/api/stackchan/brain"
BRAIN_PAGE = "/brain"
INSTALLED = "/api/stackchan/installed"
INSTALLED_PAGE = "/on-my-robot"
HEALTH = "/api/stackchan/health"
HEALTH_PAGE = "/health"
WAKEWORD = "/api/stackchan/wakeword"


def render_page(lang: str | None) -> bytes:
    """The whole page for one language: one HTML document with its own style and script, no outside file."""
    from maipai_body.settings_ui import CSS, JS, PAGE

    code = normalize(lang)
    strings = catalog(code)
    page = (
        PAGE.replace("__CSS__", CSS)
        .replace("__JS__", JS)
        .replace("__PICS__", pictures_js(code))
        .replace("__STRINGS__", json.dumps(strings).replace("</", "<\\/"))
        .replace("__TITLE__", html.escape(strings["settings.title"]))
        .replace("__CODE__", code)
        .replace("__LANG__", code)
    )
    return page.encode("utf-8")
