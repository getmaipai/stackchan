# Languages

Spanish is the first non-English language (decision 25). One firmware image. Language is chosen at run time.

## The setting

`language` in `robot.toml`, the web settings page and the unit. Changing it writes the host config and pushes it to the unit.
No reflash and no file edit. Every build step runs a language check: the same spoken turn and the same captions pass in English and Spanish.

## Layers, easiest first

1. Speech and replies: host side. Needs a speech-to-text model, a text-to-speech voice and a language model that handle Spanish.
   The persona prompt is written in Spanish. Verify quality on the owner's actual models before promising it.
2. Web app, setup flow and flasher: translated strings from one message catalog source shared with other MaiPai products.
3. On-screen text and captions: a language pack in the assets partition. Spanish needs accents and the inverted marks. A small extra glyph set in the Latin font.
4. Spoken numbers, dates, times and currency go through the speech normalizer ("las tres y media", not digits). Dates and clock follow the language, day-month-year, 24 hour.
5. Voice commands on the unit: the command model is trained per language. Spanish commands (`para`, `silencio`, `cállate`, `no te muevas`, `muévete`) need a model that supports them. Not verified.
   Fallback: say the wake word first, then the command. The host handles it. This loses the no-wake-word benefit.
6. Wake word: a language-specific model file. The current phrase is English. A Spanish phrase needs a trained model. Fallback: keep the English phrase, which works as a name.
7. Docs and error messages: English first, Spanish translation later. Every error still says what went wrong and what to do, in Spanish too.

## Web settings page

- Spoken language, screen language (default same as spoken), wake word from installed packs, voice list for that language, clock and date format, and a test button that speaks and captions one line.
- Packs show install state (installed, downloadable, size). Install is one click and follows the memory gate. A pack that does not fit says so and names what to remove.
- Limits are stated plainly on the page: which features fall back when a language has no on-device wake word or command model.
- The page itself switches language at once and remembers the choice per browser.

## Fonts and scripts

- Latin plus accents ships by default.
- Chinese, Japanese and Korean text ships as an optional font pack loaded only when selected, or is rendered on the host as small bitmaps. Offline those languages fall back to tones and Latin.
- Right-to-left screens are out of scope for the small screen. Speech works for any language the host supports.

## Rules

- One language pack, one sound pack, one face pack active at a time. Others stay compressed in flash.
- Tones are language-free, which helps accessibility.
- Alarm and timer labels are spoken in the chosen language, off by default for alarms.
- The low-battery request and offline phrases come from the pack, rendered by the owner's own voice at setup.
- Language and safety rules run in code on model output, not only in the prompt. Every speech path goes through the same normalizer.
- Thinking cue is tone and dots, so Spanish needs no filler phrases.

## Open

- Whether the unit's speech library supports Spanish commands and a Spanish wake word.
- Which fallback the owner accepts if not.
- Whether non-Latin captions pass the memory gate or fall back to the web app.
