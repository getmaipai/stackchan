# Watch your room and get alerts

<span class="planned-tag">Planned</span>

Turn the robot into a watch post. It notices motion and loud sounds, tells you right away, and, if you want, flashes red and blue and sounds a siren.
Most of this works with your own LLM. MaiPai Home adds more, and it is marked where it does.

## Arm it

Say "arm watch", or press **Watch** in the web app. The robot counts down for 30 seconds so you can leave the room, then it starts watching.
To stop, say "disarm", press **Watch** again, or tap the robot's face.

While the robot is watching, the screen always shows a camera icon and the word **Watching**, and a microphone icon if it is listening for sounds. You cannot turn those cues off.
Mute and camera off still work: if you turn the camera off, motion watching stops, and if you mute the robot, sound watching stops.

![The robot face with a camera icon, a microphone icon and the word Watching.](../images/watching.svg)

## What it notices

| It notices | How | Needs |
|---|---|---|
| **Motion** | The host compares snapshots from the camera and sees something move | The camera on |
| **A loud sound** | The robot measures the loudness of the room. Nothing is recorded or sent unless an alert fires | Sound watching on |
| **The robot being moved or lifted** | Its motion sensor feels it | Nothing extra |
| **A person** <span class="home-tag">Needs MaiPai Home</span> | MaiPai Home tells a person from a pet or a curtain, and can say who it is | MaiPai Home |

You set how sensitive each one is, and you can draw an area on the picture to ignore, such as a window with trees outside.

## What happens when it triggers

You pick one of three responses for each watch:

1. **Quiet alert.** The robot tells you and saves a snapshot. It makes no noise.
2. **Warning.** It says "You are being recorded. Please leave", flashes its lights and shows an alert on its screen.
3. **Alarm.** Everything in the warning, plus a loud siren.

In a warning or an alarm, the light bars swap between red and blue, twice a second, the screen flashes the same red and blue and shows a big **ALERT**, and the siren, if you chose it, rises and falls.
We keep the swap slow, under three flashes a second, so it is safer for people who are sensitive to flashing lights. It stops by itself after one minute, or when you disarm it.

![The robot screen in alert mode, red and blue with a large ALERT.](../images/alert-screen.svg)

Red and blue are used only in alert mode, so you never see them for anything else.

## Where alerts go

| | With your own LLM | With MaiPai Home <span class="home-tag">Needs MaiPai Home</span> |
|---|---|---|
| A notice in the web app, with the snapshot | Yes | Yes |
| The local API, the event stream, MQTT and a home-automation bridge | Yes | Yes |
| An alert on your phone | Through the web app, over your Tailscale network | Through MaiPai Home, to the people you choose |
| What it saw, in words ("a person at the door") | No | Yes |
| Who it saw | A name from your local list, if you enrolled one | Yes |
| Quiet hours and who gets which alert | No | Yes |

The alert is a short message with a time, what it noticed and the snapshot. The video and the sound stay on your host.

## Keep false alarms down

- Start with **Quiet alert** for a day to see what it notices.
- Draw the areas to ignore, and set sensitivity lower in a room with a fan or a window.
- The robot ignores its own voice, its own moves and its own siren.
- A short pause between alerts keeps one visitor from sending you ten messages.

## Use it fairly

Watching a room records people. Tell the people who live there, and do not point the robot at a neighbour's home or anywhere people expect privacy. The rules about recording differ by place, and you are responsible for following them.
The robot always shows when it is watching, and it is not a replacement for a real alarm system or a smoke alarm.

## Lights and sounds

While armed, the screen shows the camera icon and **Watching**. In an alert, the light bars swap red and blue and a siren plays. See [Lights and sounds](lights-and-sounds.md).

## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us what you saw.
