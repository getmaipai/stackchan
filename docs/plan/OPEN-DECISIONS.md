# Open decisions (2026-11-18)

Each has a recommendation and a default. The default applies on its own until the owner chooses; nothing waits. Reversible ones are marked R.

| # | Question | Recommendation = default | R |
|---|---|---|---|
| 1 | Content filter in own-model mode (decision 13 says none) | Basic filter on by default with an off switch, an "adults" label, Home required for a child's robot | yes |
| 2 | Cloud model addresses | Explicit opt-in and a visible mark; warn on plain http | yes |
| 3 | Privacy switches (decision 44, single taps) | Tap turns ON; a short hold or the sheet turns OFF; the alarm-stop press never toggles | yes |
| 4 | Camera cue | Also drives the lights and wakes the screen; no capture with a dark screen | yes |
| 5 | Lock | Pause after wrong tries; code needed to change auto-lock; the model never sets a code | yes |
| 6 | Face following `always` and idle motion off | Decide after the camera path works, with noise and cue-time numbers; keep current until then | yes |
| 7 | Red light uses against the no-red standard | One table, red only for alarm and low battery | yes |
| 8 | Bluetooth | Off for v1; decide after v1 on product grounds; measure both cost figures first | yes |
| 9 | Coding companion | Request text on screen, no voice-to-task, project name only, not red | yes |
| 10 | Release key holder | Owner holds it; Studio Keychain signs; one release yes per release | no |
| 11 | Public history (key-shaped values in early commits) | Publish a fresh squashed history; keep the old one private | no |
| 12 | Wake word and its license | Family-chosen wake word, trained locally; license note stays in `wake-word-licensing-2026-11-17.md` | yes |
| 13 | eFuses (flash encryption, secure boot) | Not burned until after the first signed update works; revisit then | no |
| 14 | Camera-frames path to the host | On-unit detector first (already built, off); frames to the host after the privacy review | yes |
| 15 | Sponsors, egress capture, Reachy questions | The tree's own open list stays; none blocks steps 1 to 5 | yes |

Owner-only and irreversible (10, 11, 13) are not defaulted by silence: work continues without them, and the release waits.
