"""The virtual unit view under a real pointer: a browser is driven through its own input pipeline (mouse press, move, release),
not through scripted events, so the page sees what a hand on a mouse produces.

Covers the owner's reports of 2026-11-18: sliders that snapped back while dragged, a USB-C port that did not take a click,
and moving the head by dragging it. Needs Google Chrome and the screens renderer; skips with the reason when either is missing.
The 3D part also needs the pinned three.js from the network and skips without it. Nothing is played aloud and no real unit is touched.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VU = ROOT / "scripts" / "virtual-unit"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


class Page:
    """One browser tab, driven over the debugging socket."""

    def __init__(self, ws):
        self.ws, self.n = ws, 0

    def send(self, method, **params):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv(timeout=20))
            if msg.get("id") == self.n:
                assert "error" not in msg, f"{method} failed: {msg['error']}"
                return msg.get("result", {})

    def js(self, expr):
        res = self.send("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
        assert "exceptionDetails" not in res, f"the page raised on {expr!r}: {res['exceptionDetails'].get('text')}"
        return res["result"].get("value")

    def until(self, expr, seconds=8.0):
        end = time.time() + seconds
        while time.time() < end:
            if self.js(expr):
                return True
            time.sleep(0.1)
        return False

    def mouse(self, kind, x, y, buttons=1):
        self.send("Input.dispatchMouseEvent", type=kind, x=x, y=y, button="left", buttons=buttons if kind != "mouseReleased" else 0, clickCount=1)

    def drag(self, x0, y0, x1, y1, pause=None, steps=12):
        """Press at one point, move to another in small steps, release. `pause` runs while the button is still down."""
        self.mouse("mouseMoved", x0, y0, 0)
        self.mouse("mousePressed", x0, y0)
        for i in range(1, steps + 1):
            self.mouse("mouseMoved", x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps)
            time.sleep(0.02)
        out = pause() if pause else None
        self.mouse("mouseReleased", x1, y1)
        return out

    def click(self, x, y):
        self.drag(x, y, x, y, steps=1)


@pytest.fixture(scope="module")
def page():
    websockets = pytest.importorskip("websockets.sync.client")
    if not Path(CHROME).exists():
        pytest.skip("needs Google Chrome in /Applications to drive a real pointer")
    if not ((ROOT / ".runs" / "vu-screens" / "render").exists() or (ROOT / ".runs" / "vu-build" / "render").exists()):
        pytest.skip("needs a renderer: bash scripts/virtual-unit/build-screens.sh")
    view = subprocess.Popen([sys.executable, str(VU / "view.py"), "0"], stdout=subprocess.PIPE, text=True)
    profile = tempfile.mkdtemp(prefix="vu-pointer-")
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
        p = Page(ws)
        p.base = base
        p.send("Page.enable")
        p.send("Page.navigate", url=base + "/")
        assert p.until("typeof ST === 'object' && ST && ST.hw && ST.hw.on === true", 15), "the side panel never got the unit's state"
        yield p
        ws.close()
    finally:
        for proc in (chrome, view):
            if proc:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
        shutil.rmtree(profile, ignore_errors=True)


def spot(page, ident, value):
    """Page coordinates of a slider's track at a value."""
    r = page.js(f"(() => {{ const e = document.getElementById('{ident}'); e.scrollIntoView({{block: 'center'}}); const b = e.getBoundingClientRect();"
                f" return {{l: b.left, w: b.width, y: b.top + b.height / 2, min: +e.min, max: +e.max}}; }})()")
    return r["l"] + 8 + (value - r["min"]) / (r["max"] - r["min"]) * (r["w"] - 16), r["y"]


