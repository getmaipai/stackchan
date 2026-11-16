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
from maipai_body import unit_device as device_mod
from maipai_body import unit_extras as extras_mod
from maipai_body.hal.errors import BodyLost
from maipai_body.settings_page import SettingsBackend
from maipai_body.settings_server import SettingsServer
from maipai_body.unit_settings import UnitSettingsStore

KITCHEN = "aa:bb:cc:00:10:01"
DEN = "aa:bb:cc:00:10:02"
FEATURES = ["config", "captions", "tod", "clock", "thinking", "timers", "packs", "decor"]


class SimUnit:
    """One stand-in unit: same tool names and reply shapes as the firmware, state kept in memory."""

    def __init__(self, device_id: str, *, online: bool = True, version: str = "1.6.2-maipai.1") -> None:
        self.device_id, self.online, self.version = device_id, online, version
        self.face = face_settings.FaceConfig().to_wire()
        self.table: list[dict[str, str]] | None = None
        self.zone, self.epoch = "utc", 0
        self.travel: dict[str, Any] = {"enabled": False, "has_key": False, "state": "off"}
        self.pictures: dict[str, Any] = {"held": False}
        self.privacy: dict[str, Any] = {"muted": False, "vision_off": False, "quiet": False}
        self.device: dict[str, Any] = {}
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.lock = threading.Lock()

    def handle(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self.calls.append((name, args))
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
                        {"id": "memory", "title": "Colour Memory", "lower_is_better": False, "scores": [7, 5, 4]},
                        {"id": "reaction", "title": "Quick Tap", "lower_is_better": True, "scores": [412, 455]},
                        {"id": "whack", "title": "Whack a Mole", "lower_is_better": False, "scores": []},
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
            if name == "self.tailnet.set":
                if args.get("forget"):
                    self.travel = {"enabled": False, "has_key": False, "state": "off"}
                elif args.get("key"):
                    self.travel = {"enabled": True, "has_key": True, "state": "waiting"}
                elif "enabled" in args:
                    self.travel = {**self.travel, "enabled": bool(args["enabled"]), "state": "waiting" if args["enabled"] else "off"}
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


def build(data_dir: Path, *, language: str = "en") -> tuple[SettingsBackend, dict[str, SimUnit]]:
    """A backend wired to two stand-in units, with every store in ``data_dir``."""
    units = {KITCHEN: SimUnit(KITCHEN), DEN: SimUnit(DEN, online=False, version="1.5.0-maipai.2")}

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
        ),
        people=extras_mod.PeopleStore(data_dir / "people.json"),
        device=device_mod.UnitDevice(call),
        pictures=picture_mod.PictureService(call, picture_mod.PictureStore(data_dir / "pictures")),
    )
    return backend, units


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="maipai_body.settings_sim", description=__doc__)
    parser.add_argument("--port", type=int, default=9781)
    parser.add_argument("--data", type=Path, default=None, help="scratch folder (default: a new temporary one)")
    parser.add_argument("--lang", default="en")
    args = parser.parse_args(argv)
    data = args.data or Path(tempfile.mkdtemp(prefix="stackchan-settings-sim-"))
    data.mkdir(parents=True, exist_ok=True)
    backend, _units = build(data, language=args.lang)
    server = SettingsServer(backend, "127.0.0.1", args.port)
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
