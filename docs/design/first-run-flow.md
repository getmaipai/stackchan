# First run on the robot (plan step 7)

Status: design plus patch UX05a (the step rules), UX05b (the screens), UX11 (StackChan first on the name step) and UX12 (skip, the brain question, the last screen). The unit draws these screens itself and works with no phone: the first start of a unit with no saved choice shows them once. The calls that start the flow and save its answer are the firmware track's (maipai_firstrun_show(), a saved record); this note fixes the words and the order.

## Placement (docs/dev/scope-core-vs-home.md)

Basics the robot must do alone, so built small in the core: language, a name, Wi-Fi, how to think (a Home hub or an own model), and the privacy promise in plain words. Nothing here duplicates a Home feature.

## The six steps

| Step | Screen words (English / Spanish) | Answer |
|---|---|---|
| 1 Language | "Hello · Hola · Bonjour · Hallo · Olá · Ciao" (the same line in every language); six tiles, each language's own name: English, Español, Français, Deutsch, Português, Italiano; English highlighted; a small Skip | language code |
| 2 Name | "What should I be called?" / "Como me llamo?"; a wide first tile **StackChan** (the product's own name, highlighted as the default), then six tiles: Astro, Clover, Ember, Nova, Pippa, Rover; hint "Type your own name later, on the settings page." (in each language) | name index 0 to 6 (6 is StackChan) |
| 3 Wi-Fi | "Let's join your Wi-Fi" / "Conectemos tu Wi-Fi"; the existing Wi-Fi setup cover takes over (hotspot name and address); skipped when the unit already has Wi-Fi | none |
| 4 Brain | "Where should my brain live?"; three buttons, the three ways of decision 12: "MaiPai Home", "My own servers", "Set one up for me" ("Set one up for me" highlighted unless a hub is already known, then Home); hint "Your voice stays in your home either way."; a small Skip (takes the highlighted answer) | mode: 0 home, 1 own servers, 2 set one up for me |
| 5 Privacy | "Private by design" / "Privado por diseno"; "Your voice and pictures stay in your home." "Nothing goes to the internet unless you turn it on."; one button "Got it" / "Entendido" | none |
| 6 Done | "All set!" for a second and a half, when the answers are saved | marks first run done |
| 7 What now | "What now?": say Hi, Stack Chan; change anything on the settings page at the address shown (the host the unit talks to, port 8051; a plain sentence when the unit has no host saved); on a phone, the phone code on that page; one button, or it closes by itself after two minutes | none |

Back is a small arrow at the top left on steps 2, 4 and 5; step 1 has none. A step with a hands-off screen (3) goes forward when the existing flow reports done. A long press anywhere on steps 1 to 5 shows nothing extra: no hidden menus.

## Rules the core keeps (maipai_firstrun_core.h)

- The order above, with step 3 skipped when Wi-Fi is already set, and step 4 pre-selecting Home when a hub is already known.
- A language choice at step 1 changes the words of every later step at once.
- Back never loses an answer; leaving the flow (power off) keeps the answers given so far and resumes at the first unanswered step.
- The flow ends only at step 6; the result is {language, name index, mode}.

## Proof

Core: PC test. Screens: golden frames from the unit's own drawing code in `host/tests/golden/screens` (first-run-1 to first-run-6, plus a Spanish step 4).


## The name step (patch UX11, 2026-11-18)

- **StackChan is the first choice and the default.** It is a wide tile at the top, highlighted until another name is picked; the other six sit under it. A tap picks a name and goes on to the next step, as every step does.
- **The saved value is the index exactly as picked.** Astro to Rover keep 0 to 5, so a robot that finished the first run before keeps its meaning; StackChan is 6. The unit saves it (patch SF09, key `name` of `mp_firstrun`) and sends `first_run_done` with `{"lang", "name", "mode"}`. This is stored on the unit, as before: UX11 adds no new storage and no new wiring.
- **No custom name on the robot, and why.** The flow has touch tiles and no keyboard; a typing screen on a 320 by 240 glass is the part of setup people dislike most. The hint says where to type one (later, on the settings page), in all six languages.
- **The host takes the name.** `host/maipai_body/first_run_name.py` turns the index into the unit's name when the unit has none saved on the settings page; a name typed there is never replaced. The settings page, the unit list and the parent view show it; a unit with no name shows `StackChan` (two units with the same name get the last five characters of their Device-Id so the unit picker tells them apart).
- **Proof:** the core test (`host/tests/firmware/firstrun_core_test.c`, run by `test_first_run_core.py`), golden frames `first-run-2-<language>.png` for all six languages, and `host/tests/test_first_run_name.py` for the host half.

## The first run through a parent's eyes (findings of 2026-11-18 and what patch UX12 did)

Read as a person who has never seen the robot, step by step. Findings 1 to 3 and 6 to 7 are fixed by UX12; the rest are decisions or limits.
1. **Skip.** Fixed: a small Skip at the top right of the language and name steps (English, StackChan), on the brain step; the robot works with the defaults and everything stays changeable on the settings page. The Wi-Fi step is the base's setup cover and has no skip; a unit with no Wi-Fi cannot reach a host, so it is not offered. Privacy has its one "Got it".
2. **Step 1 was English only.** Fixed: the title is the same line in six languages and the tiles are each language's own name.
3. **"How should I think?"** Fixed: "Where should my brain live?" with the three ways of owner decision 12 (2026-11-18). What the step means in the code: the answer (0 home, 1 own servers, 2 set one up for me) is saved on the unit and sent in `first_run_done`; nothing on the robot changes what it does because of it. The host hands the word to whoever registers with `FirstRunNames.on_brain` and logs it; what each way does on the host (pairing with Home, asking for the three addresses, installing the minimal stack) is the app track's build, agreed in `docs/plan/first-run-brain-choice.md`. Until then the brain the host uses is `brain` in `robot.toml`.
4. **Defaults.** English (step 1), StackChan (step 2) and, on step 4, Home when a hub is known else "later" are all highlighted now: one tile is always highlighted. A tap on any tile still picks it and goes on.
5. **A tap also advances.** Unchanged: back fixes a wrong tap and keeps the answer.
6. **Progress.** Unchanged: there is no "2 of 5"; the back arrow is the only hint.
7. **The end.** Fixed: after "All set!" a last screen says what to do next (above). No QR code on the robot: the LVGL QR widget is not built into this firmware and costs memory; the settings page shows the phone code as a QR.
8. **Wi-Fi leaves the numbered flow** for the setup cover and comes back by itself. Unchanged.
9. **A family name needs the settings page** afterwards; the hint on the name step says so.
10. **Fixed (2026-11-18).** The settings page words for the Family and safety card, the pairing code card and the phone card (including the phone code labels) now have French, German, Portuguese and Italian drafts (`host/maipai_body/i18n_family.py`), marked as machine drafts for a speaker to read.
