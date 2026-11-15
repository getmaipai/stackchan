# Voice

## Talk to the robot

1. Say the wake word. The face perks up and a short tone plays.
2. Ask your question. Dots show while it thinks.
3. It answers out loud. The mouth moves as it speaks.

After an answer the robot keeps listening for a few seconds. You can ask a follow-up without the wake word.
You can also interrupt: speak while it talks and it stops and listens.

> **Screenshot placeholder:** `listening.png`. The robot face in the listening state.

## Voice commands

These work in any sentence that starts with the wake word.

| Say | What happens |
|---|---|
| "stop" | It stops talking and any alarm. |
| "mute" | Quiet mute. It still hears the wake word, so you can say "unmute". |
| "hard mute" | The microphone is powered down. Only touch, a button or the web app undoes it. |
| "quiet" | Slow, gentle moves and a low voice. |
| "don't move" | The servos hold still. |
| "volume up", "volume 40" | Changes the volume. |
| "brightness down" | Changes the screen brightness. |
| "sleep" | The robot turns away and the screen goes dark. |
| "what time is it" | It speaks the time. |
| "night mode" | Turns night mode on or off. |

## Personas

A persona sets the name, the voice and the way the robot talks. Pick one in the web page or set `persona` in `robot.toml`.
Lock a persona with `persona_lock = true` so a spoken request cannot change it. A family-friendly persona is included.
It is a prompt, not a guarantee. The model you connect decides what is said.

> **Screenshot placeholder:** `personas.png`. The persona list in the web page with one locked.

## Actions through the model

The robot can do things when you ask in plain words: set a timer, change the volume, show a face. The model chooses the action.
If the model cannot call actions, the voice commands above still work.

## Offline phrases

Short replies such as "I cannot reach my model right now" can play in your own voice, so the robot still talks when the model is down.
Record them once from the web page.

## Your own models

Set `llm_url`, `stt_url` and `tts_url` in `robot.toml`. Leave the speech addresses blank to use the built-in engines.
Run `stackchan check` after any change.