@pytest.mark.parametrize("ident,start,goal,state", [
    ("bat", 75, 40, "ST.hw.battery"),
    ("yaw", 0, 60, "ST.head.yaw"),
    ("pitch", 10, 50, "ST.head.pitch"),
])
def test_a_dragged_slider_keeps_its_value_and_the_unit_follows(page, ident, start, goal, state):
    page.js("fetch('/hw', {method: 'POST', body: JSON.stringify({key: 'battery', value: 75})}).then(r => r.json())")
    assert page.until("ST.hw.battery === 75 && ST.motion.state === 'free'", 12), page.js("JSON.stringify([ST.hw.battery, ST.motion])")
    page.js("fetch('/call', {method: 'POST', body: JSON.stringify({name: 'self.robot.set_head_angles', arguments: {yaw: 0, pitch: 10}})}).then(r => r.json())")
    assert page.until("Math.abs(ST.head.yaw) < 1 && Math.abs(ST.head.pitch - 10) < 1 && !Object.keys(HOLD).length", 12), page.js("JSON.stringify([ST.head, HOLD])")
    x0, y = spot(page, ident, start)
    x1, _ = spot(page, ident, goal)

    def while_held():
        # some browsers never give a slider the keyboard on a click: take it away, then let several state polls pass with the button down
        page.js("document.activeElement && document.activeElement.blur()")
        time.sleep(0.5)
        return float(page.js(f"+document.getElementById('{ident}').value"))
    held_value = page.drag(x0, y, x1, y, pause=while_held)
    assert abs(held_value - goal) <= 4, f"{ident} snapped back to {held_value} while it was being dragged toward {goal}"
    assert page.until(f"Math.abs({state} - {held_value}) <= 1"), f"the unit did not follow {ident} to {held_value}: {page.js(state)}"
    time.sleep(0.4)
    assert abs(float(page.js(f"+document.getElementById('{ident}').value")) - held_value) <= 1, f"{ident} moved away after the release"
    assert page.js(f"document.getElementById('{ident}v').textContent.trim()") == str(round(held_value))


def test_a_refused_head_move_says_why_and_the_slider_returns_to_the_real_angle(page):
    page.js("fetch('/hw', {method: 'POST', body: JSON.stringify({key: 'carried', value: true})}).then(r => r.json())")
    assert page.until("ST.hw.carried === true")
    try:
        before = page.js("ST.head.yaw")
        x0, y = spot(page, "yaw", before)
        x1, _ = spot(page, "yaw", -70)
        page.drag(x0, y, x1, y)
        assert page.until("/limiter/i.test(document.getElementById('limmsg').textContent)"), "a refused move must say that the limiter refused it"
        assert page.until(f"Math.abs(+document.getElementById('yaw').value - {before}) <= 1", 5), "the slider must go back to where the head really is"
    finally:
        page.js("fetch('/hw', {method: 'POST', body: JSON.stringify({key: 'carried', value: false})}).then(r => r.json())")
        assert page.until("ST.hw.carried === false")


def test_the_panel_layout_does_not_move_when_the_numbers_change(page):
    top = "Math.round(document.getElementById('dstop').getBoundingClientRect().top + scrollY + document.getElementById('side').scrollTop)"
    before = page.js(top)
    page.js("(() => { document.getElementById('pitchv').textContent = '87'; document.getElementById('yawv').textContent = '-128';"
            " document.getElementById('pitchr').textContent = '3.5 to 45.5'; document.getElementById('yawr').textContent = '-64.5 to 64.5'; })()")
    assert page.js(top) == before, "the Stop dance button must stay where it is while the angles change"
    assert page.js("document.getElementById('dstop').previousElementSibling === null"), "Stop dance is the first button of its row"


def test_quick_actions_light_the_bars_and_say_through_a_session(page):
    page.js("(() => { document.getElementById('ledc').value = '#ffd400'; document.getElementById('ledon').click(); })()")
    assert page.until("ST.leds.every(c => c[0] === 255 && c[1] === 212 && c[2] === 0)"), "Turn on must set all 12 lights to the picked color"
    page.js("document.getElementById('ledoff').click()")
    assert page.until("ST.leds.every(c => c[0] + c[1] + c[2] === 0)")
    page.js("(() => { document.getElementById('sayt').value = 'hello'; document.getElementById('saygo').click(); })()")
    assert page.until("/Sent to the robot/.test(document.getElementById('qmsg').textContent)"), page.js("document.getElementById('qmsg').textContent")


