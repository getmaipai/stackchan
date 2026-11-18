# Talk to the virtual robot

Status: planned. The panel exists; the voice does not run yet.

The **Talk** panel in the side panel is built to show a conversation with the virtual robot: whether a microphone is live, how loud you and the robot are, how long the answer took, and the words that were said. It never opens your microphone by itself. Today it shows a plain message that the voice bridge is not connected, so there is nothing to speak to.

## What works now

- **Type to the robot.** The box under **Quick actions** sends words to the robot's speech path, and the mouth moves with them. Lights and speech are one click each.
- **The offline voice.** When the robot has words but no voice, it mumbles them. Listen to it on the sounds page of the developer tools: `python3 scripts/sounds-demo.py`.

## What it will do

When the bridge is built, you will press one button to talk, see the live level and the transcript, and hear the answer. Your microphone will be off until you press it, and the panel will say so in words. Voice in the browser version is planned after the desktop one.

## Why it is not on yet

Talking needs a speech service and a model behind it, and each of those is a choice about privacy. The robot's promise is that nothing leaves your home without your say-so, so the voice bridge waits for that design rather than guessing.

Back: [index](index.md).
