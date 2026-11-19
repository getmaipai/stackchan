# Test suites and rigs

- `bash scripts/test-all.sh` runs the whole host suite in four processes. `bash scripts/test-fast.sh` leaves out the slow tests.
- `host/tests/test_virtual_unit*.py` test the virtual unit: the hardware model, ports, dance, memory, assets, host-away.
- The end-to-end rig (`scripts/virtual-unit/e2e.py`) runs the real host in a clean environment against virtual units with scripted model and speech servers. `--fleet` runs the many-unit, chaos and service scenarios (`e2e_fleet.py`). Details: `docs/dev/e2e-virtual-unit.md`.
- Tests for the games: `test_more_games_cores.py` (the pure core of each new game against its patch text), `test_games_budget_revisions.py` (one draw callback, dirty rectangles, no changed pixel outside them), `test_games_audit.py` (the data-pack games' click areas), `test_offline_lines.py`, `test_brain_route.py`, `test_brain_screens.py`. A test for a patch that is not on the list yet skips and says why.
- Hostile-peer and fuzz tools: `docs/dev/fuzzing-and-hostile-peer.md`.

- Filmstrips (several frames in one golden): `clock-flip-*` (the style flip), `game-c4-drop-filmstrip` (a chip dropping, SF72), `host-away-two-messages` (Offline, then the ten-minute notice on the banner row for 20 s, then Offline again; SF64, SF68, SF73) and `mumble-mouth-sync`.
- The host-away rig (`scripts/virtual-unit/host_away.py`) runs the reconnect core as SF49 and SF64 leave it (0.5 s first wait, caps 5, 15, 30 then 120 s), the Offline sign after 45 s, the sleepy face after 3 minutes, the notice at ten minutes and every 30 minutes, and records the `ws_away_notice` events.

Back: [index](index.md).
