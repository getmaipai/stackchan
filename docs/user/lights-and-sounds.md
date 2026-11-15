# Lights and sounds

The robot has two light bars, one on each side of the base, with six lights each, and a set of soft bell tones. The light bars are off most of the time. They light only when something needs you right now, and each colour has one meaning.
The screen's face shows moods. The light bars never do.

## The light bars

| Light | Colour and pattern | What it means | Sound with it |
|---|---|---|---|
| ![Green, steady](../images/light-green.svg) | **Green**, steady | Your voice is being sent to your host or hub | None |
| ![Pink, two flashes then steady](../images/light-pink.svg) | **Pink**, two quick flashes, then steady | The camera is taking a picture. For live view <span class="planned-tag">Planned</span>, it stays steady pink the whole time, with a LIVE dot on the screen | A short double click |
| ![Cyan, slow pulse](../images/light-cyan.svg) | **Cyan**, a slow pulse every 2 seconds | The robot needs you: Wi-Fi setup, waiting to be paired, or a timer ringing | Two rising notes for setup. The notification tone for a timer |
| ![Amber, one short pulse](../images/light-amber.svg) | **Amber**, one short pulse every 10 seconds | Look at the screen: offline, a fault, or low battery | Two falling notes when it goes offline. A chirp for low battery |
| ![Blue, steady](../images/light-blue.svg) | **Blue**, steady | It is your turn to talk | A short rising pop |
| ![White, fast pulse](../images/light-white.svg) | **White**, a fast pulse every second | Updating. Do not unplug | None |
| ![Red and blue swapping sides](../images/light-alert.svg) | **Red and blue**, swapping sides twice a second | Security alert <span class="planned-tag">Planned</span>. The screen flashes the same colours | The siren, if you chose the alarm |
| ![All off](../images/light-dark.svg) | **Dark** | Everything else: idle, thinking, speaking, asleep | None |
| ![One small red light at the back](../images/light-charging.svg) | **Red light at the back** | Charging. It is a separate light from the charger and the light bars do not repeat it | Two quick rising notes when you plug in |
| ![Colour walking along the light bars](../images/light-rainbow.svg) | **Rainbow**, one turn every 2 seconds | The dance light show | A rising chime when the dance starts |
| ![Pulsing in time, colour stepping](../images/light-beat.svg) | **Pulsing**, the colour steps on each beat | The dance light show on a beat | None |

Both bars show the same colour at the same time. The dance light show is the one exception, because the colour walks along one bar and up the other.

Red and blue are used only for a security alert.

Green and pink never dim, even at night or in the quietest setting, because they tell you about your privacy. The other colours get softer at night.
While the robot charges, a small red light at the back is on. It is a separate light from the charger, and the light bars do not repeat it.

## The tones

All tones are soft bells. A rising tone is good news and a falling tone is bad news.

| Tone | Name | Sounds like | When |
|---|---|---|---|
| ![](../images/tone-needs-you.svg) | Needs you | Two rising notes, insistent | Wi-Fi setup or pairing is waiting |
| ![](../images/tone-plug-in.svg) | Plug in | Two quick rising notes | You plugged in the charger |
| ![](../images/tone-charged.svg) | Charged | Three rising notes | The battery is full and the cable is in |
| ![](../images/tone-unplug.svg) | Unplug | One falling note | You pulled the cable out |
| ![](../images/tone-offline.svg) | Offline | Two falling notes | The link to your host or hub dropped, once for each outage |
| ![](../images/tone-goodbye.svg) | Goodbye | Three slow falling notes | You turned the robot off with the power key |
| ![](../images/tone-shutter.svg) | Shutter | A short double click | The camera took a picture |
| ![](../images/tone-back-online.svg) | Back online | A rising chime | The robot connected, or an update finished |
| ![](../images/tone-listening.svg) | Listening | A short rising pop | The wake word or a tap opened your turn |
| ![](../images/tone-low-battery.svg) | Low battery | A chirp | The battery reached 20 percent |
| ![](../images/tone-siren.svg) | Siren <span class="planned-tag">Planned</span> | A loud siren that rises and falls | A security alert, if you chose the alarm |
| ![](../images/tone-error.svg) | Error | A low, short tone | Something you asked for failed |

The robot chimes only for something you need to notice or something you just did. It never chimes for something it chose to do by itself.

## At night

At night and in quiet hours the tones go silent, except three: the first-setup tone, the shutter click and the goodbye tone. Those matter for safety or privacy.
Timers and alarms you set still ring. Every tone follows the volume setting, and mute silences all of them except the privacy click.

## Where each light and tone is explained

- [Talk to the robot](voice.md), [Use the camera](camera.md), [Set a timer or alarm](timers-and-alarms.md)
- [How the robot reacts](moves-and-moods.md), [Update the robot](updates.md), [Mute, camera off and full quiet](mute-and-camera-off.md)
- [Getting started](getting-started.md), [Take the robot on the go](use-it-anywhere.md), [Music and dance](music-and-dance.md)

## Still need help?

If a light or tone does not match this page, run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us the colour, the pattern and what you were doing.
