"""The virtual unit view's Simulation or Live picker (owner decision 21) and the battery drain switch, under a real pointer.

A fake host (scripts/virtual-unit/fake_host.py, a test double on loopback with fake robots that only record calls) stands in for the real
one: no real robot is contacted. The token is the fake host's own test value. Needs Google Chrome, the screens renderer and the playground's
backends.py and fake_host.py; skips with the reason when any is missing.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_vu_view_pointer import CHROME, ROOT, VU, Page, spot_of  # noqa: E402


def _load(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, VU / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(VU))
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def live():
    websockets = pytest.importorskip("websockets.sync.client")
    if not (VU / "backends.py").exists() or not (VU / "fake_host.py").exists():
        pytest.skip("needs the playground's backends.py and fake_host.py (Live mode is not in this checkout yet)")
    if not Path(CHROME).exists():
        pytest.skip("needs Google Chrome in /Applications to drive a real pointer")
    if not ((ROOT / ".runs" / "vu-screens" / "render").exists() or (ROOT / ".runs" / "vu-build" / "render").exists()):
        pytest.skip("needs a renderer: bash scripts/virtual-unit/build-screens.sh")
    fake = _load("fake_host")
    host = fake.FakeHost()
    host_url = host.start(0)
    env = dict(os.environ, MAIPAI_PLAYGROUND_HOST=host_url, MAIPAI_PLAYGROUND_TOKEN=fake.TOKEN)
    view = subprocess.Popen([sys.executable, str(VU / "view.py"), "0"], stdout=subprocess.PIPE, text=True, env=env)
    profile = tempfile.mkdtemp(prefix="vu-live-")
    chrome = None
    try:
        base = view.stdout.readline().split()[-1].rstrip("/")
        chrome = subprocess.Popen([CHROME, "--headless=new", "--remote-debugging-port=0", f"--user-data-dir={profile}", "--window-size=1200,820", "--mute-audio",
                                   "--enable-unsafe-swiftshader", "--no-first-run", "--no-default-browser-check", "about:blank"],
                                  stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
        port = None
        for _ in range(200):
            line = chrome.stderr.readline()
            if "DevTools listening on" in line:
                port = line.split("ws://127.0.0.1:")[1].split("/")[0]
                break
        assert port, "the browser did not open its debugging port"
        tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list"))
        ws = websockets.connect(next(t["webSocketDebuggerUrl"] for t in tabs if t["type"] == "page"), max_size=None)
        page = Page(ws)
        page.base = base
        page.send("Page.enable")
        page.send("Page.navigate", url=base + "/")
        assert page.until("typeof ST === 'object' && ST && ST.hw && ST.hw.on === true && document.getElementById('backend').options.length >= 2", 20), "the page never listed the robots"
        page.js("window.confirm = () => true")   # the page asks before it takes a real robot; the test says yes
        yield page, host
        ws.close()
    finally:
        for proc in (chrome, view):
            if proc:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
        host.stop()
        shutil.rmtree(profile, ignore_errors=True)


def test_the_picker_lists_the_simulation_and_the_registered_robots(live):
    page, _ = live
    names = page.js("[...document.getElementById('backend').options].map(o => o.textContent)")
    assert names[0] == "Simulation" and any("Kitchen robot (real robot)" == n for n in names) and any("Garage robot (offline)" == n for n in names), names
    assert page.js("ST.backend.kind === 'simulation' && !ST.backend.live && document.getElementById('livebar').style.display === 'none'")
    assert page.js("document.getElementById('bdisconnect').style.display === 'none'")


def test_connecting_shows_the_live_banner_sends_tools_to_the_robot_and_disconnect_returns(live):
    page, host = live
    page.js("(() => { const s = document.getElementById('backend'); s.value = 'r1'; s.dispatchEvent(new Event('change')); })()")
    page.click(*spot_of(page, "bconnect"))
    assert page.until("ST.backend.live && ST.backend.id === 'r1'"), page.js("document.getElementById('backendmsg').textContent")
    assert page.until("document.getElementById('livebar').style.display === 'block' && /^LIVE: you are controlling Kitchen robot/.test(document.getElementById('livebar').textContent)")
    assert page.js("document.title.startsWith('LIVE: ') && document.getElementById('backend').disabled && document.getElementById('bconnect').style.display === 'none'")
    # a tool call from the page now goes to the robot, not to the simulation
    before = len(host.robots["r1"].calls)
    page.js("(() => { document.getElementById('ledc').value = '#00ff00'; document.getElementById('ledon').click(); })()")
    end = time.time() + 5
    while len(host.robots["r1"].calls) == before and time.time() < end:
        time.sleep(0.1)
    assert host.robots["r1"].calls[before:][0][0] == "self.robot.set_led_colors", "the lights call reached the robot through the host"
    assert page.js("ST.leds.every(c => c[0] + c[1] + c[2] === 0)"), "and the simulation's own lights did not change"
    # the simulation's body controls are refused in plain words while a robot is connected
    out = page.js("fetch('/hw', {method: 'POST', body: JSON.stringify({key: 'battery', value: 10})}).then(r => r.json())")
    assert out["isError"] and "real robot" in out["text"] and "Disconnect" in out["text"]
    # the lease is kept alive: after more than one heartbeat period the robot is still ours
    time.sleep(7)
    assert host.leases.holder("r1") is not None and page.js("ST.backend.live")
    page.click(*spot_of(page, "bdisconnect"))
    assert page.until("!ST.backend.live && document.getElementById('livebar').style.display === 'none' && !document.title.startsWith('LIVE')")
    assert host.leases.holder("r1") is None, "disconnect gives the robot back at once"
    assert page.js("/Simulation again/.test(document.getElementById('backendmsg').textContent)")


def test_a_robot_someone_else_holds_is_refused_in_plain_words(live):
    page, host = live
    assert host.leases.acquire("r2", "other-session", "the family tablet")[0]
    try:
        page.js("(() => { const s = document.getElementById('backend'); s.value = 'r2'; s.dispatchEvent(new Event('change')); })()")
        page.click(*spot_of(page, "bconnect"))
        assert page.until("/family tablet/.test(document.getElementById('backendmsg').textContent)"), page.js("document.getElementById('backendmsg').textContent")
        assert page.js("!ST.backend.live && document.getElementById('livebar').style.display === 'none'"), "a refusal leaves the Simulation active"
    finally:
        host.leases.release("r2", "other-session")
    page.js("(() => { const s = document.getElementById('backend'); s.value = 'r3'; s.dispatchEvent(new Event('change')); })()")
    page.click(*spot_of(page, "bconnect"))
    assert page.until("/offline/.test(document.getElementById('backendmsg').textContent) && !ST.backend.live")


def test_the_drain_switch_runs_the_battery_down_and_the_rows_say_the_numbers_are_placeholders(live):
    page, _ = live
    if page.js("ST.util.drain === undefined"):
        pytest.skip("the power model is not in this checkout yet")
    text = "document.getElementById('utilv').textContent"
    assert page.until(f"/Draw\\d+ mA \\(assumed, a placeholder until measured\\)/.test({text}) && /hours left \\(assumed\\)/.test({text})"), page.js(text)
    page.js("fetch('/hw', {method: 'POST', body: JSON.stringify({key: 'battery', value: 60})}).then(r => r.json())")
    assert page.until("ST.hw.battery === 60")
    page.click(*spot_of(page, "drain"))
    assert page.until("ST.util.drain === true && document.getElementById('drain').checked")
    page.js("(() => { const s = document.getElementById('tscale'); s.value = '20'; s.dispatchEvent(new Event('change')); })()")
    assert page.until("ST.hw.battery < 60", 40), "with drain on and the clock at 20 times, the battery level falls"
    page.js("(() => { const s = document.getElementById('tscale'); s.value = '1'; s.dispatchEvent(new Event('change')); })()")
    page.click(*spot_of(page, "drain"))
    assert page.until("ST.util.drain === false && ST.util.time_scale === 1")
