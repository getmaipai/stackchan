# What stays private

Private, local AI that is yours. Nothing leaves your home.


## What talks to what

- The robot talks only to your host and the Wi-Fi it joined.
- The host talks only to addresses you put in `robot.toml`.
- No telemetry, no crash upload, no vendor account and no vendor cloud. It works fully offline once set up.

## Every connection the robot and host make

| From | To | When | What it sends |
|---|---|---|---|
| Robot | Your host | Always, over your Wi-Fi | Audio while you talk, button and sensor events, and snapshots when the camera is on |
| Robot | A public coordination service, over an encrypted connection | Only when it joins your private network away from home | What it needs to find your devices. No voice, snapshots or settings |
| Host | The addresses you set under `[llm]` as `url`, `stt_url` and `tts_url` | Each turn | Your words, to the model and speech tools you chose |
| Host | Your release folder | Each update check | Nothing. The host reads the folder and fetches nothing |
| Host | MaiPai Home | Only if `brain = "home"` | Your turns and records, to your own hub |

That is the full list. If you see anything else on your network, it is a bug: tell us on the Issues tab. We have not yet published a network capture that proves this list, so we treat it as our design, and we will publish the capture before release.

## The update check

The host does not look for new versions online. It reads the release folder you set under `[update]` in `robot.toml`, and sends nothing. Nothing installs until you run the update.

## What the core robot streams

The core robot never streams a camera or a microphone to anything except your paired host, and only for a voice turn. The extras, such as the camera features, watching and remote control, are opt-in, and each shows its cue on the screen. See [The robot never monitors in secret](no-stealth.md).

## No stealth

Whenever the robot listens, looks or watches, it shows it on the screen. There are no hidden modes. See [The robot never monitors in secret](no-stealth.md).

## The camera

The camera is opt-in. Frames stay on the host. You set how long to keep them and you can delete all. A cue shows whenever the camera streams, and you cannot turn it off.

## Microphone

Mute powers the microphone chip down, so the robot cannot hear you or the wake word. Only a tap on the mouth, the settings page on your host or MaiPai Home undoes it. Camera off and full quiet are separate switches. See [Mute, camera off and full quiet](mute-and-camera-off.md).

## Time

The host sends the time. The robot does not call public time servers.

## The link on your network

On your home network the link between the robot and the host is plain, not encrypted. Use a network you trust.
Pairing uses a code and a token you can revoke with `stackchan forget`.

## Security

Privacy is about your data staying home. For what keeps other people out, see [Keep the robot secure](security.md).

## Content

With your own LLM, the robot adds no content filter. The model you connect is responsible for what it says.

## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us what you saw.
