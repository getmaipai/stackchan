# The host layer (for `docs/design/architecture-layers.md`)

Written by the app track for the firmware track's layer document: merge this section into it (kernel on the unit, compiled-in modules, assets in slots, host). It does not repeat the long plans; it names them.

## What the layers put on the host

| Feature | The host serves or computes | Protocol | Per-unit state | When the unit is away | Detail |
|---|---|---|---|---|---|
| Pages, setup, settings, brain choice, parent view, health | The settings server | none: the person's browser | per unit where it holds unit state | the page shows "away" and the last known state | `offload-to-host.md`, `service-and-supervision.md` |
| Speech to text, text to speech, models | The brain and speech stack (own, Home, or the local stack) | short audio and events on the voice socket | per turn, per unit | the unit keeps its local features and an offline phrase | `minimal-stack.md` |
| Mouth cues, captions line layout, word reactions | Computed from the reply | small events with the audio | per reply | not needed | `mouth-cues-append.md` |
| Asset signing and serving | A signing key in the host's data folder; the signed manifest; ranged, cacheable data | `GET /assets/<unit>/<id>/manifest|data` | the installed set per unit | the unit keeps what it has; the host prefetches nothing a unit cannot hold | `offload-to-host.md`, `installed-set.md` |
| Catalogs and thumbnails | The pack library (the catalog repo later); previews from the virtual unit's renderer (planned) | the dashboard page | per unit choice, shared library | catalog shown, "robot is away" on the set | `installed-set.md` |
| Installed sets | Choice, memory meter, defaults, retrying reconciler | `self.assets.list|install|remove|swap` (unit half) | `installed-sets.json`, per unit | the set is sent when the robot returns; failed items retry by themselves | `installed-set.md` |
| Face detection and seeking, analysis | The host, from camera frames | camera frames to the host, look events back | per unit | the unit keeps the carve-out it has | `offload-to-host.md` (candidate 5) |
| Dance shows | The ladder director with a synthetic or a real beat | `self.music.stage`, `self.face.music_notes`, `self.overlay.set`, ring pixels | one dance runner per robot | no dance with no robot | `dance_ladder.py` |
| Updates | Signed update headers, the board id, the build number, serve once | `/firmware/<unit>/<token>` | per unit | the update happens when the unit returns | `signed-update-header.md` |
| Supervision | Watchdog, health document, service install | none | per unit parts | n/a | `service-and-supervision.md` |
| Playground | Lease and scope, state stream, snapshot, tool call | `/api/playground/...` | per unit lease | "away" | `playground-live.md` |

## Rules for every row

- The unit keeps what it has: nothing the host serves is needed for the unit's safety features (timers, privacy, lock, cues, clock, stop word).
- Fetches are chunked, ranged, signed and resumable; the id is the content hash, so caches are safe.
- Prefetch: the host sends a set while the unit is on and idle, and again when it returns; it never starts a large transfer during a turn.
- Every call names its unit; one unit's failure or slowness never touches another.

## Image profiles (decision 19, narrowed by decision 20)

One image unless the memory budget proves a split. The profile picker and the "Robot software" page are a thin capability, hidden unless the update service finds more than one profile for a unit: a manifest per profile (name, plain description, what it adds and costs, size, memory table, build number, board id), `release.sh` signing each, and a switch as a normal signed update with first-boot trial and rollback. Not built: there is one image. The board id already travels in the signed header (`signed-update-header.md`); a profile switch at the same build number needs a firmware-track rule agreed there first.
