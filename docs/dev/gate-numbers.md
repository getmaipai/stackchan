# Gate numbers (2026-11-18)

What a firmware build must show on the unit before it counts as good. The bench agent measures; a script checks; a number that was not measured fails.

| Gate | Number | Checked by |
|---|---|---|
| Internal RAM free, median after settling | at least 40,000 bytes | `scripts/fw-stress.py` |
| Internal RAM, lowest seen | at least 24,000 bytes | `scripts/fw-stress.py` |
| Largest free internal block, median / lowest | at least 24,000 / 16,000 bytes | `scripts/fw-stress.py` |
| PSRAM free, lowest | above 6,000,000 bytes | `scripts/fw-stress.py` |
| Task stack margin | at least 1,024 bytes (idle and ipc tasks excepted) | `scripts/fw-stress.py` |
| Resets, watchdog, panics, host websocket drops, host calls failed | 1 reset (the start), 0, 0, 0, at most 20 percent of calls | `scripts/fw-stress.py`, `scripts/fw-voice-bench.py --gate` |
| OTA slot free | at least 20 percent of each slot, plain and gate images | `scripts/release-report.py` |
| Face refresh rate while it moves | at least 30 a second (`self.face.bench_run` workload move; 44.7 measured) | `scripts/gate-check.py --move-fps` |
| One face refresh | at most 8 ms (3 to 7 measured) | `scripts/gate-check.py --face-refresh-ms` |
| One full-screen picture refresh | at most 40 ms (26 to 35 measured) | `scripts/gate-check.py --picture-refresh-ms` |
| Wake event to the listening sound queued | median at most 100 ms (5 and 17 ms measured) | `scripts/gate-check.py --voice-log` |
| End of the question to the first reply sound | median at most 8 s, 95th percentile at most 25 s (provisional: 6.9 s and 24.8 s on a loaded Mac, one run) | `scripts/gate-check.py --voice-log` |
| Static screens flush no pixels | 0 pixels per frame on pages, walls, Settings, first run | virtual unit: `scripts/virtual-unit/frame_cost.py` |

## How to run the frame and latency gates

1. Voice: `python3 scripts/fw-voice-bench.py 8 voice.log --gate` (bench build, unit on the cable), then `python3 scripts/gate-check.py --voice-log voice.log`.
2. Frames: with the bench build, call `self.face.bench_run` with workload `move` for 20 seconds and read the refresh rate and the per-refresh time from its counters (`self.face.bench_fps`); give them to `gate-check.py` as `--move-fps`, `--face-refresh-ms`, `--picture-refresh-ms`.
3. One command with everything: `python3 scripts/gate-check.py --voice-log voice.log --move-fps 44.7 --face-refresh-ms 5 --picture-refresh-ms 31`. It prints each number with its floor and `GATE PASS` or `GATE FAIL`.

## Why these numbers

Memory floors come from `docs/design/memory-headroom-2026-11-16.md`. The frame numbers are the target (30 a second) and the measured costs of `docs/design/picture-faces-2026-11-16.md`. The unit adds about 0.3 s to a spoken turn (`docs/design/latency-2026-11-16.md`); the rest is host time, which a loaded Mac inflates, so the end-to-end limits are provisional until measured on a quiet host. Change a number here and in `scripts/gate-check.py` together; `host/tests/test_gate_check.py` fails when they drift.
