# Build from source

Status: planned. The build script does not exist yet. This is the design.

## Command

`stackchan firmware build` from a clone, or `scripts/build.sh`. No Docker.

It prints exact versions and a size and time estimate first. Then it installs the pinned toolchain into a user folder (several GB),
fetches pinned sources by commit hash, applies our patches in order, builds, and writes an image plus a manifest and a memory report.
A build below the memory gate floor fails.

Options live in `firmware.toml`: board, language packs, face packs, features compiled in or out, default Wi-Fi and host (both empty by default) and a signing key.

## Reproducible

The same inputs give the same image hash. The build prints the patch list, pinned commits and licence list.
`verify` compares a downloaded release image with a local build.

## Secret scan

After the build, the output and every image are scanned for key patterns. An image with a key is private and cannot go into a release folder.
Private builds read keys from a file outside the repo.

## Upstream firmware bases

This repo patches two upstream firmware bases. Their notices are in LICENSE, NOTICE and THIRD-PARTY.md.

- Old base: xiaozhi-esp32 v2.2.4 on ESP-IDF 5.5.4, with the M5Stack StackChan firmware pinned at one commit.
- New base, two hops: first xiaozhi-esp32 2.5.2 with M5Stack's patch on ESP-IDF 6.1, then xiaozhi-esp32 2.6.0. The rebase happens before v1.
  The first step is a spike: run the stock tree on a unit and measure free internal heap, the largest block and the PSRAM low water.

The patch set is about 130 files, applied in order by a recipe script. Patch classes and the re-port order are in `docs/design/firmware-base.md`.

## Memory gate

Each build step runs a full spoken turn with camera and music on, then reads the per-minute memory report for 10 minutes.
Pass: steady `internal_free` at least 25 KB, lowest at least 15 KB, `int_big` at least 16 KB, `psram_min` above 6 MB, at least 20 percent of each OTA slot free, no reset or watchdog fire.
Latency p95 per stage must not get worse. Details: `docs/design/firmware-memory.md`.

## Flashing and recovery

The flasher takes the official image or a local file. `esptool` commands are documented too. A USB recovery path and the last known-good signed image are kept.

## Cloud builds

A public workflow lets anyone fork the repo and build in the cloud, signed with their own key.
