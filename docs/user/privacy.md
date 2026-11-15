# Privacy

Private, local AI that is yours. Nothing leaves your home.


## What talks to what

- The robot talks only to your host and the Wi-Fi it joined.
- The host talks only to addresses you put in `robot.toml`.
- No telemetry, no crash upload, no vendor account and no vendor cloud. It works fully offline once set up.

## The update check

If you leave checking on, the host makes one small request to your chosen update source. It sends only the firmware version.
You can set the source to your own server or folder, or turn checking off. Nothing installs until you turn that on.

## The camera

The camera is opt-in. Frames stay on the host. You set how long to keep them and you can delete all. A cue shows whenever the camera streams, and you cannot turn it off.

## Microphone

Quiet mute keeps the wake word, so you can unmute by voice. Hard mute powers the microphone down. Only touch, the web app or a button undoes it.

## Time

The host sends the time. The robot does not call public time servers.

## The link on your network

Until a later security step ships, the link between the robot and host is plain, not encrypted. Use a network you trust.
Pairing uses a code and a token you can revoke with `stackchan forget`.

## Optional private-network client

It is off by default. When on, it contacts its own control and relay servers. The full list of connections and a firewall sample will be on this page.

## Content

The standalone robot adds no content filter. The model you connect is responsible for what it says.
