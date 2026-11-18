# First run on the robot (plan step 7)

Status: design plus patch UX05a (the step rules), UX05b (the screens) and UX11 (StackChan first on the name step). The unit draws these screens itself and works with no phone: the first start of a unit with no saved choice shows them once. The calls that start the flow and save its answer are the firmware track's (maipai_firstrun_show(), a saved record); this note fixes the words and the order.

## Placement (docs/dev/scope-core-vs-home.md)

Basics the robot must do alone, so built small in the core: language, a name, Wi-Fi, how to think (a Home hub or an own model), and the privacy promise in plain words. Nothing here duplicates a Home feature.

## The six steps

| Step | Screen words (English / Spanish) | Answer |
|---|---|---|
| 1 Language | "Hello! Pick your language" / "Hola! Elige tu idioma"; six tiles: English, Espanol, Francais, Deutsch, Portugues, Italiano | language code |
| 2 Name | "What should I be called?" / "Como me llamo?"; a wide first tile **StackChan** (the product's own name, highlighted as the default), then six tiles: Astro, Clover, Ember, Nova, Pippa, Rover; hint "Type your own name later, on the settings page." (in each language) | name index 0 to 6 (6 is StackChan) |
| 3 Wi-Fi | "Let's join your Wi-Fi" / "Conectemos tu Wi-Fi"; the existing Wi-Fi setup cover takes over (hotspot name and address); skipped when the unit already has Wi-Fi | none |
| 4 Brain | "How should I think?" / "Como debo pensar?"; two big buttons: "Pair with MaiPai Home" / "Use my own model"; hint "Both stay in your home." | mode: home or own |
| 5 Privacy | "Private by design" / "Privado por diseno"; "Your voice and pictures stay in your home." "Nothing goes to the internet unless you turn it on."; one button "Got it" / "Entendido" | none |
| 6 Done | "All set!" / "Todo listo!" for 2 seconds | marks first run done |

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

## The first run through a parent's eyes (findings, 2026-11-18)

Read as a person who has never seen the robot, step by step, from the golden frames and the flow code. Not changed by UX11; for the owner and the firmware track to decide.
1. **No skip, no "not now".** Every step wants a tap; a person who just wants to try the robot cannot go on without choosing a language, a name and a brain. A visible "Skip" on steps 2 and 4 (defaults: StackChan, own model) would match what people expect.
2. **Step 1 is English only until a language is picked.** "Hello! Pick your language" is the one line a person who reads Spanish sees first. A line in each language (or flags) would help.
3. **"How should I think?" is a hard question.** The two buttons say "Pair with MaiPai Home" and "Use my own model"; a parent has no idea what either means. A one-line plain hint under each ("I use my own computer" / "I use your MaiPai Home") would do.
4. **Defaults differ by step.** English is highlighted at step 1, StackChan now at step 2, but step 4 highlights nothing unless a hub is known; the pattern "one tile is always highlighted" would be easier to learn.
5. **A tap on a tile also advances.** There is no confirmation and no "Next"; back (the arrow) fixes a wrong tap and keeps the answer, which works, but a person who taps by accident while looking for a way to scroll will not know what happened. It is consistent through the flow.
6. **No sign of how long it is.** Five steps and no "2 of 5". The back arrow is the only hint that there is a before.
7. **The end is two seconds of "All set!" and then the face.** Nothing says what to do next. One line ("Say Hi, Stack Chan") on the last screen would close the loop.
8. **Wi-Fi is the one step that leaves the flow.** It hands over to the setup cover (the robot's hotspot, an address and a code) and comes back by itself; the title of that cover is not part of the numbered flow.
9. **The name is a choice among names, and now also the product's name.** A person who wants a family name has to go to the settings page afterwards; the hint says so.
