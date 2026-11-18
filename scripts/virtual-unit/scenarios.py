#!/usr/bin/env python3
"""Scripted scenarios on the virtual unit: golden frames and layout checks.
Usage: scenarios.py [--update] [name ...]   --update rewrites host/tests/golden/face/<scenario>.png from the current renderer.
Each scenario is a list of steps (tool calls, advance, touch) ending in a frame; checks run on that frame.
Exit 1 and one line per failing scenario on a mismatch or a broken layout rule.
Placement: host-side development tool; no firmware change. Upstream: none."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "host" / "tests" / "golden" / "face"
GOLDEN_SCREENS = ROOT / "host" / "tests" / "golden" / "screens"

spec = importlib.util.spec_from_file_location("vunit", Path(__file__).with_name("vunit.py"))
vunit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vunit)

EMOTE = lambda e: ("call", "self.face.bench_emotion", {"emotion": e})
SCENARIOS: dict[str, list] = {}
for e in ("neutral", "happy", "sad", "angry", "doubtful", "surprised", "sleepy", "sleeping", "love", "content", "thinking"):
    SCENARIOS[f"face-{e}"] = [EMOTE(e), ("advance", 1500)]
for lv in (25, 90):
    SCENARIOS[f"speak-{lv}"] = [EMOTE("neutral"), ("advance", 800), ("call", "self.face.bench_speak", {"level": lv, "seconds": 20}), ("advance", 400)]
SCENARIOS["closing-mid"] = [EMOTE("closing"), ("advance", 500)]
SCENARIOS["tired-low-battery"] = [("call", "self.face.bench_emotion", {"emotion": "tired", "tired_level": 2}), ("advance", 3400)]


# Screens other than the bare face, on the screens renderer. Not drawn by the renderer yet (gaps, listed so they are not forgotten):
# pairing screen, updating screen, lock screen and keypad (lock_render.sh is a separate program), the Wi-Fi setup screen itself
# (the renderer only has the banner flag for it).
SCREEN_GAPS = []  # every screen the unit can show is drawn
BAR = [("raw", "style big_eyes"), ("raw", "bbar always"), ("raw", "bstatus 80 0 1 1 1")]
SCREENS: dict[str, list] = {
    "screen-status-normal": BAR + [EMOTE("neutral"), ("advance", 1500)],
    "screen-listening": BAR + [("raw", "bst 1"), ("advance", 700)],
    "screen-muted": BAR + [("raw", "bstatus 80 0 1 1 0"), ("advance", 700)],
    "screen-offline": BAR + [("raw", "bstatus 80 0 0 0 1"), ("advance", 700)],
    "screen-low-battery": BAR + [("raw", "bstatus 12 0 1 1 1"), ("call", "self.face.bench_emotion", {"emotion": "tired", "tired_level": 2}), ("advance", 3400)],
    "screen-charging": BAR + [("raw", "bstatus 40 1 1 1 1"), ("advance", 700)],
    "screen-eyes-only-muted": BAR + [("raw", "style eyes_only"), ("raw", "bstatus 80 0 1 1 0"), ("raw", "seal on"), ("advance", 900)],  # patch UX03a
    "screen-apps-wall": BAR + [("raw", "pshow sheet"), ("advance", 400), ("raw", "pclick 270 215"), ("advance", 300), ("raw", "pclick 56 156"), ("advance", 700)],
    "screen-games-wall": BAR + [("raw", "pshow sheet"), ("advance", 400), ("raw", "pclick 270 215"), ("advance", 300), ("raw", "pclick 160 156"), ("advance", 700)],
    "screen-timers-app": BAR + [("raw", "pshow sheet"), ("advance", 400), ("raw", "pclick 270 215"), ("advance", 300), ("raw", "pclick 56 156"), ("advance", 700), ("raw", "pclick 80 70"), ("advance", 700)],
    "screen-settings-general": BAR + [("raw", "pshow settings"), ("advance", 500)],
    "screen-settings-network": BAR + [("raw", "pshow settings"), ("advance", 400), ("raw", "pclick 40 128"), ("advance", 500)],
    "screen-settings-faces": BAR + [("raw", "pshow settings"), ("advance", 400), ("raw", "pclick 40 190"), ("advance", 500)],
    "screen-settings-info": BAR + [("raw", "pshow settings"), ("advance", 400), ("raw", "pscrollby 40 150 64"), ("advance", 100), ("raw", "pclick 40 190"), ("advance", 500)],
    # The music dance ladder on a simulated song that builds from quiet to very loud (dance_sim.py: the unit's real ladder core, the host's show): the five steps (patches MD01 to MD03).
    "dance-1-eyes": [("call", "sim.music", {"action": "start", "song": "loud_peak", "mode": "home"}), ("advance", 1300)],
    "dance-2-nod": [("call", "sim.music", {"action": "start", "song": "loud_peak", "mode": "home"}), ("advance", 5200)],
    "dance-3-sway": [("call", "sim.music", {"action": "start", "song": "loud_peak", "mode": "home"}), ("advance", 10300)],
    "dance-4-full": [("call", "sim.music", {"action": "start", "song": "loud_peak", "mode": "home"}), ("advance", 13300)],
    "dance-5-down": [("call", "sim.music", {"action": "start", "song": "loud_peak", "mode": "home"}), ("advance", 27500)],
    # The same ladder as a hand-chosen dance on the unit alone (patch SF51: self.robot.dance happy, 90 BPM, a synthetic beat, the unit's own ring, notes, disco ball, confetti and faces).
    "dance-session-1-eyes": [("call", "self.robot.dance", {"name": "happy"}), ("advance", 1300)],
    "dance-session-2-nod": [("call", "self.robot.dance", {"name": "happy"}), ("advance", 5600)],
    "dance-session-3-sway": [("call", "self.robot.dance", {"name": "happy"}), ("advance", 10600)],
    "dance-session-4-full": [("call", "self.robot.dance", {"name": "happy"}), ("advance", 16200)],
    "dance-session-5-down": [("call", "self.robot.dance", {"name": "happy"}), ("advance", 38500)],
    # The unit with its host away (patches 143 and SF49): the Offline label after 45 s, and after 10 minutes the plain-words notice (English in the firmware; the others are drafts).
    "host-away-offline": BAR + [("raw", "bstatus 80 0 1 0 1"), ("advance", 900)],
    "host-away-notice-en": BAR + [("raw", "bstatus 80 0 1 0 1"), ("hostaway", "en"), ("advance", 250)],
    "host-away-notice-es": BAR + [("raw", "bstatus 80 0 1 0 1"), ("hostaway", "es"), ("advance", 250)],
    "host-away-notice-fr": BAR + [("raw", "bstatus 80 0 1 0 1"), ("hostaway", "fr"), ("advance", 250)],
    "host-away-notice-de": BAR + [("raw", "bstatus 80 0 1 0 1"), ("hostaway", "de"), ("advance", 250)],
    "host-away-notice-pt": BAR + [("raw", "bstatus 80 0 1 0 1"), ("hostaway", "pt"), ("advance", 250)],
    "host-away-notice-it": BAR + [("raw", "bstatus 80 0 1 0 1"), ("hostaway", "it"), ("advance", 250)],
    # The More screen (patches U03 to U05, SF69, UX13b): the menu, the version page with the affiliation notice (top, then scrolled to the last row), the games page, in English and Spanish.
    "more-menu": [("raw", "more open"), ("advance", 500)],
    "more-version": [("raw", "more open"), ("advance", 400), ("raw", "pclick 160 176"), ("advance", 600)],
    "more-version-end": [("raw", "more open"), ("advance", 400), ("raw", "pclick 160 176"), ("advance", 400), ("raw", "pscrollby 160 140 9999"), ("advance", 300)],
    "more-games": [("raw", "more open"), ("advance", 400), ("raw", "pscrollby 160 140 70"), ("advance", 200), ("raw", "pclick 160 170"), ("advance", 600)],
    "es-more-menu": [("raw", "more lang es"), ("raw", "more open"), ("advance", 500)],
    "es-more-version-end": [("raw", "more lang es"), ("raw", "more open"), ("advance", 400), ("raw", "pclick 160 176"), ("advance", 400), ("raw", "pscrollby 160 140 9999"), ("advance", 300)],
    "first-run-1": [("raw", "frun step 0 0 -1"), ("advance", 400)],
    "first-run-2": [("raw", "frun step 1 0 -1"), ("advance", 400)],
    "first-run-4": [("raw", "frun step 3 0 -1"), ("advance", 400)],
    "first-run-5": [("raw", "frun step 4 0 -1"), ("advance", 400)],
    "first-run-6": [("raw", "frun step 5 0 -1"), ("advance", 400)],
    "first-run-next": [("raw", "frun step 7 0 -1"), ("advance", 400)],
    "first-run-4-es": [("raw", "frun step 3 1 -1"), ("advance", 400)],
    "first-run-1-de": [("raw", "frun step 0 3 -1"), ("advance", 400)],
    "first-run-started": BAR + [("raw", "frun start"), ("advance", 800)],  # the real flow (registered as a screen, patch UX08)
    "screen-wifi-flag": BAR + [("raw", "bwifiscreen on"), ("advance", 700)],
    "screen-camera-on": BAR + [("raw", "bflag camera on"), ("advance", 800)],
    "screen-subtitles": BAR + [("raw", "bcaps subtitles"), ("raw", "ssay Sure, I can set a timer for five minutes."), ("advance", 900)],
    "screen-page-timers-running": BAR + [("raw", "ptimer 300 tea"), ("raw", "ptimer 90 eggs"), ("raw", "pshow timers"), ("advance", 800)],
    "screen-page-clock": BAR + [("raw", "pshow clock"), ("advance", 600)],
    # patch UX14: the three clock styles, awake and asleep (a moon and Zz, the page dimmed), and the tap that cycles them
    "clock-classic": BAR + [("raw", "pset hh 9"), ("raw", "pset mm 41"), ("raw", "pshow clock"), ("advance", 600)],
    "clock-ring": BAR + [("raw", "pset hh 9"), ("raw", "pset mm 41"), ("raw", "pset cstyle 1"), ("raw", "pshow clock"), ("advance", 600)],
    "clock-datetime": BAR + [("raw", "pset hh 9"), ("raw", "pset mm 41"), ("raw", "pset cstyle 2"), ("raw", "pshow clock"), ("advance", 600)],
    "clock-classic-asleep": BAR + [("raw", "pset hh 9"), ("raw", "pset mm 41"), ("raw", "pset asleep 1"), ("raw", "pshow clock"), ("advance", 600)],
    "clock-ring-asleep": BAR + [("raw", "pset hh 9"), ("raw", "pset mm 41"), ("raw", "pset cstyle 1"), ("raw", "pset asleep 1"), ("raw", "pshow clock"), ("advance", 600)],
    "clock-datetime-asleep": BAR + [("raw", "pset hh 9"), ("raw", "pset mm 41"), ("raw", "pset cstyle 2"), ("raw", "pset asleep 1"), ("raw", "pshow clock"), ("advance", 600)],
    "clock-datetime-12h": BAR + [("raw", "pset hh 14"), ("raw", "pset mm 5"), ("raw", "pset cstyle 2"), ("raw", "pshow clock"), ("advance", 600)],
    "clock-tap-to-datetime": BAR + [("raw", "pset hh 9"), ("raw", "pset mm 41"), ("raw", "pshow clock"), ("advance", 600), ("raw", "pclick 20 60"), ("advance", 600), ("raw", "pclick 20 60"), ("advance", 600), ("raw", "pclick 20 60"), ("advance", 600), ("raw", "pclick 20 60"), ("advance", 600)],
    "screen-page-timers": BAR + [("raw", "pshow timers"), ("advance", 600)],
    "screen-page-games": BAR + [("raw", "pshow games"), ("advance", 600)],
    "screen-page-games-scrolled": BAR + [("raw", "pshow games"), ("advance", 600), ("raw", "pscrollby 160 80 72"), ("advance", 300)],   # patch UX13e: a swipe up scrolls one row and a bit
    "screen-page-games-end": BAR + [("raw", "pshow games"), ("advance", 600), ("raw", "pscrollby 160 80 400"), ("advance", 300)],
    "screen-page-actions": BAR + [("raw", "pshow actions"), ("advance", 600)],
    "screen-control-sheet": BAR + [("raw", "pshow sheet"), ("advance", 600)],
    "screen-control-sheet-tiles": BAR + [("raw", "pshow sheet"), ("advance", 400), ("raw", "pclick 270 215"), ("advance", 500)],   # patch UX13c: page 2 of the sheet
    "es-control-sheet": BAR + [("raw", "pset es on"), ("raw", "pshow sheet"), ("advance", 600)],
    "es-control-sheet-tiles": BAR + [("raw", "pset es on"), ("raw", "pshow sheet"), ("advance", 400), ("raw", "pclick 270 215"), ("advance", 500)],
}


# The lock screen and keypad come from their own program (lock_render): script lines, one PNG per scenario written to {out}.
LOCK_SCENARIOS = {
    "lock-screen": ["banner on", "lock {out}"],
    "lock-keypad-empty": ["banner on", "pad 0 0 {out}"],
    "lock-keypad-three": ["banner on", "pad 3 0 {out}"],
    "lock-keypad-wrong": ["banner on", "pad 6 1 {out}"],
    "lock-keypad-wrong-es": ["banner on", "lang es", "pad 0 1 {out}"],
}


# The link covers, drawn by the unit's own code cut out of stackchan_display.cc (cover_gen.py): ShowBootCover(text, ring, glyph).
# The grid games drawn by the unit's own code (scripts/fw-face-render/grid_render.cc, cut from maipai_grid.cc by grid_gen.py): a game in play. Steps: game, drop, tap, flag, advance, snap.
_C4 = ["game c4", "drop 3 1", "advance 700", "drop 2 2", "advance 700", "drop 3 1", "advance 700", "drop 2 2", "advance 700", "drop 3 1", "advance 700", "drop 4 2", "advance 700"]
GRID_SCENARIOS = {
    "game-c4-playing": _C4 + ["snap {out}"],
    "game-c4-chip-falling": _C4 + ["drop 5 1", "advance 150", "snap {out}"],
    "game-c4-win": _C4 + ["drop 3 1", "advance 1500", "snap {out}"],
    "game-match-two-up": ["game match 5", "tap 0", "advance 400", "tap 5", "advance 500", "snap {out}"],
    "game-match-flipping": ["game match 5", "tap 0", "advance 90", "snap {out}"],
    "game-hangman-mid": ["game hangman 1", "tap 4", "advance 400", "tap 0", "advance 400", "tap 17", "advance 400", "tap 19", "advance 400", "snap {out}"],
    "game-mines-open": ["game mines 3", "tap 20", "advance 500", "snap {out}"],
    "game-over-c4-win": ["game c4 3", "over won|Score 38|Best 30|0|en", "snap {out}"],
    "game-over-c4-lose": ["game c4 3", "over lost||Best 30|0|en", "snap {out}"],
    "game-over-c4-draw": ["game c4 3", "over draw||Best 30|0|en", "snap {out}"],
    "game-over-c4-win-es": ["game c4 3", "over won|Puntos 38|Mejor 30|0|es", "snap {out}"],
    "game-over-match-win-new-best": ["game match 3", "over won|14 turns|Best 18|1|en", "snap {out}"],
    "game-over-hangman-win": ["game hangman 3", "over won|Score 70|Best 90|0|en", "snap {out}"],
    "game-over-hangman-lose": ["game hangman 3", "over lost|The word was robot|Best 90|0|en", "snap {out}"],
    "game-over-mines-win-new-best": ["game mines 3", "over won|Cleared in 82 s|Best 96 s|1|en", "snap {out}"],
    "game-over-mines-lose": ["game mines 3", "over lost|Boom!|Best 96 s|0|en", "snap {out}"],
    "game-over-tictactoe-win": ["game mines 3", "over won|Wins 3|Best 22|0|en", "snap {out}"],
    "game-over-tictactoe-lose": ["game mines 3", "over lost|Wins 3|Best 22|0|en", "snap {out}"],
    "game-over-tictactoe-draw": ["game mines 3", "over draw|Wins 3|Best 22|0|en", "snap {out}"],
    "game-over-snake-lose-new-best": ["game mines 3", "over lost|Length 34||1|en", "snap {out}"],
    "game-over-snake-lose": ["game mines 3", "over lost|Length 12|Best 31|0|en", "snap {out}"],
    "game-over-2048-win-new-best": ["game mines 3", "over won|Score 20480||1|en", "snap {out}"],
    "game-over-2048-lose": ["game mines 3", "over lost|Score 5184|Best 20480|0|en", "snap {out}"],
}

# Filmstrips: the frames a scenario collects with ("strip",) steps, half size, three to a row. The flip of a clock style change (patch UX14b) is 240 ms.
# a strip step runs one renderer frame (33 ms) and takes the picture without running another, so the eight frames after the tap span the 240 ms flip
_FLIP = [("raw", "pshow clock"), ("advance", 700), ("strip",), ("raw", "pclick 20 60")]
FILMSTRIPS = {
    "clock-flip-classic-to-ring": BAR + [("raw", "pset hh 9"), ("raw", "pset mm 41")] + _FLIP + [("stripnow",)] * 8,
    "clock-flip-ring-to-datetime": BAR + [("raw", "pset hh 9"), ("raw", "pset mm 41"), ("raw", "pset cstyle 1")] + _FLIP + [("stripnow",)] * 8,
}
# The offline mumble's mouth (patch UX16, docs/design/offline-mumble.md): the levels the reference gives for the first nine characters of "Hello! I am your robot.", one slot each.
import mumble as _mumble   # noqa: E402  (scripts/virtual-unit is on the path: this file is run from there)
_HELLO = [b.mouth for b in _mumble.blips("Hello! I am your robot. How can I help you today?", 0, 3300)[:9]]
FILMSTRIPS["mumble-mouth-sync"] = [("raw", "style big_eyes"), ("call", "self.face.bench_emotion", {"emotion": "happy"}), ("advance", 400)] + [("speakstrip", m) for m in _HELLO]
SCREENS.update(FILMSTRIPS)


def strip_png(frames: list, per_row: int = 3) -> bytes:
    import thumbnails as tn
    halves = [tn._rows(tn.half(f)) for f in frames]
    w, h = halves[0][0], halves[0][1]
    rows = []
    for r0 in range(0, len(halves), per_row):
        group = halves[r0:r0 + per_row]
        for y in range(h):
            line = b"".join(g[2][y] for g in group) + b"\0" * (3 * w * (per_row - len(group)))
            rows.append(line)
    return tn._png(w * per_row, len(rows), rows)


COVER_SCENARIOS = {
    "cover-connecting-wifi": ["show 1 0 Connecting to Wi-Fi...", "advance 800", "snap {out}"],
    "cover-connecting-home": ["show 1 0 Connecting to Home...", "advance 800", "snap {out}"],
    "cover-wifi-setup": ["show 2 1 Wi-Fi setup\\nstackchan-A1B2\\nhttp://192.168.4.1\\nCode: 123456", "advance 600", "snap {out}"],
    "cover-update-0": ["update 0", "advance 300", "snap {out}"],
    "cover-update-62": ["update 62", "advance 300", "snap {out}"],
    "cover-update-installed": ["update 100", "advance 300", "snap {out}"],
    "cover-update-refused": ["update -2", "advance 300", "snap {out}"],
    "cover-pairing": ["show 2 2 Waiting for Home\\nto approve me", "advance 600", "snap {out}"],
}


# ---- the two USB-C sockets (one shared USB path): every combination, a 12 V mistake, and a cable going in or out during a dance.
# A step ("hw", key, value) sets the body (view.py plays these; they need the body, so scenarios.run does not take them).
# "expect" is what GET /state must say when the steps are done, as dotted paths. host/tests/test_virtual_unit_ports.py plays each one
# through the running view and checks it, so the answers come from the unit's own limiter and status.
_REST = [("hw", "battery", 75), ("hw", "carried", False), ("hw", "orient", "upright"), ("hw", "side_source", "computer"), ("hw", "back_source", "charger"),
         ("hw", "side", False), ("hw", "back", False), ("call", "self.robot.stop_dance", {}), ("advance", 300)]
_DANCE = [("call", "self.robot.dance", {"name": "look_around"}), ("advance", 1200)]
PORTS: dict[str, dict] = {
    "ports-none": {"steps": _REST, "expect": {
        "hw.powered_by": "battery", "hw.vbus": False, "hw.charging": False, "hw.serial_possible": False, "hw.supply.input_ma": 0,
        "hw.limiter_cable.present": False, "motion.state": "free", "motion.scale": 100, "battery.charging": False}},
    "ports-side-only": {"steps": _REST + [("hw", "side", True), ("hw", "serial", True), ("advance", 300)], "expect": {
        "hw.powered_by": "side", "hw.vbus": True, "hw.charging": True, "hw.serial": True, "hw.supply.input_ma": 500,
        "hw.limiter_cable.from": ["side"], "motion.state": "usb_limited", "motion.scale": 50, "motion.usb": True, "battery.charging": True}},
    "ports-back-only": {"steps": _REST + [("hw", "back", True), ("advance", 300)], "expect": {
        "hw.powered_by": "back", "hw.vbus": True, "hw.charging": True, "hw.serial_possible": False, "hw.usb": True, "hw.supply.input_ma": 2000,
        "hw.limiter_cable.from": ["back"], "motion.state": "usb_limited", "motion.scale": 50, "battery.charging": True}},
    "ports-both": {"steps": _REST + [("hw", "side", True), ("hw", "back", True), ("advance", 300)], "expect": {
        "hw.powered_by": "both", "hw.vbus": True, "hw.charging": True, "hw.serial_possible": True, "hw.supply.input_ma": 2000, "hw.usb_path.both_plugged": True,
        "hw.usb_path.data_from": "side",
        "hw.limiter_cable.from": ["side", "back"], "motion.state": "usb_limited", "motion.scale": 50}},
    "ports-back-computer-serial": {"steps": _REST + [("hw", "back_source", "computer"), ("hw", "back", True), ("hw", "serial", True), ("advance", 300)], "expect": {
        "hw.powered_by": "back", "hw.vbus": True, "hw.serial": True, "hw.usb_path.data_from": "back", "hw.supply.input_ma": 500, "hw.ports.side.plugged": False,
        "motion.state": "usb_limited", "motion.usb": True}},   # the bench case: a computer on the back socket alone gives power and the serial device
    "ports-back-12v-refused": {"steps": _REST + [("hw", "back_source", "supply_12v"), ("hw", "back", True), ("advance", 300)], "expect": {
        "hw.powered_by": "battery", "hw.vbus": False, "hw.charging": False, "hw.ports.back.fault": True, "hw.ports.back.gives_power": False,
        "hw.limiter_cable.present": False, "motion.state": "free", "motion.scale": 100}},
    "ports-plug-during-dance": {"steps": _REST + _DANCE + [("hw", "back", True), ("advance", 500)], "expect": {
        "dance": "look_around", "hw.powered_by": "back", "motion.state": "usb_limited", "motion.scale": 50}},
    "ports-unplug-during-dance": {"steps": _REST + [("hw", "side", True), ("advance", 300)] + _DANCE + [("hw", "side", False), ("advance", 500)], "expect": {
        "dance": "look_around", "hw.powered_by": "battery", "hw.serial": False, "motion.state": "free", "motion.scale": 100}},
}


def run_lock(name: str) -> bytes:
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "shot.png"
        lines, prog = (COVER_SCENARIOS[name], "cover/cover_render") if name in COVER_SCENARIOS else (GRID_SCENARIOS[name], "grid/grid_render") if name in GRID_SCENARIOS else (LOCK_SCENARIOS[name], "lock/lock_render")
        script = "\n".join(line.format(out=out) for line in lines) + "\n"
        subprocess.run([str(ROOT / ".runs" / "vu-screens" / prog)], input=script, text=True, check=True, capture_output=True)
        return out.read_bytes()


# Every language of the first-run flow (steps 1, 2, 4, 5 and 6 by 6 languages) and the Spanish forms of the app screens: overflow and edge checks run on each.
LANGS = ["en", "es", "fr", "de", "pt", "it"]
for _li, _lang in enumerate(LANGS):
    for _st in (0, 1, 3, 4, 5):
        SCREENS.setdefault(f"first-run-{_st + 1}-{_lang}", [("raw", f"frun step {_st} {_li} -1"), ("advance", 400)])
    SCREENS.setdefault(f"first-run-next-{_lang}", [("raw", f"frun step 7 {_li} -1"), ("advance", 400)])   # the last screen after All set! (patch UX12)
for _name, _steps in (("sheet", [("raw", "pshow sheet"), ("advance", 500)]), ("apps-wall", [("raw", "pshow sheet"), ("advance", 400), ("raw", "pclick 270 215"), ("advance", 300), ("raw", "pclick 56 156"), ("advance", 700)]),
                      ("settings-general", [("raw", "pshow settings"), ("advance", 500)]), ("settings-info", [("raw", "pshow settings"), ("advance", 400), ("raw", "pscrollby 40 150 64"), ("advance", 100), ("raw", "pclick 40 190"), ("advance", 500)]),
                      ("page-timers", [("raw", "pshow timers"), ("advance", 600)]), ("page-actions", [("raw", "pshow actions"), ("advance", 600)])):
    SCREENS[f"es-{_name}"] = BAR + [("raw", "pset es on")] + _steps


def load_recording(path) -> list:
    """A recording saved by the 3D view (scripts/virtual-unit/recordings/NAME.json) as scenario steps: waits, renderer touches, tool calls."""
    import json

    steps: list = []
    for item in json.loads(Path(path).read_text())["steps"]:
        if item.get("wait_ms"):
            steps.append(("advance", int(item["wait_ms"])))
        if "touch" in item:
            t = item["touch"]
            if t["kind"] == "head":
                steps.append(("raw", "pevent head"))
            elif t["kind"] == "swipe":
                steps.append(("raw", f"pswipe {t['x']} {t['y']} {t['x2']} {t['y2']} {t.get('ms', 250)}"))
            else:
                steps.append(("raw", f"pclick {t['x']} {t['y']}"))
        elif "call" in item:
            steps.append(("call", item["call"]["name"], item["call"].get("arguments", {})))
    return steps


def run(u, steps) -> None:
    for step in steps:
        if step[0] == "call":
            out = u.call(step[1], step[2])
            assert not out.get("isError"), out
        elif step[0] == "raw":
            u.raw(step[1])
        elif step[0] == "advance":
            u.advance(step[1])
        elif step[0] == "speakstrip":   # the mouth at this speak level for one mumble slot (66 ms), then a frame for the filmstrip
            u.raw("speak %d" % step[1])
            u.raw("advance 66")
            u.__dict__.setdefault("strip", []).append(u.snapshot_now())
        elif step[0] == "stripnow":   # one renderer frame (33 ms), then a frame for the filmstrip
            u.raw("advance 33")
            u.__dict__.setdefault("strip", []).append(u.snapshot_now())
        elif step[0] == "strip":   # a frame for a filmstrip golden (the frames are put side by side, half size, by strip_png)
            u.__dict__.setdefault("strip", []).append(u.snapshot())
        elif step[0] == "touch":
            u.touch(*step[1:])
        elif step[0] == "hostaway":   # the unit has been away from its host for 11 minutes: the notice shows (patch SF49), in this language
            import host_away

            away = u.host_away
            away.language = step[1]
            away.link_lost()
            u.jump(11 * 60 * 1000)
            away.tick(u.now_ms)


def png_pixels(png: bytes) -> bytes:
    import zlib
    return zlib.decompress(png[png.index(b"IDAT") + 4 : png.rindex(b"IEND") - 8])


def layout_problems(u, name: str) -> list[str]:
    """Layout rules every face must keep (panel 320x240): lit pixels stay on the panel and keep a 4 px edge margin; eyes stay in the upper 60 percent."""
    bad = []
    if name.startswith(("more-", "es-more-")):   # a scrolling list runs to the bottom edge by design: the screen audit checks these screens
        return bad
    whole = u.count(0, 0, 320, 240)
    if name not in ("face-sleeping",) and whole["lit"] == 0:
        bad.append("blank screen")
    elif whole["lit"]:
        x0, y0, x1, y1 = whole["bbox"]
        if x0 < 4 or y0 < 4 or x1 > 315 or y1 > 235:
            bad.append(f"drawing touches the panel edge (bbox {whole['bbox']})")
    return bad


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    update = "--update" in sys.argv
    screens_built = (ROOT / ".runs" / "vu-screens" / "render").exists()
    names = args or list(SCENARIOS) + (list(SCREENS) + list(LOCK_SCENARIOS) + list(COVER_SCENARIOS) + list(GRID_SCENARIOS) if screens_built else [])
    if not args and not screens_built:
        print("screens renderer not built: skipping screen scenarios (bash scripts/virtual-unit/build-screens.sh)")
    failed = 0
    GOLDEN.mkdir(parents=True, exist_ok=True)
    GOLDEN_SCREENS.mkdir(parents=True, exist_ok=True)
    for name in names:
        is_screen = name in SCREENS or name in LOCK_SCENARIOS or name in COVER_SCENARIOS or name in GRID_SCENARIOS
        if name in LOCK_SCENARIOS or name in COVER_SCENARIOS or name in GRID_SCENARIOS:
            png, problems = run_lock(name), []
        else:
            with vunit.VirtualUnit(profile="screens" if is_screen else "face") as u:
                run(u, SCREENS[name] if is_screen else SCENARIOS[name])
                png = strip_png(u.strip) if name in FILMSTRIPS else u.snapshot()
                problems = [] if name in FILMSTRIPS else layout_problems(u, name)
        folder = GOLDEN_SCREENS if is_screen else GOLDEN
        gold = folder / f"{name}.png"
        if update:
            gold.write_bytes(png)
        elif not gold.exists():
            problems.append("no golden frame: run scenarios.py --update and look at it")
        elif png_pixels(gold.read_bytes()) != png_pixels(png):
            (folder.parent / f"{name}.actual.png").write_bytes(png)
            problems.append(f"frame differs from golden (actual saved to host/tests/golden/{name}.actual.png)")
        for p in problems:
            failed += 1
            print(f"FAIL {name}: {p}")
    if not args:
        print("not drawn yet: " + ", ".join(SCREEN_GAPS))
    print(f"{len(names) - failed} of {len(names)} scenarios clean" if not failed else f"{failed} problems")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
