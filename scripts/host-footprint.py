#!/usr/bin/env python3
"""Report the host's footprint: source and environment size, import time, the pages' weight, docs and flasher assets, caches and logs, and (with --run) idle memory and CPU.

Usage: python3 scripts/host-footprint.py [--run] [--json]    (--run starts the host for 10 seconds on free ports and measures it; it needs the host environment)
The numbers go in the release report (scripts/release-report.py) and in docs/plan/optimization.md Part 3."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / "host"


def tree_bytes(path: Path, suffixes: tuple[str, ...] | None = None) -> int:
    total = 0
    for p in path.rglob("*"):
        if p.is_file() and (suffixes is None or p.suffix.lower() in suffixes) and ".git" not in p.parts:
            total += p.stat().st_size
    return total


def clean_venv() -> Path | None:
    """The clean install of the host package the end-to-end run makes (.runs/e2e-venv): what a friend installs, without the development extras."""
    venv = ROOT / ".runs" / "e2e-venv"
    return venv if (venv / "bin" / "python").exists() else None


def python_exe() -> str:
    venv = clean_venv() or HOST / ".venv"
    exe = venv / "bin" / "python"
    return str(exe) if exe.exists() else sys.executable


def import_time(module: str) -> float | None:
    code = f"import time;t=time.perf_counter();import {module};print(time.perf_counter()-t)"
    done = subprocess.run([python_exe(), "-c", code], capture_output=True, text=True, cwd=HOST, timeout=120)
    try:
        return round(float(done.stdout.strip().splitlines()[-1]), 2)
    except (ValueError, IndexError):
        return None


def installed_size() -> dict:
    venv = clean_venv() or HOST / ".venv"
    site = next(venv.glob("lib/python*/site-packages"), None) if venv.exists() else None
    if site is None:
        return {}
    sizes = sorted(((tree_bytes(p), p.name) for p in site.iterdir() if p.is_dir() and not p.name.endswith(".dist-info")), reverse=True)
    return {"site_packages_bytes": tree_bytes(site), "largest": [{"name": n, "bytes": b} for b, n in sizes[:8]]}


def page_weights() -> dict:
    """The pages' sizes, rendered in the host environment (the pages are built by the host's own code)."""
    code = (
        "import json;from maipai_body.brain_page import render_brain_page;from maipai_body.health import render_page as hp;"
        "from maipai_body.installed_page import render_installed_page;from maipai_body.settings_page import render_page as sp;"
        "print(json.dumps({'settings_page_bytes':len(sp('en')),'brain_page_bytes':len(render_brain_page()),'on_my_robot_page_bytes':len(render_installed_page()),"
        "'health_page_bytes':len(hp({'summary':'','uptime_s':0,'parts':[],'units':[],'advice':[]}))}))"
    )
    done = subprocess.run([python_exe(), "-c", code], capture_output=True, text=True, cwd=HOST, timeout=120)
    try:
        return json.loads(done.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"error": (done.stderr or done.stdout)[-200:]}


def run_idle(seconds: int = 10) -> dict:
    with tempfile.TemporaryDirectory() as home:
        env = {**os.environ, "HOME": home, "MAIPAI_BOT_DATA_DIR": home, "MAIPAI_BODY": "stackchan", "MAIPAI_HUB_HOST": "1", "MAIPAI_XIAOZHI_PORT": "0", "MAIPAI_STACKCHAN_AVATAR_PORT": "0", "MAIPAI_STACKCHAN_SETTINGS_PORT": "0", "MAIPAI_LINK_VOICE_PORT": "0", "MAIPAI_LINK_AVATAR_PORT": "0", "MAIPAI_LINK_HTTP_PORT": "0"}
        started = time.time()
        proc = subprocess.Popen([python_exe(), "-m", "maipai_body.app"], cwd=HOST, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(seconds)
            ps = subprocess.run(["ps", "-o", "rss=,pcpu=,nlwp=,cputime=", "-p", str(proc.pid)], capture_output=True, text=True).stdout.split()
            if not ps:
                ps = subprocess.run(["ps", "-o", "rss=,pcpu=,cputime=", "-p", str(proc.pid)], capture_output=True, text=True).stdout.split()
            return {"seconds": seconds, "rss_mb": round(int(ps[0]) / 1024, 1) if ps else None, "cpu_percent_average": float(ps[1]) if len(ps) > 1 else None, "started_after_s": round(time.time() - started, 1)}
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()


def main(argv: list[str]) -> int:
    report = {
        "host_source_bytes": tree_bytes(HOST / "maipai_body", (".py", ".json")) + tree_bytes(HOST / "maipai_packages", (".py",)),
        "environment": installed_size(),
        "import_seconds": {"maipai_body.config": import_time("maipai_body.config"), "maipai_body.app": import_time("maipai_body.app")},
        "pages": page_weights(),
        "docs_images_bytes": tree_bytes(ROOT / "docs" / "images"),
        "docs_png_bytes": tree_bytes(ROOT / "docs" / "images", (".png",)),
        "golden_bytes": tree_bytes(HOST / "tests" / "golden"),
        "flasher_bytes": tree_bytes(ROOT / "flasher"),
        "flasher_vendor_bytes": tree_bytes(ROOT / "flasher" / "vendor"),
        "local_stack_download_bytes": _stack(),
    }
    if "--run" in argv:
        report["idle"] = run_idle()
    if "--json" in argv:
        print(json.dumps(report, indent=2))
    else:
        for key, value in report.items():
            print(f"{key}: {value}")
    return 0


def _stack() -> dict:
    sys.path.insert(0, str(HOST))
    from maipai_body.brain_setup import catalog

    return {c: catalog.needs("macos-arm64", c)["download_bytes"] for c in catalog.MODELS}


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
