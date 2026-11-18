# The brain choice at first run: what the robot sends and what the host does (2026-11-18)

Agreed between the playground (robot screens, patch UX12) and the app track (host side). Source: owner decision 12 of 2026-11-18 (`docs/design/decisions.md`): a friend picks one of three ways to get a brain; the friend test needs all three to work without a terminal.

## What the robot says
Step 4 of the first run, in all six languages: **"Where should my brain live?"** with three buttons:
| Button (English) | `first_run_done` `mode` | Word the host gets (`FirstRunNames.on_brain`) | Highlighted by default |
|---|---|---|---|
| MaiPai Home | 0 | `home` | when a hub address is already saved on the unit |
| My own servers | 1 | `own` | never |
| Set one up for me | 2 | `setup` | when no hub is known |
A small Skip on the step takes the highlighted answer. The answer is saved on the unit (`mp_firstrun` key `mode`) and sent once in the `first_run_done` event next to `lang` and `name`. The robot changes nothing else because of it.

## What the host does with it (the app track builds this)
- `home`: open the Home pairing path (the six digits), no addresses to type.
- `own`: the first-run page of the host asks for the three addresses (language model, speech to text, text to speech) and checks them (`stackchan check`).
- `setup`: the host offers the minimal local stack (small defaults for all three, downloaded not vendored, a plain progress page, a removal option).
`host/maipai_body/first_run_name.py` already gives the word to any handler appended to `FirstRunNames.on_brain` (called with the unit's Device-Id and the word); until a handler exists the host only logs it and keeps the brain set in `robot.toml`.

## Settings page text (app track)
The settings page needs one plain section with the same three names and the same hint, so the page and the robot agree: "Where should my brain live?", "MaiPai Home", "My own servers", "Set one up for me". Its other strings go through the translation pack (`docs/dev/translation-review/`). Not yet in the page: this note is the agreement; the robot side is landed.

## Open
- A person who skipped the question on the robot should see it again on the settings page (the host knows `first_run_done` had `mode` set by Skip only if the unit says so; the unit does not tell skip from a tap today). Decision for the app track: ask again on the page when `brain` is still the default.
- The unit's answer is a record of intent, not a switch: changing the brain later is a settings page job.
