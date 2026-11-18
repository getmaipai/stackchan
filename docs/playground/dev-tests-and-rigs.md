# Test suites and rigs

- `bash scripts/test-all.sh` runs the whole host suite in four processes. `bash scripts/test-fast.sh` leaves out the slow tests.
- `host/tests/test_virtual_unit*.py` test the virtual unit: the hardware model, ports, dance, memory, assets, host-away.
- The end-to-end rig (`scripts/virtual-unit/e2e.py`) runs the real host in a clean environment against virtual units with scripted model and speech servers. `--fleet` runs the many-unit, chaos and service scenarios (`e2e_fleet.py`). Details: `docs/dev/e2e-virtual-unit.md`.
- Hostile-peer and fuzz tools: `docs/dev/fuzzing-and-hostile-peer.md`.

Back: [index](index.md).
