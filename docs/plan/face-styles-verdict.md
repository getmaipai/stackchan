# Face styles: what fits and what does not

Measured 2026-11-19 on the host renderer in dirty-area mode (`scripts/virtual-unit/face_style_cost.py`): each style stepped one 33 ms frame at a time for 4 seconds in five states (neutral, happy, surprised, shocked, speaking), the pixels flushed in each frame kept. A frame costs 0.733 ms per 1,000 pixels (the bench's flat box, `UNIT_BOX_US` in `games_cost.py`). Nothing here is read on a unit; the cost row is an estimate from the bench constant.

**Rule used for a face:** mean at most 6,500 pixels a frame, worst frame at most 30 ms (40,900 pixels), one 33 ms step. The 16,000 pixel worst-frame rule is for game loops; the shipped default, Big eyes, already reaches 22,000 on a blink.

| Style | Neutral mean / worst px | Speaking mean / worst px | Surprised worst px | Shocked worst px | Worst frame ms | Verdict |
|---|---|---|---|---|---|---|
| Big eyes (base) | 3343 / 22386 | 3338 / 22386 | 30130 | 25250 | 22.1 | fits, the reference |
| Stock (base) | 189 / 1620 | 189 / 1620 | 1620 | 1620 | 3.4 | fits |
| Minimal (base) | 479 / 3150 | 479 / 3150 | 4408 | 4758 | 3.5 | fits |
| Classic | 1890 / 9702 | 1890 / 9702 | 14804 | 15622 | 11.5 | fits |
| Eyes only | 1942 / 14450 | 2103 / 15390 | 19902 | 22698 | 16.6 | fits |
| Round | 2643 / 17250 | 2643 / 17250 | 22525 | 23634 | 17.3 | fits |
| Cat | 1275 / 9522 | 1275 / 9522 | 13398 | 15390 | 11.3 | fits |
| Robot | 858 / 9954 | 858 / 9954 | 13430 | 15486 | 11.4 | fits |
| Sleepy | 1713 / 14442 | 1713 / 14442 | 19838 | 22230 | 16.3 | fits |
| Pixel | 541 / 9798 | 541 / 9798 | 13746 | 15770 | 11.6 | fits |
| Heart eyes | 0 / 0 | 0 / 0 | 0 | 0 | 0.0 | fits, with two parts left out (below) |
| Rubber hose | 3709 / 23750 | 3709 / 23750 | 28886 | 30076 | 22.0 | fits, close to Big eyes |
| Neon anime | 2964 / 20806 | 2964 / 20806 | 28122 | 31970 | 23.4 | fits, close to Big eyes |
| Cartoon | 3227 / 16902 | 3251 / 16902 | 22816 | 24354 | 17.9 | fits, lighter than Big eyes |

Memory: no style costs anything until installed; see `docs/design/face-styles.md`. A style change is one full redraw (56 to 65 ms) for every style alike.

## What did not fit, and what was done

- **A beating heart eye.** The base Love face beats the hearts at 1.2 Hz. As a style that always beats, Heart eyes cost 22,000 pixels a frame on average and 50,000 on its worst frame (a full screen, 36 ms). The style keeps hearts that do not beat or blink; the Love mood in other styles is unchanged.
- **Heart drift.** With the gaze drift left on, Heart eyes still redrew both hearts every few frames (8,300 pixels mean). Drift is 0 in its recipe.
- **A glow made with a blurred shadow** (Neon anime). A blur of 14 costs 21.8 ms for a small box alone (`UNIT_BOX_US`). The glow is a wider translucent rounded box behind the ring instead.
- **Moving sparkles** (Neon anime). A twinkle redraws a rectangle every step. The four sparkles are still.
- **A film-grain or paper texture** (Rubber hose). A full-screen pattern is a 56 to 65 ms full redraw whenever anything moves. Not drawn.
- **Hands, gloves and noodle limbs** (Rubber hose). They need the body, which the face zone does not have. The look is carried by the eyes, grin, cheeks and tuft.

## Not proven

Run on a unit: the frame cost (K is the bench's constant), the internal RAM of the writable row and of a decorated style, installing a style through `self.assets.install`, and the first draw after a style change. The firmware track wires the install and applies the recipe; the patch only adds the reader, the row and the drawing.

## Cartoon: what was left out

- **Arched brows.** Brows are straight bars (a curved one needs two segments per brow and a redraw of both on every gaze move); tilt and lift carry the mood.
- **A glossy gradient or a blurred highlight.** A gradient fill costs 9 ms and a blur 14 to 22 ms a box (`UNIT_BOX_US`); the eye has one flat white oval and one small flat highlight.
- **Eyes drawn from the picture path.** The picture path knows two colors, so a cartoon eye is drawn from its shape list; it still measures lighter than Big eyes.
- **A tongue that moves with the voice.** The tongue shows whenever the smile is open (happy, joy, excited, speaking); it does not wag.
- **The navy background as part of the style.** A style has no background of its own; the character file names it (`#0f1b3d`).

## Face ideas from the audits

Sources: `home/data-scratch/reports/stackchan-own-repo-plan-2026-11-15.md` (the research of other robots and community projects, section "Feature research: other bots and Reachy Mini"; the Apple home display audit is `stackchan-homeview-audit-2026-11-15.md`), `docs/design/firmware-v1-cut.md` row 132-expressive-faces, `docs/dev/stackchan-faces-2026-11-14.md`, `docs/design/features.md` "Ideas added after a market audit". Ideas only; no other project's art, names or code is used.

| Idea (source) | What we built or decided | Verdict |
|---|---|---|
| Seven expressive faces: joy, content, excited, shocked, curious, love, worried (firmware-v1-cut 132) | Content and love existed. Joy, excited, shocked, curious and worried are mood rows in patch UXF02, drawn by every style | Built, fits: no new shape, no new memory |
| Emoji-to-face reactions (a community assistant project, plan line "Emoji-to-face reactions") | The host would map an emoji at the start of a reply to one of the 17 moods; nothing to draw | Host mapping, not a look; the moods it needs now exist |
| Mirror mode copies your expression (the maker's app, plan line "Mirror mode") | Needs the host to read expression from a camera and send a mood name | Host work; the 17 moods are its vocabulary |
| Idle life: blink, breath, drift, microsaccades, gaze (a community firmware project) | Blink, drift and gaze already run in every style | Have |
| Expression clips mapped to the face (a robot's open emotion library, 81 clips) | Motion and sound need a head with more joints; the face half is the mood set above | Moods built; clips skipped |
| Pet that depends on care (plan item 11, "Reachygotchi style pet") | Content, tired and sleepy exist; the care record is host work | Have the looks |
| Bedtime fading face (plan item 14) | Sleepy style (lid floor 38 percent) plus the time-of-day lid cap (patch F03) | Built as the Sleepy style |
| Time-of-day faces (home display audit) | Patch F03, in the image | Have |
| Photo-frame face (home display audit) | Deferred until the memory gate has headroom | Not built |
| Timers, weather, clock and state on the face (plan items 5, 8, 20) | Screens and overlays, not face styles | Have or planned elsewhere |
| Big-eyes face pack, minimal pack (feature table) | Big eyes and Minimal are base styles | Have |
| Wink, silly, serene, dizzy, listening (stackchan-faces-2026-11-14) | Accents and decorators on any style: wink, tongue, shut eyes, dizzy decorator | Have |

No list of face styles from other GitHub projects exists in the repo, the notes folders or the earlier sessions' transcripts. What the audits hold is behaviors and the expressive set above, so the ten new styles come from the owner's older list (round, cat, robot, sleepy, pixel, heart eyes) and the two requested looks.
