# Cloud brain test: can our firmware use the vendor's hosted servers?

Firmware track, 2026-11-18. Sources: our own pinned tree (xiaozhi-esp32 v2.5.2 inside the StackChan firmware, replayed from `firmware/patches/ORDER`) and public documentation only. Nothing here was run against a vendor server and no script contacts one. **Unknown stays unknown**; each unknown names the one check that settles it.

**Bottom line.** Yes, in principle: the client code is still in our tree. Our normal build switches it off. A separate image kind, `cloudtest` (patch SF96, never the default, never in a release), switches it back on with the safeguards below. Nothing is flashed and no server is contacted until the owner says yes.

## 1. What of the upstream client is still in our tree

| Part | Where | State in the normal build |
|---|---|---|
| OTA check, vendor address | `main/ota.cc`, `Kconfig.projbuild` (`OTA_URL`) | The upstream default was `https://api.tenclass.net/xiaozhi/ota/` (read from the pinned tree's own Kconfig). Our patch 155 emptied it. `STACKCHAN_OTA_CHECK` is off, so `ActivationTask` skips the check and the unit never contacts a vendor server. |
| Activation | `Ota::Activate`, `GetActivationPayload` | Compiled. Needs the check on. It signs the server's challenge with the chip's HMAC key block 0 when one exists (`esp_hmac_calculate`, use only: no key is read out). Whether this unit holds such a key is **unknown** (check: one `Ota` boot log line "HMAC calculation failed" or not, in the test build). |
| Activation code on screen | upstream showed the code | **Removed by the base** (comment in `ota.cc`: "StackChan World handles binding"): with a code in the reply the unit reboots into the phone-app setup (`requestAppSetup`). |
| Websocket protocol | `protocols/websocket_protocol.cc` | The only protocol built. Reads `url`, `token` from NVS namespace `websocket` (our host pairing). |
| MQTT protocol | `protocols/mqtt_protocol.cc` | Not built into this unit (a first cloudtest build failed to link on it). |
| MCP tools | `mcp_server.cc` | All our `self.*` tools register on whichever link is up. |
| Server reply handling | `Ota::CheckVersion` | A reply with `websocket` or `mqtt` sections is **written into the same NVS namespaces as our host pairing**, so a vendor reply would overwrite the host address and token. |

## 2. What the patches changed

- **075 / 143** (offline mode, "Offline" label after 45 s): link-state behavior for the host link; not vendor related.
- **106** (privacy core): mute, vision off and full quiet are three bits owned by the unit in `maipai_priv`. With mute or quiet the microphone cannot be opened whoever asks. This holds on any link.
- **155** (host-URL tools removed, signed updates): removed the tools that installed firmware or sent a snapshot to any address; the camera address must be the paired host's or it is ignored; wireless updates need an Ed25519 signature. Also emptied `OTA_URL`.
- **159** (update from the paired host only): `Ota::Upgrade` refuses an image address that is not the paired host, so a vendor firmware offer would be refused.
- Host-link changes (SF20 to SF35): a paired unit can require the encrypted link to the host.

## 3. What the `cloudtest` kind restores, and what it blocks

Restores: `STACKCHAN_OTA_CHECK=y` and `OTA_URL` set to the upstream address, only in `firmware/configs/sdkconfig.cloudtest.defaults`. The check runs, the activation challenge is answered, the vendor's websocket address and token are used.

Changes so it is safe to try (all behind `MAIPAI_CLOUDTEST`, patch SF96):

1. The vendor link's settings go to their own namespaces (`cl_websocket`, `cl_mqtt`). The host pairing is never overwritten, so flashing the plain image back restores the old setup.
2. The activation code is shown on the screen, silently (no reboot into the phone-app setup).
3. Firmware offers from the vendor are ignored.
4. The vendor service can call only four generic tools: device status, volume, brightness, theme. The privacy, lock, update, asset, game, pantry and question-game tools are refused with a plain error. (This also blocks the paired host in this build.)
5. An amber strip "Cloud brain test" stays on the screen (system layer, 16 px at the bottom).

## 4. How it behaves with our privacy rules

- **Microphone:** mute and full quiet still stop it (patch 106), and the strip tells which build runs. When the unit listens, **voice goes to the vendor's servers**: that is what a hosted brain is. This is the one rule of "nothing leaves the home" the test breaks, on purpose and only with the owner's yes.
- **Camera:** vision off still holds. A camera address from the service is ignored unless it is the paired host (patch 155), so pictures cannot be sent to the vendor through the old explain-image path. The vendor may still see the device status reply.
- **Sent at the check (stock behavior, unchanged):** the MAC address, a client UUID, the serial number when the chip carries a readable one, the firmware version and board facts. No script of ours sends it; the image does when it runs.
- **Offline fallback:** with no reply the unit shows the retry alerts of the stock check (up to 10 tries, then gives up), keeps its local face, clock and games, and the host link (when paired and the plain image runs) is untouched.
- **Quiet hours and sounds:** unchanged; the code alert is silent.

## 5. The steps the owner does himself (his own account)

Nothing here is done by us. The vendor's own pages decide the details; check their current instructions first, because we have not contacted them.

1. Say yes to contacting the vendor service (we ask first).
2. We flash the `cloudtest` image to the unit and the owner powers it with Wi-Fi up. The strip "Cloud brain test" is on the screen.
3. After a short wait the screen shows "Enter this code in your own console: NNNNNN" (6 digits in the stock service), with no sound.
4. On a computer or phone, the owner opens the vendor's own console in a browser and signs in with his own account (or creates one himself). We never see or type a password.
5. In the console he adds a device and types the code from the screen.
6. The unit connects; he can talk to it after the wake word. He can mute it (the unit's mute) or press nothing else.
7. To go back: we flash the plain image. His host pairing is still in place (it was never overwritten).

## 6. Unknowns and what settles each

- Does this unit's chip hold an HMAC key for activation? One boot log line in the test build.
- Does the vendor's server accept our hello (it carries extra feature fields)? The first connect shows it; a refusal is a plain "can't connect".
- Does the activation reply carry the code the same way in the current service? Shown or not shown on the screen.
- Does the code screen stay long enough to read? The check loop retries up to 10 times; a longer hold is a small follow-up.
