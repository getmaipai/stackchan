# What Home must send or accept for StackChan (spec-first record, 2026-11-18)

Written from the host code on `main`. This is the record the spec and Home work from; Home's repository is not touched from here. Each row says what the StackChan host does today and what is missing.

## 1. Commands Home sends to the host (command channel)

| Command | Payload | State |
|---|---|---|
| `settings_changed` | the unit's changed setting keys | Works today. |
| `child_present` | `{ "device_id"?: string, "present": bool, "seconds"?: number (default 300) }` | The host accepts it and the command bus then limits the model's sounds to the quiet set while it holds. Home sends nothing yet. Without a `device_id` it applies to every connected unit. A note expires after `seconds`, so Home must repeat it while a child stays near. |

## 2. What Home gets from the host on a turn

- **Speaker evidence:** the StackChan path attaches `speaker_evidence` only when the speech result carries one (`result.speaker_evidence`, shape from `maipai_body/speaker_evidence.py`: person id, basis, level). The StackChan own-microphone path has no voice recognition of its own, so Home receives none unless Home's speech service attaches it. Needed from Home: attach a confirmed `person_id` to the speech result.
- **Age band:** the host sends no age band on robot turns. Needed (step 9 of the plan): Home returns the band (`adult`, `teen`, `child`) with the speaker evidence, and the host passes it to the command bus (`child_present`) and to the notes package so a child never has notes.
- **Presence:** none sent. The host has no recognition of who is near; Home's own presence is the source for `child_present`.

## 3. The update path (signed)

Host calls, all with the unit's session cookie:

1. `GET /api/devices/me/firmware-update?current=<version>` returns `{ "available": bool, "version": string, "size": int, "sha256": hex }`.
2. `GET /api/devices/me/firmware-update/app.bin` returns the image bytes (size and sha256 must match step 1).
3. **New, required:** `GET /api/devices/me/firmware-update/app.bin.sig` returns the detached Ed25519 signature over the image bytes (raw 64-byte signature, the same one `stackchan flash` and the release manifest use). Status 404 or an empty body means "unsigned".

The host verifies the signature with `[update] trusted_key` in `robot.toml` and serves the signature to the unit beside the image. No trusted key, no signature, or a bad signature means the update is refused and nothing is served. Home must therefore publish the release's `.sig` file next to each image it offers and must never offer an image it cannot sign.

## 4. Pairing

The host's discovery is off unless `brain = "home"` or a hub URL is set (`MAIPAI_HUB_URL` or `[home] url`). Home pairs with the host through the existing code flow. A unit already paired is not re-paired by a code; Home's repair screen should say to forget the unit first.

## 5. Not asked of Home

Memory notes, the Home Assistant package and the coding companion are local packages and need nothing from Home. When Home is paired, Home's memory replaces the notes package (decision 1d of 2026-11-18); the notes package stays off.
