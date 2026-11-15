# Face and look

You can change every item here at any time. None of it needs a reflash.

## Face style

Two styles ship: **big eyes** and **minimal**. Pick one in the web settings page or set `face_style` in `robot.toml`.
The page shows a live preview that uses the same drawing code as the robot.

> **Screenshot placeholder:** `face-styles.png`. The big-eyes face and the minimal face side by side.

## Face colour

Set `face_color` to none, a named colour or a custom colour. The default is neutral, with no colour until you pick one.
Colour never carries meaning alone. Every state also has a shape or an icon, so the robot reads well if you cannot tell colours apart.

> **Screenshot placeholder:** `face-colors.png`. The same face in three colours.

## Captions

Captions show the spoken words on the screen. They are off by default. Turn them on with `captions = true`, or in the web page.
The screen is small, so long answers are spoken and shown in the web app, not on the robot.

## Clock face

The clock shows big digits or a ring. It dims at night. It keeps working if the host is off, once the host has set the time.

> **Screenshot placeholder:** `clock-face.png`. The clock face with big digits, then dimmed in night mode.

## Night mode

Night mode dims the screen and the lights and softens the clock. Set it by hand, say "night mode", or set quiet hours so it starts by itself.

## Thinking cue

While the robot thinks, animated dots show on every face, with a quiet tone. Set `thinking_cue` to change the tone.

## Quick sliders

Slide your finger along the head strip to open a small overlay. It shows volume and brightness. Add more with `quick_sliders`.
If you prefer petting on the strip, leave `strip_mode` at `petting`. Set it to `control` to use the sliders.

> **Screenshot placeholder:** `quick-sliders.png`. The slider overlay for volume on the robot screen.
