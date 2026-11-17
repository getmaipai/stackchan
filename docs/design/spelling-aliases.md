# Spelling aliases (owner rule, 2026-11-16)

American spelling everywhere: color, behavior, center, gray, license, canceled. This note lists the only places where an old British
spelling stays in code, and why. `scripts/spelling-check.py` (run by `scripts/hygiene-check.sh`) fails on any other British spelling;
`scripts/spelling-allow.txt` holds the same list as rules.

## Host keys: read old, write new

`host/maipai_body/spelling_aliases.py` is the one place. `upgrade_keys` renames an old key when the host reads it:

| Old key | New key | Where it can still arrive |
|---|---|---|
| `colour` | `color` | saved face file, people file, an older settings page, `--colour` on the CLI, a game pack file |
| `listen_light_colour` | `listen_light_color` | saved unit settings, an older settings page |
| `fx_colour_mode` | `fx_color_mode` | saved unit settings, an older settings page |
| `licence`, `licence_checked` | `license`, `license_checked` | an older offline voice manifest (`speech/offline_clips.json`) |

The host writes only the new key. When both are present the new one wins.

## Unit keys: the flashed unit keeps its spelling

The unit's firmware reads `colour` in `self.face.set_config` and `listen_light_colour` and `fx_colour_mode` in `self.prefs.set`
(NVS keys are limited to 15 characters, so they are never renamed by a host change). The host builds those calls with
`to_unit_keys`, which maps the new names back to the unit's names in one table (`UNIT_KEYS`). `FaceConfig.to_wire()` and
`PrefsService._send` are the two call sites. The unit's read-back (`colour`) is compared against the same table.
When a unit update accepts both spellings the table changes in one place and the host sends `color`.

## Left alone on purpose

- Wire names owned by another side: the unit event `music_clip_cancelled`, the Stack error code `turn_cancelled` and its `cancelled`
  reply field, `honoured_by` in the indicator standard shared with the robot, `licence` in the shared asset records
  (`link/assets.py`, spec-vendor) and in `assets/phrases/phrases.json`.
- `asyncio.CancelledError` and `concurrent.futures.CancelledError`, and the HTML attribute `aria-labelledby`: standard names.
- `host/spec-vendor/`: vendored text from the shared spec.
- `firmware/patches/`, the bundled `host/maipai_body/bodies/stackchan/firmware/` tree, `scripts/fw-face-render/` and
  `host/tests/firmware/*.c`: firmware identifiers (`mf_set_colour`, `MP_FX_COLOUR_MODE`, `colour_mode`) and patch text owned by the
  firmware session. A patch comment or string is changed only in a patch's own revision and only after a replay shows it still
  applies, because a later patch may carry the line as context.
- Non-English text: a word that is also correct in another language (French "Licence" on the About card).
