# The installed set in the virtual unit

Owner decision 17. The virtual unit fakes what `docs/plan/installed-set.md` (B1 to B5, E3) asks of the unit, so the host's reconciler and the dashboard can be tested against it. Nothing here ran on a unit.

- **One table.** `schema/asset-kinds.json` (kinds, slots, caps, trust, the pool of 382 sectors of 4,096 bytes). The playground track seeded it from the plan's section C; the firmware track owns the numbers.
- **The store** (`scripts/virtual-unit/assets_sim.py`, `u.assets`): the 128 byte header (B4) with an Ed25519 signature made by a test key built at run time (no key is stored), install in 2,048 byte pieces that must arrive in order, a commit that checks length and SHA-256 and writes the directory in one step, swap, remove, abort, and a power cut injected after N pieces (an install in flight is lost, what was committed stays).
- **Refusals** carry `code`, `error` and `error_es` (codes and texts are assumed until the unit's core writes them): unknown kind, bad header, bad signature, wrong board, wrong kind, too big, older version, slots full, slot busy, pool full, damaged item, bad offset, power cut.
- **Tools:** `self.assets.list|install|data|commit|remove|swap|abort` register themselves the moment `schema/tools.json` lists them (so the parity check keeps holding); until then `sim.assets {tool: ...}` reaches the same handlers.
- **Memory:** the active item of a kind is loaded through the memory model (`asset.<kind>`, internal RAM none, PSRAM from the item's own header); swap and remove free it.
- **State panel:** `u.assets.slots()` gives slots used out of available per kind, the active item, the free pool bytes and what is loaded (request for the viewer in `docs/plan/view-requests.md`).
- **Scenario:** `host/tests/test_virtual_unit_assets.py` installs three faces of a catalog of twenty, takes a turn with each, swaps one, removes one, removes the rest and asserts the memory model is back at its baseline and the pool is empty.
- **Thumbnails:** `scripts/virtual-unit/thumbnails.py` draws every face style, every overlay and combination, and the first-run language step in six languages with the real renderer (160x120 PNG) and writes `manifest.json` (name, kind, file, size, sha-256, the tree that drew it). The dashboard's catalog uses them.
