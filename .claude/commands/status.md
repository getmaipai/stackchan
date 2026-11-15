---
description: One-screen status of lanes, trains, the unit lease and spend, read from the ledger
---

Read only `.ledger/trains.md`, `.ledger/lanes.md` and `.runs/*.status`. Print at most 12 lines: each lane (name, task, running or done or blocked), the current train and its state, who holds the unit, the last gate verdict, and spend this week per pool. Do not read transcripts or logs; if a lane is blocked, name the ask in one sentence.
