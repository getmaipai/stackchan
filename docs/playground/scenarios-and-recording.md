# Scenarios and recording

A scenario is a short script of things the robot does: touches, tool calls and waits. You can play one, record your own, and run them all with the test suite. This page is for anyone using the playground.

## Play a scenario

1. Open the playground window and find **Scenarios** in the side panel.
2. Pick one from the list. The built-in ones are named for what they show, such as `face-happy` or `dance-3-sway`.
3. Press **Play**. The robot does it in real time, and the log at the bottom lists each step.

You'll know it worked when the screen, the head and the lights move as the name says.

## Record what you do

1. Press **Record** in the **Record what you do** section.
2. Tap and swipe the screen, press the buttons, or call tools. Every one is kept with the wait before it.
3. Press **Stop**, type a name, and press **Save**.

Your recording is saved as `scripts/virtual-unit/recordings/<name>.json`. It then appears in the scenario list as `rec:<name>`, and you can play it like any other. A recording keeps taps, swipes and tool calls. It does not keep camera moves in the 3D view or changes to the power panel.

## Run them without the window

All scenarios also run in the test suite, where each one ends in a picture that is compared with a saved one (a "golden"). If you change a screen on purpose, the developer pages tell you how to save the new pictures: [Tools, scenarios and goldens](dev-tools-and-goldens.md).

## Troubleshooting

- **The list has no recordings.** Recordings are read when the playground starts. Restart it after saving a new one.
- **A recording plays a different screen.** The screen depends on the robot's firmware version. Record again after an update.

Back: [index](index.md).
