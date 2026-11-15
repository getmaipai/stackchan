# Compare MaiPai for StackChan

You can run the robot's factory firmware, MaiPai for StackChan on its own, or MaiPai for StackChan with MaiPai Home. This page shows what each gives you.
We checked the factory column against M5Stack's [official project README](https://github.com/m5stack/StackChan) on 2026-11-15. For anything it does not say, see the [official docs](https://docs.m5stack.com/en/StackChan).

## The robot stays the same

MaiPai for StackChan changes the firmware and adds a host program. The robot is the same hardware: the same controller, servos, screen, camera and battery.

## Factory firmware or MaiPai for StackChan

| | Factory firmware | MaiPai for StackChan |
|---|---|---|
| AI agent | Yes, as the official docs describe | Yes, using a local LLM you run, or MaiPai Home |
| Where the AI runs | See the official docs | On your own computer or your MaiPai Home hub |
| Vendor account or cloud | See the official docs | None. The host calls only the addresses you list |
| Speed | Not measured here. See the official docs | Wake cue in under 150 ms. "Stop" and touch commands in under 300 ms with no model. Replies start on the first finished sentence |
| Animated face | Yes | Yes, with two styles, any colour or none, and captions |
| Timers and alarms with a ring | Not listed in the official README | Yes |
| Camera features | Not listed in the official README | Opt-in snapshots, "what is this", face follow, a local name list |
| Games and a pet mood | Not listed in the official README | Colour memory, an action game, a mood that depends on care |
| Coding companion | Not listed in the official README | Build light and agent status |
| Local API, MQTT, metrics | Not listed in the official README | Yes, off by default |
| Works from any Wi-Fi | See the official docs | Yes, over your Tailscale network |
| English and Spanish | See the official docs | Yes, switched at run time |
| Updates | See the official docs | Checked, never installed unless you say so, signed, with rollback |
| Mobile app for video and remote avatar control | Yes | No. We have no phone app |
| Online app downloads | Yes | No |
| ESP-NOW remote controller | Yes | Not supported yet |

If you rely on the mobile app or the remote controller, stay on the factory firmware for now.

## Standalone or MaiPai Home

Both run the same firmware. The difference is the brain behind the host.

| | Standalone | With MaiPai Home |
|---|---|---|
| What you need | The host and a local LLM you run | The host and a MaiPai Home hub |
| Speed of answers | Depends on your host. A 4B class model answers in under 400 ms warm, and a 27B class model on a weak host does not | Home keeps its models loaded on one machine built for them, so the first word arrives sooner |
| Memory across days | No | Yes |
| Knows each person by voice and name | Local name list for the camera only | Yes |
| Calendars, briefings, announcements | No | Yes |
| Rules for children and teens | No | Yes |
| Content filter | None. Your model decides | Home's household rules apply |
| Timers, faces, games, reactions | Yes | Yes |

Switch with one line, `brain = "home"` or `brain = "standalone"`. The robot is not reflashed. See [Use MaiPai Home as the brain](with-maipai-home.md).

## Still need help?

Read [Getting started](getting-started.md), or open an issue on the Issues tab and tell us what you are trying to do.