def test_actions_are_picked_by_area_and_filled_in_by_fields(page):
    assert page.until("document.getElementById('dom').options.length > 5")
    page.js("(() => { const d = document.getElementById('dom'); d.value = 'robot'; d.dispatchEvent(new Event('change'));"
            " const t = document.getElementById('tool'); t.value = 'self.robot.set_head_angles'; t.dispatchEvent(new Event('change')); })()")
    kinds = page.js("[...document.querySelectorAll('#fields [data-arg]')].map(e => e.dataset.arg + ':' + e.type)")
    assert "yaw:range" in kinds and "pitch:range" in kinds, kinds
    page.js("(() => { const y = document.querySelector('#fields [data-arg=yaw]'); y.value = 25; y.dispatchEvent(new Event('input')); document.getElementById('go').click(); })()")
    assert page.until("/^Done/.test(document.getElementById('out').textContent) && Math.abs(ST.head.yaw - 25) <= 1"), page.js("document.getElementById('out').textContent")


def test_dragging_the_head_moves_it_and_a_click_plugs_the_cable(page):
    if not page.until("window.ROBOT && ROBOT.model && ROBOT.model.ready", 12):
        pytest.skip("the 3D drawing did not start here (it needs the pinned three.js from the network and a graphics context)")
    page.js("fetch('/call', {method: 'POST', body: JSON.stringify({name: 'self.robot.set_head_angles', arguments: {yaw: 0, pitch: 10}})}).then(r => r.json())")
    assert page.until("Math.abs(ST.head.yaw) < 1 && Math.abs(ST.head.pitch - 10) < 1")
    page.js("(() => { Object.assign(ROBOT.view, {az: 1.2, el: 0.2, dist: 16}); window.scrollTo(0, 0); })()")
    time.sleep(0.3)
    p = page.js("ROBOT.pointOf('sticker_side_left')")           # a spot on the head shell, away from the screen
    view = page.js("JSON.stringify(ROBOT.view)")
    page.drag(p["x"], p["y"], p["x"] + 90, p["y"] - 60, steps=20)
    assert page.until("Math.abs(ST.head.yaw) > 20 && ST.head.pitch > 20"), f"a drag on the head must turn and nod it: {page.js('JSON.stringify(ST.head)')}"
    assert page.js("JSON.stringify(ROBOT.view)") == view, "a drag that starts on the head must not turn the view"
    assert page.js("ST.head.yaw >= -128 && ST.head.yaw <= 128 && ST.head.pitch >= 3 && ST.head.pitch <= 87")
    # the same drag with the toggle off turns the view and leaves the head alone
    time.sleep(2.0)                                             # let the head finish its move
    head = page.js("JSON.stringify(ST.head)")
    page.js("document.getElementById('draghead').checked = false")
    p = page.js("ROBOT.pointOf('sticker_side_left')")
    page.drag(p["x"], p["y"], p["x"] + 60, p["y"], steps=10)
    assert page.js("JSON.stringify(ROBOT.view)") != view and page.js("JSON.stringify(ST.head)") == head
    page.js("document.getElementById('draghead').checked = true")
    # the port on the back of the base: one click plugs the cable in, the next takes it out
    page.js("document.getElementById('vback').click()")
    time.sleep(0.3)
    for want in (True, False):
        p = page.js("ROBOT.pointOf('usb_c_port')")
        page.click(p["x"], p["y"])
        assert page.until(f"ST.hw.ports.back.plugged === {str(want).lower()}"), f"a click on the back USB-C port must make its cable {'plugged' if want else 'unplugged'}"
        assert page.js("ST.hw.ports.side.plugged") is False, "the side port has its own cable"
    # the power button: off, then on again
    page.js("Object.assign(ROBOT.view, {az: -1.2, el: 0.15, dist: 14})")
    page.js("fetch('/call', {method: 'POST', body: JSON.stringify({name: 'self.robot.set_head_angles', arguments: {yaw: 0, pitch: 10}})}).then(r => r.json())")
    assert page.until("Math.abs(ST.head.yaw) < 1")
    for want in (False, True):
        time.sleep(0.5)
        p = page.js("ROBOT.pointOf('power_button')")
        page.click(p["x"], p["y"])
        assert page.until(f"ST.hw.on === {str(want).lower()}"), f"a click on the power button must turn the unit {'on' if want else 'off'}"


