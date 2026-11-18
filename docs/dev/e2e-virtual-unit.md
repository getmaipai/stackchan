# End to end on the virtual unit (the spoken-turn check without hardware)

`uv run --project host python scripts/virtual-unit/e2e.py [--fresh-venv] [scenario ...]` runs the real host in a clean venv (the repo's host package installed with `uv pip install`, as the README's step 1 does), in its own-model mode with the documented settings. The robot is a simulated unit whose every tool call goes to the virtual unit: the real LVGL screen code, the movement limiter, the body. A scripted server on localhost plays the model (`/v1/chat/completions`), speech to text (`/v1/audio/transcriptions`) and text to speech (`/v1/audio/speech`); every request it sees is kept. Canned audio (a quiet lead, a voiced stretch, a quiet tail, Opus encoded) is streamed in real time, so the host's own endpointing finds the speech.

It runs as `host/tests/test_e2e_virtual_unit.py` in `scripts/test-all.sh` (about eight minutes for the 13 scenarios; `MAIPAI_E2E=0` turns it off; it skips without the renderer, `uv` or the cached dependencies). `--fresh-venv` installs into an empty temporary venv: the clean install.

| Scenario | What it does | Asserts (unit side, host side) |
|---|---|---|
| `spoken_turn` | wake, a spoken question, a scripted reply | the speech to text got the audio, the model got the words, the voice server spoke the reply, speech frames and a stop reached the unit, the unit shows its face again (eyes drawn, resting), no error line in the host log |
| `mood_and_overlay` | the reply holds `[happy]` and `[rain]...[/rain]` | tags are not spoken, a happy face frame reached the unit, `self.overlay.set` was called, no mouth list for a two-sentence reply |
| `long_sentence` | 12 s of speech after wake | all 200 frames reached the host and one turn came out (the host side of the SF03 rule; the unit's own 8 s guard is firmware) |
| `host_restart` | the host process restarts | the unit reconnects with its token, no new pairing, a turn works |
| `timer_by_voice` | "set a timer for four seconds" | the host sets `self.timer.set` 4 s on the unit without asking the model, speaks its confirmation, the unit rings when the time comes |
| `pair_code` | `stackchan pair`, then an unpaired unit | six digits are printed, the unpaired unit is refused |
| `second_unit` | a second paired unit connects | both stay connected, each gets its own tool calls, the host handles two units without an error |
| `readme_steps` | the README's steps on a clean install | `stackchan check` ok, `stackchan status` names the brain and unit, then `spoken_turn` |
| `privacy_tap` | a tap on the mouth, a second tap, a hold, a tap on an eye | the unit's own gesture core (SF02) decides each press; the host follows the mute on and off (its privacy log lines) |
| `listen_ended` | wake, then 8 s of silence | the unit's listening guard core (SF03) says 8 s; the host ends the quiet turn with no model request and reads the unit's `listen_ended` event |
| `key_exchange` | an unpaired unit asks to pair; the six digits are typed on the settings page | the host's commitment matches the unit's key schedule core (SF20); a wrong code is refused and the unit is told; the unit's digits are accepted and the unit is told it is paired |
| `host_id_first_wins` | heartbeats from two host ids, cued calls, session end, 10 s silence | the unit's remote session core (SF01, FM03) keeps the first id, refuses a cued call with another, drops the id with the session or after the dead-man time; the host half is a known gap |
| `idle_jump` | the fake clock jumps 3, 25 and 50 days | the timer that was due rings, the face is drawn, a spoken turn works; the host's own clock cannot be moved (known gap) |
| `soak` | 500 spoken turns (only with `MAIPAI_SOAK=1`) | every turn got a reply; the host's memory, threads, descriptors and sockets did not grow past the limits |

## The unit's own cores in the loop

`scripts/virtual-unit/e2e_extra.py` replays the firmware patches (the `ORDER` file) into an empty folder and compiles the unit's own headers into four small programs (`touch_shim.c`, `link_shim.c`, `remote_shim.c` and the existing `listen_guard.c`) kept in `.runs/vu-build/shims`, rebuilt when a patch or a shim source changes. A scenario asks the program what the unit would do and sends the result to the real host, so no rule is copied into Python.

## Soak (leak canary)

`MAIPAI_SOAK=1 uv run --project host python scripts/virtual-unit/e2e.py soak` sends 500 canned spoken turns (`MAIPAI_SOAK_TURNS` changes the count; about four seconds a turn, so 30 minutes for 500). After 10 warm-up turns it samples the host process every tenth of the run (psutil: resident memory, threads, open descriptors, internet sockets) and fails when memory grows more than 25 MB and 20 percent, threads or descriptors by more than 2 and 4, or sockets by more than 2, between the warm-up and the end. It also fails on any turn without a spoken reply and on an error line in the host log. The growth rule is `leak_verdict` in `e2e_extra.py`, tested on synthetic samples in `host/tests/test_e2e_extra.py`. Without the variable the scenario prints that it skipped.

## Idle jumps

`VirtualUnit.jump(ms)` moves the fake clock ahead at once (the renderer's tick and the tools' time). `idle_jump` uses 3, 25 and 50 days, which passes 2^31 ms and 2^32 ms where the unit's 32 bit tick wraps. The unit side is covered here and by `host/tests/firmware/wrap_soak_test.c` (the cores across both wraps). The host side cannot be jumped from outside: it runs on the machine's own clock and the repo has no tool that moves another process's clock, so its timers are covered by the fake-clock unit tests of each module.

## Known gaps and blockers

A check marked `known_gap` prints GAP and does not fail; when it starts passing, the run fails once to say the flag can go. Two gaps found earlier are fixed:
- The host sends `self.face.mouth_cues` for a reply that is one sentence: the first audio waits at most 0.25 s for the sentence to finish, then the list goes out just before it (`StackChanAudioPlayback._send_mouth_cues`, limits in `mouth_cues.fit_to_unit`). The unit takes one list per reply and keeps the mouth closed after its last cue, so a reply of two or more sentences sends none and the mouth follows the loudness. Covering longer replies needs a firmware change (a list that can be extended while speaking).
- With two units connected the face frames go to the unit of the turn, or to every unit for the resting face, instead of failing with a single-session error.
Open gaps:
- `host_id_first_wins`: the host sends `self.remote.session` only while a remote controller is live; the rig has no controller client, so the first-wins window is checked on the unit's core only.
- `idle_jump`: no tool moves the host process's clock (above).

The simulated unit does one thing the real one does not: its tools that answer with a JSON array send them wrapped in an object. The rig unwraps those (`VuFirmware._run_tool`), because the host reads the bare array; before that fix the host never saw a device event from the virtual unit.
