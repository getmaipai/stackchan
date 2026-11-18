# Suite speed (2026-11-18)

Before: `scripts/test-all.sh` ran 5,700 tests in one pytest process, about 13 minutes without the end to end and about 25 with it.

Now:
- `bash scripts/test-all.sh`: everything, in 4 pytest processes at once (`scripts/test-sharded.py`; the test files are dealt out largest first by the time each took last run, kept in `.runs/test-times.json`, so the groups finish together). `JOBS=1` runs it the old way.
- `bash scripts/test-fast.sh`: the same without the tests marked `slow` (the end to end on the virtual unit and the sanitizer fuzz), for quick feedback while working.
- The end to end runs its 16 scenarios 4 at a time, each in its own process with its own host and ports (`e2e.py --jobs N`, `MAIPAI_E2E_JOBS`), the clean install done once.
- The soak (`MAIPAI_SOAK=1`, 500 turns, half an hour) stays out of every default run.

Measured on the Mac Studio, idle: see playground report 16 for the numbers. Rules that keep the sharding safe: a test must not rely on a fixed port or a shared folder (use `tmp_path` and free ports); a file that must run alone is a candidate for a `serial` marker (none needed so far: all 5,675 tests passed when sharded). A new slow test gets `@pytest.mark.slow` (or `pytestmark`) so the fast run stays fast.

Under heavy CPU load the e2e timing is the weak point; `bash scripts/e2e-flake-hunt.sh [runs] [burners]` runs it in a loop under load and keeps the full logs of the first failure (it found the avatar-port start race, fixed).
