#!/usr/bin/env python3
"""Scripted scenarios on the virtual unit: golden frames and layout checks.
Usage: scenarios.py [--update] [name ...]   --update rewrites host/tests/golden/face/<scenario>.png from the current renderer.
Each scenario is a list of steps (tool calls, advance, touch) ending in a frame; checks run on that frame.
Exit 1 and one line per failing scenario on a mismatch or a broken layout rule.
Placement: host-side development tool; no firmware change. Upstream: none."""
from __future__ import annotations

import hashlib
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
    "first-run-4c": [("raw", "frun step 3 0 9"), ("advance", 400)],
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
    "screen-page-timers-one": BAR + [("raw", "ptimer 300 tea"), ("raw", "pshow timers"), ("advance", 800)],   # patch UX13f: one timer, the quick starts under it
    "screen-page-timers-more": BAR + [("raw", "ptimer 300 tea"), ("raw", "ptimer 90 eggs"), ("raw", "ptimer 900 laundry"), ("raw", "pshow timers"), ("advance", 800)],   # three timers: two rows and +1 more
    "screen-alarms-app": BAR + [("raw", "pshow sheet"), ("advance", 400), ("raw", "pclick 270 215"), ("advance", 300), ("raw", "pclick 56 156"), ("advance", 700), ("raw", "pclick 240 70"), ("advance", 700)],
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
    "game-hilo-start": ["game c4 3", "hilo 38 0|0|0|0|en", "snap {out}"],
    "game-hilo-streak": ["game c4 3", "hilo 21 0|0|0|7|en", "snap {out}"],
    "game-hilo-right": ["game c4 3", "hilo 4 23|1|1|8|en", "snap {out}"],
    "game-hilo-wrong": ["game c4 3", "hilo 12 13|1|2|3|en", "snap {out}"],
    "game-hilo-same": ["game c4 3", "hilo 9 22|1|3|5|en", "snap {out}"],
    "game-hilo-streak-es": ["game c4 3", "hilo 47 0|0|0|12|es", "snap {out}"],
    "game-reversi-start": ["game c4 3", "reversi |0|en", "snap {out}"],
    "game-reversi-opening": ["game c4 3", "reversi 19|0|en", "snap {out}"],
    "game-reversi-thinking": ["game c4 3", "reversi 19 44|1|en", "snap {out}"],
    "game-reversi-midgame": ["game c4 3", "reversi 19 44 3 29 9 45 26 51|0|en", "snap {out}"],
    "game-reversi-pass": ["game c4 3", "reversi board PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPU.|1|55|1|en", "snap {out}"],
    "game-reversi-midgame-es": ["game c4 3", "reversi 19 44 3 29 9 45 26 51|0|es", "snap {out}"],
    "game-battleship-start": ["game c4 3", "battleship 3||en", "snap {out}"],
    "game-battleship-midgame": ["game c4 3", "battleship 3|0 7 14 4 5 17 20 21 23 28|en", "snap {out}"],
    "game-battleship-last-shots": ["game c4 3", "battleship 3|0 1 2 3 6 7 8 9 12 13 14 15 18 19 24 25 26 27 4 5 17|en", "snap {out}"],
    "game-battleship-midgame-es": ["game c4 3", "battleship 3|0 7 14 4 5 17 20 21 23 28|es", "snap {out}"],
    "game-pong-serve": ["game c4 3", "pong 150 90 3 0|76 76|0 0|en", "snap {out}"],
    "game-pong-rally": ["game c4 3", "pong 190 40 7 -3|120 52|2 1|en", "snap {out}"],
    "game-pong-match-point": ["game c4 3", "pong 60 150 -9 4|140 100|4 3|en", "snap {out}"],
    "game-pong-rally-es": ["game c4 3", "pong 190 40 7 -3|120 52|2 1|es", "snap {out}"],
    "game-flyer-start": ["game c4 3", "flyer 4|0|103|0|0|en", "snap {out}"],
    "game-flyer-between": ["game c4 3", "flyer 4|70|120|1|0|en", "snap {out}"],
    "game-flyer-score": ["game c4 3", "flyer 4|140|150|7|0|en", "snap {out}"],
    "game-flyer-after-hit-es": ["game c4 3", "flyer 4|60|190|3|1|es", "snap {out}"],
    "game-dicepoker-start": ["game c4 3", "poker 1 1 1 1 1|0|0|1|0|0|en", "snap {out}"],
    "game-dicepoker-first-roll": ["game c4 3", "poker 2 5 3 5 6|0|2|1|0|1|en", "snap {out}"],
    "game-dicepoker-pair-held": ["game c4 3", "poker 2 5 3 5 6|10|1|1|0|1|en", "snap {out}"],
    "game-dicepoker-full-house": ["game c4 3", "poker 4 4 4 2 2|27|0|3|70|1|en", "snap {out}"],
    "game-dicepoker-straight": ["game c4 3", "poker 2 3 4 5 6|0|0|4|110|1|en", "snap {out}"],
    "game-dicepoker-five-es": ["game c4 3", "poker 6 6 6 6 6|31|0|5|180|1|es", "snap {out}"],
    "game-over-dicepoker-over-new-best": ["game c4 3", "over over|Score 230||1|en", "snap {out}"],
    # patches SF76 and SF77: 2048 and Snake, steered by the unit's own swipe classification (a swipe of 60 px or more in 450 ms or less; a still touch held 450 ms is a long press)
    "game-slide-start": ["game slide 5", "advance 100", "snap {out}"],
    "game-slide-swiped": ["game slide 5", "swipe 250 120 60 125 180", "advance 300", "swipe 160 210 165 40 180", "advance 300", "snap {out}"],
    "game-slide-2048": ["game slide 5", "tiles 11 10 9 8 4 5 6 7 3 2 1 1 0 1 2 0", "advance 100", "snap {out}"],
    "game-slide-swipes-filmstrip": ["game slide 5", "advance 100", "stripadd", "swipe 250 120 60 125 180", "advance 60", "stripadd", "advance 120", "stripadd", "swipe 160 210 165 40 180", "advance 60", "stripadd", "advance 120", "stripadd", "swipe 60 120 260 118 180", "advance 60", "stripadd", "advance 120", "stripadd", "swipe 160 40 158 210 180", "advance 60", "stripadd", "advance 120", "stripadd", "stripwrite {out} 3"],
    "game-snake-start": ["game snake 9", "advance 100", "snap {out}"],
    "game-snake-moving": ["game snake 9", "advance 2900", "snap {out}"],
    "game-snake-turned": ["game snake 9", "advance 1900", "swipe 160 200 162 60 150", "advance 900", "snap {out}"],
    "game-snake-steering-filmstrip": ["game snake 9", "advance 1700", "stripadd", "advance 330", "stripadd", "swipe 160 200 162 60 150", "advance 330", "stripadd", "advance 330", "stripadd", "swipe 250 120 60 122 150", "advance 330", "stripadd", "advance 330", "stripadd", "stripwrite {out} 3"],
    "game-snake-crashed": ["game snake 9", "advance 12000", "snap {out}"],
    "game-mines-flagged": ["game mines 3", "swipe 184 100 184 100 100", "advance 300", "swipe 100 160 100 160 600", "advance 400", "swipe 148 130 148 130 600", "advance 400", "snap {out}"],
    # patch SF72: a chip dropping into Four in a Row, one frame every 60 ms (the fall, the landing bounce), and the winning four pulsing (one frame every 120 ms): twelve frames
    "game-c4-drop-filmstrip": ["game c4", "drop 3 1", "advance 700", "drop 2 2", "advance 700", "drop 3 1", "advance 700", "drop 2 2", "advance 700", "drop 3 1", "advance 700", "drop 4 2", "stripadd"] + ["advance 60", "stripadd"] * 8 + ["advance 400", "drop 3 1", "advance 700"] + ["advance 120", "stripadd"] * 0 + ["stripwrite {out} 3"],
    "game-riddle-typing": ["game c4 3", "qa riddle|riddle|What has keys but cannot open locks?|A piano|22|0|en", "snap {out}"],
    "game-joke-ready": ["game c4 3", "qa riddle|joke|I told my robot a joke about batteries. It was not charged by it.||-1|0|en", "snap {out}"],
    "game-riddle-ready": ["game c4 3", "qa riddle|riddle|What has keys but cannot open locks?|A piano|-1|0|en", "snap {out}"],
    "game-riddle-revealed": ["game c4 3", "qa riddle|riddle|What has keys but cannot open locks?|A piano|-1|1|en", "snap {out}"],
    "game-riddle-revealed-es": ["game c4 3", "qa riddle|riddle|Que tiene dientes pero no puede morder?|Un peine|-1|1|es", "snap {out}"],
    "game-trivia-ask": ["game c4 3", "qa trivia|Which planet is known as the Red Planet?|Venus;Mars;Jupiter;Mercury|3|10|20|0|0|0|en", "snap {out}"],
    "game-trivia-right": ["game c4 3", "qa trivia|Which planet is known as the Red Planet?|Venus;Mars;Jupiter;Mercury|3|10|30|1|1|1|en", "snap {out}"],
    "game-trivia-wrong": ["game c4 3", "qa trivia|Which planet is known as the Red Planet?|Venus;Mars;Jupiter;Mercury|3|10|20|2|3|1|en", "snap {out}"],
    "game-trivia-long-three": ["game c4 3", "qa trivia|Which animal is the only mammal that can truly fly with its wings, and not just glide?|A bat;A flying squirrel;A sugar glider|7|10|60|0|0|0|en", "snap {out}"],
    "game-trivia-ask-es": ["game c4 3", "qa trivia|Cual es el planeta rojo?|Venus;Marte;Jupiter;Mercurio|3|10|20|0|0|0|es", "snap {out}"],
    "game-twenty-ask": ["game c4 3", "qa twenty|Is it bigger than a loaf of bread?|7|0|en", "snap {out}"],
    "game-twenty-guess": ["game c4 3", "qa twenty|Is it a banana?|15|1|en", "snap {out}"],
    "game-twenty-ask-es": ["game c4 3", "qa twenty|Es mas grande que una barra de pan?|7|0|es", "snap {out}"],
    "game-over-trivia-win-new-best": ["game c4 3", "over won|Score 80|Best 70|1|en", "snap {out}"],
    "game-over-colormemory-over-new-best": ["game c4 3", "over over|Round 15||1|en", "snap {out}"],
    "game-over-colormemory-over": ["game c4 3", "over over|Round 9|Best 14|0|en", "snap {out}"],
    "game-over-whack-timeup-new-best": ["game c4 3", "over timeup|Score 301||1|en", "snap {out}"],
    "game-over-whack-timeup": ["game c4 3", "over timeup|Score 120|Best 287|0|en", "snap {out}"],
    "game-over-doit-over": ["game c4 3", "over over|Score 12|Best 30|0|en", "snap {out}"],
    "game-over-rps-win": ["game c4 3", "over won|Match 2 to 1|Best 3|0|en", "snap {out}"],
    "game-over-rps-lose": ["game c4 3", "over lost|Match 1 to 2|Best 3|0|en", "snap {out}"],
    "game-over-rps-draw": ["game c4 3", "over draw|Match 1 to 1|Best 3|0|en", "snap {out}"],
    "game-over-twenty-lose": ["game c4 3", "over lost|It was a pear|Best 4 of 20|0|en", "snap {out}"],
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
    "game-over-snake-over-new-best": ["game mines 3", "over over|Length 34||1|en", "snap {out}"],
    "game-over-snake-over": ["game mines 3", "over over|Length 12|Best 31|0|en", "snap {out}"],
    "game-over-2048-win-new-best": ["game mines 3", "over won|Score 20480||1|en", "snap {out}"],
    "game-over-2048-over": ["game mines 3", "over over|Score 5184|Best 20480|0|en", "snap {out}"],
    "game-c4-look-1": ["game c4 3", "look 1", "drop 3 1", "advance 700", "drop 2 2", "advance 700", "drop 3 1", "advance 700", "drop 4 2", "advance 700", "drop 3 1", "advance 700", "snap {out}"],
    "game-c4-look-2": ["game c4 3", "look 2", "drop 3 1", "advance 700", "drop 2 2", "advance 700", "drop 3 1", "advance 700", "drop 4 2", "advance 700", "drop 3 1", "advance 700", "snap {out}"],
    "game-c4-look-0": ["game c4 3", "look 0", "drop 3 1", "advance 700", "drop 2 2", "advance 700", "drop 3 1", "advance 700", "drop 4 2", "advance 700", "drop 3 1", "advance 700", "snap {out}"],
    "game-c4-look-2-win": ["game c4 3", "look 2", "drop 3 1", "advance 700", "drop 2 2", "advance 700", "drop 3 1", "advance 700", "drop 2 2", "advance 700", "drop 3 1", "advance 700", "drop 4 2", "advance 700", "drop 3 1", "advance 2200", "snap {out}"],
    "game-balance-start": ["game c4 3", "balance 4|0|en", "snap {out}"],
    "game-balance-rolling": ["game c4 3", "balance 4|90|en", "snap {out}"],
    "game-balance-hole": ["game c4 3", "balance 4|300|en", "snap {out}"],
    "game-balance-late-es": ["game c4 3", "balance 4|1500|es", "snap {out}"],
    "game-maze-start": ["game c4 3", "maze 4|0|en", "snap {out}"],
    "game-maze-halfway": ["game c4 3", "maze 4|200|en", "snap {out}"],
    "game-maze-near-goal": ["game c4 3", "maze 4|520|en", "snap {out}"],
    "game-maze-other-es": ["game c4 3", "maze 9|260|es", "snap {out}"],
}
# The new look of the shared game-over screen (patch UX15d, docs/design/game-over-look.md): each outcome on three sample games, the neutral ends, the six languages, moments of the motion and the pressed buttons.
# The `over` fields: result|score|best|new best|language|look level|ms after it appeared|pressed button. Look 2 is the new look moving; at 2000 ms every motion has ended.
def _over(result, score, best, nb, lang="en", look=2, ms=2000, pressed=""):
    return ["game c4 3", f"over {result}|{score}|{best}|{nb}|{lang}|{look}|{ms}|{pressed}", "snap {out}"]
