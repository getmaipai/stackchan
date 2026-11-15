---
name: train
description: Assemble and run one firmware build train: batch the ready patches, run every host-side check first, build in the background, read only the memory report and verdict, then load the unit once. Use whenever firmware changes are ready to build or flash.
---

A train is many changes, one build, one load. The goal is as few firmware builds and unit loads as possible.

1. Collect the batch from `.ledger/trains.md` (items marked ready). A change enters only if its host checks passed: simulator tests, golden frames, protocol conformance, unit tests, `scripts/hygiene-check.sh`, and a compile of the touched files where possible.
2. Write the train manifest: `.ledger/train-<n>.md` (items, checks passed, on-unit checks expected, what a failure would mean). Keep it under 30 lines.
3. Build in the background: `scripts/run-bg.sh train-<n>-build -- <build command>`. While it runs, work on the next slice from the "while the build runs" queue in the ledger; never wait idle.
4. When the build finishes, read only `.runs/train-<n>-build.status` and the memory summary (internal free estimate, flash per slot, static RAM). A failure prints at most five error lines; fix in the next train unless the unit is blocked.
5. Take the unit lease, load once (OTA push when possible), run `/gate` in the background, and keep working on host streams meanwhile.
6. Record the result in the ledger (pass or fail per on-unit check, memory and latency numbers, build id) and release the unit.
7. A hot-fix train is allowed once per cycle for a blocker only.
