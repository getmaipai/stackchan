# End to end on the virtual unit (the spoken-turn check without hardware)

`uv run --project host python scripts/virtual-unit/e2e.py [--fresh-venv] [scenario ...]` runs the real host in a clean venv (the repo's host package installed with `uv pip install`, as the README's step 1 does), in its own-model mode with the documented settings. The robot is a simulated unit whose every tool call goes to the virtual unit: the real LVGL screen code, the movement limiter, the body. A scripted server on localhost plays the model (`/v1/chat/completions`), speech to text (`/v1/audio/transcriptions`) and text to speech (`/v1/audio/speech`); every request it sees is kept. Canned audio (a quiet lead, a voiced stretch, a quiet tail, Opus encoded) is streamed in real time, so the host's own endpointing finds the speech.

It runs as `host/tests/test_e2e_virtual_unit.py` in `scripts/test-all.sh` (about four minutes; `MAIPAI_E2E=0` turns it off; it skips without the renderer, `uv` or the cached dependencies). `--fresh-venv` installs into an empty temporary venv: the clean install.

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

A check marked `known_gap` prints GAP and does not fail; when it starts passing, the run fails once to say the flag can go. No gap is open now. Two were fixed:
- The host sends `self.face.mouth_cues` for a reply that is one sentence: the first audio waits at most 0.25 s for the sentence to finish, then the list goes out just before it (`StackChanAudioPlayback._send_mouth_cues`, limits in `mouth_cues.fit_to_unit`). The unit takes one list per reply and keeps the mouth closed after its last cue, so a reply of two or more sentences sends none and the mouth follows the loudness. Covering longer replies needs a firmware change (a list that can be extended while speaking).
- With two units connected the face frames go to the unit of the turn, or to every unit for the resting face, instead of failing with a single-session error.

Not covered yet, and why: the pairing key exchange itself (the six digits typed on the host page; the simulated unit does not do the exchange, so units are approved in the pairing store), a privacy tap (the mute tile is drawn by the renderer; the host learns the privacy state by tool calls the virtual unit does not tie to the tile), a turn cut by the unit's `listen_ended` event, and the host-id first-wins window. Each needs a small piece in the simulated unit.
