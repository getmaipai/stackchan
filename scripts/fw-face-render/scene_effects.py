#!/usr/bin/env python3
"""Renderer scripts for render_fx: every overlay, every screen effect, the speech bubble. Usage: scene_effects.py OUTDIR,
then render < OUTDIR/scene_a.txt and render < OUTDIR/scene_bubble.txt (sheets land in OUTDIR)."""
import sys
out = sys.argv[1]
def sheet(name, lines, cols=3, div=1):
    return lines + [f"sheet {out}/{name}.png {cols} {div}"]
base = ["style big_eyes", "emotion neutral", "advance 1500"]
L = []
# weather overlays: two times each (steady state), at normal intensity
for ov, inten in [("rain", 2), ("snow", 2), ("sun", 2), ("clouds", 3), ("wind", 2), ("fog", 2), ("stars", 2), ("leaves", 2), ("disco", 2)]:
    L += base + [f"overlay {ov} {inten} 0", "advance 2200", "tile", "advance 400", "tile", "ovclear", "advance 100"]
L += base + ["overlay thunder 3 0", "ovflash", "tilenow", "advance 33", "tilenow", "advance 33", "tilenow", "ovclear", "advance 100"]
L = sheet("weather", L, 3, 1)
M = []
for ov, inten in [("confetti", 2), ("fireworks", 2), ("hearts", 2), ("steam", 2), ("balloons", 2)]:
    M += base + [f"overlay {ov} {inten} 0", "advance 2600", "tile", "advance 900", "tile", "ovclear", "advance 100"]
M = sheet("events", M, 3, 1)
# zzz on a sleeping face: frames over time
Z = ["style big_eyes", "emotion neutral", "advance 800", "emotion sleeping", "overlay zzz 2 0"]
for _ in range(9):
    Z += ["advance 1000", "tile"]
Z += ["ovclear"]
Z = sheet("zzz_big_eyes", Z, 3, 1)
Z2 = []
for st in ["stock", "minimal", "eyes_only", "classic"]:
    Z2 += [f"style {st}", "emotion sleeping", "overlay zzz 2 0", "advance 6000", "tile", "ovclear"]
Z2 = sheet("zzz_styles", Z2, 2, 1)
# effects
E = base[:]
E += ["tile"]
for fx in ["crt on"]:
    E += [f"fx {fx}", "advance 100", "tile", "fx crt off"]
for m in ["mono", "warm", "cool", "duotone", "amber", "green"]:
    E += [f"fx mode {m}", "advance 100", "tile"]
E += ["fx mode normal", "fx night on", "advance 100", "tile", "fx night off", "fx glow on", "advance 100", "tile", "fx glow off"]
E += ["fx crt on", "fx glow on", "fx mode amber", "advance 100", "tile", "fx night on", "advance 100", "tile", "fx crt off", "fx glow off", "fx mode normal", "fx night off"]
E = sheet("effects", E, 4, 1)
# effects with a mouth and speaking
F = ["style big_eyes", "emotion happy", "advance 1500", "speak 60", "advance 300", "fx crt on", "fx glow on", "tile", "fx mode green", "tile", "fx mode normal", "overlay rain 2 0", "advance 1500", "tile",
     "speak 0", "ovclear", "fx crt off", "fx glow off"]
F = sheet("effects_speaking", F, 3, 1)
open(f"{out}/scene_a.txt", "w").write("\n".join(L + M + Z + Z2 + E + F) + "\n")

# the speech bubble
B = []
B += ["style big_eyes", "emotion neutral", "advance 800", "speak 55", "bubble Hello! It is going to be a warm day today.", "advance 200", "tile",
      "bubble It looks like rain after lunch, so I would take an umbrella if you head out this afternoon and the wind picks up a little.", "advance 200", "tile",
      "advance 3200", "tile", "speak 0", "advance 2800", "tile", "advance 300", "tile", "advance 600", "tile"]
B += ["style stock", "emotion happy", "advance 600", "bubble Good morning", "advance 200", "tile", "bubble off", "advance 100"]
B += ["style classic", "emotion neutral", "advance 600", "bubble The weather is nice and warm today, around twenty four degrees.", "advance 200", "tile",
      "fx crt on", "fx mode amber", "advance 100", "tile", "fx crt off", "fx mode normal", "bubble off"]
B += ["style minimal", "emotion sad", "advance 600", "bubble I am sorry, I could not find that one.", "advance 200", "tile", "bubble off", "style big_eyes", "emotion neutral", "advance 300"]
B = sheet("bubble", B, 3, 1)
open(f"{out}/scene_bubble.txt", "w").write("\n".join(B) + "\n")
