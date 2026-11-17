# ruff: noqa: E501
"""Nobody acts on the robot without the robot showing it.

Every remote action (a Remote page button, a paired controller's request) goes through ``RemoteActivity.act``:

1. the unit is told a remote session is open (``self.remote.session``, repeated every 10 s so a crashed host clears it);
2. the unit is told what is about to happen (``self.remote.action`` with a cue token), so it shows its banner;
3. only then does the action itself run.

A unit that lacks those tools shows nothing, so the host refuses remote speech and remote photos on it (and every
controller action) unless the owner turned on "Allow remote actions on units without a remote cue". The Remote page
on this machine is local control: it needs no cue, except Say and Photo.

Every action, allowed or refused, is written to a log file that this code never shortens or clears.
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import threading
import time
from collections import deque
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from maipai_body import unit_remote
from maipai_body.hal.errors import BodyLost
from maipai_body.i18n import normalize
from maipai_body.unit_extras import ExtrasError, _JsonFile, _reply, say

logger = logging.getLogger(__name__)

MAX_SAY = 200
SAY_PER_MINUTE = 3  # the same limit the unit applies
SAY_WINDOW_S = 60.0
HEARTBEAT_S = 10.0  # the unit drops the remote glyph when it hears nothing for longer than this
SESSION_IDLE_S = 120.0  # a page that did nothing for this long is no longer "connected"
SAY_NOTICE_S = 0.8  # the unit shows the words before it speaks; the host waits this long
PHOTO_COUNTDOWN_S = 3.0  # the unit counts down on screen before the camera is used
ASK_TIMEOUT_S = 20.0  # how long the person at the robot has to tap "allow" on a remote message
SPEAKING = ("off", "ask", "on")
LOG_READ_MAX = 500

SESSION_TOOL = "self.remote.session"
ACTION_TOOL = "self.remote.action"
LOCAL_LABEL = "Settings page"

# Remote page button -> (kind sent to the unit, banner words). A stop button needs no cue and is not listed.
KINDS: dict[str, tuple[str, str]] = {
    "head": ("move", "moving"), "center": ("move", "moving"), "look": ("move", "moving"), "nod": ("move", "moving"), "shake": ("move", "moving"),
    "find": ("find", "finding me"), "photo": ("photo", "photo"), "dance": ("dance", "dance"), "game": ("game", "game"),
    "say": ("say", ""), "beep": ("sound", "sound"), "flash": ("light", "lights"), "mute": ("setting", "setting"),
    "overlay": ("look", "look"),
}  # fmt: skip
ALWAYS_REFUSED_WITHOUT_CUE = frozenset({"say", "photo"})
# How long the unit keeps a cue's kind open after its token passed the gate (the banner seconds): a find, a nod or a game
# start makes several tool calls, and each one that is marked source remote needs the cue to be open (patch TC01).
CUE_SECONDS = {"move": 6, "find": 30, "dance": 15, "game": 6, "photo": 4, "listen": 4, "say": 4}
FIND_RENEW_S = 20.0  # a find runs 90 s: the loop asks the unit for a fresh cue before the 30 s window closes

_WORDS = {
    "en": {
        "off": "Remote access is off. Turn on Remote access in the Remote activity settings, then try again.",
        "no_controller": "That controller is not paired, or it was revoked. Pair it again from the Remote activity settings.",
        "pending": "That controller is waiting to be allowed. Press Allow next to it in the Remote activity settings, then try again.",
        "no_cue": "This unit shows no remote cue yet, so a remote {kind} is refused. Update the unit firmware, or turn on Allow remote actions on units without a remote cue.",
        "cue_failed": "The unit did not accept the remote cue, so nothing was done. Check that it is on and near the router, then try again.",
        "say_off": "Remote speaking is off. Turn it on, or set it to Ask first on the robot, in the Remote activity settings.",
        "say_rate": "That is {n} remote messages in a minute. Wait a few seconds, then say it again.",
        "say_denied": "The person at the robot did not allow that message, so nothing was said.",
        "say_filtered": "That message was not sent: {why}. Change the words and try again.",
        "bad_setting": "{what} is not a choice this setting has. Pick one from the list.",
        "bad_label": "Give the controller a name of 1 to 40 characters.",
        "no_such": "That controller is not in the list. Reload the page.",
        "no_cue_note": "this unit shows no remote cue yet",
    },
    "es": {
        "off": "El acceso remoto esta apagado. Activalo en los ajustes de Actividad remota y vuelve a intentarlo.",
        "no_controller": "Ese control no esta emparejado o se revoco. Vuelve a emparejarlo en los ajustes de Actividad remota.",
        "pending": "Ese control espera permiso. Pulsa Permitir junto a el en los ajustes de Actividad remota y vuelve a intentarlo.",
        "no_cue": "Esta unidad aun no muestra aviso remoto, asi que se rechaza {kind} remoto. Actualiza el firmware o activa Permitir acciones remotas en unidades sin aviso remoto.",
        "cue_failed": "La unidad no acepto el aviso remoto, asi que no se hizo nada. Comprueba que este encendida y cerca del router, y vuelve a intentarlo.",
        "say_off": "Hablar en remoto esta apagado. Activalo, o ponlo en Preguntar primero en el robot, en los ajustes de Actividad remota.",
        "say_rate": "Son {n} mensajes remotos en un minuto. Espera unos segundos y vuelve a decirlo.",
        "say_denied": "La persona junto al robot no permitio ese mensaje, asi que no se dijo nada.",
        "say_filtered": "No se envio el mensaje: {why}. Cambia las palabras y vuelve a intentarlo.",
        "bad_setting": "{what} no es una opcion de este ajuste. Elige una de la lista.",
        "bad_label": "Dale al control un nombre de 1 a 40 caracteres.",
        "no_such": "Ese control no esta en la lista. Recarga la pagina.",
        "no_cue_note": "esta unidad aun no muestra aviso remoto",
    },
}
_KIND_NAMES = {
    "en": {"say": "message", "photo": "photo", "move": "move", "find": "find", "dance": "dance", "game": "game", "sound": "sound", "light": "light", "setting": "change", "look": "look"},
    "es": {"say": "mensaje", "photo": "foto", "move": "movimiento", "find": "busqueda", "dance": "baile", "game": "juego", "sound": "sonido", "light": "luz", "setting": "cambio", "look": "aspecto"},
}  # fmt: skip


def _w(lang: str | None, key: str, **values: object) -> str:
    table = _WORDS.get(normalize(lang)) or _WORDS["en"]
    return (table.get(key) or _WORDS["en"][key]).format(**values)


# ---------------------------------------------------------------------------------------------
# Settings and the paired controllers
# ---------------------------------------------------------------------------------------------

DEFAULTS: dict[str, Any] = {"enabled": False, "speaking": "ask", "allow_without_cue": False, "controllers": []}


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class RemoteStore:
    """The remote settings and the pairing list, in one small file. Tokens are stored as hashes."""

    def __init__(self, path: Path) -> None:
        self._file = _JsonFile(path)
        self._lock = threading.Lock()

    def _read(self) -> dict[str, Any]:
        data = self._file.read()
        merged = {**DEFAULTS, **{k: v for k, v in data.items() if k in DEFAULTS}}
        if merged["speaking"] not in SPEAKING:
            merged["speaking"] = "ask"
        merged["controllers"] = [c for c in merged["controllers"] if isinstance(c, dict) and c.get("id")]
        return merged

    def settings(self) -> dict[str, Any]:
        data = self._read()
        return {
            "enabled": bool(data["enabled"]),
            "speaking": data["speaking"],
            "allow_without_cue": bool(data["allow_without_cue"]),
        }

    def controllers(self) -> list[dict[str, Any]]:
        return [{k: v for k, v in c.items() if k != "token_hash"} for c in self._read()["controllers"]]

    def update(self, values: Mapping[str, Any], lang: str | None = None) -> dict[str, Any]:
        with self._lock:
            data = self._read()
            if "speaking" in values:
                if values["speaking"] not in SPEAKING:
                    raise ExtrasError(_w(lang, "bad_setting", what=str(values["speaking"])))
                data["speaking"] = values["speaking"]
            for key in ("enabled", "allow_without_cue"):
                if key in values:
                    if not isinstance(values[key], bool):
                        raise ExtrasError(_w(lang, "bad_setting", what=str(values[key])))
                    data[key] = values[key]
            self._file.write(data)
        return self.settings()

    def pair(self, label: object, lang: str | None = None) -> dict[str, Any]:
        """A new controller asks to pair: it is listed as waiting, and gets its token once."""
        text = label.strip() if isinstance(label, str) else ""
        if not 1 <= len(text) <= 40:
            raise ExtrasError(_w(lang, "bad_label"))
        token = secrets.token_urlsafe(24)
        with self._lock:
            data = self._read()
            entry = {"id": secrets.token_hex(4), "label": text, "token_hash": _hash(token), "status": "waiting", "asked": _stamp()}
            data["controllers"].append(entry)
            self._file.write(data)
        return {"id": entry["id"], "label": text, "token": token, "status": "waiting"}

    def allow(self, controller_id: object, lang: str | None = None) -> None:
        with self._lock:
            data = self._read()
            for entry in data["controllers"]:
                if entry["id"] == controller_id:
                    entry["status"], entry["paired"] = "paired", _stamp()
                    self._file.write(data)
                    return
        raise ExtrasError(_w(lang, "no_such"))

    def revoke(self, controller_id: object, lang: str | None = None) -> None:
        with self._lock:
            data = self._read()
            kept = [c for c in data["controllers"] if c["id"] != controller_id]
            if len(kept) == len(data["controllers"]):
                raise ExtrasError(_w(lang, "no_such"))
            data["controllers"] = kept
            self._file.write(data)

    def find(self, token: object) -> dict[str, Any] | None:
        if not isinstance(token, str) or not token:
            return None
        digest = _hash(token)
        for entry in self._read()["controllers"]:
            if secrets.compare_digest(entry.get("token_hash", ""), digest):
                return {k: v for k, v in entry.items() if k != "token_hash"}
        return None


def _stamp(now: float | None = None) -> str:
    return datetime.fromtimestamp(time.time() if now is None else now).astimezone().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------------------------
# The log: append only
# ---------------------------------------------------------------------------------------------


class RemoteLog:
    """Every remote action: when, which controller, what, what was said, and how it ended.

    There is no delete, trim or clear. A page that shows it shows the newest rows first and may filter them."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def add(self, *, controller: str, unit: str, action: str, text: str = "", result: str = "done", note: str = "", now: float | None = None) -> None:
        row = {"time": _stamp(now), "controller": controller, "unit": unit, "action": action, "text": text, "result": result, "note": note}
        line = json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line)

    def rows(self, *, controller: str | None = None, action: str | None = None, unit: str | None = None, limit: int = LOG_READ_MAX) -> list[dict[str, Any]]:
        """Newest first. A damaged line is skipped, never repaired."""
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return []
        out: list[dict[str, Any]] = []
        for line in reversed(lines):
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if not isinstance(row, dict):
                continue
            if controller and row.get("controller") != controller:
                continue
            if action and row.get("action") != action:
                continue
            if unit and row.get("unit") != unit:
                continue
            out.append(row)
            if len(out) >= limit:
                break
        return out


