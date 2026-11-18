# First release readiness: the friend test

Made by `python3 scripts/readiness.py` from the repository; do not edit by hand. A friend should be able to do each row alone. `done` needs evidence and nothing missing; `blocked` means something it needs does not exist yet; `partly` is the rest. Host tests alone never make a robot feature `done`: the missing line names the hands-on check.

| Row | Status | Evidence in the repo | Still missing |
|---|---|---|---|
| Install the robot from a web page | **blocked** | flasher page and scripts: 3 file(s), e.g. `flasher/flasher-core.js`; flasher tests: 1 file(s), e.g. `flasher/test/core.test.mjs` | a flasher published at an address a friend can open; a signed release image to flash (no release key yet) |
| Install the host program without a terminal | **blocked** | install page: 1 file(s), e.g. `docs/user/install-the-host.md`; host packaging: 1 file(s), e.g. `host/pyproject.toml` | an installer a friend can double click (today: pipx from a terminal) |
| Pair the robot with a code, no terminal | **partly** | six-digit pairing card on the settings page: 1 file(s), e.g. `host/maipai_body/settings_ui_family.py`; pairing tests: 3 file(s), e.g. `host/tests/test_phase4_pairing_cli.py` | a person pairing a real robot from a phone, start to end, with nobody helping |
| First run: language, name, mode, privacy sentence | **partly** | first-run screens as golden frames (English): 5 file(s), e.g. `host/tests/golden/screens/first-run-1-en.png`; first-run patches: 5 file(s), e.g. `SF09-first-run-wiring.patch` | a first run on a real robot (no one has seen it on glass); the five other languages read by native speakers |
| A voice reply after the wake word | **partly** | host turn tests: 1 file(s), e.g. `host/tests/test_turn_client.py`; voice page: 1 file(s), e.g. `docs/user/voice.md` | the wake cue and the first spoken sentence timed on a robot (the 150 ms and 300 ms figures are targets, not measurements) |
| Update the robot | **blocked** | signed update patches: 2 file(s), e.g. `155-host-url-tools-removed-and-signed-updates.patch`; update cover frames: 4 file(s), e.g. `host/tests/golden/screens/cover-update-0.png` | a release key and a signed image installed on a robot; a first update from one real release to the next |
| Privacy switches: mute, camera off, always-on cues | **partly** | privacy page: 1 file(s), e.g. `docs/user/mute-and-camera-off.md`; camera on and muted frames: 2 file(s), e.g. `host/tests/golden/screens/screen-camera-on.png` | the cues seen and heard on a robot with the tap, the hold and the camera |
| Lock the robot with a passcode | **partly** | lock patches: 4 file(s), e.g. `LK01-lock-core.patch`; lock screen and keypad frames: 5 file(s), e.g. `host/tests/golden/screens/lock-keypad-empty.png`; lock page: 1 file(s), e.g. `docs/user/lock.md` | a person locking and unlocking on a robot; 3 known lock bug(s) still open as expected-fail tests |
| Parent view: what the robot is doing, in plain words | **partly** | parent view code: 1 file(s), e.g. `host/maipai_body/settings_ui_family.py`; plan: 1 file(s), e.g. `docs/plan/parent-view.md` | the page's buttons measured at phone width (48 px); a parent using it on a phone |
| Docs a friend can follow | **partly** | user pages: 44 file(s), e.g. `docs/user/baby-and-pet-monitor.md`; claims check: 1 file(s), e.g. `scripts/docs-claims-check.py`; screens from the virtual unit: 14 file(s), e.g. `docs/images/vu-clock.png` | 82 placeholder drawings still to replace with real pictures; the pages read aloud to someone who has never seen the robot |

Totals: 0 done, 7 partly, 3 blocked.

## What gates the first release, in one list
- A release key and a signed image (blocks install and update).
- A published web flasher and a host installer that needs no terminal.
- Hands-on checks on a robot: first run, pairing from a phone, lock, privacy cues, the first spoken reply, the head's own timings.
- Native-speaker review of the five languages after English and Spanish.

Related: `docs/plan/friend-test-path-2026-11-18.md` (the path written as steps), `docs/dev/head-recording.md` (the servo calibration the bench still owes).
