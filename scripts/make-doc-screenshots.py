#!/usr/bin/env python3
# Intent: make the user-doc screenshots by script from the simulated units (settings_sim) and from the real commands, never by hand,
# and write them to docs/images/. Needs Google Chrome (headless) and the host environment (uv run in host/).
# Usage: host/.venv/bin/python scripts/make-doc-screenshots.py
# Placement: docs tooling. Upstream: none.
import html
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "docs" / "images"
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
PORT = 9790


def shoot(url: str, out: Path, width: int, height: int, wait_ms: int = 9000) -> None:
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={width},{height}", f"--virtual-time-budget={wait_ms}",
         "--force-device-scale-factor=1", f"--screenshot={out}", url],
        check=True, capture_output=True, timeout=120,
    )


def terminal_page(title: str, blocks: list[tuple[str, str]]) -> str:
    rows = "".join(f'<div class="cmd">$ {html.escape(c)}</div><pre>{html.escape(o)}</pre>' for c, o in blocks)
    return f"""<!doctype html><meta charset=utf-8><style>body{{margin:0;background:#101418;color:#e6edf3;font:16px/1.5 ui-monospace,Menlo,monospace}}
main{{padding:24px 28px}}h1{{font:600 18px system-ui;color:#9fb3c8;margin:0 0 14px}}.cmd{{color:#7ee787;margin-top:14px}}pre{{margin:4px 0 0;white-space:pre-wrap}}</style>
<main><h1>{html.escape(title)}</h1>{rows}</main>"""


def shoot_terminal(name: str, title: str, blocks, height: int = 520) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as handle:
        handle.write(terminal_page(title, blocks))
    shoot("file://" + handle.name, IMAGES / name, 900, height, 1000)
    os.unlink(handle.name)


def run(*argv, env=None) -> str:
    result = subprocess.run(list(argv), capture_output=True, text=True, env={**os.environ, **(env or {})}, cwd=ROOT / "host")
    return (result.stdout + result.stderr).strip()


REAL_OUTPUTS = r"""
import json, subprocess, sys, threading, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
work = Path(sys.argv[1]); os.environ["STACKCHAN_HA_TOKEN"] = "demo-token"
from maipai_packages.coding_companion import AgentStatus
from maipai_packages.coding_companion.server import AgentAuth, AgentServer
shown = []
auth = AgentAuth(work / "coding-token")
server = AgentServer(AgentStatus(), auth, shown.append, 0); server.start()
subprocess.run([sys.executable, "-m", "maipai_packages.coding_companion.hook", "waiting", "--kind", "permission", "--project", "my-app", "--port", str(server.port), "--token-file", str(work / "coding-token")], check=True)
v = shown[0]
print("@@@coding\nThe robot got: state=%s kind=%s project=%s\nRing light: amber, one soft tone. Screen says: %s" % (v.state, v.kind, v.project, v.line)); server.stop()
class HA(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"]))); r = json.dumps({"response": {"speech": {"plain": {"speech": "Turned off the " + body["text"].split("the ")[-1] + "."}}}}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(r))); self.end_headers(); self.wfile.write(r)
ha_server = ThreadingHTTPServer(("127.0.0.1", 0), HA); threading.Thread(target=ha_server.serve_forever, daemon=True).start()
from maipai_packages.home_assistant import HomeAssistant
ha = HomeAssistant("http://127.0.0.1:%d" % ha_server.server_port, allow_unidentified=True)
line = "Home assistant, turn off the kitchen light"
print("@@@ha\nYou say:    " + line + "\nRobot says: " + ha.handle(line))
"""


