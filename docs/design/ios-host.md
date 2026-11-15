# An iPhone app as the robot's host

Status: feasibility note, 2026-11-15, from platform knowledge. Nothing tested. It would be a separate client, not part of the core.

## What the robot needs from a host
The unit opens a WebSocket client connection to the host for the voice turn (Opus audio up, speech and control down) and a second one for the face and sensors, then pairs with a per-device token. The host does speech to text, the model call, text to speech and the face commands.

## Can an iOS app serve that?
- Server socket: yes. Network.framework (`NWListener` with the WebSocket protocol) can listen on the local network while the app is in the foreground.
- Local network permission: yes, needed. The app declares a usage string and the Bonjour service types it advertises; the user taps Allow once.
- Discovery: the unit finds the host by name or a saved address. Bonjour advertising from the app works on a normal Wi-Fi. On the Personal Hotspot the phone is the gateway (a fixed private address, commonly 172.20.10.1), so the unit can use that address as a fallback and skip discovery.
- Hotspot case: the app must listen on the hotspot's bridge interface. Listening on all interfaces normally covers it, but this is the part most likely to surprise; test it first.
- Background: the hard limit. iOS suspends a backgrounded app within seconds. Ways to stay alive (a playing-audio background mode, location updates, a Bluetooth role) are narrow, and abusing them risks App Store rejection. Plan for a foreground-only app that keeps the screen on in a dock, and treat true background serving as unproven until a long soak test passes.
- Audio: decode the Opus frames with a bundled libopus; speech to text with the on-device speech recogniser (only for languages it supports on-device, English and Spanish are covered); text to speech with the system synthesiser, or a bundled neural voice.
- Model: the phone's on-device system model where available, or a small bundled model through an on-device runtime. Speed and memory are the open questions (2 to 4 GB budget for a foreground app).

## Verdict and test order
Feasible in the foreground, unproven in the background. Test order: (1) a 50-line app that listens and echoes a WebSocket handshake from the unit on Wi-Fi; (2) the same on the Personal Hotspot; (3) a screen-off soak of 30 minutes with the audio mode on; (4) a full spoken turn with on-device speech and a small model. Stop at the first step that fails and report. Needs the unit, an iPhone and a Mac to build; distribution by TestFlight or a signed local install (no public store promise).
