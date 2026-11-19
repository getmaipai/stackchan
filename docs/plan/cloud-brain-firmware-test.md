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

## 7. What the official image says (read from its strings, nothing contacted)

The owner's backup of the official demo (M5Stack StackChan-UserDemo V0.4) names the same OTA and activation address as our pinned base, plus a separate avatar WebSocket on a raw IP over plain `ws://` with a camera-capture and JPEG-encode task next to it (the remote-view feature). Reading: the activation reply carries a challenge, the unit answers `POST <ota_url>/activate` with an HMAC-SHA256 over it, and the reply to the check carries the websocket or MQTT settings. See `official-firmware-connection-info.md` in the coordinator's notes folder.

- **Activation key (read-only use).** Our tree still answers the challenge with `esp_hmac_calculate(HMAC_KEY0, ...)` through the IDF: the chip computes, the key is never read out, nothing is burned (decision 14 holds). Whether this unit holds a key in block 0 is **unknown** from code; one read-only call that lists the purpose of each key block (never a value) or the "HMAC calculation failed" log line in the test build settles it. Without the key only the no-serial path (activation v1) remains.
- **Identity sent.** `Device-Id` is the MAC, `Client-Id` the board UUID, `Serial-Number` only when the eFuse user data holds printable text (else `Activation-Version: 1` and no serial). The exact values are not printed by the image; the test build's first log lines will show them to the owner only.
- **Avatar and camera paths stay off in every kind.** The StackChan server URL (`STACKCHAN_SERVER_URL`) is empty in our tree, so the avatar WebSocket, the app list and the account calls have no address and open nothing. The raw-IP address exists only inside the official image. A test pins the default empty and that the cloudtest overlay does not set it.
- **Our host link and the offline fallback in the test build.** The vendor link's settings live in `cl_` namespaces; the host pairing is never written; the unit's face, clock, games and pantry work with no link; the plain image restores the host link.

## 8. Leaving hosted (route custom)

The Brain route is a normal setting: **custom** (the unit's own host, Home or local) or **hosted** (the vendor's service, today only in the cloudtest image). Both use the same screens and cues; the "Cloud brain test" strip belongs only to the test image kind. Patch SF98 adds `self.brain.status` and `self.brain.set_route` to every image.

`self.brain.set_route {route: "custom"}` (and the cloudtest image's flash-back, which erases the same keys on its first start with route custom) does, in this order:

1. Stops the vendor check, the activation loop and the connect at once (one flag every loop looks at).
2. Erases every NVS namespace whose name starts with `cl_` (the vendor link's address and token, activation state, MQTT settings, any cached offer) and nothing else. A failed erase is reported and a second call finishes it.
3. Leaves the host pairing, the privacy bits and the chip's key blocks untouched. Nothing is burned and no key is read out.
4. Saves route custom (so a cloudtest image does not activate again at the next start).
5. Shows one plain line on the screen, silently: "Hosted link removed. To stop your account keeping this robot, remove it in the vendor's console."
6. Pushes the event `brain_route {route: "custom", hosted_removed: true}` so the dashboard shows the route.
7. Restarts four seconds later, so no vendor timer, task or RAM copy survives.

A factory reset also erases `cl_` (it is not on the keep list; a test pins this).

**Tests.** `host/tests/firmware/hosted_core_test.c` runs the rules against a fake NVS: only `cl_` namespaces go, the pairing, privacy, route and calibration namespaces stay, a failed erase is retried, repeating is harmless, and the factory reset keeps none of them. The on-unit check is `scripts/bench-trains/leave-hosted.json`: call `self.brain.set_route custom`, wait for the restart, then `self.brain.status` must answer route custom, `cl_keys` 0 and `vendor_attempts` 0, and the same again after the ten minute soak (the manifest runs it as a final check) and after a power cycle (run it twice).

**What the unit cannot delete.** The robot's binding in the vendor's account and any voice history the vendor already holds live on their servers. The owner removes the robot in the vendor's own console and asks the vendor about stored data; our firmware can only stop sending and erase what it keeps. The user guide must say this in plain words.

## 9. First run on the unit (2026-11-18) and what it showed

The first cloudtest run reached `api.tenclass.net:443` and failed at TLS ("Failed to verify certificate", mbedtls -0x3000), retried at 10, 20, 40 and 80 s, and the host link never came up. Findings, each from our own tree:

1. **No public roots on purpose.** The image's certificate bundle is a custom one (`ca/travel-roots.pem`: a placeholder and ISRG Root X1 only; the normal core config sets the default bundle to none). The vendor's chain is not visible offline, so it very likely roots in a CA the bundle does not hold. Fix (SF99): the cloudtest kind alone adds IDF's full standard root set (about 68 KB of flash) through a late defaults file read after the core trim. No other kind has public roots (a test pins it).
2. **The clock.** The unit gets its time from the host; with no host link the date is 1970 and any certificate fails its validity dates. The check now waits (up to 60 s) for a real year before asking, and logs `CLOUDTEST check waits for the clock (year N)`. No time server is contacted; if the owner prefers SNTP in this build, that is a separate yes (it is a contact with a public time server).
3. **The host link was blocked by the check.** The activation task runs the vendor check before the protocol exists, with 10 retries growing to 80 s (over 20 minutes), so the host link never started; and the single websocket client had been pointed only at the vendor's namespace. The earlier statement "host link kept" was wrong for this build until SF99. Now: 3 tries, and the websocket client reads the vendor's address only when the hosted route has stored one, otherwise the paired host's. **One link at a time, never both**: the unit has one websocket client; running two at once would need a second client and is not built.
4. **Bench lines.** `CLOUDTEST check waits for the clock`, `CLOUDTEST check starts: clock_year=N`, and at every connect `CLOUDTEST link: namespace=... route=... clock_year=...`; `self.brain.status` answers `clock_year` and `link_ns`.