def main() -> int:
    IMAGES.mkdir(exist_ok=True)
    py = str(ROOT / "host" / ".venv" / "bin" / "python")
    work = Path(tempfile.mkdtemp(prefix="stackchan-shots-"))
    sim = subprocess.Popen([py, "-m", "maipai_body.settings_sim", "--port", str(PORT), "--data", str(work / "sim")], cwd=ROOT / "host", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/settings", timeout=1)
                break
            except OSError:
                time.sleep(0.5)
        base = f"http://127.0.0.1:{PORT}/settings"
        shoot(base + "#home", IMAGES / "shot-parent-view.png", 520, 1180)          # phone width: Family and safety, pairing code, phone code
        shoot(base + "?only=own%20wake#voice", IMAGES / "shot-wake-word-maker.png", 1100, 640)
        shoot(base + "?only=character#look", IMAGES / "shot-character-pack.png", 1100, 640)
    finally:
        sim.terminate()
    # The web flasher over a test release made by scripts/release.sh --test-key (a throwaway key, never a real release).
    import json
    import shutil

    build = work / "build"
    (build / "bootloader").mkdir(parents=True)
    (build / "partition_table").mkdir()
    (build / "bootloader" / "bootloader.bin").write_bytes(b"B" * 64)
    (build / "partition_table" / "partition-table.bin").write_bytes(b"P" * 32)
    (build / "xiaozhi.bin").write_bytes(b"APP" * 100)
    (build / "flasher_args.json").write_text(json.dumps({
        "flash_settings": {"flash_mode": "dio", "flash_size": "16MB", "flash_freq": "80m"},
        "flash_files": {"0x0": "bootloader/bootloader.bin", "0x8000": "partition_table/partition-table.bin", "0x20000": "xiaozhi.bin"},
        "extra_esptool_args": {"chip": "esp32s3"}}))
    release = work / "release"
    subprocess.run(["bash", str(ROOT / "scripts" / "release.sh"), "--build-dir", str(build), "--version", "1.0.0", "--date", "2026-11-18", "--test-key", "--output", str(release)], check=True, capture_output=True)
    site = work / "flasher-site"
    shutil.copytree(ROOT / "flasher", site)
    for item in release.iterdir():
        shutil.copy(item, site / item.name)
    web = subprocess.Popen([sys.executable, "-m", "http.server", "8398", "--directory", str(site)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(1)
        shoot("http://127.0.0.1:8398/index.html", IMAGES / "shot-web-flasher.png", 700, 760, 6000)
    finally:
        web.terminate()
    # Terminal pictures from the real commands and the real packages.
    env = {"HOME": str(work / "home")}
    (work / "home").mkdir(exist_ok=True)
    notes_dir = work / "notes"
    code = f"""
import datetime
from maipai_packages.memory_notes import Notes, NotesStore
n = Notes(NotesStore({str(notes_dir)!r}), ["alex", "sam"], default_person="alex")
for line in ("remember that I like oat milk", "remember for everyone that the guest wifi is called cabin", "what do you remember", "forget oat milk", "remember my password is hunter2"):
    print("You say:  ", line); print("Robot says:", n.handle(line, "alex")); print()
"""
    spoken = subprocess.run([py, "-c", code], capture_output=True, text=True, cwd=ROOT / "host").stdout.strip()
    files = "\n".join(f"{p.name}: {p.read_text().strip()}" for p in sorted(notes_dir.glob("*.md")))
    shoot_terminal("shot-memory-notes.png", "Memory notes (the real package)", [("say it to the robot", spoken), ("cat ~/.local/share/maipai-bot/notes/*.md", files)], 720)
    real = subprocess.run([py, "-c", REAL_OUTPUTS, str(work)], capture_output=True, text=True, cwd=ROOT / "host")
    sections = dict(part.split("\n", 1) for part in real.stdout.split("@@@") if "\n" in part)
    shoot_terminal("shot-coding-companion.png", "Coding companion (the real endpoint and hook)", [("python -m maipai_packages.coding_companion.hook waiting --kind permission --project my-app", sections.get("coding", real.stderr).strip())], 360)
    shoot_terminal("shot-home-assistant.png", "Home Assistant (the real package against a fake Home Assistant)", [("(robot.toml)", '[packages.home_assistant]\nenabled = true\nurl = "https://ha.example.com"\ncameras = { "front door" = "camera.front_door" }'), ("you say, the robot answers", sections.get("ha", real.stderr).strip())], 460)
    print("screenshots written to", IMAGES)
    return 0


if __name__ == "__main__":
    sys.exit(main())
