---
description: Run the on-unit gate in the background and report one line per check
---

Take the unit lease. Start `scripts/run-bg.sh gate -- stackchan gate --report .runs/gate.md` in the background and continue other work. When it finishes read only `.runs/gate.md` (verdict table: memory floors, largest block, latency p50 and p95 per stage, audio lateness, stalls, resets). Print: `gate PASS` or `gate FAIL: <check names>` plus the report path. Release the lease. Never paste the log.
