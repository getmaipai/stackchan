# What the robot can do

Every feature on one page. Scan the table, then open the page for the ones you care about.

**MaiPai for StackChan on its own is a simple, private voice robot.** Rows marked <span class="home-tag">Needs MaiPai Home</span> run with MaiPai Home. A feature that needs something you have not set up hides itself, and the settings page says what is missing.

![The settings page with each feature switched on or off.](../images/web-features.svg)

## Talk

| Feature | What it does | Runs on | Page |
|---|---|---|---|
| **Wake word and voice** | Say the wake word and ask. The reply starts on the first finished sentence. | Robot | [Voice](voice.md) |
| **Follow-ups and interrupting** | Ask again with no wake word. Speak while it talks and it stops and listens. | Robot | [Voice](voice.md) |
| **Voice commands** | Stop, mute, quiet, volume, brightness, sleep, time and night mode, with no model involved. | Robot | [Voice](voice.md) |
| **Offline phrases** | Sixteen spoken lines when the host is out of reach. | Robot | [Voice](voice.md) |
| **Persona, speech speed and pitch** | A short text sets how it talks. Set how fast it speaks and how high. | Robot | [Voice](voice.md) |
| **Six languages** | Screens and setup in English, Spanish, French, German, Portuguese and Italian. | Robot | [Languages](languages.md) |

## Look

| Feature | What it does | Runs on | Page |
|---|---|---|---|
| **Faces and colour** | Eight face styles, any colour or none, optional captions. | Robot | [Face and look](face-and-look.md) |
| **Clock and time-of-day faces** | A clock face, a face that changes with the hour, and night mode. | Robot | [Face and look](face-and-look.md) |
| **Face extras and word reactions** | Sweat, hearts, stars and more on the face, and reactions to words like "thanks" in six languages. | Robot | [Face and look](face-and-look.md) |
| **Per-person settings** | A face colour and caption size for each person. | Robot | [Face and look](face-and-look.md) |
| **Time zone** | Pick one of 31 zones on the robot or the settings page. | Robot | [Face and look](face-and-look.md) |
| **Quick sliders** | Swipe up for volume, brightness and saved Wi-Fi. | Robot | [Voice](voice.md) |

## Keep time

| Feature | What it does | Runs on | Page |
|---|---|---|---|
| **Timers and named timers** | A ring that empties as time runs out. Run several at once. | Robot | [Timers and alarms](timers-and-alarms.md) |
| **Alarms and snooze** | Stop by voice or touch. | Robot | [Timers and alarms](timers-and-alarms.md) |
| **Hourly chime and quiet hours** | A soft tone on the hour, silent at night. | Robot | [Reactions](moves-and-moods.md) |

## React

| Feature | What it does | Runs on | Page |
|---|---|---|---|
| **Pickup, shake, tilt, petting** | It looks surprised, dizzy, tilted or happy. | Robot | [Reactions](moves-and-moods.md) |
| **Mood from care** | Its resting face follows how much you pet it. | Robot | [Reactions](moves-and-moods.md) |
| **Dance and music** | Dance on request, six named dances, and a sway to the music with mood faces. Off until you turn it on. | Robot | [Music and dance](music-and-dance.md) |
| **Pet mood and games** | Three games on the robot (colour memory, reaction time, whack-a-mole) with saved best scores, and a pet mood that depends on care. | Robot | [Games and pet](games-and-pet.md) |
| **Breathing idle and quiet mode** | Calm moves when nothing happens, softer when you ask. | Robot | [Reactions](moves-and-moods.md) |
| **Low-battery steps** | A chirp at 20 percent, a spoken ask at 10, sleep at 5. | Robot | [Reactions](moves-and-moods.md) |

## Privacy

