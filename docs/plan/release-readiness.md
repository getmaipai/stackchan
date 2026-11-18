# First release readiness: the friend test

Made by `python3 scripts/readiness.py` from the repository; do not edit by hand. A friend should be able to do each row alone. `done` needs evidence and nothing missing; `blocked` means something it needs does not exist yet; `partly` is the rest. Host tests alone never make a robot feature `done`: the missing line names the hands-on check.

| Row | Status | Evidence in the repo | Still missing |
|---|---|---|---|
| Install the robot from a web page | **blocked** | flasher page and scripts: 3 file(s), e.g. `flasher/flasher-core.js`; flasher tests: 1 file(s), e.g. `flasher/test/core.test.mjs` | a flasher published at an address a friend can open; a signed release image to flash (no release key yet) |
| Install the host program without a terminal | **blocked** | install page: 1 file(s), e.g. `docs/user/install-the-host.md`; host packaging: 1 file(s), e.g. `host/pyproject.toml` | an installer a friend can double click (today: pipx from a terminal) |
| Pair the robot with a code, no terminal | **partly** | six-digit pairing card on the settings page: 1 file(s), e.g. `host/maipai_body/settings_ui_family.py`; pairing tests: 3 file(s), e.g. `host/tests/test_phase4_pairing_cli.py` | a person pairing a real robot from a phone, start to end, with nobody helping |
| First run: language, name, mode, privacy sentence | **partly** | first-run screens as golden frames (English): 5 file(s), e.g. `host/tests/golden/screens/first-run-1-en.png`; first-run patches: 5 file(s), e.g. `SF09-first-run-wiring.patch` | a person doing the first run on a real robot with a finger (bench 2026-11-18 ran it once with test touches: it shows once after Wi-Fi and never again); the five other languages read by native speakers |
| A voice reply after the wake word | **partly** | host turn tests: 1 file(s), e.g. `host/tests/test_turn_client.py`; voice page: 1 file(s), e.g. `docs/user/voice.md` | the wake cue and the first spoken sentence timed on a robot (bench 2026-11-18: five of five short test clips answered with no reset; the 150 ms and 300 ms figures are still targets, not measurements) |
| Update the robot | **blocked** | signed update patches: 2 file(s), e.g. `155-host-url-tools-removed-and-signed-updates.patch`; update cover frames: 4 file(s), e.g. `host/tests/golden/screens/cover-update-0.png` | a release key and a signed image installed on a robot; a first update from one real release to the next |
| Privacy switches: mute, camera off, always-on cues | **partly** | privacy page: 1 file(s), e.g. `docs/user/mute-and-camera-off.md`; camera on and muted frames: 2 file(s), e.g. `host/tests/golden/screens/screen-camera-on.png` | the cues seen and heard on a robot with a real finger (bench 2026-11-18 proved tap on, hold off and no toggle while muted with a test touch) |
| Lock the robot with a passcode | **partly** | lock patches: 4 file(s), e.g. `LK01-lock-core.patch`; lock screen and keypad frames: 5 file(s), e.g. `host/tests/golden/screens/lock-keypad-empty.png`; lock page: 1 file(s), e.g. `docs/user/lock.md` | a person locking and unlocking on a robot (bench 2026-11-18: five wrong codes lock it out and the lockout survives a restart); 3 known lock bug(s) still open as expected-fail tests |
| Parent view: what the robot is doing, in plain words | **partly** | parent view code: 1 file(s), e.g. `host/maipai_body/settings_ui_family.py`; plan: 1 file(s), e.g. `docs/plan/parent-view.md` | the page's buttons measured at phone width (48 px); a parent using it on a phone |
| Docs a friend can follow | **partly** | user pages: 49 file(s), e.g. `docs/user/bench-listening.md`; claims check: 1 file(s), e.g. `scripts/docs-claims-check.py`; screens from the virtual unit: 14 file(s), e.g. `docs/images/vu-clock.png` | 81 placeholder drawings still to replace with real pictures; the pages read aloud to someone who has never seen the robot |

## The blocked rows and what unblocks each

**Install the robot from a web page**
- owner: create the release key and decide where the flasher page is published (an address a friend can open)
- firmware: build the first release image signed with that key and publish it with its signature file
- app: host the flasher page and the image, and point the page's manifest at them

**Install the host program without a terminal**
- owner: choose the systems to support first (Mac, Windows, a Raspberry Pi) and whether a bundled app is wanted
- app: build that installer, with the first-run page that opens the settings page and the pairing card, and test it on a clean machine

**Update the robot**
- owner: create the release key (the same one as the flasher row) and say when a first release is cut
- firmware: sign two releases and prove the update path with the real key: accepted, refused on a wrong signature, and rolled back when the new image fails to start
- bench: run that on a robot and record it

Totals: 0 done, 7 partly, 3 blocked.

## What gates the first release, in one list
- A release key and a signed image (blocks install and update).
- A published web flasher and a host installer that needs no terminal.
- Hands-on checks on a robot: first run, pairing from a phone, lock, privacy cues, the first spoken reply, the head's own timings.
- Finger test on the glass (owner, 2026-11-18): press Skip and Back on every first-run step, the keypad keys, every control sheet tile, both sliders, the four settings tabs, the timer delete button, the games wall tiles and the Quiet now and Vision off tiles; note any press that misses, hits the next target or needs a second try (the audit that lists them is docs/dev/screen-audit.md).
- Native-speaker review of the five languages after English and Spanish.

Related: `docs/plan/friend-test-path-2026-11-18.md` (the path written as steps), `docs/dev/head-recording.md` (the servo calibration the bench still owes).
