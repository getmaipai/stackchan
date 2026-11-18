#!/usr/bin/env python3
"""Cut the real cover-screen code (Wi-Fi connecting, Wi-Fi setup, waiting for Home to approve) out of the firmware tree's stackchan_display.cc
into three include files for cover_render.cc, so the host draws the unit's own code, not a copy. Fails loudly when the source moved.
Usage: cover_gen.py <firmware tree root> <out dir>   writes cover_helpers.inc, cover_ctor.inc, cover_funcs.inc
Placement: host-side development tool. Upstream: none."""
import sys
from pathlib import Path

tree, out = Path(sys.argv[1]), Path(sys.argv[2])
src = (tree / "firmware/main/hal/board/stackchan_display.cc").read_text()


def func(sig: str) -> str:
    """One function by brace matching, from its signature to its closing brace."""
    a = src.index(sig)
    depth, seen = 0, False
    for j in range(src.index("{", a), len(src)):
        depth += src[j] == "{"
        depth -= src[j] == "}"
        if depth == 0:
            return src[a : j + 1]
    raise ValueError(f"no end for {sig}")


try:
    helpers = src[src.index("struct LinkGlyph {") : src.index("// What the cover's glyph slot shows")]
    a = src.index("boot_cover_ = lv_obj_create(lv_screen_active());")
    end = 'lv_label_set_text(boot_label_, "Connecting to Wi-Fi...");'
    ctor = src[a : src.index(end, a) + len(end)]
    funcs = [func(f"void StackChanAvatarDisplay::{n}(") for n in ("SetCoverGlyph", "UpdateLinkTimer", "LinkTick", "ShowBootCover", "HideBootCover", "BootRingTick")]
    if "StackChanAvatarDisplay::ShowUpdateCover(" in src:  # patch UX04
        funcs.append(func("void StackChanAvatarDisplay::ShowUpdateCover("))
except ValueError as e:
    sys.exit(f"cover_gen: the cover code moved in stackchan_display.cc ({e}): update scripts/virtual-unit/cover_gen.py")
out.mkdir(parents=True, exist_ok=True)
(out / "cover_helpers.inc").write_text(helpers)
(out / "cover_ctor.inc").write_text(ctor)
(out / "cover_funcs.inc").write_text("\n\n".join(funcs) + "\n")
print(f"cover_gen: {len(helpers.splitlines())} helper lines, {len(ctor.splitlines())} constructor lines, {len(funcs)} functions")
