---
name: sim-check
description: Run every non-hardware check against the virtual unit (protocol conformance, behaviour tests, golden frames, language checks, adapter tests) and print one line plus failing names only. Use after any change to core, host, web app or packs, before any firmware build.
---

1. Run `scripts/run-bg.sh sim-check -- <the repo's sim check command>` (it wraps the virtual unit, golden frames, conformance and language checks).
2. Read only `.runs/sim-check.status`. On ok, print one line: `sim-check ok (N tests, M goldens, languages: en es)`.
3. On failure read the failing test names and, for a golden, the diff image path only; do not paste logs. Open the diff image once to judge it (a changed golden is accepted only after looking at it and updating with the explicit update command).
4. Never claim a hardware property from this check (memory, timing, audio, Wi-Fi, servos, wake model); those need the unit gate.