def test_both_usb_c_sockets_take_real_clicks_and_the_panel_shows_each_port(page):
    if not page.until("window.ROBOT && ROBOT.model && ROBOT.model.ready", 12):
        pytest.skip("the 3D drawing did not start here (it needs the pinned three.js from the network and a graphics context)")
    for key, value in (("side", False), ("back", False), ("side_source", "computer"), ("back_source", "charger")):
        page.js(f"fetch('/hw', {{method: 'POST', body: JSON.stringify({{key: '{key}', value: {json.dumps(value)}}})}}).then(r => r.json())")
    page.js("fetch('/call', {method: 'POST', body: JSON.stringify({name: 'self.robot.set_head_angles', arguments: {yaw: 0, pitch: 10}})}).then(r => r.json())")
    assert page.until("!ST.hw.vbus && Math.abs(ST.head.yaw) < 1 && ST.hw.on")
    # the side socket on the controller, seen from the robot's right
    page.js("(() => { Object.assign(ROBOT.view, {az: -1.3, el: 0.1, dist: 15}); window.scrollTo(0, 0); })()")
    time.sleep(0.4)
    p = page.js("ROBOT.pointOf('usb_c_otg')")
    page.click(p["x"], p["y"])
    assert page.until("ST.hw.ports.side.plugged && !ST.hw.ports.back.plugged && ST.hw.powered_by === 'side'"), "a click on the side socket plugs the side cable only"
    assert page.until("ROBOT.model.sideCable.visible && document.getElementById('busb').textContent === 'plugged in' && !document.getElementById('bserial').disabled")
    # the back socket on the base: both cables are in now
    page.js("document.getElementById('vback').click()")
    time.sleep(0.4)
    p = page.js("ROBOT.pointOf('usb_c_port')")
    page.click(p["x"], p["y"])
    assert page.until("ST.hw.ports.back.plugged && ST.hw.ports.side.plugged && ST.hw.powered_by === 'both'"), "a click on the back socket plugs the back cable and leaves the side one in"
    assert page.until("/both sockets/.test(document.getElementById('hwv').textContent) && /2000 mA/.test(document.getElementById('hwv').textContent)"), "two cables act as the stronger source"
    assert page.until("/side socket and the back socket/.test(document.getElementById('whylim').textContent)"), page.js("document.getElementById('whylim').textContent")
    assert page.js("/undefined on the real unit/.test(document.getElementById('bothnote').textContent)")
    # the panel buttons take each cable out again, one at a time
    page.js("document.getElementById('busb').click()")
    assert page.until("!ST.hw.ports.side.plugged && ST.hw.ports.back.plugged && ST.hw.powered_by === 'back' && document.getElementById('bserial').disabled"), "the back cable goes to a charger: no serial"
    # the bench case: a computer on the back socket alone gives the serial device
    page.js("(() => { const s = document.getElementById('srcback'); s.value = 'computer'; s.dispatchEvent(new Event('change')); })()")
    assert page.until("ST.hw.serial_possible && !document.getElementById('bserial').disabled && /back socket/.test(document.getElementById('serialnote').textContent)")
    page.js("document.getElementById('bserial').click()")
    assert page.until("ST.hw.serial && ST.hw.usb_path.data_from === 'back'")
    page.js("document.getElementById('bback').click()")
    assert page.until("!ST.hw.vbus && /nothing/.test(document.getElementById('whylim').textContent)")


