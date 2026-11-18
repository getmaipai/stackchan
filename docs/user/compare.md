# Compare MaiPai for StackChan

You can run the robot's factory firmware, MaiPai for StackChan on its own, or MaiPai for StackChan with MaiPai Home. This page rates each at a glance.

The robot stays the same. MaiPai for StackChan changes the firmware and adds a host program. The hardware is the same: the same controller, servos, screen, camera and battery.

**How to read the ratings:** ★★★ best, ★★☆ better, ★☆☆ basic, ☆☆☆ not available, TBD not rated yet.
The ratings are ours. We rate the factory firmware only where M5Stack's [official project README](https://github.com/m5stack/StackChan) says it has a feature (checked 2026-11-15).
TBD means the README is silent or we have not tested it. See the [official docs](https://docs.m5stack.com/en/StackChan) for those. Our own stars come from the design and will change as we measure.

| | Factory firmware | MaiPai for StackChan | With MaiPai Home | Why it matters |
|---|:---:|:---:|:---:|---|
| AI agent | ★★★ | ★★★ | ★★★ | Talk to it and it answers. Ours uses a model you choose. |
| Privacy: your conversations stay in your home | ★☆☆ | ★★☆ | ★★☆ | Built so your conversations and habits never leave your home. We have not yet proved it with a network capture, so we give two stars until we publish one. The official docs say the factory AI agent is powered by XiaoZhi and set up through the StackChan World app with an account you bind. |
| Security: who can control the robot | TBD | ★★☆ | ★★☆ | Nobody else can take over your robot. A code you type pairs it, and you can revoke access any time. |
| Away from home: reach your host from any Wi-Fi | TBD | ★★☆ | ★★☆ | The robot joins your private network by itself when it cannot reach your host, using a one-time key. Not yet checked with a real join. |
| Security: the link | TBD | ★★☆ | ★★☆ | On plain home Wi-Fi the link is not encrypted yet, so we give two stars. Away from home it travels over your private network. |
| Speed of replies (depends on your model and hardware) | TBD | ★★☆ | ★★☆ | Targets: wake cue under 150 ms and stop under 300 ms, not yet measured on a robot. The reply starts on the first sentence. The speed of the answer depends on your model and hardware, with or without MaiPai Home. |
| Model size and answer quality (depends on your hardware) | TBD | ★★☆ | ★★☆ | Bigger models give better answers. You can run any size your hardware allows, with or without MaiPai Home. |
| Memory across days <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ★★★ | It remembers what you told it yesterday. |
| Knows each person <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ★★★ | It knows who is talking, by voice and by name. |
| Calendars, briefings, announcements <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ★★★ | Ask about your day and hear household announcements. |
| Rules for children and teens <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ★★★ | Kids get answers that fit the rules you set. |
| Animated face | ★★☆ | ★★★ | ★★★ | The official README lists lively, expressive animations. Ours lets you choose between five styles, any color or none, and captions, and it adds a clock face and night mode. |
| Timers and alarms | TBD | ★★★ | ★★★ | A ring empties as time runs out, so you can read it across the room. |
| Camera: snapshots, turning toward you, name list | TBD | ★☆☆ | ★★★ | Take a photo from the settings page and have it turn toward you. Both are built, opt-in and show a cue. Naming who it sees needs MaiPai Home. Frames stay on your host. Not yet checked on a robot. |
| Camera: "what is this" <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ★★★ | Hold something up and hear what it is. Your hub does the looking. |
| Name the song <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ★★★ | Ask "what song is this" and hear the title and artist. |
| Announcements <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ★★★ | Hear household news out loud, like "dinner is ready". |
| Mute, camera off, full quiet | TBD | ★★★ | ★★★ | Three switches on the face: tap the mouth to mute, the eyes to stop the camera, between the eyes for full quiet. They survive a restart, and the host warns you if the robot leaks. [Details](mute-and-camera-off.md) |
| Spoken "stop" while it talks | TBD | ★★★ | ★★★ | It stops at once, with no model involved. |
| Updates over Wi-Fi | TBD | ★★★ | ★★★ | No cable. An animated icon shows the progress. |
| Games and a pet mood | TBD | ★★☆ | ★★☆ | Seven games on the robot (color memory, whack-a-mole, tic-tac-toe, Do It, rock paper scissors, a magic 8-ball, and dice with a coin) with best scores, and a pet mood that grows with care. Not yet tried by touch on a robot. |
| Coding companion <span class="planned-tag">Planned</span> | TBD | ☆☆☆ | ☆☆☆ | A light for your build, where you can see it. Not built yet. |
| Local API, MQTT, metrics <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ☆☆☆ | Wire the robot into your own tools. These are MaiPai Home features and are not built in this repository yet. |
| Dances to your music by itself | TBD | ★★★ | ★★★ | It finds the tempo, sways to it and shows a mood face. Off until you turn it on. Not yet heard on a robot. |
| Choreograph your own dance | ★★★ | ☆☆☆ | ☆☆☆ | The factory phone app lets you set music, movements and light colors for a dance. We have six named dances and no dance editor. |
| Six languages | TBD | ★★★ | ★★★ | English, Spanish, French, German, Portuguese and Italian, switched at run time with no reflash. Not yet reviewed by native speakers. |
| Signed updates with rollback | TBD | ★★★ | ★★★ | Nothing installs unless you say so, and a bad update rolls back by itself. |
| Watch the room <span class="home-tag">Needs MaiPai Home</span> | TBD | ☆☆☆ | ☆☆☆ | Photos, a low-resolution look and sound or motion alerts for a pet or a room. A convenience, not a safety device. The screen always shows when it looks or listens. Runs with MaiPai Home. |
| No stealth: monitoring always shown on screen | TBD | ★★★ | ★★★ | Every listening, looking and watching mode shows on the robot's screen, and the cue cannot be turned off. |
| Watch mode: motion and sound alerts <span class="planned-tag">Planned</span> | TBD | ☆☆☆ | ☆☆☆ | The robot notices motion and loud sounds and sends an alert with a snapshot. MaiPai Home would add what it saw and who. Not built yet. |
| Security alarm: red and blue lights, siren <span class="planned-tag">Planned</span> | TBD | ☆☆☆ | ☆☆☆ | A warning or an alarm with swapping lights, a siren and an alert on the screen. Not built yet. |
| Find my robot, beep and flash | TBD | ★☆☆ | ★☆☆ | Press Find on the settings page to make it beep and flash, even when muted. Last seen by place name is planned. No GPS chip. Not yet checked on a robot. |
| Remote beep, lights and talk | TBD | ★★☆ | ★★☆ | Make it beep, flash or speak from the settings page. Remote access is off until you turn it on, and the robot always shows when someone is using it. Not yet checked on a robot. |
| Remote pan and tilt | ★★★ | ★★☆ | ★★☆ | The factory app moves the head with a joystick. Ours is on the settings page with head, nod, shake and center buttons. Not yet checked on a robot. |
| Live camera view <span class="planned-tag">Planned</span> | ★★★ | ☆☆☆ | ☆☆☆ | The factory app has a monitoring camera mode with a joystick. Ours will be a low-resolution live view, with the pink lights and a LIVE dot always on while it runs. Not built yet. |
| Control from your phone (app or web app) | ★★★ | ★★☆ | ★★☆ | The factory app does live video and remote avatar control. We have no phone app. Our web app, served by your host, opens in any phone browser and controls settings, faces, timers and snapshots. We have no remote avatar control. If you rely on those, stay on factory. |
| Online app downloads | ★★★ | ☆☆☆ | ☆☆☆ | Removed on purpose. The on-device app system took about 548 KB of flash and 24 KB of the robot's scarce working memory, and we used that room for the voice agent and the features above. |
| ESP-NOW remote controller | ★★★ | ☆☆☆ | ☆☆☆ | Not supported yet. If you rely on the remote, stay on factory. |
| Bluetooth (phone setup and more) | ★★☆ | ☆☆☆ | ☆☆☆ | On the factory robot the phone app uses Bluetooth for its setup page. Ours is off today, and we are reviewing whether to bring it back for phone setup from a browser, a push-to-talk clicker and finding your robot. Until then you set up the robot with its own Wi-Fi setup page or over USB. |
| Chinese, Japanese and Korean text, and emoji | TBD | ★☆☆ | ★☆☆ | Removed from the default image to save space for more features. An optional font pack adds the text back. |

## Why some things are missing

The robot has about 76 KB of free working memory, so every feature has to earn its place. We removed the on-device app system to make room for the voice agent, the camera, timers and games. Bluetooth is off for a different reason: it was not needed and it is one more way in. It saved almost no memory, so we are reviewing whether to bring it back.
We chose a web app served by your host over a native phone app. We would rather say what is gone than hide it.

## What the stars mean for you

- **Privacy and security:** both MaiPai columns are built to keep your conversations in your home, and we will publish a network capture that shows it before release. The link on a home network is plain, so we rate it two stars until the encrypted home link ships. [Keep the robot secure](security.md).
- **Speed and answer quality:** these depend on your model and hardware, the same with or without MaiPai Home. A 4B class model answers in under 400 ms warm, and a 27B class model on a weak host does not. These are targets until the benchmark is run.
- **What MaiPai Home adds:** the full feature set, such as memory, recognizing people, naming songs, naming who the camera sees, and household rules.
- **What you give up:** a phone app (our settings page covers settings, photos and remote controls, and live view is planned, but there is no remote avatar control), setting up the robot from the phone over Bluetooth, online app downloads, and the official ESP-NOW remote controller. If you rely on those, stay on the factory firmware for now. You can [switch back](switch-from-the-factory-firmware.md) any time.
- **Memory, people, calendars and rules** come only with MaiPai Home.

Switch between the last two columns with one line, `brain = "llm"` or `brain = "home"`. The robot is not reflashed. See [Use MaiPai Home as the brain](with-maipai-home.md).

## Still need help?

Read [Getting started](getting-started.md), or open an issue on the Issues tab and tell us what you are trying to do.