for _g, _score, _best in (("c4", "Score 38", "Best 30"), ("rps", "Match 2 to 1", "Best 3"), ("tictactoe", "Wins 3", "Best 22")):
    for _res, _nb in (("won", 0), ("lost", 0), ("draw", 0), ("won", 1)):
        _o = "newbest" if _nb else _res
        GRID_SCENARIOS[f"game-over-look-{_o}-{_g}"] = _over(_res, _score, "" if _nb else _best, _nb)
GRID_SCENARIOS["game-over-look-timeup-whack"] = _over("timeup", "Score 120", "Best 287", 0)
GRID_SCENARIOS["game-over-look-over-doit"] = _over("over", "Score 12", "Best 30", 0)
GRID_SCENARIOS["game-over-look-newbest-colormemory"] = _over("over", "Round 15", "", 1)
for _lg in ("en", "es", "fr", "de", "pt", "it"):
    GRID_SCENARIOS[f"game-over-look-won-lang-{_lg}"] = _over("won", "Score 66" if _lg == "en" else {"es": "Puntos 66", "fr": "Score 66", "de": "Punkte 66", "pt": "Pontos 66", "it": "Punti 66"}[_lg], "Best 70", 0, _lg)
    GRID_SCENARIOS[f"game-over-look-newbest-lang-{_lg}"] = _over("over", "Score 301", "", 1, _lg)
