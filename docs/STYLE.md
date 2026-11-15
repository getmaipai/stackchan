# Writing style

0. The project is called "MaiPai for StackChan" in every doc. Say "the robot" for the hardware and "MaiPai Home" for the hub.
1. Write for the robot's owner. Short sentences, plain words, concrete numbers and names.
2. User docs read at grade 6. Developer docs may use technical terms, defined once.
3. Until v1.0.0 ships, user docs describe the finished product and the README carries a Draft notice. Remove the notice at release. Developer docs say what is confirmed on a unit.
4. Every error message says what went wrong and what to do next, in terms the person sees.
5. No em dashes. Use a comma, a period or a colon.
6. No filler vocabulary. The hygiene check lists the banned words.
7. No exclamation points. No rhetorical questions as transitions.
8. Do not mention, compare to or credit other projects. Required notices live only in LICENSE, NOTICE and THIRD-PARTY.md.
   The two upstream firmware bases are named only in `docs/dev/build-from-source.md`.
   One exception (owner rule, 2026-11-15): the README and the getting-started page link the official StackChan project, its docs and its store page, and credit M5Stack as the robot's maker. The one comparison lives in `docs/user/compare.md` (owner request, 2026-11-15): facts only, each taken from the official README or docs and dated, never a claim about what the official firmware lacks that we have not checked.
9. Examples use 192.0.2.x addresses, example.com and persona names. Never real names, addresses or hostnames.
10. Say "snapshots" for camera images, because the resolution is low.
11. MaiPai Home appears only as an optional brain.
12. Docs change in the same commit as the behaviour they describe.
13. Run `bash scripts/check.sh` before landing. It must print "hygiene: ok".

## Lights and sounds

Every feature page that lights the ring, changes the face or plays a tone has a "Lights and sounds" table: what you see (colour, pattern, face), what you hear, and when. `docs/user/lights-and-sounds.md` is the one master list. A new light or tone is added to both places in the same commit.

## Tags

A feature that needs MaiPai Home carries the tag `<span class="home-tag">Needs MaiPai Home</span>` where it is first described (heading line or feature list) and in the compare table. The site draws it as a small label. On GitHub it shows as plain text.

A feature that is designed but not built carries `<span class="planned-tag">Planned</span>` in the same places. Remove the tag when the feature runs on a unit.

## README and page shape

A README opens the way successful firmware projects do:

1. One sentence: what it is, for which device, and the benefit. No slogans and no claims about other products.
2. A short "why use it" list. Each point is a fact with a number or a name.
3. A table of what you get, one row per area, each row linking to its page.
4. A screenshot near the top and one per major feature. Use an image, never a text note, even before the real capture exists.
5. A quick start in a few lines, close to the top, then a link to the full steps.
6. Docs, contributing, license and an independence note at the bottom.
