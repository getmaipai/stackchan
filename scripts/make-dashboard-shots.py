#!/usr/bin/env python3
# Intent: the docs screenshots of the new dashboard (Home, Robot, Safety, Look and feel) at desktop and phone width, drawn by the real page against simulated robots, never by hand.
# Usage: host/.venv/bin/python scripts/make-dashboard-shots.py   (needs Google Chrome; writes docs/images/dash-<page>-<size>.png)
# Placement: docs tooling. Upstream: none.
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "host"))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PAGES = {"home": "#home", "robot": "#robot", "safety": "#safety", "look": "#robot/look", "search": "?q=quiet#home"}
SIZES = {"desktop": (1100, 760), "phone": (500, 960)}


def main() -> int:
    from maipai_body import settings_sim
    from maipai_body.settings_server import SettingsServer

    with tempfile.TemporaryDirectory() as tmp:
        backend, _ = settings_sim.build(Path(tmp), language="en")
        server = SettingsServer(backend, "127.0.0.1", 0)
        server.start()
        try:
            for page, frag in PAGES.items():
                for size, (w, h) in SIZES.items():
                    out = ROOT / "docs" / "images" / f"dash-{page}-{size}.png"
                    url = f"http://127.0.0.1:{server.port}/settings" + (frag if frag.startswith("?") else "") + ("" if frag.startswith("?") else frag)
                    if frag.startswith("?"):
                        url = f"http://127.0.0.1:{server.port}/settings{frag}"
                    cmd = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={w},{h}", "--virtual-time-budget=6000", "--force-dark-mode", f"--screenshot={out}", url]
                    subprocess.run(cmd, check=True, capture_output=True, timeout=60)
                    print(f"wrote {out.relative_to(ROOT)}")
        finally:
            server.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
