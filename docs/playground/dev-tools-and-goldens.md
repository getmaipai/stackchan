# Tools, scenarios and goldens

**Add a tool.** Add the handler in `scripts/virtual-unit/tools/<group>.py` with `@tool("self.x.y")`. A tool the firmware does not list fails the parity check (`host/tests/test_virtual_unit_parity.py`), so the name must be in `schema/tools.json`. Controls that are only for the rig are named `sim.*`.

**Add a scenario.** Add steps to `SCREENS` in `scenarios.py` (`call`, `raw` renderer commands, `advance`). Run `python3 scripts/virtual-unit/scenarios.py --update NAME`, open the new picture in `host/tests/golden/screens/`, and judge it before you commit it.

**Add a screen.** The screen is firmware code. A change to a screen is a patch in `firmware/patches/` (display only). Then add its scenario and run the screen audit.

**Goldens.** A golden is a PNG the renderer drew. A test fails when a frame differs, so a change to a picture is always looked at.

**Gate a scenario by its patch.** A scenario that shows a screen only a patch that is not on `firmware/patches/ORDER` can draw goes in the `REQUIRES` list of `scenarios.py` with that patch's name. It is dropped from every list while the patch is off the list, and its golden waits on the branch with the patch.

**Offline lines.** `offline_lines.py` holds six situations in six languages (each line one subtitle row, at most the record's 100 bytes) and the mouth levels the mumble reference gives. Each is a scenario `offline-line-<situation>-<language>`. A test checks the limits, that every situation is a real tag of the pantry record, and that every line has a golden.

**The brain route.** `brain_route.py` models what the unit saves: the pairing with the host in one place, the hosted link only in the `cl_` settings. Joining the hosted brain writes them, leaving it wipes them, keeps the pairing and queues the notice.

**Measure a game.** `games_cost.py` and the renderer commands `diffbegin`, `play`, `technique`, `timeit` and `objcount` are explained, with the pass rules, in [how to measure a game](../dev/measure-a-game.md). The cost table is in `docs/plan/games-visual-budget.md`.

**Run with a named tree.** `MAIPAI_FW_TREE_ROOT=<tree> bash scripts/virtual-unit/build-face.sh`, then `build-screens.sh`. Build the browser version from the same tree (`MAIPAI_FW_TREE` for `scripts/virtual-unit/wasm/site-build.sh all`), or the two will draw differently.

Back: [index](index.md).
