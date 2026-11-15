# Compare MaiPai for StackChan

You can run the robot's factory firmware, MaiPai for StackChan on its own, or MaiPai for StackChan with MaiPai Home. This page shows what each gives you.
We checked the factory column against M5Stack's [official project README](https://github.com/m5stack/StackChan) on 2026-11-15. For anything it does not say, see the [official docs](https://docs.m5stack.com/en/StackChan).

The robot stays the same. MaiPai for StackChan changes the firmware and adds a host program. The hardware is the same: the same controller, servos, screen, camera and battery.

| | Factory firmware | MaiPai for StackChan | With MaiPai Home |
|---|---|---|---|
| **What you need** | A robot. See the official docs for the rest | The host and a local LLM you run | The host and a MaiPai Home hub |
| **AI agent** | Yes, as the official docs describe | Yes, using your local LLM | Yes, using Home's models |
| **Where the AI runs** | See the official docs | Your own computer | Your MaiPai Home hub |
| **Privacy: where your voice goes** | See the official docs | Only to your own computer | Only to your hub |
| **Vendor account or cloud** | See the official docs | None | None |
| **Security: who can control it** | See the official docs | Pairing with a code you type, revocable tokens, a token on every API, no router ports. [Details](security.md) | Same |
| **Security: the link** | See the official docs | Encrypted over Tailscale. Plain on a home network without it | Same |
| **Speed** | Not measured here. See the official docs | Wake cue under 150 ms. "Stop" and touch under 300 ms with no model. Replies start on the first finished sentence | Same, and the first word arrives sooner because Home keeps its models loaded on one machine built for them |
| **Model size** | See the official docs | What your host can run. A 4B class model answers in under 400 ms warm, and a 27B class model on a weak host does not | Bigger models on a machine built for them |
| **Memory across days** | Not listed in the official README | No | Yes |
| **Knows each person** | Not listed in the official README | A local name list for the camera only | Yes, by voice and by name |
| **Calendars, briefings, announcements** | Not listed in the official README | No | Yes |
| **Rules for children and teens** | Not listed in the official README | No | Yes |
| **Content filter** | See the official docs | None. Your model decides | Home's household rules apply |
| **Animated face** | Yes | Yes, two styles, any colour or none, and captions | Same |
| **Timers and alarms with a ring** | Not listed in the official README | Yes | Yes |
| **Camera features** | Not listed in the official README | Opt-in snapshots, "what is this", face follow, a local name list | Same |
| **Games and a pet mood** | Not listed in the official README | Colour memory, an action game, a mood that depends on care | Same |
| **Coding companion** | Not listed in the official README | Build light and agent status | Same |
| **Local API, MQTT, metrics** | Not listed in the official README | Yes, off by default | Same |
| **On the go (phone hotspot, any Wi-Fi)** | See the official docs | Yes, over your Tailscale network | Yes, and it reaches your hub over Tailscale |
| **English and Spanish** | See the official docs | Yes, switched at run time | Same |
| **Signed updates** | See the official docs | Checked, never installed unless you say so, signed, with rollback | Same |
| **Mobile app for video and remote avatar control** | Yes | No. We have no phone app | No |
| **Online app downloads** | Yes | No | No |
| **ESP-NOW remote controller** | Yes | Not supported yet | Not supported yet |

If you rely on the mobile app or the remote controller, stay on the factory firmware for now.

Switch between the last two columns with one line, `brain = "standalone"` or `brain = "home"`. The robot is not reflashed. See [Use MaiPai Home as the brain](with-maipai-home.md).

## Still need help?

Read [Getting started](getting-started.md), or open an issue on the Issues tab and tell us what you are trying to do.
