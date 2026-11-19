# ruff: noqa: E501
"""``python -m maipai_body.settings_sim``: the settings page against simulated units, for looking and testing.

No real unit and no hub: two stand-in units answer the same tools the firmware does (face, reactions,
clock, network test, details, games, pictures, travel key), keep what they are sent, and can be read back.
Everything the page saves lands in a scratch folder, never in the real settings. Loopback only, like the
real page.
"""

from __future__ import annotations

import argparse
import json
import signal
import tempfile
import threading
from pathlib import Path
from typing import Any

from maipai_body import faces as face_settings
from maipai_body import picture_faces as picture_mod
from maipai_body import remote_activity as activity_mod
from maipai_body import unit_device as device_mod
from maipai_body import unit_extras as extras_mod
from maipai_body import unit_remote as remote_mod
from maipai_body.hal.errors import BodyLost
from maipai_body.settings_page import SettingsBackend
from maipai_body.settings_server import SettingsServer
from maipai_body.unit_polish import Polish
from maipai_body.unit_settings import UnitSettingsStore

KITCHEN = "aa:bb:cc:00:10:01"
DEN = "aa:bb:cc:00:10:02"
FEATURES = ["config", "captions", "tod", "clock", "thinking", "timers", "packs", "decor"]


class SimUnit:
    """One stand-in unit: same tool names and reply shapes as the firmware, state kept in memory."""

    def __init__(self, device_id: str, *, online: bool = True, version: str = "1.6.2-maipai.1", next_unit: bool = False) -> None:
        self.device_id, self.online, self.version = device_id, online, version
        # True: this stand-in has the tools of the next unit update (overlays, packs, fillers, prefs).
        self.next_unit = next_unit
        self.overlay: dict[str, Any] = {}
        self.pack_held: dict[str, dict[str, Any]] = {}
        self.pack_buffer: dict[str, Any] = {}
        self.prefs: dict[str, Any] = {}
        self.pages: dict[str, Any] = {}  # swipe pages (firmware patches P10 to P13)
        # The passcode lock as the unit keeps it (unit_lock.py): the code lives only here, like the unit's hash; the host never sees it.
        self.lock_code: str | None = None
        self.locked = False
        self.lock_auto = 0
        self.shown = ""
        self.tiles: list[dict[str, Any]] = []
        self.face = face_settings.FaceConfig().to_wire()
        self.table: list[dict[str, str]] | None = None
        self.zone, self.epoch = "utc", 0
        self.travel: dict[str, Any] = {"compiled": True, "enabled": False, "key_saved": False, "peer_saved": False, "joined": False, "state": "off", "ip": "", "ready": False, "route": "home", "fails": 0, "refusal": 0}
        self.pictures: dict[str, Any] = {"held": False}
        self.privacy: dict[str, Any] = {"muted": False, "vision_off": False, "quiet": False}
        self.device: dict[str, Any] = {}
        self.head = {"yaw": 0, "pitch": 5}
        self.played = 0
        self.remote_allow = True  # the person at the robot taps "allow" on a remote message
        self.accept_head = True  # False: the firmware ignores host head moves (an idle look rule)
        self.actions: list[tuple[str, dict[str, Any]]] = []
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.lock = threading.Lock()

    def handle(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self.calls.append((name, args))
            if name in NEXT_TOOLS:
                if not self.next_unit:
                    return {"ok": False, "error": f"Unknown tool: {name}"}
                return self._next(name, args)
            if name == "self.face.set_config":
                self.face.update(json.loads(args["config"]))
                return {"ok": True, **self.face, "features": FEATURES}
            if name == "self.face.get_config":
                return {"ok": True, **self.face, "features": FEATURES}
            if name in {"self.face.decorate", "self.face.thinking"}:
                return {"ok": True}
            if name == "self.reaction.set_table":
                self.table = json.loads(args["table"])
                return {"ok": True, "builtin": False, "table": self.table}
            if name == "self.reaction.get_table":
                rows = [{k: (v or "none") for k, v in r.items()} for r in (self.table or [])]
                return {"ok": True, "builtin": self.table is None, "table": rows}
            if name == "self.reaction.reset":
                self.table = None
                return {"ok": True, "builtin": True, "table": []}
            if name == "self.clock.set_zone":
                self.zone = args["zone"]
                return {"ok": True, "zone": self.zone, "local": "07:30"}
            if name == "self.clock.set":
                self.epoch = args["epoch"]
                return {"ok": True, "zone": self.zone, "local": "07:30"}
            if name == "self.network.test":
                return {
                    "ok": True,
                    "problems": 0,
                    "summary": "All good. Wi-Fi is strong and this host answers.",
                    "fix": "",
                    "steps": [
                        {"step": "wifi", "state": "ok", "line": "Wi-Fi: connected, strong signal"},
                        {"step": "host", "state": "ok", "line": "This host: answers in 12 ms"},
                        {"step": "private", "state": "ok", "line": "Private network: not needed at home"},
                    ],
                }
            if name == "self.version.get":
                return {
                    "ok": True,
                    "version": self.version,
                    "tag": "v" + self.version,
                    "image": "core",
                    "slot": "ota_0",
                    "internal_free": 55000,
                    "internal_min": 39000,
                }
            if name == "self.game.list":
                return {
                    "ok": True,
                    "playing": False,
                    "games": [
                        {"id": "memory", "title": "Color Memory", "lower_is_better": False, "scores": [7, 5, 4]},
                        {"id": "whack", "title": "Whack a Mole", "lower_is_better": False, "scores": []},
                        {"id": "tictactoe", "title": "Tic-Tac-Toe", "lower_is_better": False, "scores": [30, 10]},
                        {"id": "bopit", "title": "Do It", "lower_is_better": False, "scores": [9]},
                        {"id": "rps", "title": "Rock Paper Scissors", "lower_is_better": False, "scores": [3]},
                        {"id": "eightball", "title": "Magic 8-Ball", "lower_is_better": False, "scores": []},
                        {"id": "dice", "title": "Dice and Coin", "lower_is_better": False, "scores": []},
                    ],
                }
            if name == "self.battery.get_status":
                return {"ok": True, "percent": 78, "charging": True}
            if name == "self.privacy.get":
                return {"ok": True, **self.privacy}
            if name == "self.privacy.set":
                for key, flag in (("mute", "muted"), ("vision_off", "vision_off"), ("quiet", "quiet")):
                    if key in args:
                        self.privacy[flag] = bool(args[key])
                return {"ok": True, **self.privacy}
            if name == "self.screen.get_ambient_light":
                return {"ok": True, "lux": 180}
            if name in {"self.audio_speaker.set_volume", "self.screen.set_brightness", "self.robot.set_idle_motion", "self.robot.set_led_color"}:
                self.device[name] = dict(args)
                return {"ok": True}
            if name == "self.system.reset":
                return {"ok": False, "error": "Unknown tool: self.system.reset"}
            if name == "self.tailnet.status":
                return {"ok": True, **self.travel}
            if name == "self.robot.get_head_angles":
                return {"ok": True, **self.head}
            if name == "self.audio.sound_info":
                return {"ok": True, "played": self.played, "refused": 0, "clips_played": 0, "clips_missing": 0}
            if name == "self.robot.set_head_angles":
                self.actions.append((name, dict(args)))
                if self.accept_head:
                    self.head = {"yaw": args.get("yaw", self.head["yaw"]), "pitch": args.get("pitch", self.head["pitch"])}
                return {"ok": True}
            if name == "self.audio.play_sound":
                self.actions.append((name, dict(args)))
                if self.privacy["muted"] and not args.get("find"):
                    return {"ok": False, "error": "muted"}
                if args.get("find") != 2:
                    self.played += 1
                return {"ok": True}
            if name in {"self.audio.speak", "self.robot.dance", "self.robot.stop_dance", "self.game.start"}:
                self.actions.append((name, dict(args)))
                return {"ok": True}
            if name == "self.robot.dance_list":
                return {"ok": True, "dances": [{"name": n, "seconds": 4} for n in ("happy", "robot", "panic", "look_around", "sway", "nod_yes", "shake_no", "wiggle", "bow", "groove")]}
            if name == "self.tailnet.set":
                if args.get("forget"):
                    self.travel.update({"enabled": False, "key_saved": False, "peer_saved": False, "joined": False, "state": "off", "ip": "", "route": "home"})
                else:
                    if args.get("key"):
                        self.travel["key_saved"] = True
                    if args.get("peer"):
                        self.travel["peer_saved"] = True
                        self.travel["peer"] = args["peer"]
                    if "enabled" in args:
                        self.travel["enabled"] = bool(args["enabled"])
                    self.travel["state"] = "idle" if self.travel.get("enabled") else "off"
                    if self.travel.get("enabled") and self.travel.get("peer_saved") and args.get("key"):
                        # the stand-in joins at once so the page can show the connected state
                        self.travel.update({"state": "connected", "joined": True, "key_saved": False, "ip": "100.101.12.8", "ready": True, "route": "private"})
                return {"ok": True, **self.travel}
            if name == "self.facepic.begin":
                self.pictures = {"held": False, "mode": args.get("mode"), "frames": 0, "bytes": 0}
                return {"ok": True}
            if name == "self.facepic.frame":
                self.pictures["frames"] = int(self.pictures.get("frames", 0)) + 1
                self.pictures["bytes"] = int(self.pictures.get("bytes", 0)) + int(args.get("bytes", 0))
                return {"ok": True}
            if name == "self.facepic.data":
                return {"ok": True}
            if name == "self.facepic.commit":
                self.pictures["held"] = True
                return {"ok": True}
            if name == "self.facepic.status":
                return {"ok": True, **self.pictures, "showing": "neutral" if self.pictures["held"] else None}
            return {"ok": True}


NEXT_TOOLS = frozenset({
    "self.overlay.status", "self.overlay.set", "self.overlay.clear",
    "self.pack.status", "self.pack.begin", "self.pack.data", "self.pack.commit", "self.pack.remove",
    "self.filler.status", "self.filler.play", "self.prefs.get", "self.prefs.set", "self.listen.test",
    "self.remote.session", "self.remote.action",
    "self.look.status", "self.look.claim", "self.look.release",
    "self.pages.status", "self.pages.get", "self.pages.set", "self.page.show", "self.page.tiles",
    "self.lock.status", "self.lock.set", "self.lock.clear", "self.lock.now", "self.lock.config",
})  # fmt: skip


def _next(self: SimUnit, name: str, args: dict[str, Any]) -> dict[str, Any]:
    """The tools the next unit update brings, as the settings page expects them."""
    self.actions.append((name, dict(args)))
    if name == "self.overlay.status":
        return {"ok": True, "running": self.overlay.get("name"), "names": 16}
    if name == "self.overlay.set":
        self.overlay = dict(args)
        return {"ok": True}
    if name == "self.overlay.clear":
        self.overlay = {}
        return {"ok": True}
    if name == "self.pack.status":
        held = self.pack_held.get(str(args.get("type")), {})
        return {"ok": True, "held": bool(held), "sha256": held.get("sha256", ""), "name": held.get("name", "")}
    if name == "self.pack.begin":
        self.pack_buffer = {"meta": dict(args), "bytes": 0}
        return {"ok": True}
    if name == "self.pack.data":
        self.pack_buffer["bytes"] = int(self.pack_buffer.get("bytes", 0)) + len(str(args.get("b64", ""))) * 3 // 4
        return {"ok": True}
    if name == "self.pack.commit":
        meta = self.pack_buffer.get("meta", {})
        self.pack_held[str(meta.get("type"))] = {"sha256": meta.get("sha256", ""), "name": meta.get("name", "")}
        return {"ok": True}
    if name == "self.pack.remove":
        self.pack_held.pop(str(args.get("type")), None)
        return {"ok": True}
    if name == "self.filler.status":
        return {"ok": True, "clips": 0}
    if name == "self.prefs.get":
        return {"ok": True, **self.prefs}
    if name == "self.remote.action":
        return {"ok": True, "cue": args.get("cue"), "allowed": self.remote_allow, "token": 4242}
    if name == "self.remote.session":
        return {"ok": True, "active": bool(args.get("active"))}
    if name == "self.prefs.set":
        self.prefs.update(json.loads(args.get("json", "{}")))
        return {"ok": True}
    if name in {"self.pages.status", "self.pages.get"}:
        return {"ok": True, "version": 1, **self.pages}
    if name == "self.pages.set":
        self.pages.update(json.loads(args.get("json", "{}")))
        return {"ok": True}
    if name == "self.page.show":
        self.shown = str(args.get("name"))
        return {"ok": True}
    if name == "self.page.tiles":
        self.tiles = json.loads(args.get("json", "[]"))
        return {"ok": True, "tiles": len(self.tiles)}
    if name.startswith("self.lock."):
        return self._lock_tool(name, args)
    if name == "self.look.status":
        holder = getattr(self, "look_holder", None)
        return {"ok": True, "owner": "host" if holder else "unit", "lease_owner": holder or ""}
    if name == "self.look.claim":
        holder = getattr(self, "look_holder", None)
        if holder not in (None, args.get("owner")):
            return {"ok": False, "error": f"Face seeking is held by {holder}. Wait for it to be released."}
        self.look_holder = args.get("owner")
        return {"ok": True}
    if name == "self.look.release":
        if getattr(self, "look_holder", None) == args.get("owner"):
            self.look_holder = None
        return {"ok": True}
    return {"ok": True}


def _lock_tool(self: SimUnit, name: str, args: dict[str, Any]) -> dict[str, Any]:
    """The five lock tools with the unit's rules: while locked only status and now answer; a change to an existing code needs the current one."""
    if name == "self.lock.status":
        return {"ok": True, "has_code": self.lock_code is not None, "locked": self.locked, "auto_minutes": self.lock_auto}
    if name == "self.lock.now":
        if self.lock_code is None:
            return {"ok": False, "reason": "no_code"}
        self.locked = True
        return {"ok": True, "locked": True}
    if self.locked:
        return {"ok": False, "reason": "locked"}
    if name == "self.lock.config":
        minutes = args.get("auto_minutes")
        if minutes not in (0, 1, 15) or isinstance(minutes, bool):
            return {"ok": False, "reason": "bad_minutes"}
        self.lock_auto = minutes
        return {"ok": True, "auto_minutes": minutes}
    if name == "self.lock.clear":
        if self.lock_code is None:
            return {"ok": False, "reason": "no_code"}
        if args.get("current") != self.lock_code:
            return {"ok": False, "reason": "wrong_current"}
        self.lock_code = None
        return {"ok": True}
    code = args.get("code")  # self.lock.set
    if not (isinstance(code, str) and code.isascii() and code.isdigit() and 4 <= len(code) <= 6):
        return {"ok": False, "reason": "bad_code"}
    if self.lock_code is not None:
        if "current" not in args:
            return {"ok": False, "reason": "current_needed"}
        if args["current"] != self.lock_code:
            return {"ok": False, "reason": "wrong_current"}
    self.lock_code = code
    return {"ok": True}


SimUnit._lock_tool = _lock_tool  # type: ignore[attr-defined]
SimUnit._next = _next  # type: ignore[attr-defined]


def _sim_synth(text: str) -> tuple[Any, int]:
    """A stand-in voice: a soft rising hum whose pitch depends on the text, with quiet before and after."""
    import numpy as np

    rate = 22050
    freq = 180 + (sum(map(ord, text)) % 90)
    t = np.arange(int(0.45 * rate)) / rate
    body = 0.4 * np.sin(2 * np.pi * (freq + 60 * t) * t) * np.sin(np.pi * t / t[-1]) ** 2
    pad = np.zeros(int(0.15 * rate))
    return np.concatenate((pad, body, pad)).astype(np.float32), rate


def _sim_photo(_unit: str) -> bytes:
    """A small gradient PNG, made with the standard library, standing in for the camera."""
    import struct
    import zlib

    width, height = 160, 120
    rows = b"".join(
        b"\x00" + bytes(v for x in range(width) for v in (40 + x // 2, 80 + y, 160 - y))
        for y in range(height)
    )

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


def build(data_dir: Path, *, language: str = "en", next_unit: bool = False, link_secure: Any = True) -> tuple[SettingsBackend, dict[str, SimUnit]]:
    """A backend wired to two stand-in units, with every store in ``data_dir``."""
    units = {KITCHEN: SimUnit(KITCHEN, next_unit=next_unit), DEN: SimUnit(DEN, online=False, version="1.5.0-maipai.2")}

    def call(name: str, arguments: dict[str, Any], *, device_id: str | None = None, timeout: float = 5.0) -> object:
        unit = units.get(device_id or "")
        if unit is None or not unit.online:
            raise BodyLost("the unit is not connected")
        return unit.handle(name, arguments)

    store = UnitSettingsStore(data_dir / "units.json")
    store.update(KITCHEN, {"name": "Kitchen"})
    store.update(DEN, {"name": "Den"})
    live = lambda d: {  # noqa: E731
        "online": units[d].online,
        "firmware_version": units[d].version,
        "wifi_configured": True,
        "muted": False,
    }
    polish = Polish(call, store.get, store.update, data_dir=data_dir, synth=_sim_synth, background=False)
    backend = SettingsBackend(
        devices=lambda: {d: {} for d in units},
        store=store,
        live=live,
        host_address="this computer",
        language=language,
        faces=face_settings.FaceService(call, face_settings.FaceStore(data_dir / "faces.json")),
        extras=extras_mod.UnitExtras(
            call,
            reactions=extras_mod.ReactionStore(data_dir / "reactions.json"),
            clock=extras_mod.ClockStore(data_dir / "clock.json"),
            link_secure=(link_secure if callable(link_secure) else None if link_secure is None else (lambda _u, v=bool(link_secure): v)),
        ),
        people=extras_mod.PeopleStore(data_dir / "people.json"),
        device=device_mod.UnitDevice(call),
        remote=remote_mod.UnitRemote(call, photo=_sim_photo, sleep=lambda _s: None),
        pictures=picture_mod.PictureService(call, picture_mod.PictureStore(data_dir / "pictures")),
        polish=polish,
        activity=activity_mod.RemoteActivity(
            call,
            polish.probe,
            activity_mod.RemoteStore(data_dir / "remote-access.json"),
            activity_mod.RemoteLog(data_dir / "remote-activity.jsonl"),
            sleep=lambda _s: None,  # the notice and countdown are the unit's; the stand-in does not wait
        ),
    )
    from maipai_body.game_scores import ScoreBook

    book = ScoreBook(data_dir / "game-scores.json")  # demo scores for the Games page: named players come from MaiPai Home or the notes passphrase
    for person, game, score in (("nadia", "memory", 9), ("nadia", "memory", 6), ("nadia", "bopit", 7), ("atlas", "memory", 5), ("atlas", "rps", 2), ("Someone", "memory", 3)):
        book.record(KITCHEN, person, game, score)
    backend.score_book = book
    from maipai_packages.pantry import Pantry
    from maipai_packages.pantry.record import Record

    def demo_model(prompt: str) -> str:  # the stand-in model: says yes to kid checks and writes one new joke
        if "suitable for a six year old" in prompt:
            return "Yes"
        return '[{"text": "What do you call a bear with no teeth? | A gummy bear."}]'

    pantry = Pantry(data_dir / "pantry", demo_model)
    pantry.library.add([
        Record("joke", "en", "kid", "Why did the cat sit on the computer? | To keep an eye on the mouse."),
        Record("joke", "en", "kid", "What do you call a sleeping bull? | A bulldozer."),
        Record("riddle", "en", "kid", "What has hands but cannot clap?", "a clock"),
        Record("trivia", "en", "kid", "What is the largest planet in our solar system?", "Jupiter", "Mars|Venus"),
    ])
    backend.pantry = pantry
    return backend, units


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="maipai_body.settings_sim", description=__doc__)
    parser.add_argument("--port", type=int, default=9781)
    parser.add_argument("--data", type=Path, default=None, help="scratch folder (default: a new temporary one)")
    parser.add_argument("--lang", default="en")
    parser.add_argument("--next-unit", action="store_true", help="the Kitchen stand-in has the tools of the next unit update")
    args = parser.parse_args(argv)
    data = args.data or Path(tempfile.mkdtemp(prefix="stackchan-settings-sim-"))
    data.mkdir(parents=True, exist_ok=True)
    backend, _units = build(data, language=args.lang, next_unit=args.next_unit)
    from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore
    from maipai_body.local_guard import SettingsAuth

    pairing = PairingStore(data / "pairing.json")
    auth = SettingsAuth(data / "settings-token")
    from maipai_packages.wake_word_maker import WakeStore, WakeWordMaker

    backend.wakeword = WakeWordMaker(WakeStore(data / "wakeword"))  # the wake word maker card shows in the stand-in too
    backend.pair_code = pairing.create_pair_code  # the pairing code button and the phone code work in the stand-in too
    backend.phone_link = lambda: {"lan": True, "base": f"http://192.0.2.10:{args.port}", "token": auth.token}
    server = SettingsServer(backend, "127.0.0.1", args.port, auth=auth)
    server.start()
    print(f"settings page (simulated units) on http://127.0.0.1:{server.port}/settings  data: {data}", flush=True)
    done = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: done.set())
    signal.signal(signal.SIGTERM, lambda *_: done.set())
    done.wait()
    server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