def test_the_lights_glow_follow_the_ring_and_both_power_lights_follow_usb_power(page):
    if not page.until("window.ROBOT && ROBOT.model && ROBOT.model.ready", 12):
        pytest.skip("the 3D drawing did not start here (it needs the pinned three.js from the network and a graphics context)")
    page.js("(() => { document.getElementById('rich').checked = true; document.getElementById('ledoff').click(); })()")
    assert page.until("ST.leds.every(c => c[0] + c[1] + c[2] === 0)")
    dark = "ROBOT.model.glowLights.every(g => g.l.intensity === 0) && ROBOT.model.halos.every(h => !h.visible) && !ROBOT.model.leds[0].visible"
    assert page.until(dark), "off means dark: no halo, no light thrown, no lit plate"
    bar = "Array.from(ROBOT.model.bars[0].mesh.geometry.attributes.color.array.slice(0, 3)).map(v => +v.toFixed(2)).join()"
    unlit = page.js(bar)
    # amber on the left bar only: its halos, its two point lights and its bar light up; the right side stays dark
    page.js("(() => { document.getElementById('ledc').value = '#ff9600'; document.getElementById('ledleft').click(); })()")
    assert page.until("ST.leds[0][0] === 255 && ST.leds[11][0] === 0")
    assert page.until("ROBOT.model.halos[0].visible && ROBOT.model.ledHalos[0].visible && !ROBOT.model.halos[11].visible")
    assert page.js("ROBOT.model.glowLights[0].l.intensity > 1 && ROBOT.model.glowLights[1].l.intensity > 1 && ROBOT.model.glowLights[2].l.intensity === 0 && ROBOT.model.glowLights[3].l.intensity === 0")
    assert page.js("(c => c.r > 0.9 && c.b < 0.2)(ROBOT.model.glowLights[0].l.color)"), "the thrown light takes the ring's color"
    assert page.js(bar) != unlit, "the bar itself takes the color"
    assert page.js("(c => c.r > 0.6 && c.b < 0.1)(ROBOT.model.gaps[0].m.material.color) && !ROBOT.model.gaps[0].sp.visible && ROBOT.model.gaps[1].m.material.color.r < 0.05"), "light shows in the slit behind the lit side's connector only"
    # simple lights: plain colors only
    page.js("document.getElementById('rich').checked = false")
    assert page.until("ROBOT.model.glowLights.every(g => g.l.intensity === 0) && !ROBOT.model.halos[0].visible && ROBOT.model.leds[0].visible")
    page.js("(() => { document.getElementById('rich').checked = true; document.getElementById('ledoff').click(); })()")
    assert page.until(dark)
    # both small power lights: dark on battery, lit with a cable in either socket
    for key in ("side", "back"):
        page.js(f"fetch('/hw', {{method: 'POST', body: JSON.stringify({{key: '{key}', value: false}})}}).then(r => r.json())")
    lit = "ROBOT.model.chargeLed.material.color.r > 0.9 && ROBOT.model.bottomLed.material.color.r > 0.9 && ROBOT.model.powerGlow.every(g => g.l.intensity > 0)"
    assert page.until("!ST.hw.vbus") and page.until("ROBOT.model.chargeLed.material.color.r < 0.2 && ROBOT.model.bottomLed.material.color.r < 0.2")
    for key in ("back", "side"):
        page.js(f"fetch('/hw', {{method: 'POST', body: JSON.stringify({{key: '{key}', value: true}})}}).then(r => r.json())")
        assert page.until(lit), f"both power lights come on with a cable in the {key} socket"
        page.js(f"fetch('/hw', {{method: 'POST', body: JSON.stringify({{key: '{key}', value: false}})}}).then(r => r.json())")
        assert page.until("!ST.hw.vbus && ROBOT.model.chargeLed.material.color.r < 0.2")
    # the page keeps up with the dances: the unit's clock is read at least 15 times a second and a picture takes well under a frame
    stamps = set()
    end = time.time() + 1.0
    while time.time() < end:
        stamps.add(page.js("ST.now_ms"))
        time.sleep(0.01)
    assert len(stamps) >= 12, f"the state reached the page only {len(stamps)} times in a second"
    assert page.js("ROBOT.perf.frames > 10 && ROBOT.perf.ms < 20"), page.js("JSON.stringify(ROBOT.perf)")


