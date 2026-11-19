# The brain routes on the unit (owner decision 34)

Status: on branch `ux/unproven-games`, unproven (patches UX19 and UX20 wait for a bench plain-boot proof). Screens, words and tests are here; the flow behind them is the firmware track's and the app track's.

## Step 4 of the first run: two equal routes

The brain step offers two tiles of the same size, neither highlighted, neither an "extra" (patch `UX19-brain-two-equal-routes.patch`):

| Tile | Words (English) | Saves | What it does |
|---|---|---|---|
| A | Hosted by M5Stack/Xiaozhi, then "Your voice goes to their servers, outside your home." | mode 3 | goes on to the privacy step |
| B | Custom, then "Your voice stays where you point it." | opens the Custom page | MaiPai Home, My own servers, Set one up for me (modes 0, 1, 2 as before) |

Each tile is 304 by 78 px, 8 px apart, 8 px under the header (y 60 to 138 and 146 to 224). The words exist in English, Spanish, French, German, Portuguese and Italian (route A keeps the name M5Stack/Xiaozhi in every language). Back on the Custom page returns to the two tiles; Back on the two tiles goes to the name step. Skip never picks A: it takes the old default (MaiPai Home when a hub is known, else Set one up for me). `first_run_done` carries mode 3 for the hosted route, so the host's `FirstRunNames.on_brain` gets a new word (`hosted`; the app track maps it).

## The notice after leaving hosted

`UX20-hosted-link-removed-notice.patch` adds `maipai_brain_notice_core.h` (words, six languages, the button box) and `maipai_brain_notice.h` (the LVGL screen, `mbn::build`). It says "Hosted link removed", "The saved link to M5Stack/Xiaozhi is deleted." and "Your voice now goes where you pointed it.", with one OK button (160 by 56). The leaving-hosted flow of the firmware track shows it after it wiped the `cl_websocket` and `cl_mqtt` settings, and closes it on OK.

## The route switch in the playground

`scripts/virtual-unit/brain_route.py` models what the settings store keeps: the host pairing in `websocket`, the hosted link only in `cl_websocket` and `cl_mqtt` (the firmware track's cloud-brain test, `docs/plan/cloud-brain-firmware-test.md`). Joining hosted writes the cl_ settings and leaves the pairing alone. Leaving it wipes them, keeps the pairing, and queues the notice. `host/tests/test_brain_route.py` runs the switch and compares the notice with the unit's own drawing.

## Frames

`first-run-4` and `first-run-4-<language>` (the two tiles), `first-run-4c` and `first-run-4c-<language>` (the Custom page), `brain-removed-<language>` (the notice). All are audited by `scripts/virtual-unit/screen_audit.py` (targets of 48 px and more, 8 px apart, text of 16 px and more).

## What is the firmware track's

Showing the notice after the wipe, the `cl_` wipe itself, and the hosted route's connection (decision 34: planned until a test build proves the vendor's server accepts the firmware; if it does not, tile A is hidden and the docs say why, which this patch does by leaving tile A out; a build flag for that is a small follow-up).
