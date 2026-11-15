# What stays private

Private, local AI that is yours. Nothing leaves your home.


## What talks to what

- The robot talks only to your host and the Wi-Fi it joined.
- The host talks only to addresses you put in `robot.toml`.
- No telemetry, no crash upload, no vendor account and no vendor cloud. It works fully offline once set up.

## Every connection the robot and host make

| From | To | When | What it sends |
|---|---|---|---|
| Robot | Your host | Always, over your Wi-Fi or Tailscale | Audio while you talk, button and sensor events, and snapshots when the camera is on |
| Host | The addresses you set in `llm_url`, `stt_url` and `tts_url` | Each turn | Your words, to the model and speech tools you chose |
| Host | Your update source | Each update check, off if you choose | The firmware version only |
| Host | MaiPai Home | Only if `brain = "home"` | Your turns and records, to your own hub |
| Robot and host | Tailscale servers | Only if you turn Tailscale on | What Tailscale needs to find your devices. No voice, snapshots or settings |

That is the full list. If you see anything else on your network, it is a bug: tell us on the Issues tab. We have not yet published a network capture that proves this list, so we treat it as our design, and we will publish the capture before release.

## The update check

If you leave checking on, the host makes one small request to your chosen update source. It sends only the firmware version.
You can set the source to your own server or folder, or turn checking off. Nothing installs until you turn that on.

## What the core robot streams

The core robot never streams a camera or a microphone to anything except your paired host, and only for a voice turn. The extras, such as the camera features, watching and remote control, need the MaiPai Home firmware build, and each shows its cue on the screen. See [The robot never monitors in secret](no-stealth.md).

## No stealth

Whenever the robot listens, looks or watches, it shows it on the screen. There are no hidden modes. See [The robot never monitors in secret](no-stealth.md).

## The camera

The camera is opt-in. Frames stay on the host. You set how long to keep them and you can delete all. A cue shows whenever the camera streams, and you cannot turn it off.

## Microphone

Mute powers the microphone chip down, so the robot cannot hear you or the wake word. Only a tap on the mouth, the web app or MaiPai Home undoes it. Camera off and full quiet are separate switches. See [Mute, camera off and full quiet](mute-and-camera-off.md).

## Time

The host sends the time. The robot does not call public time servers.

## The link on your network

On your home network the link between the robot and the host is plain, not encrypted. Use a network you trust, or put the robot on your Tailscale network (see [Use it anywhere](use-it-anywhere.md)), which encrypts it.
Pairing uses a code and a token you can revoke with `stackchan forget`.

## Tailscale

It is off until you paste a Tailscale key. When on, the robot contacts your Tailscale control server and its relay servers to find your devices. It sends no voice, snapshots or settings there.

## Security

Privacy is about your data staying home. For what keeps other people out, see [Keep the robot secure](security.md).

## Content

With your own LLM, the robot adds no content filter. The model you connect is responsible for what it says.

## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us what you saw.
