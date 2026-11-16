# Wireless update, 2026-11-16

Tree: `~/esp/stackchan-rebase/main` (branch `ours`), ESP-IDF 6.1.1. Built, not flashed, no USB touched, not run on a unit.
New patches on `firmware/patches/ORDER`: `159-wireless-update-from-paired-host`, `160-first-boot-rollback`.
Replay of 159 and 160 onto copies of the pre-159 files reproduces the tree byte for byte (nine files).

## How an update runs

1. The host (settings page Update button, or `stackchan update`) checks the signed release folder, the preset, the chip and the 20 percent slot rule, and needs a 64-byte `stack-chan-maipai.bin.sig` beside the app image. Dry run stays the default.
2. The host publishes the image and the signature once each on its own address (`/firmware/<device>/<token>` and `<token>.sig`, ten minutes, one read) and calls the unit's `self.firmware.update` tool.
3. The unit refuses, with a plain sentence returned to the host and a log line, when: the address is not the host it is paired with; the version text is odd or equal to the running one; the image would leave under 20 percent of the inactive slot free (declared size, then the real length again while downloading); the unit is not idle; the battery is under 40 percent and not charging; the key or signature is missing, the wrong size, or does not match.
4. It streams the image into the inactive slot while hashing it, finishes the Ed25519 check, and only then sets that slot to boot (patch 155 order; the final boot flag is never written before the check passes). Events `firmware_update_started`, `_progress` (every 10 percent), `_done` or `_failed` (with the reason) go to the host. After `_done` it restarts.
5. First boot of the new image (patch 160): the image is pending. It is kept only after 20 seconds of uptime with the host link up (`firmware_update_validated`). A timer armed at boot, outside the main loop, marks the image invalid and reboots into the old slot at 60 seconds, so a hang rolls back too. Images flashed over USB are never pending and behave as before.

Kconfig: `STACKCHAN_WIRELESS_UPDATE` (default y, set in `sdkconfig.core.defaults`). With no `STACKCHAN_UPDATE_PUBKEY` built in, the unit accepts no update, as before.

## One copy of the shared checks

The address host parser, the paired-host test and the slot rule are in `update_verify.h`. The camera-address check in `mcp_server.cc` (patch 155) now uses the same parser. `Ota::Upgrade` repeats the paired-host and slot checks itself, so no other caller can install from another address.

## Measured

App image 0x2e4140 B, smallest slot 0x4f0000 B, free 0x20bec0 B (41 percent). That is 18,000 B over the 0x2dfaf0 B recorded after patch 158: the tool, the update task, the rollback timer and the signature code now linked in. Internal RAM was not re-measured.

## Host

`updater.update_over_air` requires the signature file; `LiveUnits.push` serves image and signature, reads the unit's reply and raises the unit's own reason as `UpdateRefused`; `serve_firmware_once` takes the signature. English and Spanish messages added. Tests: `host/tests/test_stackchan_ota_unit.py` runs a stand-in unit that follows the firmware order and checks a real Ed25519 signature with OpenSSL: good image written and kept, tampered image refused, other key refused, bad first boot rolls back, unpaired host refused, 20 percent rule refused, missing signature file stops the host before anything is sent, dry run sends nothing.

## Clock fix (update windows)

Not done, on purpose. Update windows (`update_install: auto within a window`) are decided by the host with the host's own clock; the unit never needs its time for an update, and the check is made by the host, not the unit. The unit clock (RTC; SNTP stays off by default, patch 004) only feeds the face clock. The cut has no row named for a clock fix, so there is nothing to implement here. If the host later asks the unit for the time of day, that belongs with the clock-face work (F04), not the update path.

## Not done, and why

- The Home-served update path (`FirmwareUpdater`, image from Home) does not send a signature yet; the unit refuses it with "no valid signature file". It needs Home to publish the `.sig` with the image.
- No release key exists in this repo (custody is still open in `release-and-updates.md`), so a real signed image could not be produced for a unit test. The Ed25519 check itself was tested on a PC in the security run.
- A refused image that already finished writing leaves the inactive slot holding unsigned data. It is never set to boot; the next update overwrites it.
- Redirects: the unit's HTTP client was not checked for following a redirect to another host. The host answers with no redirect.
- On a unit: not verified. The checks after a flash are in the two patch headers.