# ---------------------------------------------------------------------------------------------
# The service
# ---------------------------------------------------------------------------------------------


def _gated_kind(name: str, arguments: Mapping[str, Any]) -> str | None:
    """The cue kind a unit tool call belongs to when it is a remote-facing action, else None (patch TC01)."""
    if name == "self.robot.set_head_angles":
        return "move"
    if name == "self.robot.dance":
        return "dance"
    if name == "self.game.start":
        return "game"
    if name == "self.audio.play_sound" and arguments.get("find") == 1:
        return "find"
    if name == "self.listen.test":
        return "listen"
    if name == "self.camera.take_photo":
        return "photo"
    return None


class RemoteCue:
    """The cue of one controller action, as the unit answered it: marks the action's unit tool calls ``source: remote`` and
    carries the one-use token on the first of them (the unit then keeps the kind open for the banner time).

    A unit that answered no token has no gate: its calls go unmarked, as before."""

    def __init__(self, kind: str, token: object, renew: Callable[[], object] | None = None, clock: Callable[[], float] = time.monotonic) -> None:
        self.kind = kind
        self.token = token if isinstance(token, int) and not isinstance(token, bool) and token > 0 else 0
        self.gated = self.token > 0  # a unit whose cue answer has no token has no gate
        self._renew, self._clock = renew, clock
        self._at = clock()

    def marker(self, name: str, arguments: Mapping[str, Any]) -> dict[str, object]:
        if not self.gated:
            return {}
        kind = _gated_kind(name, arguments)
        if kind is None or (kind != self.kind and not (kind == "move" and self.kind == "find")):
            return {}
        token = self.token
        self.token = 0
        if self.kind == "find" and self._renew is not None and self._clock() - self._at > FIND_RENEW_S:
            try:
                fresh = self._renew()
            except Exception:
                fresh = 0
            if isinstance(fresh, int) and not isinstance(fresh, bool) and fresh > 0:
                token, self._at = fresh, self._clock()
        out: dict[str, object] = {"source": "remote", "token": token}
        if kind == "move" and self.kind == "find":
            out["cue_kind"] = "find"
        return out


