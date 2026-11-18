# Tools, scenarios and goldens

**Add a tool.** Add the handler in `scripts/virtual-unit/tools/<group>.py` with `@tool("self.x.y")`. A tool the firmware does not list fails the parity check (`host/tests/test_virtual_unit_parity.py`), so the name must be in `schema/tools.json`. Controls that are only for the rig are named `sim.*`.

**Add a scenario.** Add steps to `SCREENS` in `scenarios.py` (`call`, `raw` renderer commands, `advance`). Run `python3 scripts/virtual-unit/scenarios.py --update NAME`, open the new picture in `host/tests/golden/screens/`, and judge it before you commit it.

**Add a screen.** The screen is firmware code. A change to a screen is a patch in `firmware/patches/` (display only). Then add its scenario and run the screen audit.

**Goldens.** A golden is a PNG the renderer drew. A test fails when a frame differs, so a change to a picture is always looked at.

Back: [index](index.md).