| Feature | What it does | Runs on | Page |
|---|---|---|---|
| **Mute, camera off, full quiet** | Three taps on the face. The screen shows each state. | Robot | [Mute and camera off](mute-and-camera-off.md) |
| **Lights and sounds** | One light colour and one tone per meaning. | Robot | [Lights and sounds](lights-and-sounds.md) |
| **No stealth** | Every monitoring mode shows on the robot. | Robot | [No stealth](no-stealth.md) |
| **Conversations stay in your home** | Only your host or hub is called. | Robot | [Privacy](privacy.md) |

## Connect

| Feature | What it does | Runs on | Page |
|---|---|---|---|
| **Wi-Fi setup page** | A setup code on the robot screen, a short window and a lock after wrong tries. | Robot | [Getting started](getting-started.md) |
| **Away from home (Tailscale)** | The robot joins your private network by itself when it cannot reach your host, using a one-time key. Works from any Wi-Fi: a friend's house, a hotel, the office. | Robot | [Away from home](use-it-anywhere.md) |
| **Several robots, one host** | One host serves each robot by its own ID. | Robot | [Install the host](install-the-host.md) |
| **Network test and version screen** | Swipe up, More: a plain check of Wi-Fi, your host and the private network, and the version. | Robot | [Troubleshooting](troubleshooting.md) |
| **Your own LLM or MaiPai Home** | Point the robot at any OpenAI-compatible chat address, or at a MaiPai Home hub. | Robot | [Which setup?](which-setup.md) |

## Set up and keep safe

| Feature | What it does | Runs on | Page |
|---|---|---|---|
| **Pairing, revocable token** | Pair with a six-digit code. Revoke any time. | Robot | [Security](security.md) |
| **Reset on the robot** | Hold a button for 3 seconds to erase Wi-Fi, pairing and settings. | Robot | [Troubleshooting](troubleshooting.md) |
| **Signed updates with rollback** | You choose when to install. A failed start rolls back. | Robot | [Updates](updates.md) |

## With MaiPai Home

All of these need a MaiPai Home hub. Set `brain = "home"` to use them: [Use MaiPai Home as the brain](with-maipai-home.md).

| Feature | What it does | Runs on | Page |
|---|---|---|---|
| **Take my picture, snapshots** | Ask for a picture and see it on your phone. | <span class="home-tag">Needs MaiPai Home</span> | [Camera](camera.md) |
| **Face follow, wave, mirror** | The head follows your face, waves back and mirrors you. | <span class="home-tag">Needs MaiPai Home</span> | [Camera](camera.md) |
| **What is this** | Hold something up and hear what it is. | <span class="home-tag">Needs MaiPai Home</span> | [Camera](camera.md) |
| **Name list** | A local list of names it can match to faces you enrol. | <span class="home-tag">Needs MaiPai Home</span> | [Camera](camera.md) |
| **Live view** | A low-resolution live view of the room, with the pink lights on the whole time. | <span class="home-tag">Needs MaiPai Home</span> | [Find and remote](find-and-remote.md) |
| **Watch and alerts** | Motion and sound alerts with a snapshot. | <span class="home-tag">Needs MaiPai Home</span> | [Watch and alerts](watch-and-alerts.md) |
| **Alarm and siren** | Red and blue lights and a siren for a security alert. | <span class="home-tag">Needs MaiPai Home</span> | [Watch and alerts](watch-and-alerts.md) |
| **Baby and pet monitor** | Listen and look from your phone. Started on the robot and always shown. | <span class="home-tag">Needs MaiPai Home</span> | [Baby and pet monitor](baby-and-pet-monitor.md) |
| **Find my robot** | See where it was last seen and make it beep and flash. | <span class="home-tag">Needs MaiPai Home</span> | [Find and remote](find-and-remote.md) |
| **Remote beep, lights, talk** | Control the robot from the web app. It always shows when someone is using it. | <span class="home-tag">Needs MaiPai Home</span> | [Find and remote](find-and-remote.md) |
| **Remote pan and tilt** | Move the head from your phone, within a safe range. | <span class="home-tag">Needs MaiPai Home</span> | [Find and remote](find-and-remote.md) |
| **Coding companion** | Agent status on the face, a build light, dictation and touch approvals. | <span class="home-tag">Needs MaiPai Home</span> | [Coding companion](coding-companion.md) |
| **Local API, event stream, MQTT** | Wire the robot to your own tools and home automation, all off by default. | <span class="home-tag">Needs MaiPai Home</span> | [Home tools](home-tools.md) |
| **Home-automation bridge and metrics** | Trigger scenes and chart the robot. | <span class="home-tag">Needs MaiPai Home</span> | [Home tools](home-tools.md) |
| **Face and voice recognition** | It knows each person by face and by voice. | <span class="home-tag">Needs MaiPai Home</span> | [With MaiPai Home](with-maipai-home.md) |
| **Memories** | What matters is remembered from one day to the next: people, preferences, events and things you told it. | <span class="home-tag">Needs MaiPai Home</span> | [With MaiPai Home](with-maipai-home.md) |
| **Content filtering and household rules** | Rules for the whole home, including children and teens. | <span class="home-tag">Needs MaiPai Home</span> | [With MaiPai Home](with-maipai-home.md) |
| **Companions and personalities** | Different characters with their own personality, for different people or moods. | <span class="home-tag">Needs MaiPai Home</span> | [With MaiPai Home](with-maipai-home.md) |
| **Custom and cloned voices** | Speak in a voice you choose or make: a celebrity voice, a family member's voice or a custom one. | <span class="home-tag">Needs MaiPai Home</span> | [With MaiPai Home](with-maipai-home.md) |
| **Calendars, briefings and announcements** | Daily briefings and household announcements. | <span class="home-tag">Needs MaiPai Home</span> | [With MaiPai Home](with-maipai-home.md) |
| **Song naming** | "What song is this" names the song and the artist. | <span class="home-tag">Needs MaiPai Home</span> | [Music and dance](music-and-dance.md) |