GRID_SCENARIOS["game-over-look-lost-lang-de"] = _over("lost", "Punkte 12", "Beste 30", 0, "de")
GRID_SCENARIOS["game-over-look-timeup-lang-es"] = _over("timeup", "Puntos 120", "Mejor 287", 0, "es")
GRID_SCENARIOS["game-over-look-won-confetti"] = _over("won", "Score 66", "Best 70", 0, ms=660)
GRID_SCENARIOS["game-over-look-won-landing"] = _over("won", "Score 66", "Best 70", 0, ms=210)
GRID_SCENARIOS["game-over-look-lost-rain"] = _over("lost", "Score 12", "Best 30", 0, ms=700)
GRID_SCENARIOS["game-over-look-draw-squeeze"] = _over("draw", "Match 1 to 1", "Best 3", 0, ms=600)
GRID_SCENARIOS["game-over-look-timeup-sweep"] = _over("timeup", "Score 120", "Best 287", 0, ms=900)
GRID_SCENARIOS["game-over-look-newbest-glitter"] = _over("won", "Score 301", "", 1, ms=600)
GRID_SCENARIOS["game-over-look-won-pressed-again"] = _over("won", "Score 66", "Best 70", 0, pressed=1)
GRID_SCENARIOS["game-over-look-lost-pressed-quit"] = _over("lost", "Score 12", "Best 30", 0, pressed=2)
GRID_SCENARIOS["game-over-look-won-still"] = _over("won", "Score 66", "Best 70", 0, look=1)
GRID_SCENARIOS["game-over-look-newbest-still"] = _over("won", "Score 301", "", 1, look=1)

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
# Offline lines by situation (decision 24 extension): the subtitle strip with the canned line and the mumble's mouth, six situations in six languages (offline_lines.py).
import offline_lines as _ol   # noqa: E402
for _sit in _ol.SITUATIONS:
    for _lg in _ol.LANGS:
        _txt = _ol.line(_sit, _lg)
        SCREENS[f"offline-line-{_sit.replace('_', '-')}-{_lg}"] = BAR + [("raw", "bcaps subtitles"), ("raw", f"ssay {_txt}"), ("advance", 500), ("raw", f"speak {_ol.mid_speech_level(_txt)}"), ("advance", 200)]
