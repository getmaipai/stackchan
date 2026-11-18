# Camera frames to the host (feature 8g): the path today, where it breaks, the smallest fix

Firmware track, 2026-11-18. Read from the replayed tree (`scripts/fw-rebuild.sh`, 293 patches) and the host's avatar server. Nothing here was run on a unit.

## What works today

- **Host side is complete.** `host/maipai_body/bodies/stackchan/avatar/server.py` listens on port 8766 (18776 encrypted), accepts the path `/stackChan/ws?deviceType=StackChan` with the headers `Device-Id`, `Client-Id` and `Authorization: Bearer <pairing token>`, expects a JSON `hello` text frame, answers with a session id, asks for the camera with frame type 0x05 until the first frame arrives (every 5 s), climbs a stall ladder when frames stop, keeps the newest valid JPEG per unit (`pop_camera_frame`, 0.5 s freshness) and `host/maipai_body/vision` decodes, detects and tracks faces; `look_owner.py` and the setting "who turns toward faces" decide whether this host or the Home hub steers the head.
- **Unit side has the pieces.** `hal_ws_avatar.cpp` handles 0x05 (start) and 0x06 (stop), captures a frame about every 350 ms (700 ms in video mode; about 3 and 1.4 frames a second), encodes it with `image_to_jpeg` at quality 20, 10 then 5 until it fits the payload limit, and sends it as frame type 0x02. Vision off skips the capture and counts the skip. The camera-on cue (patch T05) is drawn by the capture path itself, so a frame cannot be taken without it. The camera driver keeps its frames in PSRAM (M06) and its start race is fixed (FI02).
- **Local face turning (the unit alone)** works without any host: the seek task (S10 to S14, FI07) turns to a mover from 40 by 30 gray frames; the optional detector `facedet` (FD02) is an experiment image.

## Where it breaks

All three are on the unit and are why no frame reaches the host:

1. **The unit never connects to the host's avatar port.** `WebSocketAvatar::init()` builds its URL from `secret_logic::get_server_url()`, which is the build constant `CONFIG_STACKCHAN_SERVER_URL`. In the plain build that constant is the empty string (`sdkconfig`: `CONFIG_STACKCHAN_SERVER_URL=""`), so the URL is `/stackChan/ws?deviceType=StackChan` and the connect fails. Nothing derives the avatar address from the paired host (the voice socket's saved address).
2. **The headers are wrong.** The avatar socket sends only `Authorization` with the constant `hi-stack-chan`. The host refuses a socket without `Device-Id`, `Client-Id` and a valid pairing token.
3. **The camera gates miss two privacy rules.** The capture checks vision off only. A muted or locked unit would still stream once connected.

(The unit's second avatar path, `avatar_lan`, connects to an address that a phone app announces; it is separate and stays as it is.)

## The smallest fix (unit half, one switch)

`CONFIG_MAIPAI_AVATAR_TO_HOST` (default off; off builds none of it):

- **Address:** the saved voice address of the paired host, scheme and host kept, port 8766, path `/stackChan/ws?deviceType=StackChan`. With the encrypted link on, the address goes through `maipai_link_secure_url` (8766 becomes wss 18776, TLS-PSK) and a plain address is never used while a link key is stored. No saved address: no connect.
- **Headers:** `Device-Id` (the MAC, as the voice socket sends it), `Client-Id` (the unit's UUID) and `Authorization: Bearer <the saved pairing token>`, the same credentials the voice socket uses. The constant token is no longer sent.
- **Gates (a pure core, `maipai_avatar_core.h`, host C test):** no frame while vision is off, the unit is muted, the unit is locked or full quiet is on; no frame when the largest free internal block is under a floor (a frame needs a send buffer in internal RAM for a moment); one frame in flight (a busy camera lock skips the round). Each refusal has a counter by reason.
- **Rate, size, format:** unchanged: JPEG, about 3 frames a second, a frame at most the payload limit; one frame a second is enough for steering and the host can ask for fewer by stopping and starting. No new transport.
- **The cue:** unchanged and unconditional. Frames are only captured through the camera path that draws it; the host cannot turn it off, and the switch adds no code path that captures without it.
- **Status tool (new):** `self.avatar.status` answers `{configured, host, connected, streaming, frames_sent, skipped: {vision_off, muted, locked, quiet, memory, busy}, last_frame_age_ms}`; it is the one thing the virtual unit has to fake (the playground adds it to `scripts/virtual-unit/tools/`). The frames themselves are the existing type 0x02 messages on the avatar socket, which the virtual unit's fake avatar socket already produces.

## Memory budget (estimates to confirm on a bench run; the heap dump of window 13 and `self.avatar.status` will show the real numbers)

| Where | What | Size |
|---|---|---|
| PSRAM | camera frames (existing, M06) | unchanged |
| PSRAM | JPEG output buffer per frame | about 10 to 30 KB for a QVGA frame at quality 20, freed after the send |
| Internal, static | avatar core state and counters | under 100 bytes |
| Internal, task | the avatar worker already exists (`avatar_lan` 8 KB and `avatar_rx` 4 KB are created only for the LAN path); the remote socket adds one `tcp_receive` or `ssl_receive` stack of 4 KB while connected | 4 KB |
| Internal, TLS | with the encrypted link: one TLS session (about 40 KB of internal RAM per session in the IDF's default mbedTLS settings, to be measured with the linkpsk image) | to measure |

Gate: the stream refuses to start when the largest free internal block is under 20,000 bytes (the heap floor of `docs/dev/gate-numbers.md` is 16,000 for the lowest largest block); it stops again if the figure falls under 16,000.

## Privacy rules (hard)

Mute, vision off, full quiet and the lock each stop the stream at once and the counters say which rule did it; the camera-on cue cannot be hidden by any setting; frames go to the paired host only (never to another address, never to the saved remote constant); nothing is stored on the unit.

## Not in this note

The host deciding where to look (already built), the Home hub taking over steering (Home's version replaces the host's when paired), and the family wake word (feature 8e, `docs/plan/custom-wake-word.md`).