def test_a_touched_head_pad_glows_and_says_which_pad(page):
    if not page.until("window.ROBOT && ROBOT.model && ROBOT.model.ready", 12):
        pytest.skip("the 3D drawing did not start here (it needs the pinned three.js from the network and a graphics context)")
    page.js("fetch('/call', {method: 'POST', body: JSON.stringify({name: 'self.robot.set_head_angles', arguments: {yaw: 0, pitch: 10}})}).then(r => r.json())")
    assert page.until("Math.abs(ST.head.yaw) < 1 && ST.hw.on", 10)
    page.js("(() => { Object.assign(ROBOT.view, {az: 0.3, el: 1.2, dist: 16}); window.scrollTo(0, 0); })()")
    time.sleep(0.4)
    p = page.js("ROBOT.pointOf('touch_back_1')")
    page.mouse("mouseMoved", p["x"], p["y"], 0)
    time.sleep(0.2)
    page.mouse("mouseMoved", p["x"] + 1, p["y"], 0)
    hit = "ROBOT.model.hits.find(h => h.name === 'touch_back_1')"
    assert page.until(f"{hit}.hl.visible"), "the pad glows under the pointer"
    page.click(p["x"] + 1, p["y"])
    assert page.until("/pad 2 of 3/.test(document.getElementById('msg').textContent)"), page.js("document.getElementById('msg').textContent")
    assert page.js(f"{hit}.hl.visible"), "and stays lit for a moment after the touch"


def spot_of(page, ident):
    """Page coordinates of the middle of a control, scrolled into view."""
    r = page.js(f"(() => {{ const e = document.getElementById('{ident}') || document.querySelector('{ident}'); e.scrollIntoView({{block: 'center'}});"
                f" const b = e.getBoundingClientRect(); return {{x: b.left + b.width / 2, y: b.top + b.height / 2}}; }})()")
    return r["x"], r["y"]


def test_a_dance_button_starts_a_session_and_the_lights_and_the_table_follow(page):
    page.js("fetch('/call', {method: 'POST', body: JSON.stringify({name: 'self.robot.stop_dance', arguments: {}})}).then(r => r.json())")
    for key, value in (("side", False), ("back", False), ("battery", 75)):
        page.js(f"fetch('/hw', {{method: 'POST', body: JSON.stringify({{key: '{key}', value: {json.dumps(value)}}})}}).then(r => r.json())")
    assert page.until("ST.hw.on && !ST.dance && ST.motion.state === 'free'", 10)
    page.click(*spot_of(page, "[data-dance=happy]"))
    assert page.until("ST.dance === 'happy' && ST.dance_sim && ST.dance_sim.running"), "the Dance happy button starts a dance session"
    assert page.until("/happy \\(step \\d, \\w+\\)/.test(document.getElementById('limv').textContent)"), page.js("document.getElementById('limv').textContent")
    assert page.until("ST.dance_sim.step >= 2 && ST.leds.some(c => c[0] + c[1] + c[2] > 0)", 12), "the ring comes on as the ladder climbs"
    if page.js("!!(window.ROBOT && ROBOT.model && ROBOT.model.ready)"):
        assert page.until("ROBOT.model.leds.slice(0, 12).some(m => m.visible) && ROBOT.model.glowLights.some(g => g.l.intensity > 0)"), "the drawn lights follow the unit's ring"
    page.click(*spot_of(page, "dstop"))
    assert page.until("!ST.dance && !ST.dance_sim.running && ST.leds.every(c => c[0] + c[1] + c[2] === 0)", 8), "Stop dance ends it and the ring goes dark"


def test_the_music_dance_row_starts_and_stops_a_simulated_song(page):
    page.js("(() => { document.getElementById('song').value = 'fast'; document.getElementById('mmode').value = 'unit'; })()")
    page.click(*spot_of(page, "mstart"))
    assert page.until("ST.dance_sim && ST.dance_sim.running && ST.dance_sim.song === 'fast'"), page.js("JSON.stringify(ST.dance_sim)")
    page.click(*spot_of(page, "mstop"))
    assert page.until("!ST.dance_sim.running", 8)


