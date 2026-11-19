# The data-pack games drawn by one draw callback (patch UX29)

Playground track, 2026-11-19. The seven packs (Tic-Tac-Toe, Whack, Do It, 8 Ball, Dice and Coin, Color Memory, Rock Paper Scissors) used one LVGL object for every shape. They now use three objects on every screen, and the pixels are the same. This is the engine change that `docs/plan/games-packs-look.md` named as step 1 of a richer look. Nothing was flashed: the patch waits on the branch `ux/unproven-games` for a bench pass.

## What changed

- **Display only.** The pack format, the seven `.mpk` files, every counter, rule and sound are unchanged. The patch touches `maipai_games_draw.h` and two lines of `maipai_games.cc` (the type of the shape array, and one call to `mgd::begin`).
- **A shape is a node, not an object.** `begin()` takes one block for the whole game: a small record per shape (and per part of the mole, a die, the coin and an icon) plus room for the texts. One canvas object paints the nodes in one draw callback, in the order they were made, each clipped to its parent the way LVGL clips a child. Deleting the game's root frees the block.
- **The old calls keep their shape.** The functions named `vo_size`, `vo_pos`, `vo_flag_on` and the like take the arguments the LVGL calls took, so `mole_apply`, `icon_show`, `animate` and the rest read as before. Each one that changes something marks its node first.
- **A change flushes what moved.** `commit()` runs at the end of `draw_state` and `animate` and invalidates the old and the new area of each marked node. A still screen costs nothing. The old engine invalidated a whole label on every state update and the whole 320 by 240 mole holder whenever the mole appeared or left.

## Measured

| Pack | LVGL objects before | after | Nodes | Block on the unit, about | Before, about | Saved, about |
|---|---|---|---|---|---|---|
| Tic-Tac-Toe | 46 | 3 | 45 | 3.5 KB | 5.9 KB | 2.1 KB |
| Whack | 64 | 3 | 63 | 5.0 KB | 8.6 KB | 3.3 KB |
| Do It | 44 | 3 | 43 | 3.8 KB | 6.3 KB | 2.1 KB |
| 8 Ball | 47 | 3 | 46 | 4.6 KB | 7.4 KB | 2.5 KB |
| Dice and Coin | 49 | 3 | 48 | 3.7 KB | 6.3 KB | 2.2 KB |
| Color Memory | 15 | 3 | 14 | 1.2 KB | 2.0 KB | 0.5 KB |
| Rock Paper Scissors | 87 | 3 | 86 | 7.1 KB | 11.7 KB | 4.3 KB |

The three objects are the game's root, the canvas and the drag bar. "Before" uses the sheet's rule of thumb (110 bytes a plain object, 200 a label, `games_pack_sheet.py --counts`); "after" is `32 + 64 * nodes + text room` for the block (a node is 64 bytes on the unit's 32-bit core, 80 on the host) plus the three objects. The saving is an estimate until the bench measures free internal RAM before and during a game (`docs/dev/measure-a-game.md`).

The text room is 64 bytes for each text shape, so it is the largest part for the packs with many texts (8 Ball keeps 25 answers, 1.6 KB). A tighter room per text, taken from the longest text the pack can make, is a follow-up if the bench shows the need.

## Proof

- **Same pixels.** `scripts/virtual-unit/packs_pixel_proof.py OLD NEW` runs two builds of the pack renderer through the same scenes: every state of every pack in both languages at three moments of the motion, then random counters and board cells at ten moments. 3118 frames (seed 5) and 2418 frames (seed 11 and 21): 0 differing pixels. The old drawing's hashes for a fixed set of 493 frames are kept in `host/tests/golden/pack_games_digests.json`, and `host/tests/test_pack_engine_one_draw.py` fails on any frame that no longer matches.
- **The invalidation covers every change.** `PARTIAL=1` makes the renderer refresh only what the player invalidated, keeping the frame as the panel does. 1718 frames drawn that way equal the same frames drawn in full: 0 differing pixels. With `commit()` switched off the same run differs in 364 of 388 frames, so the test can fail.
- **Objects.** 3 on every state of every pack (`objcount`), checked by the same test file.

## One thing kept on purpose

The coin's flip positions the coin with `lv_obj_get_width`, which returns the width of the last layout, not the one just set. So the first tick after a face change has always placed the coin by the width of the face before. The new drawing keeps that exactly (`vo_width` returns the width at the last draw), which is why the pixels match. A one-line change in `vo_width` (return the new width) would center the coin on that first tick and change those frames. It was not made, because this patch is display-only and pixel-identical; it is a candidate for the look step.

## What is not done

- Not flashed and not benched: free internal RAM and tick gaps while a pack game runs, and the free internal after closing one (the block must be given back).
- The packs' richer look (`docs/plan/games-packs-look.md`) starts only after this patch is measured on the unit.
