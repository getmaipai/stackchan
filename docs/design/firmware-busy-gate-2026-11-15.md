# Firmware tools and busy gate, 2026-11-15

## Part A: the six tools

Tree `~/esp/stackchan-rebase/main`, branch `ours`. Each change was built before the next; all built, none rolled back. New patches are in `firmware/patches/` and on `ORDER` after 105 (applied and built in that order; each also passes `git apply --check` on the tree before it).

| Tool | Cut tag | Choice | Where |
|---|---|---|---|
| `self.robot.set_idle_motion` | CORE-V1 (037) | Built. Still by default, choice saved in NVS, read at boot. | `037-idle-motion-tool.patch` |
| `self.power.keep_awake` | CORE-V1 (074) | Built (the bridge call already existed; only the tool was missing). | `074-keep-awake-tool.patch` |
| `self.audio.set_sound_policy`, `sound_info` | CORE-V1 (116) | Built on the 115 core: policy in NVS namespace `mp_sounds`, also `play_sound` for the five sounds in the base image. The seven extra earcons and the 16 offline clips are not in this build (they answer `missing`; `clips_present` is 0). | `116-sound-policy-tools.patch` |
| `self.music.set` | HOME-PRESET (100) | Not built: the music feature core is far larger than a stub. The host now stops asking after the first Unknown tool answer. | `music_dance_wiring.py`, test added |
| `self.screen.set_face_background` | DEFER (017) | Not built. The host client treats Unknown tool as done after one try, so a night edge (brightness, lights) is no longer blocked by the failed call. | `xiaozhi/server.py`, test added |

Host tests: `uv run pytest` on the night, music dance, sounds and power-idle files, 192 passed. `scripts/check.sh`: hygiene and boundary ok.

Found, not fixed: the unit also answers Unknown tool for `self.audio.notify` (the self-test speech check) and `self.camera.take_photo` fails. Neither was on the list.

Patch `143-offline-label-after-45-s.patch` does not apply to the tree (`websocket_protocol.cc:312`). It was already like that and is not in the tree.

## Part B: busy gate

Measurement build: one log line in `SystemInfo::PrintHeapStats` raised to WARN (saved source restored afterwards, byte-identical). Unit `/dev/cu.usbmodem103401`, backup hash `3f1611bc...49e13e` checked before flashing; no restore was needed.

How it was driven: the bench page cannot attach to a real unit (its `--sim` is the only mode; gap noted in `.runs/bench-page.result.md`), and the live hub host already holds the unit. So the load came from the host's own local self-test endpoint (`POST 127.0.0.1:<vision port>/selftest/run`): checks `led` (six ring looks) and `reply` (a real chat reply through the hub), repeated 67 times over 10.5 minutes, all passing. Not covered: timer set and ring, head move (the host reported the head stopped by its software stop), speech (`self.audio.notify` missing), a spoken turn (the unit is muted or in full quiet: "wake word stays off").

| Measure | Observed over 69 heap lines | Gate | Result |
|---|---|---|---|
| internal_free, lowest steady line | 60,195 | at least 25,000 | pass |
| internal_min (lowest ever) | 39,828 | at least 15,000 | pass |
| int_big, lowest | 31,744 | at least 16,000 | pass |
| psram_min | 8,137,616 | above 6,000,000 | pass |

No panic, backtrace, watchdog or stall line. One reset line, from opening the serial port. Without music or camera or a spoken turn the gate is only partly exercised; the full gate (spoken turn, camera, music on) is still open.

After the run: source restored, plain build rebuilt (app 3,043,248 bytes, 41 percent of the slot free) and flashed with hash verified; it boots, registers `set_idle_motion` and `keep_awake`, and no Unknown tool lines appear for the four built tools. The live hub host (an older release) still asks for `music.set` and `set_face_background`; the host change takes effect when it ships.

Where the change is: patches and host edits are uncommitted files in the main checkout of the stackchan repo (not on GitHub); the firmware commits are on branch `ours` in the scratch tree; the unit runs the plain build.