def test_the_utilization_panel_shows_what_the_rig_knows(page):
    text = "document.getElementById('utilv').textContent"
    assert page.until(f"/Battery/.test({text}) && /Servo supply/.test({text}) && /assumed/.test({text})")
    rate = page.js(f"+(/State updates(\\d+) a second/.exec({text}) || [0, 0])[1]")
    assert rate >= 12, f"the panel reports {rate} state updates a second"
    page.js("fetch('/hw', {method: 'POST', body: JSON.stringify({key: 'back', value: true})}).then(r => r.json())")
    assert page.until(f"/USB, back socket/.test({text})")
    page.js("fetch('/hw', {method: 'POST', body: JSON.stringify({key: 'back', value: false})}).then(r => r.json())")
    assert page.until(f"/the battery/.test({text})")


def test_time_lapse_runs_the_units_clock_faster_and_back(page):
    def rate():
        a = page.js("ST.now_ms")
        time.sleep(1.0)
        return page.js("ST.now_ms") - a
    page.js("(() => { const s = document.getElementById('tscale'); s.value = '5'; s.dispatchEvent(new Event('change')); })()")
    assert page.until("ST.util.time_scale === 5 && /5 times faster/.test(document.getElementById('tscalemsg').textContent)")
    fast = rate()
    page.js("(() => { const s = document.getElementById('tscale'); s.value = '1'; s.dispatchEvent(new Event('change')); })()")
    assert page.until("ST.util.time_scale === 1 && document.getElementById('tscalemsg').textContent === ''")
    slow = rate()
    assert fast > 3 * slow > 0, f"at 5 times the clock ran {fast} ms in a second, at real time {slow} ms"


def test_the_installed_block_draws_what_the_state_carries(page):
    text = page.js("(() => { paintBody(Object.assign({}, ST, {assets: {kinds: {style: {used: 2, slots: 4, active: 'face-01'}, sound: {used: 0, slots: 3, active: null}},"
                   " pool_free_bytes: 1000, pool_bytes: 4000, loaded: {}}})); return document.getElementById('installed').textContent; })()")
    assert "style: 2 of 4, active face-01" in text and "sound: 0 of 3" in text and "1,000 of 4,000 bytes" in text, text
    assert page.until("document.getElementById('installed').textContent === ''"), "with no installed set on the unit the block is empty"


def test_the_talk_panel_is_off_without_a_bridge_and_follows_a_fake_one(page):
    assert page.until("window.TALK && /not running here/.test(document.querySelector('#talk #tmsg').textContent)"), "without a voice bridge the panel says so"
    assert page.js("document.querySelector('#talk #tmic').disabled && document.querySelector('#talk #tspk').disabled && document.querySelector('#talk #tlive').style.display === 'none'")
    # a fake bridge in the page: it keeps the state the real one will, and records what the panel asks of it. No microphone is opened.
    page.js("""(() => { TALK.stop();
      window.FAKE = {mic_on: false, speaker_on: false, live_mic: false, mic_level: 0, speaker_level: 0, latency_ms: null, transcript: [], calls: []};
      const view = () => ({ok: true, json: async () => Object.assign({}, FAKE)});
      const post = async (u, b) => { FAKE.calls.push(b.action);
        if (b.action === 'mic_on') Object.assign(FAKE, {mic_on: true, live_mic: true, mic_level: 42, latency_ms: 830, transcript: [{who: 'you', text: 'hello <robot>'}, {who: 'robot', text: 'hi'}]});
        if (b.action === 'mic_off') Object.assign(FAKE, {mic_on: false, live_mic: false, mic_level: 0});
        if (b.action === 'speaker_on') Object.assign(FAKE, {speaker_on: true, speaker_level: 30});
        if (b.action === 'speaker_off') Object.assign(FAKE, {speaker_on: false, speaker_level: 0});
        return {json: async () => ({ok: true})}; };
      window.TALK = initTalk(document.getElementById('talk'), {fetch: async () => view(), post, every: 100}); })()""")
    assert page.until("!document.querySelector('#talk #tmic').disabled")
    page.click(*spot_of(page, "#talk #tmic"))
    assert page.until("FAKE.calls.join() === 'mic_on' && document.querySelector('#talk #tlive').style.display !== 'none' && /Microphone: on/.test(document.querySelector('#talk #tmic').textContent)"), "a real click turns the microphone on and the LIVE MIC sign shows"
    assert page.js("document.querySelector('#talk #tmicl').style.width === '42%' && document.querySelector('#talk #tlat').textContent === '0.83 s'")
    assert page.js("/you: hello <robot>/.test(document.querySelector('#talk #ttext').textContent) && !document.querySelector('#talk #ttext robot')"), "the transcript shows as text, never as markup"
    page.click(*spot_of(page, "#talk #tspk"))
    assert page.until("/Speaker: on/.test(document.querySelector('#talk #tspk').textContent) && document.querySelector('#talk #tspkl').style.width === '30%'")
    page.click(*spot_of(page, "#talk #tmic"))
    assert page.until("FAKE.calls.join() === 'mic_on,speaker_on,mic_off' && document.querySelector('#talk #tlive').style.display === 'none'"), "and off again: the sign goes with the microphone"
    page.js("(() => { TALK.stop(); window.TALK = initTalk(document.getElementById('talk')); })()")


