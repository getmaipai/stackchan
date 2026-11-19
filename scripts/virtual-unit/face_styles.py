"""The face styles, colors, backgrounds and moods the contact sheets and the budget table use: one list, here.
Colors and the background rule are the unit's own (maipai_face_core.h: MF_PALETTE_RGB, and a palette background is the color at 26 percent of its brightness).
Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

# Base styles are rows of the image; recipe styles are 44-byte assets (scripts/face-recipe.py) the renderer loads with its `recipe` command.
BASE_STYLES = ["big_eyes", "stock", "minimal"]          # in the firmware image (owner decision 22)
RECIPE_STYLES = ["classic", "eyes_only", "round", "cat", "robot", "sleepy", "retro_pixel", "heart_eyes", "hose", "neon", "cartoon"]   # installable: firmware/styles/NAME.rcp, drawn after patch UXF01
STYLES = BASE_STYLES + RECIPE_STYLES
MOODS = ["neutral", "happy", "sad", "angry", "doubt", "surprised", "sleepy", "tired", "closing", "sleeping", "love", "content", "joy", "excited", "shocked", "curious", "worried", "thinking"]   # joy to worried: patch UXF02
PALETTE = {"mint": (0x7F, 0xE0, 0xB8), "sky": (0x7F, 0xC4, 0xF0), "amber": (0xF2, 0xB2, 0x4A), "rose": (0xF0, 0x8F, 0xB0), "lilac": (0xB8, 0x9C, 0xF0), "lime": (0xB4, 0xE0, 0x5A), "coral": (0xF2, 0x84, 0x6C)}
BG_PCT = 26
# Four face colors (white is the default "none") and four backgrounds (none is black).
COLORS = {"white": (255, 255, 255), "mint": PALETTE["mint"], "amber": PALETTE["amber"], "rose": PALETTE["rose"]}
BACKGROUNDS = ["none", "sky", "lilac", "navy"]   # navy: a dark #0f1b3d, a plain dark custom color (the Cartoon style's own look)


def bg_rgb(name: str) -> tuple[int, int, int]:
    if name == "none":
        return (0, 0, 0)
    if name == "navy":
        return (15, 27, 61)
    r, g, b = PALETTE[name]
    return (r * BG_PCT // 100, g * BG_PCT // 100, b * BG_PCT // 100)
