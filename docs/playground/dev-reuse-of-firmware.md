# How the real firmware code is reused

The screens and rules are the unit's own code, not copies.

1. **The overlay tree.** `build-face.sh` takes the newest built firmware tree (`~/esp/stackchan-rebuild/bNN`) and `overlay_patches.py` applies any patch of `firmware/patches/ORDER` the tree lacks. The renderer is built from that.
2. **The tree stamp.** `.runs/vu-build/tree-stamp.json` records the tree and the hash of `ORDER`. `test_virtual_unit_tree_stamp.py` fails when `ORDER` changed since the build, so goldens cannot silently come from an old tree.
3. **The skip list.** A patch the tree cannot take is named in `scripts/virtual-unit/overlay-skip.txt` with the reason. An unexplained failure fails the build.
4. **Cores from patches.** Headers added by patches (dance ladder, reconnect) are cut out of the patch files and compiled, so the rule is the unit's.
5. **Host stand-ins.** What the unit's code asks of the rest of the system (the version numbers, the lock, the games list) comes from `scripts/fw-face-render/more_host.cc` and the hooks.

6. **Which tree.** The default is the newest built tree. A newer tree can hold patches that are not on `firmware/patches/ORDER` yet, and an older one can have lost its build folder, so the goldens only match a tree whose patch set is the list. Name one with `MAIPAI_FW_TREE_ROOT`. At the time of writing the complete tree without unproven patches is `b66`, with the overlay applying what it lacks; the firmware track names the current reference tree. Build the browser version from the same tree.
7. **Native and browser agree.** The renderers build with `-ffp-contract=off` and a fixed random source (`scripts/fw-face-render/stub/esp_random.h`) so the browser build, which has neither fused arithmetic nor the Mac's random numbers, draws the same pixels. The parity run (`scripts/virtual-unit/wasm/parity.js`) compares 335 cases; read `docs/plan/wasm-port-report.md` for the last result.

Back: [index](index.md).
