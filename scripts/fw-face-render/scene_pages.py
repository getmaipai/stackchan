#!/usr/bin/env python3
"""Writes the renderer scripts for the swipe pages and the control sheet (patches P10 to P12): every page and the sheet on the Big eyes
and the Stock style, a Spanish set, a night clock, and the gesture checks. Usage: scene_pages.py OUTDIR -> OUTDIR/scene_*.txt
run: render < scene_pages.txt (PNGs land next to the script's snap lines)"""
import sys
out = sys.argv[1]
STYLES = ["big_eyes", "stock"]
PAGES = ["clock", "timers", "games", "actions", "frame", "tiles"]
CFG_ALL = "L=clock,timers,games;R=actions,frame,tiles;S=6;I=20;A=find,beep,dance,game,hello;C=volume,brightness,mute,quiet,lock,find,timers,games,wifi,battery,tailnet,address"


def head(lines):
    lines += ["bcaps subtitles", "pcfg " + CFG_ALL, "pset hh 10", "pset mm 24", "pset ss 36"]


def tiles(lines):
    lines += ["ptiles_clear", "ptile sun Weather 72~F", "ptile home Garage Open", "ptile lamp Lights 3~on", "ptile temp Inside 68~F",
              "ptile bell Mail 1", "ptile heart Mom Home"]


with open(f"{out}/scene_pages.txt", "w") as f:
    L = []
    head(L)
    tiles(L)
    L += ["pset frames 3", "pset age 300", "ptimer 272 Tea", "ptimer 1500 Pasta~water"]
    for style in STYLES:
        L += [f"style {style}", "emotion neutral", "advance 600"]
        L += [f"snap {out}/{style}_face.png", f"pcount {style}_face"]
        for page in PAGES:
            L += [f"pshow {page}", "advance 400", f"snap {out}/{style}_page_{page}.png", f"pcount {style}_{page}"]
        L += ["pshow face", "advance 200", "pshow sheet", "advance 400", f"snap {out}/{style}_sheet.png", f"pcount {style}_sheet"]
        L += ["pshow face", "advance 200"]
    # the clock in ring style, at night, 24 hour
    L += ["style big_eyes", "pset ring on", "pshow clock", "advance 300", f"snap {out}/big_eyes_page_clock_ring.png", "pset ring off"]
    L += ["pset night on", "pshow clock", "advance 300", f"snap {out}/big_eyes_page_clock_night.png"]
    L += ["pshow tiles", "advance 300", f"snap {out}/big_eyes_page_tiles_night.png", "pshow face", "pset night off"]
    # Spanish
    L += ["pset es on", "pshow actions", "advance 300", f"snap {out}/big_eyes_page_actions_es.png", "pshow games", "advance 300", f"snap {out}/big_eyes_page_games_es.png",
          "pshow sheet", "advance 300", f"snap {out}/big_eyes_sheet_es.png", "pshow face", "pset es off"]
    # states: quiet and mute on the sheet and the actions page, stale tiles, no tiles, no timers, no pictures
    L += ["pset quiet on", "pset mute on", "pshow actions", "advance 300", f"snap {out}/big_eyes_page_actions_quiet.png", "pshow sheet", "advance 300", f"snap {out}/big_eyes_sheet_quiet.png", "pshow face", "pset quiet off", "pset mute off"]
    L += ["pset age 9000", "pshow tiles", "advance 300", f"snap {out}/big_eyes_page_tiles_stale.png", "pshow face", "ptiles_clear", "pshow tiles", "advance 300", f"snap {out}/big_eyes_page_tiles_none.png", "pshow face"]
    L += ["ptiles_clear", "ptile sun Weather 72~F", "ptile home Garage Open", "ptile lamp Lights 3~on", "pshow tiles", "advance 300", f"snap {out}/big_eyes_page_tiles_three.png"]
    L += ["ptiles_clear", "ptile temp Living~room 21.5~C", "pshow tiles", "advance 300", f"snap {out}/big_eyes_page_tiles_one.png", "pshow face"]
    L += ["ptiles_clear", "ptile cloud Forecast Cloudy~later", "ptile rain Tomorrow Rain", "ptile bell Doorbell Rang~5m~ago", "ptile check Backup OK", "ptile sun Sunrise 6:48~AM", "ptile home Home Alarm~armed", "pshow tiles", "advance 300", f"snap {out}/big_eyes_page_tiles_long.png", "pshow face"]
    L += ["pset frames 0", "pshow frame", "advance 300", f"snap {out}/big_eyes_page_frame_none.png", "pshow face"]
    L += ["pshow timers", "pset hh 10", "advance 300", f"snap {out}/big_eyes_page_timers_two.png"]
    f.write("\n".join(L) + "\nsheet {0}/pages_sheet_all.png 4 2\n".format(out))

