# Compare MaiPai for StackChan

You can run the robot's factory firmware, MaiPai for StackChan on its own, or MaiPai for StackChan with MaiPai Home. This page rates each at a glance.

The robot stays the same. MaiPai for StackChan changes the firmware and adds a host program. The hardware is the same: the same controller, servos, screen, camera and battery.

**How to read the ratings:** ★★★ best, ★★☆ better, ★☆☆ basic, ☆☆☆ not available, TBD not rated yet.
The ratings are ours. We rate the factory firmware only where M5Stack's [official project README](https://github.com/m5stack/StackChan) says it has a feature (checked 2026-11-15).
TBD means the README is silent or we have not tested it. See the [official docs](https://docs.m5stack.com/en/StackChan) for those. Our own stars come from the design and will change as we measure.

| | Factory firmware | MaiPai for StackChan | With MaiPai Home | Why it matters |
|---|:---:|:---:|:---:|---|
| AI agent | ★★★ | ★★★ | ★★★ | Talk to it and it answers. Ours uses a model you choose. |
| Privacy: your voice stays in your home | ★☆☆ | ★★☆ | ★★☆ | Built so your voice and habits never leave your home. We have not yet proved it with a network capture, so we give two stars until we publish one. The official server README lists a backend service with a XiaoZhi integration. You can self-host it, but that is extra work. |
| Security: who can control the robot | TBD | ★★☆ | ★★☆ | Nobody else can take over your robot. A code you type pairs it, and you can revoke access any time. |
| Security: the link | TBD | ★★☆ | ★★☆ | Encrypted over Tailscale. On plain home Wi-Fi it is not yet, so we give two stars. |
| Speed of replies | TBD | ★★☆ | ★★★ | Wake cue under 150 ms, stop under 300 ms, and the reply starts on the first sentence. Home is faster again. |
| Model size and answer quality | TBD | ★★☆ | ★★★ | Bigger models give better answers. A hub runs them. |
| Memory across days | TBD | ☆☆☆ | ★★★ | It remembers what you told it yesterday. |
| Knows each person | TBD | ★☆☆ | ★★★ | It knows who is talking, by voice and by name. |
| Calendars, briefings, announcements | TBD | ☆☆☆ | ★★★ | Ask about your day and hear household announcements. |
| Rules for children and teens | TBD | ☆☆☆ | ★★★ | Kids get answers that fit the rules you set. |
| Animated face | ★★☆ | ★★★ | ★★★ | The official README lists lively, expressive animations. Ours lets you choose between two styles, any colour or none, and captions, and it adds a clock face and night mode. |
| Timers and alarms | TBD | ★★★ | ★★★ | A ring empties as time runs out, so you can read it across the room. |
| Camera features | TBD | ★★★ | ★★★ | Ask "what is this" or have it follow you. Frames stay on your host. |
| Games and a pet mood | TBD | ★★★ | ★★★ | Something to do together. The pet mood grows with care. |
| Coding companion | TBD | ★★★ | ★★★ | A green or red light for your build, where you can see it. |
| Local API, MQTT, metrics | TBD | ★★★ | ★★★ | Wire the robot into your own tools. |
| On the go (phone hotspot, any Wi-Fi) | TBD | ★★★ | ★★★ | Join your phone's hotspot and take it to a friend's house. |
| English and Spanish | TBD | ★★★ | ★★★ | Switch language at run time with no reflash. |
| Signed updates with rollback | TBD | ★★★ | ★★★ | Nothing installs unless you say so, and a bad update rolls back by itself. |
| Control from your phone (app or web app) | ★★★ | ★★☆ | ★★☆ | The factory app does live video and remote avatar control. We have no phone app. Our web app, served by your host, opens in any phone browser and controls settings, faces, timers and snapshots. It has no live video or remote avatar control. If you rely on those, stay on factory. |
| Online app downloads | ★★★ | ☆☆☆ | ☆☆☆ | Removed on purpose. The on-device app system took about 548 KB of flash and 24 KB of the robot's scarce working memory, and we used that room for the voice agent and the features above. |
| ESP-NOW remote controller | ★★★ | ☆☆☆ | ☆☆☆ | Not supported yet. Pose mirroring between two robots is planned. If you rely on the remote, stay on factory. |
| Bluetooth | TBD | ☆☆☆ | ☆☆☆ | Turned off on purpose to free memory. Presence comes from your network and the camera instead. |
| Chinese, Japanese and Korean text, and emoji | TBD | ★☆☆ | ★☆☆ | Removed from the default image to save space for more features. An optional font pack adds the text back. |

## Why some things are missing

The robot has about 76 KB of free working memory, so every feature has to earn its place. We removed the on-device app system and Bluetooth to make room for the voice agent, the camera, timers and games.
We chose a web app served by your host over a native phone app. We would rather say what is gone than hide it.

## What the stars mean for you

- **Privacy and security:** both MaiPai columns are built to keep your voice in your home, and we will publish a network capture that shows it before release. The link is encrypted over Tailscale and plain on a home network without it, so we rate it two stars until the encrypted home link ships. [Keep the robot secure](security.md).
- **Speed and answer quality:** a MaiPai Home hub keeps its models loaded on one machine built for them, so the first word arrives sooner and it can run bigger models. A 4B class model answers in under 400 ms warm, and a 27B class model on a weak host does not. These are targets until the benchmark is run.
- **What you give up:** a phone app (our web app covers settings and snapshots, not live video or remote avatar control), online app downloads, Bluetooth, and the official ESP-NOW remote controller. If you rely on those, stay on the factory firmware for now.
- **Memory, people, calendars and rules** come only with MaiPai Home.

Switch between the last two columns with one line, `brain = "standalone"` or `brain = "home"`. The robot is not reflashed. See [Use MaiPai Home as the brain](with-maipai-home.md).

## Still need help?

Read [Getting started](getting-started.md), or open an issue on the Issues tab and tell us what you are trying to do.
