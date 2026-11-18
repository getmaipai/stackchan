# Lights and sounds

The robot has two light bars, one on each side of the base, with six lights each, and a set of soft bell tones. The light bars are off most of the time. They light only when something needs you right now, and each color has one meaning.
The screen's face shows moods. The light bars never do.

## The light bars

| Light | Color and pattern | What it means | Sound with it |
|---|---|---|---|
| ![Green, steady](../images/light-green.svg) | **Green**, steady | Your voice is being sent to your host or hub | None |
| ![Pink, two flashes then steady](../images/light-pink.svg) | **Pink**, two quick flashes, then steady | The camera is taking a picture. For live view, it stays steady pink the whole time, with a LIVE dot on the screen | A short double click |
| ![Cyan, slow pulse](../images/light-cyan.svg) | **Cyan**, a slow pulse every 2 seconds | The robot needs you: Wi-Fi setup, waiting to be paired, or a timer ringing | Two rising notes for setup. The notification tone for a timer |
| ![Amber, one short pulse](../images/light-amber.svg) | **Amber**, one short pulse every 10 seconds | Look at the screen: offline, a fault, or low battery | Two falling notes when it goes offline. A chirp for low battery |
| ![Blue, steady](../images/light-blue.svg) | **Blue**, steady | It is your turn to talk | A short rising pop |
| ![White, fast pulse](../images/light-white.svg) | **White**, a fast pulse every second | Updating. Do not unplug | None |
| ![Dim amber, steady](../images/light-amber.svg) | **Dim amber**, steady, by day only | Watch or monitor mode is on. At night the light bars stay off and the screen carries the cue | None |
| ![Red and blue swapping sides](../images/light-alert.svg) | **Red and blue**, swapping sides twice a second | Security alert. The screen flashes the same colors | The siren, if you chose the alarm |
| ![All off](../images/light-dark.svg) | **Dark** | Everything else: idle, thinking, speaking, asleep | None |
| ![One small red light at the back](../images/light-charging.svg) | **Red light at the back** | Charging. It is a separate light from the charger and the light bars do not repeat it | Two quick rising notes when you plug in |

Both bars show the same color at the same time.

Red and blue are used only for a security alert.

Pink never dims, even at night or in the quietest setting, because it tells you about your privacy. The other colors get softer at night. The listening light is your choice on the settings page: off, dim or normal, and its color. It is off in full quiet.
While the robot charges, a small red light at the back is on. It is a separate light from the charger, and the light bars do not repeat it.

## The tones

All tones are soft bells. A rising tone is good news and a falling tone is bad news.

| Tone | Name | Sounds like | When |
|---|---|---|---|
| ![The needs you tone, drawn as a sound wave](../images/tone-needs-you.svg) | Needs you | Two rising notes, insistent | Wi-Fi setup or pairing is waiting |
| ![The plug in tone, drawn as a sound wave](../images/tone-plug-in.svg) | Plug in | Two quick rising notes | You plugged in the charger |
| ![The charged tone, drawn as a sound wave](../images/tone-charged.svg) | Charged | Three rising notes | The battery is full and the cable is in |
| ![The unplug tone, drawn as a sound wave](../images/tone-unplug.svg) | Unplug | One falling note | You pulled the cable out |
| ![The offline tone, drawn as a sound wave](../images/tone-offline.svg) | Offline | Two falling notes | The link to your host or hub dropped, once for each outage |
| ![The goodbye tone, drawn as a sound wave](../images/tone-goodbye.svg) | Goodbye | Three slow falling notes | You turned the robot off with the power key |
| ![The shutter tone, drawn as a sound wave](../images/tone-shutter.svg) | Shutter | A short double click | The camera took a picture |
| ![The back online tone, drawn as a sound wave](../images/tone-back-online.svg) | Back online | A rising chime | The robot connected, or an update finished |
| ![The listening tone, drawn as a sound wave](../images/tone-listening.svg) | Listening | A short rising pop | The wake word or a tap opened your turn |
| ![The low battery tone, drawn as a sound wave](../images/tone-low-battery.svg) | Low battery | A chirp | The battery reached 20 percent |
| ![The siren tone, drawn as a sound wave](../images/tone-siren.svg) | Siren | A loud siren that rises and falls | A security alert, if you chose the alarm |
| ![The error tone, drawn as a sound wave](../images/tone-error.svg) | Error | A low, short tone | Something you asked for failed |

The robot chimes only for something you need to notice or something you just did. It never chimes for something it chose to do by itself.

## At night

At night and in quiet hours the tones go silent, except three: the first-setup tone, the shutter click and the goodbye tone. Those matter for safety or privacy.
Timers and alarms you set still ring. Every tone follows the volume setting, and mute silences all of them except the privacy click.

## Where each light and tone is explained

- [Talk to the robot](voice.md), [Use the camera](camera.md), [Set a timer or alarm](timers-and-alarms.md)
- [How the robot reacts](moves-and-moods.md), [Update the robot](updates.md), [Mute, camera off and full quiet](mute-and-camera-off.md)
- [Getting started](getting-started.md), 

## Still need help?

If a light or tone does not match this page, run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us the color, the pattern and what you were doing.