# ---- the gesture run: swipes through the real state machine and the real page code; the lines the renderer prints are the evidence ----
with open(f"{out}/scene_gestures.txt", "w") as f:
    L = ["bcaps subtitles", "pcfg L=clock;R=games,actions;S=6;I=20;A=find,beep,dance,game;C=volume,brightness,mute,quiet,lock,find,timers,games,wifi,battery", "style big_eyes", "advance 300"]
    L += ["# right: the page left of the face (clock); left from the face: games, then actions, then a bump"]
    L += ["pswipe 100 100 220 100 200", "advance 300", f"snap {out}/g_clock.png", "pswipe 220 100 100 100 200", "pswipe 220 100 100 100 200", "advance 300", f"snap {out}/g_games.png",
          "pswipe 220 100 100 100 200", "pswipe 220 100 100 100 200", "# an edge swipe is the volume, never a page", "pswipe 4 100 120 100 200", "pswipe 316 100 200 100 200",
          "# swipe down on a page: back to the face and stop", "pswipe 160 40 160 150 250", "# swipe up from the bottom band: the sheet", "pswipe 160 225 160 120 250", "advance 300", f"snap {out}/g_sheet.png",
          "# a tap on Mute (72 by 38 at the sheet row) is not a swipe; the sheet closes after 6 s by itself", "advance 5800", "pstate", "advance 400", "pstate",
          "# a page returns to the face after 20 s", "pshow clock", "advance 19500", "pstate", "advance 800", "pstate",
          "# the wake word, speech and a head tap each bring the face back", "pshow games", "pevent wake", "advance 300", "pstate", "pshow games", "pevent speech", "advance 300", "pstate", "pshow games", "pevent head", "advance 300", "pstate",
          "# the sheet over a page returns to the page", "pswipe 220 100 100 100 200", "pswipe 160 230 160 120 250", "pswipe 160 150 160 232 250", "pstate",
          "# a slow drag is no swipe", "pswipe 100 100 220 100 1500", "pstate"]
    f.write("\n".join(L) + "\n")

# ---- patch NX03: the games page is up, the sheet opens over it, a tap on Apps (and then Games and the gear): only that screen is on the glass ----
with open(f"{out}/scene_overlap.txt", "w") as f:
    DEFAULT = "pcfg L=clock;R=games;S=10;I=20;A=beep,dance,game,hello;C=volume,brightness,mute,quiet,lock,timers,games,wifi,battery"
    L = ["bcaps subtitles", DEFAULT, "style big_eyes", "advance 300", "pset hh 10", "pset mm 24"]
    L += ["pshow games", "advance 400", f"snap {out}/o_games_page.png", "pshow sheet", "advance 300", f"snap {out}/o_sheet_over_games_page.png", "pstate"]
    L += ["# the Apps tile (the fourth tile of the one row of six, at x 163 to 207)", "pclick 185 212", "advance 400", f"snap {out}/o_apps_only.png", "pstate"]
    L += ["# back to the face, then the same with Games and with the gear", "pshow face", "advance 300", "pshow games", "advance 300", "pshow sheet", "advance 300", "pclick 235 212", "advance 400", f"snap {out}/o_games_wall_only.png", "pstate"]
    L += ["pshow face", "advance 300", "pshow games", "advance 300", "pshow sheet", "advance 300", "pclick 285 212", "advance 400", f"snap {out}/o_settings_only.png", "pstate"]
    f.write("\n".join(L) + "\n")

# ---- the draw cost: run it with PERF=1 (dirty-area flushing, as on the unit); `perf` lines give pixels flushed per frame ----
with open(f"{out}/scene_perf.txt", "w") as f:
    L = ["bcaps subtitles", "pcfg L=clock,timers,games;R=actions,frame,tiles;S=6;I=300;A=find,beep,dance,game,hello;C=volume,brightness,mute,quiet,lock,find,timers,games,wifi,battery", "style big_eyes",
         "ptile sun Weather 72~F", "ptile home Garage Open", "pset frames 3", "ptimer 600 Tea", "advance 800", "perfbegin", "advance 3000", "perfend face_3s"]
    for page in PAGES + ["sheet"]:
        L += [f"pshow {page}", "advance 500", "perfbegin", "advance 3000", f"perfend {page}_3s"]
    L += ["pshow face", "advance 800", "perfbegin", "advance 3000", "perfend face_again_3s"]
    f.write("\n".join(L) + "\n")
