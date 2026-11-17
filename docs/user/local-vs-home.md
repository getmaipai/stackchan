# What you get with your own model and with MaiPai Home

The robot works the same way with both. The difference is where the thinking happens and where live information comes from.

## The short version

- **Your own model:** everything stays in your home. The robot answers from what the model knows. It has no live weather, news or web lookups.
- **MaiPai Home:** the hub adds live information, memory, people and household tools.
- The robot never goes to the internet on its own. Anything that needs the internet comes through Home, or the feature is off.

## What works in both

Voice chat, the wake word, the stop word, faces and animations, screen effects, swipe pages, games, timers and alarms (set and cancel by voice, with no model), the settings page, remote controls with their cues (beep, flash, find my robot, say, pan and tilt, photo), turning toward you, the private network option and updates from your own host.

## The rule: if it needs no outside service and no household data, it can run on your own host

The robot's camera, remote control and monitoring can run with your own model. They are opt-in, off by default, and show a cue on the robot that cannot be hidden. Frames, photos and sound stay on your own host. Built and flashed today: remote controls, photo and turning toward you. Live view, watching, alerts and the monitor are planned. Not yet checked on a robot.

## What MaiPai Home adds

<span class="home-tag">Needs MaiPai Home</span>

- Outside services: live weather, news, calendars and email, shown as a card or spoken.
- Names and recognizing people by face and voice.
- Memories and household records, and other rooms.
- Household rules, including the gates for children and teens.
- Companions and personalities, cloned voices, scenes and household tools, and the package catalog.

With your own model, ask about the weather and the model answers from what it knows, with no live data. The page says "Connect Home for live weather" where it matters. Not yet checked: that the hub's weather tool can send a card back to the robot.

## What the factory firmware does with the internet, and what replaces it

| The factory firmware | With your own model | With MaiPai Home |
|---|---|---|
| Sends your voice to a cloud AI | Your model, on your network | The hub's model, memory and persona |
| Answers weather, news and sports questions from a cloud service | The model answers from what it knows | The hub looks it up and answers |
| Sets the time from the internet | Your host sets the clock, and time zones are built in | Same |
| Updates from the maker's server | A signed update from your own host (no release key yet, so not tested) | Same, through the hub |
| Phone app and Bluetooth | Not built. The settings page and remote controls replace them. | Same, plus the hub's app |
| Video call and camera upload to a web address | Removed on purpose, because it sent video to a cloud | Camera and photos go to your hub only |
| App store, cloud data and accounts | Removed on purpose | The hub's package catalog |
| Reminders and timers | On the robot, no network | Same |

We have not yet checked the factory app for every other cloud feature, such as music or stories. If one you miss is not in this table, tell us on the Issues tab.

## The remote banner

When something controls the robot from outside, the top row says where it came from: "Remote: Settings", "Remote: Phone", "Remote: Home hub" or "Remote". You cannot turn this cue off.

## Choose

Not sure which to use? Read [Which setup is right for me?](which-setup.md). To connect Home, see [Use MaiPai Home as the brain](with-maipai-home.md).
