# Music and dance

The robot dances on request, and it can sway to music. It listens through its own microphone and keeps nothing.

Not yet heard or seen on a robot: real music, the mood faces and the dances. The test robot was muted.

## Ask it to dance

Say the wake word, then "dance". Name one to pick it: **sway**, **nod yes**, **shake no**, **wiggle**, **bow** or **groove**. Each is a short routine of 8 seconds or less that ends with the head centered. Say "stop" any time and it stops where it is.

![The robot mid-dance with a happy face and its head tilted.](../images/dance.svg)

*The robot mid-dance with a happy face and its head tilted. A placeholder drawing, not a real screenshot.*

## It sways to your music

Turn on **Dance to music** (built and flashed, not yet checked with a real song) on the Behavior page of the settings page on your host. It is off by default. The page shows a status line: off, waiting for the unit, listening, dancing, paused (muted or quiet) or the unit needs an update.
The unit measures sound levels and tempo only. No audio is kept or sent.
When music plays near the robot, it finds the beat and dances to it in steps: eyes only first, then a head nod, then side to side, then every direction with a disco ball and confetti, and back down again in reverse. Its face changes every 8 or 16 beats among happy, serene, laughing, love, surprised, wink, silly and excited. Music notes float by and the side lights follow how strong the music is.

- It will not dance to speech, and it pauses when the music pauses.
- It does nothing while the robot is muted or in full quiet.
- With several robots on one host, each robot listens and dances on its own, and muting one silences only that one.
- It moves only as much as the movement limits below allow.
- Away from your hub, the robot still sways on its own.

![The settings page on the host with Dance to music switched on.](../images/dance-settings.svg)

*The settings page on the host with Dance to music switched on. A placeholder drawing, not a real screenshot.*

## What song is this

<span class="home-tag">Needs MaiPai Home</span>

Say "what song is this" while music plays. The robot sends a short clip to your MaiPai Home hub, which names the song and the artist, and the robot says it out loud.
Without MaiPai Home, this feature is hidden. See [Use MaiPai Home as the brain](with-maipai-home.md).

## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us what you saw.
