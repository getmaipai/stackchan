# Characters

Status: file shape, six default characters and the check are built; the host store, the dashboard picker and the edit page are the app track's (hand-over: `characters-state.md` in the session notes).

A character is who the robot is, in one small file: a name, a short persona for the language model, a default face (a style, a color, a background) and voice settings. One person picks a character and the robot looks, talks and sounds like it. This extends decision 31 (a persona names a default face recipe) and sits beside the style recipe kind (`docs/design/face-styles.md`).

Not the same as a character pack (`docs/design/character-pack-format.md`), which is a set of pictures for the face. A character may use any face the unit can draw, picture packs included later; today it names a style.

## The file

`schema/character.json` is the one definition (JSON Schema). A character file is under 1,024 bytes as compact UTF-8; `scripts/character-check.py` checks both the schema and the size.

| Field | Meaning |
|---|---|
| `schema` | `maipai.character/1` |
| `id` | 2 to 12 lower-case letters, digits or underscores. The bank's ids come from the persona roster; a copy picks its own |
| `name`, `about` | Shown in the picker. `about` is one plain sentence, 80 characters at most |
| `based_on` | The id this one was copied from, when it is a copy |
| `lang` | `en`, `es`, `fr`, `de`, `pt` or `it` |
| `persona` | Plain text for the model, 480 characters at most |
| `face` | `style` (one of the 13 style names), `color` and `background` (`none`, a palette name or `#rrggbb`, the face settings as they are) |
| `voice` | `speed` 0.75 to 1.5, `pitch` -12 to 12 semitones (`speech/pitch.py`), `ids.local` and `ids.home` voice ids by route; a missing id means that route's default |
| `wake` | Optional wake phrase. It needs a trained wake model, so no default character has one |

The face style is named, never embedded. A base style (Big eyes, Stock, Minimal) is always there; any other is a style asset the dashboard installs first, by name. The unit learns nothing new: it receives the same face settings it already takes, so a character costs the unit no memory.

## How a character reaches the robot, by route

| Part | Own LLM | Home | Hosted vendor |
|---|---|---|---|
| Who owns the list | The host (`robot.toml` folder of files) | Home; same file shape | The host, face part only |
| Persona text | Sent to the model as the system prompt (`[llm] persona`) | Home's brain uses it | Hidden: the vendor's persona is the vendor's |
| Face, color, background | Host sends them to the unit with the face settings | Home names them; the robot shows them | Applies, same as own LLM |
| Speed and pitch | Host applies them to the voice | Home applies them | Hidden |
| Voice id | `ids.local` on the person's own speech engine | `ids.home`: stock or cloned voices, which Home owns and the host never stores | Hidden |
| Language | Sets the language setting | Same | Sets the unit's screen language only |

The edit page shows only what the route uses. A hosted-vendor person sees name, face, color and background; the persona, voice and wake fields are not shown and the host does not send them anywhere.

## The six that come with the robot

Atlas, Bruno, Clover, Cosmo, Daisy and Ember (names from the persona roster of the org standards). Each pairs one style with one color, a persona and voice settings. They are in `host/maipai_body/characters/`, signed with the rest of the catalog when they go in the bank.

| Character | Face | Color | Voice speed, pitch | In a sentence |
|---|---|---|---|---|
| Atlas | Big eyes | sky | 1.0, 0 | Explains things step by step, calm and clear |
| Bruno | Robot | amber | 0.95, -3 | A steady helper: short answers, the next step first |
| Clover | Cat | mint | 1.1, +2 | Playful and curious, loves small questions |
| Cosmo | Rubber hose | coral | 1.05, +1 | An old-time cartoon cheerleader who tells jokes |
| Daisy | Sleepy | lilac | 0.85, -1 | Gentle and sleepy, good for bedtime stories |
| Ember | Neon anime | rose | 1.15, +2 | Bright and bold, full of energy and encouragement |

Atlas works with no install. The other five need their style installed (installed set, decision 17); until it is, the host shows the character with its style's name and the robot keeps the face it has.

## Customizing

**Copy, then edit.** The picker's Copy makes a new file with `based_on` set to the original and a new id; the original is never changed. The edit page changes any field and the host checks it with the same schema before saving. A copy is an `owner` file: it stays on the person's own host and robots, shows a "made at home" label and is never signed. A character from the bank is `signed` and read-only.

## The bank

A character is a bank entry like a style recipe (`docs/plan/face-parts.md` section 4): the file plus a manifest (id, kind `character`, title, license CC0-1.0 or CC-BY-4.0, author, source, SHA-256 of the file, signing key id) and a thumbnail that is the render of its face. Rules for entries are the style rules: original work, no look-alike or name of another product's character, plain words, a human read of the persona.

## Safety

The persona is text for the model, not a guarantee (`docs/design/own-llm-brain.md`, and the persona note in `docs/design/decisions.md`). A character cannot turn off the lock, the child gate, the movement limiter, the privacy marks or the cues: it carries no field that could. Family rules and age rules stay with Home.

## Checks

`python3 scripts/character-check.py` validates every file in `host/maipai_body/characters/` (schema, size, the style name exists, the file name matches its `id`). `scripts/virtual-unit/character_sheet.py` renders each character's face in six moods in its own color.
