# Fuzzing the unit's parsers, and a hostile peer against the host

Two checks that try to break the system from outside. Neither needs a robot.

## 1. The unit's parsers under sanitizers

`bash scripts/fuzz-cores.sh [iterations] [seed] [target ...]` (default 20000 inputs, seed 1, every target). It replays the firmware patches (`ORDER`) into an empty folder, builds one program per parser from `scripts/fuzz/core_fuzz.c` with `-fsanitize=address,undefined -fno-sanitize-recover=all` into `.runs/fuzz`, and runs each. Any sanitizer report stops that target with the report in `.runs/fuzz/run_<target>.log` and the line that repeats it.

Targets, each the real `*_core.h` function: `FACE` (`mf_load`), `FILLER` (`tf_parse_index`, the host's clip index JSON), `GAMES` (`mg_parse`), `LANG` (`mlw_parse`), `REACT` (`mr_load`), `PACKCACHE` (`tpc_decode`), `TIMERS` (`mt_load`), `UPDATEHDR` (`muh_parse`), `MOOD` (`mm_load`), `TAILNET` (`mt_parse_ip`), `REMOTE` (`mr_parse_speaking` and the remote session and say path), `LISTEN` (`tl_parse_*`), `LOCK` (`mlk_load`, `mlk_check`).

How inputs are made: structured seeds written by the cores' own writers where there is one (face blob, timers, reaction table, pack directory, update header, words file), the few text seeds in the harness, then bit flips, random bytes, truncation, swaps, runs of 0x00 and 0xFF, extension to thousands of bytes, and pure noise, from a seeded generator (the seed and count make a failure repeat). Every input is copied into a heap block of exactly its length, so one byte read or written past it is an error. A deliberate overflow is caught by the same flags on this machine.

Result on 2026-11-18: three seeds of 300000 inputs for each of the 13 targets, no finding. What it does not cover: the stock firmware's JSON tool-call layer (the `mcp_server` of the base firmware) is not built from this repository, so it is not here; the cores above are the parsers the patches add. `GAMES` and `FILLER` start with few valid seeds, so their deep paths are reached mostly by luck: a seed made by the pack builder would reach more.

`host/tests/test_fuzz_cores.py` runs a 3000 input version in the suite (`MAIPAI_FUZZ=0` turns it off). `host/tests/test_hostile_unit_replies.py` does the same for the other direction: 3000 seeded garbage replies from a "unit" to the host's own parsers (events, saved networks, privacy), which must never raise.

## 2. A hostile peer against the real host

Three scenarios of `scripts/virtual-unit/e2e.py` (`e2e_hostile.py`), against the real host in a clean venv with a virtual unit paired and answering:
- `hostile_unauthenticated`: a peer with no credentials. Wrong and absurd headers, frames sent before any hello, 300 connections held open with no hello, hostile pairing messages (wrong order, start twice, bad base64, 31, 33 and low-order keys, a 2 MB key, non-object JSON, a short nonce), and 60 pairing requests from one address (the host closes after 8 in 10 minutes with code 1013).
- `hostile_paired_peer`: a peer holding a valid token (a stolen or broken unit). 33 kinds of malformed text frame after a hello and with none (truncated JSON, arrays, null, 20000 nested brackets, a 200 KB string, bad audio parameters), binary frames of 0 bytes to 700 KB, a message over the 1 MiB limit, 4000 hellos and 3000 listen start and stop messages in a row, 60 sessions with one token at once, and bad frames on the avatar port.
- `hostile_settings`: the settings page. Broken, huge (20 MB) and mistyped bodies on 17 routes, path tricks, guessing the six digits, and replaying an accepted code for the same exchange and for a new one.

After each attack the same health check runs: the host process is alive, the real unit still gets a spoken reply, threads, descriptors and sockets are back near where they were (a 20 second grace before calling it a leak), and the host logged no `ERROR` line. Three log findings are kept as `known_gap` checks (they do not fail the run; when fixed, the run says to remove the flag): a request that is not valid HTTP logs `ERROR opening handshake failed` with two tracebacks; a command cut by a closing or superseded session logs `Future exception was never retrieved`; and a unit that drops during the pairing exchange logs a warning with a traceback.

Result: no crash, no hang, no leak, no file served, no pairing by guess or replay, no 500 from the settings routes. The real bugs found this way are in `host/tests/test_cross_review_open_bugs_2.py` (a second exchange replacing the one waiting for its digits; an exchange nobody finished staying on the pairing card).

Run one: `uv run --project host python scripts/virtual-unit/e2e.py hostile_paired_peer` (about two minutes each; `E2E_LOG=file` keeps the host log).