## Planned

Likely to come, not finished. Do not count on these yet.

| Feature | What it will do | Page |
|---|---|---|
| **Fluid faces** <span class="planned-tag">Planned</span> | Smoother eyes and mouth: eased eye motion, a smooth blink, a drifting gaze and a mouth that follows how loud you speak. Aim: 30 frames a second, to be measured. | [Face and look](face-and-look.md) |
| **Your own picture faces** <span class="planned-tag">Planned</span> | Upload your own pictures on the settings page, one per expression, and the robot shows them as its face. Nothing leaves your home. | [Face and look](face-and-look.md) |
| **Per-person wake phrase** <span class="planned-tag">Planned</span> | A different wake phrase for each person. The phrase is stored today but not matched. | [Face and look](face-and-look.md) |
| **Encrypted link at home** <span class="planned-tag">Planned</span> | Encrypt the robot's link to your host on your home Wi-Fi, and check it is talking to your host. | [Security](security.md) |
| **Outside games** <span class="planned-tag">Planned</span> | Load games you or others make. Signed packs only. | [Games](games-and-pet.md) |
| **Infrared and NFC** <span class="planned-tag">Planned</span> | Learn and send infrared, and read tags. Needs the body's pin list. | none yet |
| **Phone as the host** <span class="planned-tag">Planned</span> | Run the host from a phone, with no computer. | [Hardware](hardware-and-models.md) |
| **Reviewed translations** <span class="planned-tag">Planned</span> | Native-speaker review of French, German, Portuguese and Italian. | [Languages](languages.md) |

## Not included

Sound direction, Bluetooth, a phone app, and anything that calls an outside service by itself.

## Also useful

[Which setup is right for me?](which-setup.md) · [Compare](compare.md) · [Settings](settings.md) · [Pick hardware and a model](hardware-and-models.md) · [Switch from the factory firmware, or go back](switch-from-the-factory-firmware.md) · [Questions](faq.md) · [Glossary](glossary.md) · [Release notes](release-notes.md)

## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us what you saw.