class RemoteActivity:
    def __init__(
        self,
        call: Callable[..., object],
        probe: Any,
        store: RemoteStore,
        log: RemoteLog,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        content_filter: Callable[[str], str | None] | None = None,
        heartbeat: bool = True,
    ) -> None:
        self._call, self._probe, self.store, self.log = call, probe, store, log
        self._clock, self._sleep = clock, sleep
        # Hook: returns None when the words may be said, or a short plain reason when they may not.
        self.content_filter = content_filter
        self._says: dict[str, deque[float]] = {}
        self._sessions: dict[tuple[str, str], float] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._heartbeat = heartbeat
        # Set by the page: gives the unit tool caller the cue of the action now running (a per-thread marker, or None).
        self.bind_marker: Callable[[Callable[[str, Mapping[str, Any]], dict[str, object]] | None], None] | None = None

    # ---- what the page shows ----

    def has_cue(self, unit_id: str) -> bool | None:
        """True when the unit has the remote tools, False when it does not, None when it cannot be reached."""
        try:
            return self._probe.has(unit_id, "remote")
        except Exception:
            return None

    def state(self, lang: str | None = None, *, unit_id: str | None = None) -> dict[str, Any]:
        cue = self.has_cue(unit_id) if unit_id else None
        return {
            "ok": True,
            **self.store.settings(),
            "controllers": self.store.controllers(),
            "cue": cue,
            "cue_note": _w(lang, "no_cue_note") if cue is False else "",
            "limits": {"say_chars": MAX_SAY, "say_per_minute": SAY_PER_MINUTE},
            "activity": self.log.rows(limit=LOG_READ_MAX),
        }

    # ---- one action ----

    def act(
        self,
        unit_id: str,
        do: str,
        values: Mapping[str, Any],
        run: Callable[[], dict[str, Any]],
        lang: str | None = None,
        *,
        controller: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run ``run`` for the Remote button ``do`` after the unit has shown a cue. ``controller`` is a paired
        controller's row, or None for this machine's own settings page (local control)."""
        kind_banner = KINDS.get(do)
        label = str(controller["label"]) if controller else LOCAL_LABEL
        if controller is not None and not self.store.settings()["enabled"]:
            raise ExtrasError(_w(lang, "off"))
        if kind_banner is None or (do == "find" and values.get("on") is not True):
            return run()  # stop buttons and anything that is not an action on the robot need no cue
        kind, banner = kind_banner
        text = str(values.get("text", "")).strip() if do == "say" else ""
        shown = text if do == "say" else (f"Remote: {banner}" if banner else "")
        try:
            self._allowed(unit_id, do, kind, text, label, controller is None, lang)
        except ExtrasError as error:
            self.log.add(controller=label, unit=unit_id, action=kind, text=text, result="refused", note=str(error))
            raise
        try:
            reply = self._cue(unit_id, do, kind, shown, label, lang)
            if controller is not None and reply is not None and self.bind_marker is not None:
                cue = RemoteCue(kind, reply.get("token"), lambda: self._renew(unit_id, kind, label), self._clock)
                self.bind_marker(cue.marker)
            if do == "say":
                self._wait_for_say(reply, lang)
            lead = {"say": SAY_NOTICE_S, "photo": PHOTO_COUNTDOWN_S}.get(do, 0.0)
            if reply is not None and lead:
                self._sleep(lead)
            result = run()
        except ExtrasError as error:
            self.log.add(controller=label, unit=unit_id, action=kind, text=text, result="refused", note=str(error))
            raise
        except Exception as error:
            self.log.add(controller=label, unit=unit_id, action=kind, text=text, result="failed", note=str(error))
            raise
        finally:
            if self.bind_marker is not None:
                self.bind_marker(None)
        self.log.add(controller=label, unit=unit_id, action=kind, text=text, result="done")
        return result

    def _allowed(self, unit_id: str, do: str, kind: str, text: str, label: str, local: bool, lang: str | None) -> None:
        settings = self.store.settings()
        if do == "say":
            if settings["speaking"] == "off":
                raise ExtrasError(_w(lang, "say_off"))
            if not text or len(text) > MAX_SAY:
                raise ExtrasError(unit_remote._w(lang, "bad_text", max=MAX_SAY))
            if self.content_filter is not None:
                why = self.content_filter(text)
                if why:
                    raise ExtrasError(_w(lang, "say_filtered", why=why))
            self._rate(unit_id, lang)
        cue = self.has_cue(unit_id)
        if cue is True or settings["allow_without_cue"]:
            return
        # No cue on this unit: speech and photos are always refused, and so is everything a controller asks.
        # The owner's own page on this machine may still move, beep or play (it is local control).
        if not local or do in ALWAYS_REFUSED_WITHOUT_CUE:
            if cue is None:
                raise ExtrasError(say(lang, "unreachable"))
            kind_name = (_KIND_NAMES.get(normalize(lang)) or _KIND_NAMES["en"]).get(kind, kind)
            raise ExtrasError(_w(lang, "no_cue", kind=kind_name))

    def _rate(self, unit_id: str, lang: str | None) -> None:
        now = self._clock()
        with self._lock:
            window = self._says.setdefault(unit_id, deque())
            while window and now - window[0] > SAY_WINDOW_S:
                window.popleft()
            if len(window) >= SAY_PER_MINUTE:
                raise ExtrasError(_w(lang, "say_rate", n=len(window) + 1))
            window.append(now)

    def _cue(self, unit_id: str, do: str, kind: str, shown: str, label: str, lang: str | None) -> dict[str, Any] | None:
        """Tell the unit what is about to happen. Returns the unit's reply, or None when the unit has no cue tools
        (and the settings allow going on)."""
        if self.has_cue(unit_id) is not True:
            return None
        self.begin_session(unit_id, label)
        token = secrets.token_hex(8)
        arguments: dict[str, object] = {"kind": kind, "text": shown, "label": label, "cue": token, "seconds": CUE_SECONDS.get(kind, 4)}
        if do == "say":
            arguments["confirm"] = self.store.settings()["speaking"]
        if do == "photo":
            arguments["countdown"] = int(PHOTO_COUNTDOWN_S)
        timeout = ASK_TIMEOUT_S if do == "say" and self.store.settings()["speaking"] == "ask" else 4.0
        try:
            reply = _reply(self._call(ACTION_TOOL, arguments, device_id=unit_id, timeout=timeout))
        except BodyLost:
            raise ExtrasError(_w(lang, "cue_failed")) from None
        if reply.get("ok") is False:
            raise ExtrasError(_w(lang, "cue_failed"))
        return reply

    def _renew(self, unit_id: str, kind: str, label: str) -> object:
        """A fresh cue for a long action (the find loop): the unit's new token, or 0 when it would not give one."""
        reply = _reply(self._call(ACTION_TOOL, {"kind": kind, "text": "", "label": label, "seconds": CUE_SECONDS.get(kind, 4)}, device_id=unit_id, timeout=4.0))
        return reply.get("token") if reply.get("ok") is not False else 0

    def _wait_for_say(self, reply: dict[str, Any] | None, lang: str | None) -> None:
        if reply is None or self.store.settings()["speaking"] != "ask":
            return
        if reply.get("allowed") is not True:  # silence from the robot is never a yes
            raise ExtrasError(_w(lang, "say_denied"))

    # ---- the session, so the robot shows the remote glyph while someone is connected ----

    def begin_session(self, unit_id: str, label: str) -> None:
        key = (unit_id, label)
        with self._lock:
            fresh = key not in self._sessions
            self._sessions[key] = self._clock()
        if fresh:
            self._send_session(unit_id, True, label)
        self._ensure_thread()

    def end_session(self, unit_id: str, label: str) -> None:
        with self._lock:
            known = self._sessions.pop((unit_id, label), None) is not None
        if known:
            self._send_session(unit_id, False, label)

    def tick(self) -> None:
        """One heartbeat round: renew every open session, end the idle ones."""
        now = self._clock()
        with self._lock:
            sessions = dict(self._sessions)
        for (unit_id, label), seen in sessions.items():
            if now - seen > SESSION_IDLE_S:
                self.end_session(unit_id, label)
            else:
                self._send_session(unit_id, True, label)

    def _send_session(self, unit_id: str, active: bool, label: str) -> None:
        try:
            self._call(SESSION_TOOL, {"active": active, "label": label}, device_id=unit_id, timeout=3.0)
        except Exception:
            logger.debug("remote session %s not sent to %s", active, unit_id[-5:], exc_info=True)

    def _ensure_thread(self) -> None:
        if not self._heartbeat:
            return
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, name="remote-heartbeat", daemon=True)
            self._thread.start()

    def _loop(self) -> None:
        while not self._stop.wait(HEARTBEAT_S):
            self.tick()
            with self._lock:
                if not self._sessions:
                    self._thread = None
                    return

    def close(self) -> None:
        """Host shutting down: every open session ends, so the robot clears its glyph at once."""
        self._stop.set()
        for unit_id, label in list(self._sessions):
            self.end_session(unit_id, label)
