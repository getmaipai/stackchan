# Compare MaiPai for StackChan

You can run the robot's factory firmware, MaiPai for StackChan on its own, or MaiPai for StackChan with MaiPai Home. This page rates each at a glance.

The robot stays the same. MaiPai for StackChan changes the firmware and adds a host program. The hardware is the same: the same controller, servos, screen, camera and battery.

**How to read the ratings:** ★★★ best, ★★☆ better, ★☆☆ basic, ☆☆☆ not available, TBD not rated yet.
The ratings are ours. We rate the factory firmware only where M5Stack's [official project README](https://github.com/m5stack/StackChan) says it has a feature (checked 2026-11-15).
TBD means the README is silent or we have not tested it. See the [official docs](https://docs.m5stack.com/en/StackChan) for those. Our own stars come from the design and will change as we measure.

| | Factory firmware | MaiPai for StackChan | With MaiPai Home | Why it matters |
|---|:---:|:---:|:---:|---|
| AI agent | ★★★ | ★★★ | ★★★ | Talk to it and it answers. Ours uses a model you choose. |
| Privacy: your voice stays in your home | ★☆☆ | ★★☆ | ★★☆ | Built so your voice and habits never leave your home. We have not yet proved it with a network capture, so we give two stars until we publish one. The official docs say the factory AI agent is powered by XiaoZhi and set up through the StackChan World app with an account you bind. |
| Security: who can control the robot | TBD | ★★☆ | ★★☆ | Nobody else can take over your robot. A code you type pairs it, and you can revoke access any time. |
| Security: the link | TBD | ★★☆ | ★★☆ | Encrypted over Tailscale. On plain home Wi-Fi it is not yet, so we give two stars. |
| Speed of replies (depends on your model and hardware) | TBD | ★★☆ | ★★★ | Wake cue under 150 ms, stop under 300 ms, and the reply starts on the first sentence. Home is faster again. |
| Model size and answer quality (depends on your hardware) | TBD | ★★☆ | ★★★ | Bigger models give better answers. A hub runs them. |
| Memory across days <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ★★★ | It remembers what you told it yesterday. |
| Knows each person <span class="home-tag">Needs MaiPai Home</span> | TBD | ★☆☆ | ★★★ | It knows who is talking, by voice and by name. |
| Calendars, briefings, announcements <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ★★★ | Ask about your day and hear household announcements. |
| Rules for children and teens <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ★★★ | Kids get answers that fit the rules you set. |
| Animated face | ★★☆ | ★★★ | ★★★ | The official README lists lively, expressive animations. Ours lets you choose between two styles, any colour or none, and captions, and it adds a clock face and night mode. |
| Timers and alarms | TBD | ★★★ | ★★★ | A ring empties as time runs out, so you can read it across the room. |
| Camera: snapshots, face follow, name list <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ★★★ | Have it follow you, take your picture, or say who it sees. Frames stay on your host. Runs with MaiPai Home. |
| Camera: "what is this" <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ★★★ | Hold something up and hear what it is. Your hub does the looking. |
| Dances to your music by itself | TBD | ★★★ | ★★★ | It hears music, shows it likes it, and dances to the beat. Off until you turn it on. |
| Choreograph your own dance | ★★★ | ☆☆☆ | ☆☆☆ | The factory phone app lets you set music, movements and light colours for a dance. We do not have a dance editor. |
| Name the song <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ★★★ | Ask "what song is this" and hear the title and artist. |
| Announcements <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ★★★ | Hear household news out loud, like "dinner is ready". |
| Mute, camera off, full quiet | TBD | ★★★ | ★★★ | Three switches on the face: tap the mouth to mute, the eyes to stop the camera, between the eyes for full quiet. They survive a restart, and the host warns you if the robot leaks. [Details](mute-and-camera-off.md) |
| Spoken "stop" while it talks | TBD | ★★★ | ★★★ | It stops at once, with no model involved. |
| Updates over Wi-Fi | TBD | ★★★ | ★★★ | No cable. An animated icon shows the progress. |
| Games and a pet mood <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ★★★ | Something to do together. The pet mood grows with care. Runs with MaiPai Home. |
| Coding companion <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ★★★ | A green or red light for your build, where you can see it. Runs with MaiPai Home. |
| Local API, MQTT, metrics <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ★★★ | Wire the robot into your own tools. Runs with MaiPai Home. |
| On the go (phone hotspot, any Wi-Fi) | TBD | ★★★ | ★★★ | Join your phone's hotspot and take it to a friend's house. |
| English and Spanish | TBD | ★★★ | ★★★ | Switch language at run time with no reflash. |
| Signed updates with rollback | TBD | ★★★ | ★★★ | Nothing installs unless you say so, and a bad update rolls back by itself. |
| Baby and pet monitor <span class="planned-tag">Planned</span> <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ☆☆☆ | Hear and see a nursery or a pet's room from your phone and get alerts. You start it on the robot, and the screen always says so. Not a certified baby monitor. Runs with MaiPai Home. |
| No stealth: monitoring always shown on screen | TBD | ★★★ | ★★★ | Every listening, looking and watching mode shows on the robot's screen, and the cue cannot be turned off. |
| Watch mode: motion and sound alerts <span class="planned-tag">Planned</span> <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ☆☆☆ | The robot notices motion and loud sounds and sends an alert with a snapshot. Better with MaiPai Home, which can say what it saw and who. Runs with MaiPai Home. |
| Security alarm: red and blue lights, siren <span class="planned-tag">Planned</span> <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ☆☆☆ | A warning or an alarm with swapping lights, a siren and an alert on the screen. Runs with MaiPai Home. |
| Find my robot, beep and flash <span class="planned-tag">Planned</span> <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ☆☆☆ | Press Find to see where it was last seen, by place name, and make it beep and flash. No GPS chip. A map lookup from Wi-Fi is an opt-in that uses an outside service. Runs with MaiPai Home. |
| Remote beep, lights and talk <span class="planned-tag">Planned</span> <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ☆☆☆ | Make it beep, light up or speak from the web app. The robot always shows when someone is using it. Runs with MaiPai Home. |
| Remote pan and tilt <span class="planned-tag">Planned</span> <span class="home-tag">Needs MaiPai Home</span> | ★★★ | ☆☆☆ | ☆☆☆ | The factory app moves the head with a joystick. Ours is planned in the web app with a Home button and a safe tilt range. Runs with MaiPai Home. |
| Live camera view <span class="planned-tag">Planned</span> <span class="home-tag">Needs MaiPai Home</span> | ★★★ | ☆☆☆ | ☆☆☆ | The factory app has a monitoring camera mode with a joystick. Ours is planned as a low-resolution live view in the web app, with the pink lights and a LIVE dot always on while it runs. Runs with MaiPai Home. |
| Control from your phone (app or web app) | ★★★ | ★★☆ | ★★☆ | The factory app does live video and remote avatar control. We have no phone app. Our web app, served by your host, opens in any phone browser and controls settings, faces, timers and snapshots. Live view is planned. We have no remote avatar control. If you rely on those, stay on factory. |
| Online app downloads | ★★★ | ☆☆☆ | ☆☆☆ | Removed on purpose. The on-device app system took about 548 KB of flash and 24 KB of the robot's scarce working memory, and we used that room for the voice agent and the features above. |
| ESP-NOW remote controller | ★★★ | ☆☆☆ | ☆☆☆ | Not supported yet. Pose mirroring between two robots is planned. If you rely on the remote, stay on factory. |
| Bluetooth (phone setup and more) | ★★☆ | ☆☆☆ | ☆☆☆ | On the factory robot the phone app uses Bluetooth for its setup page. Ours is off today, and we are reviewing whether to bring it back for phone setup from a browser, a push-to-talk clicker and finding your robot. Until then you set up the robot with its own Wi-Fi setup page or over USB. |
| Chinese, Japanese and Korean text, and emoji | TBD | ★☆☆ | ★☆☆ | Removed from the default image to save space for more features. An optional font pack adds the text back. |

## Why some things are missing

The robot has about 76 KB of free working memory, so every feature has to earn its place. We removed the on-device app system to make room for the voice agent, the camera, timers and games. Bluetooth is off for a different reason: it was not needed and it is one more way in. It saved almost no memory, so we are reviewing whether to bring it back.
We chose a web app served by your host over a native phone app. We would rather say what is gone than hide it.

## What the stars mean for you

- **Privacy and security:** both MaiPai columns are built to keep your voice in your home, and we will publish a network capture that shows it before release. The link is encrypted over Tailscale and plain on a home network without it, so we rate it two stars until the encrypted home link ships. [Keep the robot secure](security.md).
- **Speed and answer quality:** a MaiPai Home hub keeps its models loaded on one machine built for them, so the first word arrives sooner and it can run bigger models. A 4B class model answers in under 400 ms warm, and a 27B class model on a weak host does not. These are targets until the benchmark is run.
- **What you give up:** a phone app (our web app covers settings and snapshots, and live view is planned, but there is no remote avatar control), setting up the robot from the phone over Bluetooth, online app downloads, and the official ESP-NOW remote controller. If you rely on those, stay on the factory firmware for now. You can [switch back](switch-from-the-factory-firmware.md) any time.
- **Memory, people, calendars and rules** come only with MaiPai Home.

Switch between the last two columns with one line, `brain = "llm"` or `brain = "home"`. The robot is not reflashed. See [Use MaiPai Home as the brain](with-maipai-home.md).

## Still need help?

Read [Getting started](getting-started.md), or open an issue on the Issues tab and tell us what you are trying to do.
