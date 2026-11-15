# Use MaiPai Home as the brain

MaiPai Home is an optional brain. The robot is complete without it. Use it if you already run a MaiPai Home hub and want the robot to share the household's records.

## What it adds

MaiPai for StackChan on its own is a simple, private voice robot. These run with MaiPai Home:

- The camera: snapshots, face follow, the name list and "what is this". [Details](camera.md)
- Watch mode and security alerts, and the baby and pet monitor. [Watch](watch-and-alerts.md), [monitor](baby-and-pet-monitor.md)
- Find my robot, remote beep, lights, talk, pan and tilt, and live view. [Details](find-and-remote.md)
- Games and a pet mood, the coding companion, and home tools such as the local API and MQTT. [Games](games-and-pet.md), [coding](coding-companion.md), [tools](home-tools.md)

And the household features:


- Memory across days.
- "What is this": hold something up to the camera and hear what it is.
- Voices matched to each person.
- Calendars, briefings and household announcements.
- Household rules, including rules for children and teens.
- Song naming and other services that need more than one room.

With your own LLM, the robot does none of these by itself.

## What changes on the robot

When you connect MaiPai Home, Home puts the firmware build on the robot that has the extras. You do not choose a build. The core robot is a small build with no camera streaming, no monitor audio and no remote path, and the Home build adds the parts that Home's features need.

## Turn it on

1. Open `robot.toml`.
2. Set `brain = "home"` and `home_url` to the hub address, for example `http://192.0.2.20:3000`.
3. Run `stackchan check`. You'll know it worked when the check lists Home as the brain and every line says ok.

The robot is not reflashed. Set `brain = "llm"` to go back. Your timers, faces and settings stay.

![The web page with the brain choice set to MaiPai Home.](../images/brain-switch.svg)

## What Home needs

MaiPai Home runs on a Mac and lists its memory sizes and disk space on its own install page. Pick the plan that matches your Mac. A bigger Mac runs bigger models, so answers are faster and better. See [Pick hardware and a model](hardware-and-models.md).

## Away from home

If your hub is on your Tailscale network, the robot reaches it from any Wi-Fi. Use the hub's Tailscale address as `home_url`.
See [Use it anywhere](use-it-anywhere.md).

## What stays on the robot

Timers, faces, reactions and dance work the same either way. A feature that needs a service the brain lacks hides itself.

## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us what you saw.
