# Change a setting

You will find the same settings in three places: the `robot.toml` file, the settings page on your host and the robot itself. Wi-Fi is set on the robot's own setup screen, not on the host's page.
Changing a setting never needs a reflash.

![The on-robot settings, General page, with Volume and Brightness sliders.](../images/vu-settings-general.png)

*The on-robot settings, General page, with Volume and Brightness sliders.*

## Face style (`face_style`)

Picks the look of the face: big eyes, stock or minimal. The settings page on your host shows a preview.

## Face color (`face_color`)

Choose none, a named color or a custom color. The default is neutral and has no color until you pick one.
Color never carries meaning alone. Every state also has a shape or an icon.

## Captions (`captions`)

Shows spoken words on the screen. It is off by default. You can turn it on for any face.

## Night mode (`night_mode`)

Dims the screen and the lights, and the clock face gets softer. Quiet hours are a separate setting.

## Quiet hours

On the settings page, Behavior tab, **Quiet now** keeps the robot's own sounds quiet until you turn it off. **Quiet on a schedule** does the same between two times, on the days you pick. It is off until you turn it on. Alarms and timers you set still ring, and the privacy and safety cues never stop.

## Language (`language`)

One of six languages. See `languages.md`. The robot changes at once with no file edit.

## Other keys

- `brain`: `llm` (your own LLM, the default) or `home`.
- `url`, `stt_url`, `tts_url` under `[llm]` in `robot.toml`: your model and speech addresses. A blank speech address uses the built-in engine, which also needs its model folder (`stt_model_dir`, or `tts_model`, `tts_tokens` and `tts_data_dir`). The [Brain page](choose-a-brain.md) can download small speech models for you.
- `voice`: the voice to speak with.
- `thinking_cue`: dots always, plus a quiet tone by default.
- `strip_mode`: `petting` (default) or `control` for quick sliders.
- `update_*`: the updater. Checking is on and installing is off until you turn it on.

Run `stackchan check` after any change to your addresses. Environment variables override secrets in the file.

## Open the settings page from your phone

The page is for the host computer only until you turn this on. In `robot.toml` add `lan = true` under `[settings]` and restart the host. Run `stackchan settings-token`, then open `http://<the host's address>:8051/settings?token=<the token>` on your phone once; the phone stays logged in. Anyone on your Wi-Fi who learns the token can change the robot's settings, so keep it private. The page is plain web (not encrypted) inside your home network, so do not turn this on for a network you do not trust.

## All settings at a glance

| Setting | What it does | Default |
|---|---|---|
| `brain` | Who answers: your own LLM (`llm`) or MaiPai Home (`home`) | `llm` |
| `[llm] url` | Your model's OpenAI-compatible address | blank |
| `[llm] stt_url`, `tts_url` | Your speech tools. Blank uses the built-in engines when their model folders are set | blank |
| `[home] url` | Your MaiPai Home hub address | blank |
| `language` | English, Spanish, French, German, Portuguese or Italian | English |
| `voice` | The voice the robot speaks with | built-in voice |
| `speech_speed` | How fast it talks, 0.75 to 1.5 | 1 |
| `speech_pitch` | Pitch, -12 to 12 semitones | 0 |
| `hourly_chime` | A soft tone at the top of each hour | off |
| `persona` | A short text that tells the model how to behave | none |
| `face_style` | Big eyes or minimal | big eyes |
| `face_color` | None, a named color or a custom color | none |
| `captions` | Show spoken words on screen | off |
| `night_mode`, `quiet_from`, `quiet_to` | Dim and quiet at night | off |
| `thinking_cue` | The tone while it thinks | quiet tone |
| `strip_mode`, `quick_sliders` | Head strip behavior and its sliders | petting |
| `hourly_chime`, `idle_motion` | Small behaviors | off, on |
| `local_unmute` | Whether the robot's own face can unmute it | on |
| `update_channel`, `update_source`, `update_check`, `update_install` | Updates | stable, official, weekly, ask |

The settings page on your host has a Remote controls section: beep, flash, find my robot (it works even when muted), say something, head pad, nod, shake, dance, start a game and take a photo. Camera, watching and home tools are opt-in packages with their own pages; some also need MaiPai Home. See [Compare](local-vs-home.md).

Run `stackchan check` after any change to your addresses.

## Reset the robot

Clears Wi-Fi networks, pairing and settings, after a confirmation. See [Keep the robot secure](security.md).

## More keys

- `persona`: a short text that tells the model how to behave.
- `quick_sliders`: which sliders the head strip opens. The default is volume and brightness.
- `hourly_chime`: a soft tone each hour. Quiet hours are set on the settings page (Behavior), not in the file.
- `idle_motion`: turn the idle moves off.

![The settings page on the host with robot status, settings, the pairing code, mute and update.](../images/web-settings.svg)

*The settings page on the host with robot status, settings, the pairing code, mute and update. A placeholder drawing, not a real screenshot.*

## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us what you saw.
