#!/usr/bin/env python3
"""Renderer scripts for the overlay pass (patch O01): every overlay and every named combination, drawn by the unit's own overlay
core over the real face. Usage: scene_overlays.py OUTDIR, then run render (overlays_render.sh does both).
Per overlay NAME the sheets land in OUTDIR:
  NAME.png          six moments on Big eyes, full size (320 by 240 each)
  NAME_phone.png    the five styles, each tile 300 px wide: what a phone photo of the unit shows
  NAME_zones.png    banner showing, subtitles showing, both: the text zones stay clean (phone size)
The scripts are split in one file per group so a run stays short: scene_a_elements.txt, scene_b_presets.txt."""
import sys

out = sys.argv[1]
STYLES = ["big_eyes", "eyes_only", "stock", "classic", "minimal"]
ELEMENTS = ["rain", "snow", "sun", "clouds", "wind", "thunder", "fog", "stars", "disco", "leaves", "confetti", "fireworks", "hearts", "steam", "balloons", "zzz", "moon", "sparkles"]
PRESETS = ["stormy", "rainy", "snowy", "sunny", "windy", "night", "party", "celebrate", "love", "sleeping"]
# Moments (ms after the start) of the six pictures; fireworks and thunder need their own.
TIMES = {"fireworks": [1900, 2300, 2700, 3100, 3500, 3900], "celebrate": [2300, 2700, 3100, 3500, 3900, 4300], "thunder": [1500, 2600, 3700, 4800, 5900, 7000]}
PHONE_AT = {"fireworks": 2900, "celebrate": 3100, "thunder": 4800, "stormy": 4800}
SUB = "Good morning! Today it will be sunny, so it is a good day to play outside."
BANNER = "bpost privacy remote cue 0 Remote: finding me"


def times(name):
    return TIMES.get(name, [1800, 3600, 5400, 7200, 9000, 10800])


def group(names, fname):
    L = []
    for name in names:
        inten = 3 if name in ("clouds", "stormy") else 2
        emo = "neutral"
        # six moments on Big eyes
        L += ["style big_eyes", f"emotion {emo}", "advance 600", f"overlay {name} {inten} 0"]
        last = 0
        if name in ("fireworks", "celebrate"):
            for age in (4, 10, 16, 22, 28, 36):
                L += [f"ovspark {age}", "tilenow"]
        else:
            for t in times(name):
                L += [f"advance {t - last}", "tile"]
                last = t
        if name in ("thunder", "stormy"):
            L += ["ovflash", "tilenow", "advance 33", "tilenow"]
        L += ["ovclear", "advance 700", f"sheet {out}/{name}.png 3 1"]
        # the five styles at phone size
        for st in STYLES:
            L += [f"style {st}", f"emotion {emo}", "advance 500", f"overlay {name} {inten} 0"]
            if name in ("fireworks", "celebrate"):
                L += ["ovspark 14"]
            else:
                L += [f"advance {PHONE_AT.get(name, 4200)}"]
            if name in ("thunder", "stormy"):
                L += ["ovflash"]
            L += ["ptilenow", "ovclear", "advance 400"]
        L += [f"psheet {out}/{name}_phone.png 3"]
        # the text zones
        L += ["style big_eyes", "emotion neutral", "advance 500", f"overlay {name} {inten} 0"]
        L += ["ovspark 12"] if name in ("fireworks", "celebrate") else [f"advance {PHONE_AT.get(name, 4200)}"]
        if name in ("thunder", "stormy"):
            L += ["ovflash"]
        L += [BANNER, "advance 500", "ptile", "bclear cue", f"ssay {SUB}", "advance 700", "ptile", BANNER, "advance 500", "ptile", "bclear cue", "sstop", "ovclear", "advance 2400", f"psheet {out}/{name}_zones.png 3"]
    open(f"{out}/{fname}", "w").write("\n".join(L) + "\n")


group(ELEMENTS, "scene_a_elements.txt")
group(PRESETS, "scene_b_presets.txt")
# the sleeping look as the unit runs it: the sleepy emotion starts the z letters by itself; every style, phone size
Z = []
for st in STYLES:
    Z += [f"style {st}", "emotion neutral", "advance 500", "emotion sleeping", "overlay zzz 2 0", "advance 4600", "ptile", "ovclear", "emotion neutral", "advance 400"]
Z += [f"psheet {out}/zzz_sleeping_phone.png 3"]
open(f"{out}/scene_c_sleeping.txt", "w").write("\n".join(Z) + "\n")
