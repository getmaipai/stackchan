# Compare MaiPai for StackChan

You can run the robot's factory firmware, MaiPai for StackChan on its own, or MaiPai for StackChan with MaiPai Home. This page rates each at a glance.

The robot stays the same. MaiPai for StackChan changes the firmware and adds a host program. The hardware is the same: the same controller, servos, screen, camera and battery.

**How to read the ratings:** ★★★ best, ★★☆ better, ★☆☆ basic, ☆☆☆ not available, ? not rated yet.
The ratings are ours. We rate the factory firmware only where M5Stack's [official project README](https://github.com/m5stack/StackChan) says it has a feature (checked 2026-11-15).
A ? means the README is silent or we have not tested it. See the [official docs](https://docs.m5stack.com/en/StackChan) for those. Our own stars come from the design and will change as we measure.

| | Factory firmware | MaiPai for StackChan | With MaiPai Home |
|---|:---:|:---:|:---:|
| AI agent | ★★★ | ★★★ | ★★★ |
| Privacy: your voice stays in your home | ? | ★★★ | ★★★ |
| Security: who can control the robot | ? | ★★☆ | ★★☆ |
| Security: the link (encrypted over Tailscale) | ? | ★★☆ | ★★☆ |
| Speed of replies | ? | ★★☆ | ★★★ |
| Model size and answer quality | ? | ★★☆ | ★★★ |
| Memory across days | ? | ☆☆☆ | ★★★ |
| Knows each person | ? | ★☆☆ | ★★★ |
| Calendars, briefings, announcements | ? | ☆☆☆ | ★★★ |
| Rules for children and teens | ? | ☆☆☆ | ★★★ |
| Animated face | ★★★ | ★★★ | ★★★ |
| Timers and alarms | ? | ★★★ | ★★★ |
| Camera features | ? | ★★★ | ★★★ |
| Games and a pet mood | ? | ★★★ | ★★★ |
| Coding companion | ? | ★★★ | ★★★ |
| Local API, MQTT, metrics | ? | ★★★ | ★★★ |
| On the go (phone hotspot, any Wi-Fi) | ? | ★★★ | ★★★ |
| English and Spanish | ? | ★★★ | ★★★ |
| Signed updates with rollback | ? | ★★★ | ★★★ |
| Mobile app for video and remote avatar control | ★★★ | ☆☆☆ | ☆☆☆ |
| Online app downloads | ★★★ | ☆☆☆ | ☆☆☆ |
| ESP-NOW remote controller | ★★★ | ☆☆☆ | ☆☆☆ |

![The compare table with star ratings in three columns.](../images/compare-chart.svg)

## What the stars mean for you

- **Privacy and security:** both MaiPai columns keep your voice in your home. The link is encrypted over Tailscale and plain on a home network without it, so we rate it two stars until the encrypted home link ships. [Keep the robot secure](security.md).
- **Speed and answer quality:** a MaiPai Home hub keeps its models loaded on one machine built for them, so the first word arrives sooner and it can run bigger models. A 4B class model answers in under 400 ms warm, and a 27B class model on a weak host does not. These are targets until the benchmark is run.
- **What you give up:** MaiPai for StackChan has no phone app, no online app downloads and no support for the official ESP-NOW remote controller yet. If you rely on those, stay on the factory firmware for now.
- **Memory, people, calendars and rules** come only with MaiPai Home.

Switch between the last two columns with one line, `brain = "standalone"` or `brain = "home"`. The robot is not reflashed. See [Use MaiPai Home as the brain](with-maipai-home.md).

## Still need help?

Read [Getting started](getting-started.md), or open an issue on the Issues tab and tell us what you are trying to do.
