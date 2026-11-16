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
firmware version, and an Update button that runs the same checks, then pushes over the air. Every
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

## Not verified or not built

- No unit was flashed and no USB port was opened. esptool itself was not run.
- The live app (`maipai_body/app.py`) does not yet hand the settings page its live unit version, Wi-Fi
  state or OTA push, and does not yet read the per-unit persona, model, volume cap or alarms. The
  page works against the files and pairing store; wiring those live values is the next step.
- Over-the-air push needs a `push` callable from the running host; `FirmwareUpdater` in
  `firmware_update.py` already serves an image once and calls the unit tool.
- No release is published, so no real signature has been checked; the trusted key is not shipped.