def test_a_still_screen_is_put_on_the_robots_screen_and_goes_away(page):
    names = page.js("[...document.getElementById('scen').options].map(o => o.value)")
    stills = [n for n in names if n.startswith("still:")]
    if not stills:
        pytest.skip("no still-screen renderer is built here: bash scripts/virtual-unit/build-screens.sh")
    live = page.js("fetch('/frame.png').then(r => r.arrayBuffer()).then(b => b.byteLength)")
    page.js(f"(() => {{ const s = document.getElementById('scen'); s.value = '{stills[0]}'; s.scrollIntoView({{block: 'center'}}); }})()")
    page.click(*spot_of(page, "play"))
    assert page.until(f"ST.still === '{stills[0][6:]}' && /still screen/.test(document.getElementById('msg').textContent)"), page.js("document.getElementById('pl').textContent")
    shown = page.js("fetch('/frame.png').then(r => r.arrayBuffer()).then(b => b.byteLength)")
    assert shown > 100 and shown != live, "the robot's screen shows the still picture, not the running face"
    assert page.until("ST.still === ''", 14), "and the running screen comes back by itself"


def test_the_small_web_copy_of_the_model_loads_and_works_the_same(page):
    if not page.js("!!(window.ROBOT && ROBOT.model && ROBOT.model.ready)"):
        pytest.skip("the 3D drawing did not start here (it needs the pinned three.js from the network and a graphics context)")
    names = page.js("Object.keys(ROBOT.model.nodes).sort().join()")
    page.send("Page.navigate", url=page.base + "/?model=web")
    assert page.until("window.ROBOT && ROBOT.model && ROBOT.model.ready && /web\\.glb$/.test(ROBOT.modelFile) && typeof ST === 'object' && ST", 20), "the page did not load the web copy"
    web = page.js("Object.keys(ROBOT.model.nodes).filter(n => !/\\.mesh$/.test(n)).sort().join()")
    assert web == names, "the web copy has the same named parts"
    assert page.js("ROBOT.model.bars.length === 2 && ROBOT.model.hits.length >= 10 && !!ROBOT.model.screen")
    page.js("fetch('/hw', {method: 'POST', body: JSON.stringify({key: 'back', value: false})}).then(r => r.json())")
    assert page.until("ST.hw.on && !ST.hw.ports.back.plugged")
    page.js("(() => { document.getElementById('vback').click(); window.scrollTo(0, 0); })()")
    time.sleep(0.5)
    p = page.js("ROBOT.pointOf('usb_c_port')")
    page.click(p["x"], p["y"])
    assert page.until("ST.hw.ports.back.plugged"), "a click on the back socket works on the web copy too"
    page.js("fetch('/hw', {method: 'POST', body: JSON.stringify({key: 'back', value: false})}).then(r => r.json())")
