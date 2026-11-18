# First run on the robot (U-4, plan step 7 E)

Status: design plus patch UX05a (the step rules) and UX05b (the screens). The unit draws these screens itself and works with no phone: the first start of a unit with no saved choice shows them once. The calls that start the flow and save its answer are the firmware track's (maipai_firstrun_show(), a saved record); this note fixes the words and the order.

## Placement (docs/dev/scope-core-vs-home.md)

Basics the robot must do alone, so built small in the core: language, a name, Wi-Fi, how to think (a Home hub or an own model), and the privacy promise in plain words. Nothing here duplicates a Home feature.

## The six steps

| Step | Screen words (English / Spanish) | Answer |
|---|---|---|
| 1 Language | "Hello! Pick your language" / "Hola! Elige tu idioma"; six tiles: English, Espanol, Francais, Deutsch, Portugues, Italiano | language code |
| 2 Name | "What should I be called?" / "Como me llamo?"; six tiles: Astro, Clover, Ember, Nova, Pippa, Rover; hint "You can change it later." | name index 0 to 5 |
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
