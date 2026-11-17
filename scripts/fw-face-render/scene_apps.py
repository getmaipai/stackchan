#!/usr/bin/env python3
"""Writes the renderer script for the Apps wall, the games wall, Timers, Alarms and Settings (patch UI16): usage scene_apps.py <out dir>.
Every screen the owner asked for is written as a PNG, and the finger steps are asserted from the 'state' lines in the renderer's log."""
import sys

out = sys.argv[1]
L = ["banner on", "games 8", "lockcode on", "clearall"]


def snap(name):
    L.append(f"snap {out}/{name}.png")


# the control sheet is drawn by the pages renderer (pages_render.sh); here the screens it opens
L += ["show apps"]; snap("apps_page1")
L += ["swipe 250 120 80 120 200"]; snap("apps_page2")
L += ["swipe 80 120 250 120 200"]; snap("apps_back_to_page1")
L += ["pictures on", "show apps"]; snap("apps_pictures_page1")
L += ["swipe 250 120 80 120 200"]; snap("apps_pictures_page2")
L += ["pictures off", "lang es", "show apps"]; snap("apps_es_page1"); L += ["lang en"]
# the games wall follows the games table: eight games, then seven (Reaction Time gone)
L += ["games 8", "show games"]; snap("games_page1")
L += ["swipe 250 120 80 120 200"]; snap("games_page2")
L += ["games 7", "show games", "swipe 250 120 80 120 200"]; snap("games7_page2")
L += ["games 8"]
# timers
L += ["clearall", "show timers"]; snap("timers_0")
L += ["timer 272 tea", "show timers"]; snap("timers_1")
L += ["timer 1500 laundry", "timer 3725 _", "show timers"]; snap("timers_3")
L += ["lang es", "show timers"]; snap("timers_3_es"); L += ["lang en"]
# alarms
L += ["clearall", "show alarms"]; snap("alarms_0")
L += ["alarm 7 30 wake_up", "show alarms"]; snap("alarms_1")
L += ["alarm 12 5 lunch", "alarm 21 0 _", "show alarms"]; snap("alarms_3")
L += ["tap 160 60", "state"]; snap("alarm_picker_12h")
L += ["clock 24", "show alarms", "tap 160 60"]; snap("alarm_picker_24h"); L += ["clock 12"]
L += ["lang es", "show alarms", "tap 160 60"]; snap("alarm_picker_es"); L += ["lang en"]
# settings
L += ["show settings"]; snap("settings_general")
L += ["scroll 90"]; snap("settings_general_scrolled")
L += ["scroll 600"]; snap("settings_general_end")
L += ["tab 1"]; snap("settings_network")
L += ["tab 2"]; snap("settings_faces")
L += ["pictures on", "show settings", "tab 2"]; snap("settings_faces_pictures"); L += ["pictures off"]
L += ["tab 3"]; snap("settings_info")
L += ["scroll 600"]; snap("settings_info_end")
L += ["lang es", "show settings"]; snap("settings_es_general"); L += ["scroll 600"]; snap("settings_es_general_end"); L += ["tab 1"]; snap("settings_es_network"); L += ["lang en"]
L += ["lockcode off", "show settings", "scroll 600"]; snap("settings_general_end_nocode"); L += ["lockcode on"]
print("\n".join(L))