# The two-message state of a unit whose host is away (patches SF64, SF68, SF73): Offline steady (after 45 s), then at ten minutes the notice takes the banner row for 20 s at the privacy
# priority (it is long, so it scrolls), then Offline again. Frames: 1 minute away, the notice at 10 min 2 s, 7 s in, 14 s in, 19 s in, then 11 minutes away (the notice has ended).
FILMSTRIPS["host-away-two-messages"] = BAR + [("awaystep", 60000), ("awaystep", 541000), ("awaystep", 5000), ("awaystep", 7000), ("awaystep", 5000), ("awaystep", 30000)]
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
    SCREENS.setdefault(f"brain-removed-{_lang}", [("raw", f"bnotice {_li}"), ("advance", 400)])   # the Hosted link removed notice (patch UX20)
    SCREENS.setdefault(f"first-run-4c-{_lang}", [("raw", f"frun step 3 {_li} 9"), ("advance", 400)])   # the Custom page of the brain step: the three ways (patch UX19; preview value 9)
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
        elif step[0] == "awaystep":   # the host-away rig: move the unit's fake time by ms (the notice, the label and the face follow), then a frame for the filmstrip
            import host_away
            away = u.host_away
            if away.since is None:
                away.language = "en"
                away.link_lost()
            u.jump(step[1])
            away.tick(u.now_ms)
            u.raw("advance 66")
            u.__dict__.setdefault("strip", []).append(u.snapshot_now())
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


