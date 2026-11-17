#!/usr/bin/env python3
"""Writes a renderer script for the banner row and the subtitle strip (patches N01, N04): every state on every style, one sheet per
state, then a zone check over every style and emotion. Usage: scene_banner.py OUTDIR -> OUTDIR/banner_scene.txt
run: render < banner_scene.txt (sheets land in OUTDIR/<state>.png; the zone check prints `zone ...` lines)"""
import sys
out = sys.argv[1]
STYLES = ["big_eyes", "eyes_only", "stock", "classic", "minimal"]
LONG = "Remote message: please come to the kitchen when you hear this, dinner is ready and the table is set"
SUB1 = "Good morning!"
SUB2 = "Good morning! What would you like to do today? I can tell you the weather."
SUB3 = "Good morning! Today it will be sunny with a light wind, so it is a good day to open the windows and play outside, and I can read you a story if you like."
ES = "¡Buenos días! ¿Qué te gustaría hacer hoy? Puedo contarte el tiempo."
CLEAN = ["bclear game", "bclear find", "bclear cue", "bclear volume", "bclear link", "bclear say", "bclear caption", "sstop"]
STATES = [  # name, setup commands, ms to run before the picture, teardown commands
    ("none", [], 900, []),
    ("session_chip", ["bsession on remote"], 900, ["bsession off"]),
    ("session_chip_label", ["bsession on Settings page"], 900, ["bsession off"]),
    ("session_heartbeats", ["bsession on Settings page", "advance 300", "bsession on Settings page", "advance 300", "bsession on Settings page"], 600, ["bsession off"]),
    ("session_chip_long_label", ["bsession on Kitchen tablet in the hall"], 900, ["bsession off"]),
    ("cue_short", ["bpost privacy remote cue 6000 Remote: photo in 3"], 700, []),
    ("session_then_cue", ["bsession on remote", "bpost privacy remote cue 6000 Remote: moving"], 700, ["bsession off"]),
    ("say_long_start", [f"bpost privacy remote say 0 {LONG}"], 700, []),
    ("say_long_mid", [f"bpost privacy remote say 0 {LONG}"], 4200, []),
    ("say_ask_first", ["bpost privacy remote say 0 Tap to allow, or say stop: Dinner is ready"], 700, []),
    ("find_here_i_am", ["bpost notice ring find 6000 Here I am!"], 700, []),
    ("game_best", ["bpost notice check game 6000 New best! 120"], 700, []),
    ("link_offline", ["bpost notice wifioff link 0 Offline", "bstatus 80 0 1 0 0"], 700, ["bstatus 80 0 1 1 0"]),
    ("link_connecting", ["bpost notice bars link 0 Connecting..."], 700, []),
    ("notice_volume", ["bpost notice none volume 6000 Volume 40"], 700, []),
    ("low_battery_text", ["bpost notice battery game 6000 Battery low: 15 percent", "bstatus 15 0 1 1 0"], 700, ["bstatus 80 0 1 1 0"]),
    ("strip_privacy", ["bstatus 80 0 1 1 1", "bflag camera on", "bsession on remote"], 2600, ["bstatus 80 0 1 1 0", "bflag camera off", "bsession off"]),
    ("strip_low_battery_wifi", ["bstatus 12 0 0 0 0"], 2600, ["bstatus 80 0 1 1 0"]),
    ("strip_top_bar_always", ["bbar always", "bstatus 64 0 1 1 0"], 2600, ["bbar hidden", "bstatus 80 0 1 1 0"]),
    ("subtitles_one_line", [f"ssay {SUB1}"], 500, []),
    ("subtitles_two_lines", [f"ssay {SUB2}"], 500, []),
    ("subtitles_long_page1", [f"ssay {SUB3}"], 500, []),
    ("subtitles_long_page2", [f"ssay {SUB3}"], 3800, []),
    ("subtitles_accents", [f"ssay {ES}"], 500, []),
    ("subtitles_while_speaking", [f"ssay {SUB2}", "speak 90"], 500, ["speak 0"]),
    ("both_chip_and_subtitles", ["bsession on Settings page", f"ssay {SUB2}"], 700, ["bsession off"]),
    ("both_say_marquee_and_subtitles", [f"bpost privacy remote say 0 {LONG}", f"ssay {SUB2}"], 1500, []),
    ("both_everything", ["bsession on remote", "bstatus 12 0 0 0 1", "bflag camera on", f"bpost privacy remote say 0 {LONG}", f"ssay {SUB2}", "speak 90"], 2600, ["bstatus 80 0 1 1 0", "bflag camera off", "bsession off", "speak 0"]),
    ("both_surprised_speaking", ["emotion surprised", "bsession on remote", f"ssay {SUB2}", "speak 100"], 700, ["bsession off", "speak 0", "emotion neutral"]),
    ("both_angry", ["emotion angry", "bsession on remote", f"ssay {SUB2}"], 900, ["bsession off", "emotion neutral"]),
    ("both_thinking", ["emotion doubt", "think on", "bsession on remote", f"ssay {SUB1}"], 900, ["bsession off", "think off", "emotion neutral"]),
    ("both_tired", ["emotion tired", "bsession on remote", f"ssay {SUB2}"], 3600, ["bsession off", "emotion neutral"]),
    ("both_happy_speaking", ["emotion happy", "bsession on remote", f"ssay {SUB2}", "speak 100"], 700, ["bsession off", "speak 0", "emotion neutral"]),
    ("captions_banner_mode", ["bcaps banner", f"bubble {SUB2}"], 700, ["bubble off", "bcaps subtitles"]),
    ("captions_off", ["bcaps off", f"bubble {SUB2}"], 700, ["bcaps subtitles"]),
]
L = []
for name, setup, ms, down in STATES:
    for st in STYLES:
        L += [f"style {st}", "emotion neutral", "advance 400"]
        L += setup
        L += [f"advance {ms}", "tile"]
        L += down + CLEAN
        L += ["advance 2600"]
    L += [f"sheet {out}/{name}.png 3 1"]
# The zone check: with no banner and no subtitles every style, every emotion, the voice open and shut, thinking on and off must
# light nothing in the banner zone (y 0 to 28) or the subtitle zone (y 184 to 240). `zone STYLE EMOTION speak think top bottom`.
EMO = ["neutral", "happy", "angry", "sad", "doubt", "sleepy", "surprised", "tired", "closing", "sleeping", "love", "content"]
for st in STYLES:
    for e in EMO:
        for speak in (0, 100):
            for think in (0, 1):
                L += [f"style {st}", f"emotion {e}", f"speak {speak}", f"think {'on' if think else 'off'}", "advance 900", f"zonecheck {st} {e} {speak} {think}"]
L += ["speak 0", "think off"]
open(f"{out}/banner_scene.txt", "w").write("\n".join(L) + "\n")
