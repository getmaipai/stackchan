# Face parts and the asset bank (plan)

Status: plan, nothing built. Placement: playground track (the builder and the previews), firmware track (the part drawing), catalog and host (the bank). It extends the installed set (`docs/plan/installed-set.md`, owner decision 17); it adds no new storage, no new loader and no new trust level.

**Bottom line.** A face style today is about 30 bytes of integers (eye size, spacing, mouth kind, brows, drift) over shapes the face code already draws. Face parts make the shapes themselves choosable: a small set of eye, mouth, brow and cheek parts that ship in the image, a recipe (a face style asset) that picks one of each and tunes numbers, and a bank where more parts and recipes are published as signed, tiny assets. The unit stays cheap (a recipe is under 1 KB, parts are shape lists of a few dozen bytes, nothing is held when not in use) and every face is previewed by the unit's own drawing code before anyone installs it.

## 1. What exists, and the gap

- Five face styles are a const table, about 30 bytes each; styles are the `style` kind of `schema/asset-kinds.json` (8 slots, 256 bytes an item, signed).
- Picture faces (`look`, up to 1 MB, one slot) are photos made on the owner's side; they are not parts.
- Overlays (weather, confetti, hearts) are drawn by code and cost PSRAM only while running.
- The gap: you can tune a style's numbers but you cannot give the robot different eyes, a different mouth, or a hat. Asking for a new look means a firmware change.

## 2. The part model

A part is a short list of shapes in a 100 by 100 box, drawn by the face code's existing primitives (disc, rounded box, ring, line, arc), each with a color index (the face color, the mouth color, the highlight, the cheek, black). A shape is 8 bytes: kind, x, y, w, h, radius or width, color index, flags. A part holds at most 16 shapes (128 bytes) and at most 4 poses.

| Slot in a face | Examples | Poses (what moves) |
|---|---|---|
| Eyes (left, right mirrored) | round, big with a highlight, sleepy lid, heart, star, wink, tired | open, half, closed, look direction |
| Mouth | small, smile, flat, open oval, o, tongue | closed, speaking levels 0 to 4 (the mouth follows the voice) |
| Brows | none, soft, angled, worried | neutral, raised, lowered |
| Cheeks | none, blush, freckles | on, off |
| Extras | glasses, hat, bow, antenna | a fixed overlay over the face |

The face code already moves eyes, mouth and gaze with emotion, speech and a look direction; a part only supplies the shapes for the poses it names. A part with a missing pose falls back to the nearest one it has, never to a blank, so a half-made part cannot show an empty face.

## 3. The recipe

A recipe is a `style` asset: a version, a name, one part id for each slot, the numbers the styles already have, and up to four custom parts embedded in the recipe itself (so a recipe is complete on its own and needs nothing from the bank at run time).

| Field | Size |
|---|---|
| Header: version, flags, name (12 characters) | 16 bytes |
| Style numbers (eye size, spacing, drift, colors) | 24 bytes |
| One part id per slot (built-in id, or an index into the embedded parts) | 8 bytes |
| Up to four embedded parts at 8 + 128 bytes | at most 544 bytes |

At most 592 bytes, under a 1 KB cap (the `style` kind's 256 byte cap rises to 1,024; eight slots cost 8 KB of flash at most). No PSRAM is held beyond the active recipe's shapes (under 1 KB) and the internal cost is zero, as for a style today.

## 4. The bank

The bank is the public signed catalog (`getmaipai/catalog`): an entry per part or recipe with its asset file, a manifest and a thumbnail.

- **Manifest** (`part.json` or `recipe.json`): id, kind, title, slot, license (CC0-1.0 or CC-BY-4.0), author, source (original work, with the date), the asset's SHA-256 and the signing key id, the sizes, the languages of its name, and the memory cost row.
- **Thumbnails** are drawn by the virtual unit's renderer (`scripts/virtual-unit/thumbnails.py` already does it for every style): the same pixels the robot will show, in the six languages' first-run frames where they matter. A thumbnail that does not match a fresh render fails the catalog check.
- **Trust:** parts and recipes from the catalog are signed by the catalog key (`signed`). A recipe someone made at home is `owner` trust: it installs only on that owner's units, shows a plain "made at home" label, and cannot carry anything but shapes and numbers (the signature check and the slot limits are the same code).
- **Rules for entries:** original shapes only; no maker mark, logo, character or look-alike of another product's face; no text in a shape; every part passes the memory gate, the hygiene check and a render of every pose; a name is plain words (the dad test).

## 5. The playground part

- **A builder page** in the playground: pick a part for each slot, move the sliders, and see the face drawn by the unit's own face code in every emotion and while speaking (the renderer gains a `recipe` command that loads a recipe text). It writes a recipe file and the thumbnail, and shows the memory row and the byte count.
- **Preview before install:** the dashboard shows the same render of any recipe in the bank before the person installs it; install goes through the existing asset install flow (the virtual unit already refuses a bad signature, a full slot, a too big item).
- **Goldens:** one frame per built-in part per pose, in `host/tests/golden/`, and the audit for any text or touch target a part brings (none are expected).

## 6. Phases

1. **Parts in the image, no bank** (firmware): the part drawing for eyes and mouth, five parts each, the recipe reader; the five existing styles become recipes. Proof: every existing golden unchanged.
2. **Recipes as assets** (firmware, playground): install, swap and remove a recipe through the asset slots; the builder page; the renderer `recipe` command.
3. **Brows, cheeks, extras** and the memory row for each.
4. **The bank** (catalog, host): the entries, the thumbnails and the dashboard preview; the first ten recipes, all original.
5. **Owner-made recipes** only after the signing and trust rules for `owner` assets are proven on a unit.

## 7. Costs and risks

- **Flash:** the built-in parts are about 40 shapes a slot at 8 bytes: roughly 3 KB for twenty parts. A recipe is under 1 KB; eight slots are 8 KB. Both fit the 407,000 bytes the installed set leaves before the 80 percent rule.
- **Memory:** nothing is allocated unless a recipe other than a built-in one is active; then the recipe's shapes (under 1 KB) sit in PSRAM. The gate (internal free median 40,000, lowest 24,000) is not touched.
- **Drawing time:** a shape is one LVGL object or one draw call; a face today draws a handful of objects, so 16 shapes an eye must be judged on the frame cost table (`scripts/virtual-unit/frame_cost.py`) before phase 2 ships. The limit of 16 shapes is the guess to test.
- **Look-alikes:** a bank of faces is where a copy of someone's character would creep in. The rule in section 4 and a human read of each entry are the guard.
- **Safety:** none of this touches the lock, the child gate, the limiter or the privacy sign. A part cannot hide the mute or the camera sign (those are drawn on the banner row, above the face).

## 8. Questions for the owner (answered 2026-11-18, decisions 28 to 30)

1. **Faces made at home:** the bank first; home-made faces only after phase 5, once the signing and trust rules are proven on a unit (decision 28).
2. **Personas:** a persona picks a default face recipe; the unit can still override it (decision 29).
3. **Shapes a part:** 16 (decision 30).