# Scenarios that show a screen only a patch that is not in firmware/patches/ORDER yet can draw (the patch waits on the branch for its bench proof, plain boot first). They are dropped from every
# list below while the patch is out of ORDER, and their goldens live on the branch with the patch; when the patch joins ORDER, the scenarios and goldens come back with it.
import re as _re
_ORDER = set((ROOT / "firmware" / "patches" / "ORDER").read_text().split()) if (ROOT / "firmware" / "patches" / "ORDER").exists() else set()
REQUIRES = [
    (r"^(screen-page-timers-one|screen-page-timers-more|screen-alarms-app)$", "UX13f-timers-and-alarms-at-finger-size.patch"),
    (r"dicepoker", "UX18-dice-poker.patch"),
    (r"^game(-over)?-hilo", "UX21-higher-or-lower.patch"),
    (r"^game(-over)?-reversi", "UX22-reversi.patch"),
    (r"^game-battleship", "UX23-battleship-lite.patch"),
    (r"^game-over-look", "UX15d-game-over-look.patch"),
    (r"^game-pong", "UX24-pong.patch"),
    (r"^game-flyer", "UX25-flyer.patch"),
    (r"^game-c4-look", "UX26-four-in-a-row-richer-look-bench.patch"),
    (r"^game-balance", "UX27-balance.patch"),
    (r"^game-maze", "UX28-maze.patch"),
    (r"^first-run-4c", "UX19-brain-two-equal-routes.patch"),
    (r"^brain-removed", "UX20-hosted-link-removed-notice.patch"),
    (r"^game-over-(colormemory|whack|doit|snake|2048)-", "UX15c-game-over-neutral-end-after-sf82.patch"),
    (r"^mumble-", "UX16-offline-mumble-core.patch"),
    (r"^game-(riddle|joke|trivia|twenty)-|^game-over-(trivia|twenty)-", "UX17-question-and-answer-game-screens.patch"),
]


def _gate() -> None:
    for d in (SCENARIOS, SCREENS, LOCK_SCENARIOS, COVER_SCENARIOS, GRID_SCENARIOS, FILMSTRIPS):
        for name in list(d):
            if any(_re.search(rx, name) and patch not in _ORDER for rx, patch in REQUIRES):
                del d[name]


_gate()


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
    if not args and screens_built and not failed:   # every scenario matches its golden for this ORDER: stamp the goldens with it (scripts/golden-stamp.py checks it)
        (GOLDEN.parent / "golden-order.sha1").write_text(hashlib.sha1((ROOT / "firmware" / "patches" / "ORDER").read_bytes()).hexdigest() + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
