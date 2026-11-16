# Flasher and updater

`stackchan flash` and `stackchan update` put a signed release on a unit. Both check the release first
and refuse anything unsigned, altered or for the wrong preset. Both take `--dry-run`, which checks
everything and changes nothing, so tests and a first look need no hardware.

## What a release is

A release folder holds `flash-manifest.json` and the image files it lists (bootloader, partition
table, OTA data, app, assets). `release.sh --signing-key` builds it. The manifest carries one
Ed25519 signature, made with the one MaiPai signing key. The core and home presets share that key.
The preset is the word in the manifest id: `stackchan-esp32s3-core-1.2.0` or
`stackchan-esp32s3-home-1.2.0`. An id with no preset word counts as core. The pinned manifest
schema has no preset field and refuses extra fields, so the id carries it until the spec adds one.

## Checks, in order

1. The manifest exists, parses, and has a signature. Unsigned means refused.
2. A trusted public key exists. Default `~/.config/maipai/stackchan-release.pub.pem`; override with
   `--public-key` or `update.trusted_key` in `robot.toml`. No key means refused (nothing is trusted
   by default, and this repo ships no key).
3. The manifest passes the pinned schema, and the signature matches the key (OpenSSL, Ed25519).
4. The preset matches `--preset` (default `update.preset`, which defaults to `core`).
5. The chip is ESP32-S3.
6. Every part exists and matches its signed size and SHA-256.
7. The 20 percent rule: the app image must leave at least 20 percent of the smaller OTA slot free.
   The slot sizes come from the release's own partition table. The result is printed, for example
   "App image 3,064,240 bytes of a 5,177,344 byte slot: 40.8 percent free".

Each refusal says what went wrong and what to do, in English or Spanish (`--lang`, or
`home.language`).

## Commands

- `stackchan flash --port /dev/cu.usbmodem101 [--source DIR] [--preset core|home] [--dry-run]`
  writes every part with `esptool write_flash`. Without `--port` it stops; nothing flashes by
  accident. `--dry-run` prints the esptool command.
- `stackchan update --unit DEVICE_ID [--source DIR] [--dry-run]` asks the running host to push the
  app image to that unit over the air, using the unit's `self.firmware.update` tool. It sends only
  when the release is newer than the unit's version. Without a running host it says so and points at
  `flash` over USB.
- `update.source` in `robot.toml` is a release folder (a local folder or a share you mount).
  Nothing is fetched from the internet by this code.

## Settings page

The host serves `/settings` (local administrator only, like pairing): unit name, Wi-Fi setup status,
host address, persona, model URL, model name and key variable name, alarms, volume cap, mute,
firmware version, online state, and two buttons. "Update" runs every check and changes nothing (a
dry run, the default). "Install update" asks for a confirm, then pushes over the air; the request
must carry `"confirm": true`, and without a connected unit that can take the push the page refuses
with a plain message and the USB `stackchan flash --port` fallback. Every
unit is keyed by its Device-Id. Settings are stored in `~/.config/maipai/stackchan-units.json`; keys
are never stored, only the name of the environment variable. `UnitSettingsStore.effective()` overlays
a unit's values on the top-level config. English and Spanish: `?lang=es`, or the browser language.
The strings are in `host/maipai_body/i18n.py`, a small catalog with a test that Spanish has every key.

## What is verified

Unit tests (`test_stackchan_updater.py`, `test_stackchan_settings_page.py`) build real signed
releases with an OpenSSL Ed25519 key and cover: good release, unsigned, wrong key, altered manifest,
altered or missing part, wrong preset, the 20 percent boundary, smallest-slot choice, dry-run flash,
runner failure, over-the-air push only when newer, the CLI, the page in both languages, the HTTP
routes and cross-origin refusal.

## Live wiring (2026-11-16)

The running host serves the page itself (`settings_server.py`, loopback only, port 8051, change it
with `MAIPAI_STACKCHAN_SETTINGS_PORT`, `0` turns it off). `live_units.py` reads the live voice
connection for each unit by its Device-Id: online state, firmware version (from the unit's once-a-minute
`fw` event, firmware patch 062, `{"version", "rssi"}`; `LiveUnits.note_event` keeps it per unit, and
with one unit connected the host's single `fw_version` fact is used), and
whether it has saved Wi-Fi networks (`self.wifi.list_saved`). The OTA push serves the image to that one
unit and calls its `self.firmware.update` tool. Persona, model, volume cap and recurring alarms are
read and written through `unit_settings.py` and used per unit (see "Several robots" in
`docs/design/config.md`). The dashboard process (`python -m maipai_body.dashboard`) has no live
connection: there the online state reads "unknown" and Install update is refused.

Fixed on the way: the one-read firmware URL served `bytes.read_bytes()` and would have failed on
the first unit download; it now serves the bytes it stored. `serve_firmware_once` and
`call_device_tool` take an optional Device-Id so two connected units are told apart.

## Not verified or not built

- No unit was flashed and no USB port was opened. esptool itself was not run.
- The live paths (Wi-Fi list, OTA tool call) are tested with a fake voice link, not a real unit.
  The version key is no longer a guess: the firmware reports it only in the `fw` event (key
  `version`), not in `self.get_device_status`. The host polls events with one unit-less call
  (`self.robot.get_events`), so with two units connected the version shows "unknown" until the event
  poll is made per unit; `LiveUnits.note_event(device_id, kind, extra)` is the hook for that.
- The `stackchan update` CLI still pushes through the single-unit host path.
- No release is published, so no real signature has been checked; the trusted key is not shipped.

## Over the air (2026-11-16)

The over-the-air case needs `stack-chan-maipai.bin.sig` (64 bytes, Ed25519 over the whole app image) beside the app image. The host serves it with the image; the unit checks it against its built-in key before it switches the boot slot, and rolls back if the new image does not reach the host within 60 seconds. A refusal from the unit comes back as the unit's own plain sentence. Details: `docs/design/ota-update-2026-11-16.md`.
