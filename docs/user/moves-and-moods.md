# How the robot reacts

## Reactions

| You do | The robot does |
|---|---|
| Pick it up | Looks surprised, then settles. |
| Shake it | Looks dizzy. |
| Tilt it | Tilts its head to match. |
| Pet its head | Looks happy and may purr. |

Petting uses the head strip. If you set `strip_mode = "control"`, the strip opens quick sliders instead.

![Four faces: surprised, dizzy, tilted and happy.](../images/reactions.svg)

## Tap the face

You touch the screen, not the head strip. Each tap has its own screen so you always know what you did. Details: [Mute, camera off and full quiet](mute-and-camera-off.md).

| Tap | What happens |
|---|---|
| The mouth | Mutes or unmutes the robot. |
| The eyes | Turns the camera off, or back on. |
| Above and between the eyes | Full quiet: no moving, no talking and no listening. Tap again to wake it. |

The screen shows a calm icon for each state, not an X on the eyes.

![The three face tap zones marked on the robot's face.](../images/tap-zones.svg)

## How you hold it

The robot knows which way up it is. Upright is normal. On its side it looks curious. Face down or on its back it looks sleepy.
Upside down, the screen turns 180 degrees so you can still read it. Motor power never changes, so it is safe to turn it over.

## Head pats and shakes

A slow stroke along the head makes it happy, with a small heart. The heart is rare, so it means something.
A shake gets a spoken line and a dizzy face.

## Idle life

When nothing is happening the robot breathes, blinks and looks around. When it speaks, its head wobbles a little with the words.
Turn the idle moves off with `idle_motion = false`.

## Quiet mode

Say "quiet". The robot moves slowly and gently, speaks softly and keeps its lights low. Say "normal" to end it.

## Privacy sleep

Say "sleep" or press the privacy button. The robot turns away, the screen goes dark and the microphone and camera stop.
Touch it to wake it.

## Wake cue

A short light and tone confirm it heard the wake word. Set the light and tone for each state in `cues`.
The camera-on cue is the one cue you cannot turn off.

## Low battery

| Battery | What happens |
|---|---|
| 20 percent | A chirp. |
| 10 percent | It asks you out loud to plug it in. |
| 5 percent | It goes to sleep before the power runs out. |

![The low-battery icon at 10 percent.](../images/low-battery.svg)

## Lights and sounds

| What you see | What you hear | When |
|---|---|---|
| Amber ring, one short pulse every 10 seconds, and a tired face | A chirp at 20 percent. A spoken request to plug in at 10 percent | The battery is low and the charger is out. The screen says "Battery low" |
| No ring. A small red light at the back | Two quick rising notes | You plugged in the charger. The red light stays on while it charges and goes off when it is full |
| No ring | Three rising notes | The battery is full and the cable is still in |
| No ring | One falling note | You pulled the cable out |
| No ring, a surprised or dizzy face | A short spoken line, not at night | You picked it up, shook it or turned it over |
| No ring, the sleeping face | Three slow falling notes | You pressed the power key to turn it off |

See [Lights and sounds](lights-and-sounds.md) for every light and tone.

## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us what you saw.
