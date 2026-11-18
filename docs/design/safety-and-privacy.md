# Safety and privacy

Promise: private, local AI that is yours. Nothing leaves the home.

## Own-LLM safety floor (decision 13)

- No content filter of our own. Content safety is the responsibility of the connected language model and the owner's persona prompt.
- The docs, the first-run setup and the README say so in one plain sentence.
- An optional family-friendly persona preset may ship. It is labeled as a prompt, not a guarantee.
- A brain such as MaiPai Home may add its own age and household gates. Those belong to the brain and are not weakened by this repo.
- What stays in this repo:
  - Body safety: servo limits, slow eased moves, volume cap, thermal and wear limits, no hard shaking by games.
  - Privacy cues: the camera-on cue cannot be turned off while the camera streams. Mute and error cues cannot both be disabled.
  - No fast flashing in any light option (photosensitivity).
  - Pairing and token security. Voice commands never change safety settings, pairing or Wi-Fi.
  - Coding companion approvals: touch only by default, never by voice alone. Every approval is logged.
- Camera features are opt-in. Frames stay in the home, on the host or the Home hub, with a retention setting and delete-all.
- Mute has two kinds. Quiet keeps the wake word, so a voice unmute works. Hard mute powers the mic down and only touch, the web app or a button can undo it. The unit never claims a voice unmute works in hard mute.

## Zero phone-home

- The unit talks only to the host and the Wi-Fi it joined. The host talks only to addresses the owner put in the toml.
- No telemetry, no crash upload, no vendor account, no vendor cloud. Works fully offline once set up.
- The update check is one manifest request to the chosen source, sent by the host, carrying only the firmware version.
- The public privacy page lists every connection the unit may make, with a firewall rule sample.
- Optional private-network client: off by default, no key in any public build, started lazily, enrolled from the host with a one-off tagged expiring key.
- Presence comes from the network, a private-network client and the camera. No Bluetooth.

## Safety changes

Safety changes to the firmware and host are ordinary patches (the `SF` series and the signed-update, key-check and certificate-bundle patches 155 to 159 in `firmware/patches/ORDER`). Each says what it does in its own header; nothing here lists them.

## Clock and time

Public time servers were removed on purpose. The host sends the time, zone and POSIX rule at hello and every 30 minutes.
The unit shows `--:--` until the time is valid. An optional local time server field is empty by default. No public default, ever.

## Build-time rules

- A secret-scan step in the firmware build and the release tools.
- Included code keeps its notice in LICENSE, NOTICE and THIRD-PARTY. A CI check refuses an unlicensed or incompatible import.
- No names, addresses or credentials of any household in code, docs or examples. Examples use reserved documentation addresses and names.
- The local API binds to the LAN, needs the token for reads and writes, and remote reach is a separate documented switch.

## Remote control trust boundary (patch FM03, 2026-11-16)

Who is trusted: the paired host. The unit takes tool calls from it and from nobody else (pairing token on the link). A paired
controller (a phone, a page, a Tailscale link) is not trusted: it reaches the unit only through the host.

Two floors, each enough alone against a host bug:

1. **Cue floor (TC01).** A call marked `source: remote` must carry the one-use token the unit answered to `self.remote.action`
   for that kind. The host sets `source` and `token` itself from the unit's answer (`RemoteCue`).
2. **Source-free floor (FM03).** The unit does not trust the `source` field, because the caller chooses it. While a remote
   session is on, the cued kinds (head move beyond 45 degrees yaw or pitch, find, photo, dance, game, listen) need either a
   cue token for that kind or the session's host id as `token`. The host announces its id in the `self.remote.session`
   heartbeat (`host`) and stamps it on every call that is not made for a controller, at the one place all unit calls pass
   (`XiaozhiServer.call_device_tool`). A call made while a controller's action runs is never stamped.

Host rules (`host/maipai_body/remote_trust.py`, tested in `host/tests/test_remote_trust.py`): a controller request that names
`source`, `token`, `host`, `host_id`, `cue` or `cue_kind` is refused and logged before the unit hears anything; the controller's
pairing token is spent on the route and never forwarded.

What this does not cover: a hostile host (it holds the id), and a unit with no session on (nothing remote to protect; the owner's
own page and the voice turn work as before). An older host that sends no id leaves floor 2 open; floor 1 still applies. Unit test:
`host/tests/firmware/remote_floor_test.c`.

## Open

- TLS between unit and host: certificate pinned at pairing or a reverse proxy.
- Secure boot and flash encryption (burns eFuses, owner's call).
- Whether a remote camera view ever ships. It would be a separate opt-in feature with an on-robot cue, after patch 155 and TLS.
