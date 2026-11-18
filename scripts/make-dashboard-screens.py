#!/usr/bin/env python3
"""A screenshot of each host dashboard page at desktop and phone width, kept in docs/dev/dashboard-screens for review.

Starts the settings server on a free port with simulated data (no robot), opens each page in headless Chrome, writes PNG files.
Headless Chrome will not make a window narrower than about 500 px, so "phone" is 500 px wide (the tabs collapse below 700 px).
Usage: python3 scripts/make-dashboard-screens.py   (needs Google Chrome; the host environment for the Python side)"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "host"))
sys.path.insert(0, str(ROOT / "host" / "tests"))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PAGES = {"status": "/health", "on-my-robot": "/on-my-robot", "brain": "/brain"}
SIZES = {"desktop": (1280, 800), "phone": (500, 900)}


def main() -> int:
    from maipai_body.brain_setup.controller import BrainSetup
    from maipai_body.brain_setup.installer import Installer
    from maipai_body.health import build_health
    from maipai_body.installed_set import InstalledSets, InstalledStore
    from maipai_body.packs import PackLibrary, make_pack, zip_payload
    from maipai_body.settings_server import SettingsServer
    from maipai_body.settings_sim import build
    from maipai_body.supervisor import Supervisor, Worker

    out = ROOT / "docs" / "dev" / "dashboard-screens"
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        backend, _ = build(tmp)
        backend.brain_setup = BrainSetup(tmp / "robot.toml", tmp / "stack", installer=Installer(tmp / "stack", platform_id="macos-arm64", free_disk=lambda p: 50 * 10**9, memory=lambda: 16000))
        library = PackLibrary(tmp / "packs", filler_root=tmp / "fillers")
        for kind, names in (("look", ["default", "soft"]), ("game", ["memory", "quiz", "tap"]), ("language", ["french"]), ("sound", ["chimes"])):
            for n in names:
                library.add(make_pack(kind, n, zip_payload({"a.txt": n.encode() * 4000}), lang="fr" if kind == "language" else ""))

        class Transport:
            def connected(self, unit): return True
            def multi_slot(self, unit): return False
            def held(self, unit, kind): return []
            def install(self, unit, kind, pack_id): pass
            def remove(self, unit, kind, sha): pass

        backend.installed = InstalledSets(library, InstalledStore(tmp / "sets.json"), Transport(), language=lambda u: "fr")
        backend.installed_units = lambda: [{"id": "02:00:00:00:00:01", "name": "Kitchen", "connected": True}, {"id": "02:00:00:00:00:02", "name": "Den", "connected": False}]
        sup = Supervisor()
        sup.add(Worker("settings page", lambda: None, plain="the settings page"), start_now=False).state = "ok"
        backend.health = lambda: build_health(sup, connected=["02:00:00:00:00:01"], paired={"02:00:00:00:00:01": {"last_seen": 1.7e9}, "02:00:00:00:00:02": {"last_seen": 1.7e9}}, started=0.0, names={"02:00:00:00:00:01": "Kitchen", "02:00:00:00:00:02": "Den"}, now=7200)
        server = SettingsServer(backend, "127.0.0.1", 0)
        server.start()
        try:
            for name, path in PAGES.items():
                for label, (w, h) in SIZES.items():
                    target = out / f"{name}-{label}.png"
                    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={w},{h}", "--virtual-time-budget=5000", f"--screenshot={target}", f"http://127.0.0.1:{server.port}{path}"], capture_output=True, timeout=60)
                    print(target.relative_to(ROOT), target.stat().st_size if target.exists() else "MISSING")
        finally:
            server.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
