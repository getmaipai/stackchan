# Change how the robot looks

You can change every item here at any time. None of it needs a reflash.

## Face style

Eight styles ship: **big eyes**, **minimal**, **round**, **cat**, **robot**, **sleepy**, **retro pixel** and **heart eyes**. Pick one in the settings page on your host or set `face_style` in `robot.toml`.
The page shows a live preview that uses the same drawing code as the robot.

![The big-eyes face and the minimal face side by side.](../images/face-styles.svg)

## Smoother eyes and mouth

The eyes ease from place to place, blink smoothly and drift while the robot is idle, and the mouth follows how loud the robot speaks. Measured on a robot: 22 to 45 frames a second while the eyes move (best 49), and 4 to 11 while it speaks (best 21). It reaches 30 frames a second only while something keeps moving, and a fade between looks runs at about 20. Not yet seen on a robot screen.

## Extras on the face

The robot can add a small drawn extra for a few seconds: sweat, shy, dizzy, heart, anger, tears, sparkles, stars or zzz. One shows at a time. None shows while it is muted, has the camera off, is in quiet mode or a timer is ringing. Not yet seen on a robot screen.

## Word reactions

When you say a word such as "hello", "thanks", "love", "sorry" or "good night", the robot answers with a face, a quiet sound and an extra. 33 reactions come built in, in English, Spanish, French, German, Portuguese and Italian. Edit the list on the settings page, up to 40 rows. It reacts to a phrase at most once every 20 seconds. Not yet seen on a robot screen.

## Per person

On the settings page, keep a name, face colour and caption size for up to 12 people, and press **Use on this unit** to apply one. A saved wake phrase per person is stored but not matched yet.

## Your own pictures as the face

On the settings page, pick a style and one of your own pictures for each look: neutral, happy, sad, angry, doubtful, sleepy and speaking. Press **Send to the unit**.

- **Picture only** shows the picture.
- **Picture with eyes and mouth drawn on top** adds eyes that blink and drift and a mouth that follows the robot's voice. You set where the eyes and mouth go. Use a picture without eyes and a mouth for this style.
- **A short run of frames** plays up to 6 pictures in a loop for each look, at 1 to 12 frames a second.

The robot keeps up to 14 pictures, 1,000,000 bytes after they are made smaller. If your pictures do not fit, the page says so in plain words before it sends anything: use fewer or simpler pictures. A look with no picture shows the neutral one. While the robot speaks it shows the speaking picture.

Your pictures stay on your computer and go only to your robot, over your own network. Nothing is shipped with the product and nothing is uploaded anywhere else. The mute look, the camera-off look, quiet mode, the clock and a ringing timer always show instead of a picture. The robot keeps at most 3 pictures ready at a time. It keeps them in memory, so your host sends them again after a restart. Not yet seen on a robot screen. The upload has no size limit yet, so a very large photo can use a lot of your host's memory: shrink big photos first.

## Face colour

Set `face_color` to none, a named colour or a custom colour. The default is neutral, with no colour until you pick one.
Colour never carries meaning alone. Every state also has a shape or an icon, so the robot reads well if you cannot tell colours apart.

![The same face in three colours.](../images/face-colors.svg)

## Captions

Captions show the spoken words on the screen. They are off by default. Turn them on with `captions = true`, or in the settings page on your host.
The screen is small, so long answers are spoken, not shown in full on the robot.

## Clock face

The clock shows big digits or a ring. It dims at night. It keeps working if the host is off, once the host has set the time.

![The clock face with big digits, then dimmed in night mode.](../images/clock-face.svg)

## Expressions

The face shows what the robot is doing. It has a listening face and a thinking face, a happy, joyful, content and wink face, and a surprised face.
It has an offline look for when it cannot reach your host, and a link screen while it pairs.

## Time zone

Pick your time zone from 31 zones, with summer time, on the robot (swipe up, More, Time zone) or on the settings page. The host sets the clock when the robot connects, and the clock face keeps it.

## Night mode

Night mode dims the screen and the lights and softens the clock. Set it by hand, say "night mode", or set `quiet_from` and `quiet_to` so it starts by itself.

## Thinking cue

While the robot thinks, animated dots show on every face, with a quiet tone. Set `thinking_cue` to change the tone.

## Quick sliders

Slide your finger along the head strip to open a small overlay. It shows volume and brightness. Add more with `quick_sliders`.
If you prefer petting on the strip, leave `strip_mode` at `petting`. Set it to `control` to use the sliders.

![The slider overlay for volume on the robot screen.](../images/quick-sliders.svg)

## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us what you saw.
