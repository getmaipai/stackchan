# Offload to the host: what the unit does that the host could serve or compute

Owner decision 15 (2026-11-18): everything must fit; pages, forms, setup and settings belong on the host's web server; heavy computation runs on the host; the unit sends small events; assets and packs are fetched on demand, signed, and cached small; one copy of shared things.

Rule that bounds this list: the robot stays complete without a host. These stay on the unit, whatever the saving: timers and alarms (and their backstop), privacy (mute, camera off), the lock, the indicator cues, the clock, the stop word and the short on-device commands, Wi-Fi setup (there is no host to serve it yet), pairing and the six digits shown for the key exchange, the movement limiter, and what the face needs to draw itself with the host off.

Unit numbers come from the firmware track's `docs/dev/memory-budget.md`. Where it gives none, the cell says "firmware: measure" and nothing is invented here.

## Ranked candidates

| # | Candidate | Where it lives today | Host does instead | Unit memory freed | Protocol it needs | Risk |
|---|---|---|---|---|---|---|
| 1 | **Pack and asset delivery on demand** (language, look, filler, sound, dance, game, phrase packs; picture-face frames) | The unit keeps every pack it was given in flash and has two 6,144-byte internal tasks (`pack_boot`, `pack_write`) that run when a pack is written | The host keeps the library (it already does: `packs.py`) and serves one pack in chunks when the unit asks; the unit keeps only the active pack of each type and drops the rest | Flash cache of unused packs (firmware: measure); the transient 6 KB internal tasks shrink to one small fetch buffer if the write is streamed (the largest block is the binding limit, 1.6 KB of margin) | Signed asset manifest plus chunked, ranged, cacheable fetch (below) | A pack the active face needs must be on the unit before the host goes away: the unit keeps the active ones |
| 2 | **Setup and settings surfaces** (first-run name, language and brain choices; the quick-settings and info tabs beyond volume, brightness, lock and mute; pack and face pickers; wall tile editing) | Screens in LVGL on the unit; the first-run flow holds about 3.7 KB of internal RAM while open | The host's settings server, the Brain page, the parent view and pairing already cover them; the unit keeps only the Wi-Fi setup hotspot page, the six digits and the physical controls | About 3.7 KB internal while the first-run flow is open, plus the flash of the screens removed (firmware: measure) | None new: the unit shows "finish setup on your computer at <address>" and the host serves the page | A person with no host yet cannot finish setup: the unit keeps what is needed to reach one host (Wi-Fi, address, pairing digits) |
| 3 | **Language screen words** (weekday, month, alarm and timer words) | Already a language pack (K11); English built in | Already host-served; make the fetch on demand and keep one language | Flash of unused language packs (firmware: measure) | Candidate 1 | None beyond candidate 1 |
| 4 | **Subtitle line layout** | The unit breaks a caption into pieces and draws glyphs | The host already sends the exact words per sentence (`caption`); it can also send the words pre-broken into lines that fit the unit's strip | Small (the splitting code); glyph bitmaps stay | A `lines` field on `tts sentence_start`; the unit falls back to its own splitting when absent | Low; the unit's own splitting stays as the fallback |
| 5 | **Face detection and seeking** (FD01 to FD04, S10 to S14, experiment image) | On the unit (esp-dl model, a task, the camera window) | The host detects faces from the camera frames the unit sends (SF44) and sends a small "look at x, y" event | The model, its buffers and the detection task (firmware: measure; large) | Camera frames to the host (`docs/plan/camera-frames-path.md`, not built yet) and a look event the unit already understands | Needs the frame path and about three frames a second; carve-out 3 (the robot turns toward a face with no brain) is lost while the host is away |
| 6 | **Picture-face decoding** (H03, H04) | Inflate, fade and draw on the unit, 153,600 bytes of PSRAM per frame request, a 20 KB PSRAM stack | The host pre-renders each frame to the unit's exact size and format and sends it raw on demand | PSRAM peaks (not internal RAM); less flash for frames | Candidate 1 chunked fetch of one frame at a time | Face must still draw with the host away: keep a neutral frame on the unit |
| 7 | **Game packs** (G01 to G03) | The game engine and the rules run on the unit | Serve game packs on demand (candidate 1); the engine stays | The 6 KB `pack_write` task and the pack flash | Candidate 1 | The engine stays on the unit |
| 8 | **Word reactions, name matching, personas** | Host already | n/a | n/a | n/a | n/a |
| 9 | **Mouth cues** | Host already (SF10 and SF30) | n/a | n/a | n/a | n/a |
| 10 | **Music features** (MD01 to MD03, beat features about once a second) | The unit computes them from its own microphone | Could not move: the host never receives the microphone outside a turn (no remote listening) | none | none | Stays on the unit |

Not offloadable by rule: the timer backstop, privacy read-back state, lock, the cues, the clock, the stop word, `maipai_pages_core` data (the host table is checked equal to it, so there is one definition, two readers).

## The protocol (candidate 1, host half built)

Content-addressed, so a cache never serves the wrong bytes.

- `GET /assets/{device_id}/{asset_id}/manifest` returns a small JSON manifest: `{"v":1,"id","type","name","version","size","chunk":4096,"sha256":"<whole payload>","chunks":["<sha256 of chunk 0>", ...],"signer":"host"}` and a detached Ed25519 signature over its canonical bytes in the header `X-Asset-Signature` (a signing key the host makes on first use in its data folder, mode 0600; a unit trusts it because it paired with this host).
- `GET /assets/{device_id}/{asset_id}/data` serves the payload with `Range` (a unit asks for one chunk or a run of chunks), a strong `ETag` that is the payload's SHA-256, and `Cache-Control: private, max-age=31536000, immutable` (the id names the bytes). A `HEAD` returns the size and ETag.
- The unit checks the manifest signature, then each chunk's SHA-256 as it writes, then the whole SHA-256; it keeps only the active pack of each type and may drop the others and ask again.
- Authenticated like every other unit route: the unit's token or the encrypted link; a unit can fetch only assets the host wants it to have (`PackService.wanted`).
- Firmware half: a `self.pack.fetch` tool (or the unit pulls on its own at boot) is the firmware track's; the host half works today with the existing push path untouched.

## What the first offloads are

The firmware track picks from this ranking; the host half of candidate 1 (the signed, ranged, cacheable asset endpoint) is built first because candidates 3, 6 and 7 all ride on it. Candidate 2 (settings surfaces) needs no host protocol: section "Setup surfaces on the host" below is the check.

## Setup surfaces on the host (check of 2026-11-18)

| Surface | Served by | Needs a unit screen? |
|---|---|---|
| Choose a brain, install the local stack | settings server `/brain` | No |
| Pairing code (host mints, owner types digits) | settings page parent view, `stackchan pair` | The unit shows its six digits (kept) |
| Parent view, lock, family and safety | settings page | No |
| Packs, faces, pictures, people, wake word | settings page | No |
| Volume, brightness, mute, camera off, lock | the unit's physical controls and the settings page | Controls stay on the unit (safety) |
| Wi-Fi | the unit's setup hotspot page, or the settings page when a host is there | The hotspot stays (no host yet) |
| First-run name, language | settings page `/brain` and the unit settings | The unit's first-run screens are candidates for removal (candidate 2) |
