# Content pantry: jokes, riddles, trivia and stories the unit keeps (design, 2026-11-18)

Placement: unit (shelf reader, heard list, telling screens: firmware track), host (generation, library, sync: app track, own-LLM package), Home (takes over when paired). Design only, no code. Serves owner decisions 24 (offline plan), 27 (model-powered games), 17 (installed set, typed asset store) and 15 (everything must fit). Companion: `docs/design/model-games.md`. Evidence for the gaps: `docs/plan/offline-audit.md`.

**Bottom line.** The unit keeps a small shelf of text records for each kind and language in the asset store, about 200 KB for two languages, read in place from flash, zero internal RAM. The host fills the shelves from the owner's model, filters and dedupes, and refills one shelf at a time when the unit is idle and reachable. The unit remembers what it told in a small heard list and sends it back in batches. With no host, the unit tells from the shelf with a code-made mumble and captions. With a live model, the pantry is a source of seed ideas and a fallback, never the main path.

## 1. The three states

| State | Host | Model | What tells the joke |
|---|---|---|---|
| S0 unit alone | down or unreachable | none | The unit, from its shelf, with mumble and captions. |
| S1 host without model | up | down (no internet, cloud address, model off) | The host, from its library, through the normal speech path (real voice). |
| S2 connected | up | up | The live model. A shelf record may seed it ("tell a riddle like this one") or fill a gap. |

The shelf on the unit is a copy of the host's library, so S0 and S1 tell from the same pool and the heard list is one list.

## 2. The record

One record is one thing the robot can say. Fields:

| Field | Type | Rule |
|---|---|---|
| `id` | 8 bytes | First 8 bytes of SHA-256 over kind, language, normalized text and answer. Same key rule as the asset store (`sha8`, `docs/plan/installed-set.md` G2). Stable across hosts, so a deleted record stays deleted. |
| `kind` | `joke` `riddle` `trivia` `story` | |
| `language` | code such as `en`, `es` | One language per shelf. |
| `rating` | `kid` or `adult` | `kid` is the default and the only rating a shelf holds unless the owner turns on adult humor (section 6). |
| `text` | UTF-8 | Joke: setup and punchline split by one `|`. Riddle: the question. Trivia: the question. Story: the body, paragraphs split by `|`. |
| `answer` | UTF-8, may be empty | Riddle and trivia: the correct answer, 40 bytes at most. Empty for joke and story. |
| `extra` | UTF-8, may be empty | Trivia only: two wrong answers split by `|`, so the unit can show three tiles. Added to the field list in the task; see open question 2 (answered: it stays). |
| `heard` | u32 | Not in the shelf body. The shelf is never rewritten in place. `heard` is the count of the telling (a running counter, 0 means never). It lives in the heard list (section 5). Stamps are counters, not dates, because the unit may not know the date (`offline-audit.md` row 12). The host maps counters to dates when it syncs. |

Length caps, so one record fits the unit's screen and the shelf budget: joke 160 bytes, riddle question 140, trivia question 140, story 1,600. The text may carry accents. The screen folds them to plain ASCII where the font lacks them (`docs/user/features.md`, "Language packs"), the same rule as every other screen string.

## 3. Where it lives on the unit

The asset store (`docs/plan/installed-set.md` sections B and G) is the home. Nothing new is invented except one kind and one small unit-written item.

**Kind `pantry`.** Added to `schema/asset-kinds.json`: eight slots, cap 40,960 bytes per item (10 sectors), trust `owner` (the host content is the owner's, so the release key cannot sign it; accepted on SHA-256 and length over the paired host link only, the rule the `look` kind already uses, `installed-set.md` B4 "Trust by kind"). One item is one **shelf**: one kind in one language. Eight slots fit four kinds in two languages. Body layout:

- 16 byte shelf header: format version, language code, rating ceiling, record count, index offset.
- An index of 16 bytes per record: `id` (8), kind (1), rating (1), flags (1), text offset (3), text length (2).
- The packed texts.

The unit reads the index in place from flash. When a shelf is in use the index is copied to PSRAM (16 bytes times about 250 records is 4 KB, freed after the telling). Internal RAM cost: under 0.5 KB for the cursor and the choice state. That respects the rule that no persistent internal block is 2 KB or larger (`installed-set.md` A).

**The heard list.** One sector (4,096 bytes) holding a 16 byte header and up to 510 entries of 8 bytes: `id` low 32 bits, flags (heard, deny), the counter, a synced bit. The unit writes it, no one signs it, so it is a second trust class: **unit-written**. The asset store writes a new copy beside the old and flips the directory, so a power cut leaves the old copy (`installed-set.md` B3). Open question 3 asks whether to keep this in the asset store or in the unit's key-value storage; I chose the asset store because the key-value partition is 16 KB shared with Wi-Fi, scores and settings, and a 4 KB blob would take a quarter of it.

Memory gate: while the package is off nothing is installed, no tool is registered and no index is loaded (decision 30, `AGENTS.md` hard rule). The step that adds the kind runs the memory gate.

## 4. Size budget

Pool: 382 sectors of 4,096 bytes, 1,564,672 bytes, shared by every kind (`installed-set.md` C). Record sizes are estimates from the length caps and typical text, English; Spanish is about 15 percent longer.

| Kind | Bytes per record (text, answer, extra, 16 index) | Default stock | Bytes | Sectors |
|---|---:|---:|---:|---:|
| joke | 126 | 200 | 25,200 | 7 |
| riddle | 131 | 100 | 13,100 | 4 |
| trivia | 166 | 200 | 33,200 | 9 |
| story | 1,416 | 12 | 16,992 | 5 |
| One language | | 512 records | 88,492 | 25 |

Two languages: 50 sectors, 204,800 bytes, **13.1 percent** of the pool. Add the heard list (1 sector, 2 during a write) and the largest shelf written beside its old copy (9 sectors) and the peak is 61 sectors, **16.0 percent**.

Sentences of context for those numbers:

- Audio does not fit. The 16 phrase clips average 5,067 bytes each (81,070 bytes in all) for a line of a second or two. A joke of 8 seconds is about 25 KB at that rate [est], so 200 jokes would be about 5 MB, more than three times the pool. Text is the only format that fits.
- The pool is shared. The sum of every kind's cap is about 2.9 MB, so a full look pack plus a full sound pack leave no room for the pantry. The dashboard refuses a combination that does not fit (`installed-set.md` C). The pantry shrinks first: the host builds each shelf to the free bytes it is offered, down to a floor of 8 sectors (32 KB, about 20 jokes, 10 riddles, 20 trivia) below which it asks the owner to remove a pack.
- Nothing is baked into the app image. The first sync happens at setup, when the host is present, and the app image has about 407,000 bytes before the 80 percent rule (`installed-set.md` A), better kept for code.
- Wear: a refill swaps one shelf, 4 to 9 sectors. Three shelf swaps a night for ten years is 10,950 swaps, about 100,000 sector erases, spread over the free sectors by the rotating allocation start (`installed-set.md` C, "Wear budget"). If 40 sectors are free that is about 2,500 erases each, against a typical 100,000 rating [est]. Each swap also writes the directory once, 10,950 writes over a ring of 8, about 1,400 each.

## 5. Sync

**Refill rule.** The host refills a shelf when either holds:

1. **Nightly.** Once a night in the unit's quiet window (the owner's quiet hours, default 02:00 to 05:00 local), when the unit is idle, not in a game, not muted for a reason other than night, and on power or above 50 percent battery.
2. **Low stock.** Unheard records in a shelf fall below 25 percent of the shelf (below 20 records for a small one). The host learns this from `self.pantry.status` on each connect. It refills at the next idle moment, never in the middle of a turn or game.

At most three shelf swaps per window, one at a time, each its own atomic install (`self.assets.install`). A refill keeps unheard records and replaces heard ones with new ones, so the shelf size stays fixed.

**Heard list sync, in batches.** Flash is protected on both sides:

- The unit counts tellings in memory (a list of 64 entries, 256 bytes, internal RAM). It writes the heard sector when the list holds 16 entries, or 10 minutes after the last telling, or before sleep and power off. A telling never writes flash by itself.
- The unit sends new entries to the host in one message on connect and when 16 have built up, never per telling. The host acknowledges a counter; the unit sets the synced bit and keeps the entry until it needs the room (the oldest synced entry is dropped first). The host keeps the full history, so a dropped entry costs nothing: the host just does not offer that record again for the shelf it builds.

Write numbers: 40 tellings a day is about 3 flushes with the 16-entry rule, plus a few idle flushes, call it 8 sector writes a day, 29,200 in ten years. Without batching it is 146,000. Both are under the rating when spread across free sectors, and batching keeps the directory ring (shared with installs) low: 29,200 over 8 sectors is about 3,650 each.

**Proposed tool names** (the firmware track owns the final shape): `self.pantry.status` (per shelf: kind, language, count, unheard, bytes, list sequence), `self.pantry.heard` (entries since a sequence), `self.pantry.deny` (ids to skip), plus the normal `self.assets.*` calls for the shelf itself. They appear only when the pantry is on.

## 6. Host half: generation, filtering, dedupe, library

The host keeps the master library as plain files in its data folder, one JSON Lines file per language and kind, plus a per-unit heard history and a rejected list of ids. Nothing leaves the home.

**Generate.** A package, `host/maipai_packages/pantry/`, off by default and imported only when switched on in `robot.toml` (scope rules in `AGENTS.md`). It asks the configured model for batches of 20 records as JSON, with the kind, the language, the rating, the length caps and a topic mix (animals, food, space, school, nature, music, sports) so a batch does not repeat one theme. It runs when the host is idle and the model is reachable, never during a turn, with a daily cap on model calls set by the owner.

**Filter.** In order, cheapest first:

1. Shape: valid JSON, fields present, length caps, no control characters, language matches (a second cheap model call or a script check on the character set).
2. Rating: a word list for `kid` (no violence, sex, drugs, alcohol, death played for laughs, insults aimed at groups, scary content for stories), then one model pass asked only "is this suitable for a six year old, yes or no". Anything not a clear yes is dropped, not edited.
3. Facts (trivia): the model answers the question without seeing the answer. A mismatch drops the record. Questions about "the latest", "current" or dates after the model's cutoff are dropped.
4. Riddle: one clear answer. The model is asked for a second possible answer; if it gives one, drop it.

This filter curates content the host stores to tell later. It is not a chat filter and does not change the own-LLM brain's rule of decision 13 (the brain adds none). The user docs state this (decision 35).

**Dedupe.** Normalize (lowercase, fold accents, drop punctuation, collapse space). Drop on exact hash. Then drop near duplicates inside a kind and language: token set similarity of 0.7 or more, or the same answer with a similar question (riddles and trivia). Compare against the library, the shelf, the heard history and the rejected list. Keep a dedupe report (count dropped and why) for the dashboard.

**Kid-safe default.** A new install has one rating, `kid`. `adult` records exist only when the owner turns on "Adult humor" in the dashboard, which shows a plain label, builds a separate `adult` shelf, and is refused when the unit is in a child or teen profile (those need Home, decision 6). The unit tells `adult` records only when that switch is on and the unit is unlocked. The persona text of the own-LLM brain is not part of this.

**Dashboard.** One page, "Jokes and games content", in the dashboard's left-tabs pattern (`docs/plan/dashboard-structure.md`): a filter row (kind, language, rating, heard or unheard), a list with the text and the answer, a **Delete** button on each row (rows at least 56 px tall), bulk delete by search term, a **Never again** result: the id goes to the rejected list, a `deny` entry goes to the unit if it is reachable so it is skipped at once, and the next shelf swap drops the record. Also: a count of unheard records per unit and shelf, a **Refill now** button, the size used out of the free pool, and the dedupe report. No account, no upload.

## 7. What stays on the unit and what stays on the host

| Thing | Unit | Host |
|---|:---:|:---:|
| Shelves (current records, text only) | yes | copy |
| Heard list (last 510 entries) | yes | full history |
| Master library (all generated records) | no | yes |
| Rejected list | deny entries only | yes |
| Generation, filter, dedupe | no | yes |
| Telling screens, mumble, tiles | yes | no |
| Voice for a telling | no (mumble) | yes in S1 and S2 (real speech) |
| Dashboard | no | yes |

The unit never calls a model and never generates a record.

## 8. Brain halves

| | Own-LLM | MaiPai Home |
|---|---|---|
| Who generates | The package above, with the owner's model. | Home, with household rules, child and teen profiles, per person ratings. |
| Who filters | The package filter (section 6). The brain adds no chat filter. | Home's household rules. |
| Who syncs | Package, through the unit protocol. | Home, through the same unit protocol and the same shelf format. |
| When both exist | Paired to Home: the package steps aside (decision 1 test d, thin connector, Home's version takes over). The unit does not care who wrote a shelf. | |

The shelf and record format go into the shared spec as `schema/pantry-record.json` with fixtures, vendored here with a drift check (decision 5; `docs/plan/spec-vendor-drift.md`). No Home code is imported (`scripts/boundary-check.sh`). A brain half that is missing hides the feature: with neither a package switch nor Home, the pantry page and the telling screens are not shown (`AGENTS.md`, "Every feature has a body half and a brain half").

## 9. Build order

1. Spec file and a host-side shelf writer with a test that round-trips a shelf. (app, playground)
2. `pantry` kind and heard list in `maipai_assets_core.h` with the RAM flash test that cuts power at every step. (firmware)
3. Virtual unit answers `self.pantry.*`. (playground)
4. Generator, filter, dedupe, dashboard page. (app)
5. Telling screens and mumble. (firmware, `model-games.md`)

## Open questions (answered, decision 35)

1. The curation filter is named in the user docs (`docs/user/privacy.md`, `docs/user/jokes-and-games-content.md`): it curates stored content, never chat. Yes.
2. `extra` stays: trivia offline shows three tiles. Yes.
3. The heard list is a unit-written item in the asset store. Built that way (`self.pantry.heard`).
4. Ratings are `kid` and `adult` only. A teen robot needs Home. Built that way (`record.RATINGS`).
5. The refill window is the owner's quiet hours when set, else 02:00 to 05:00. Built: `_pantry_window` in `host/maipai_body/app.py` reads the quiet-hours schedule, and `sync.in_window` takes fractional hours.
6. The code-made mumble exists: see [offline-mumble.md](offline-mumble.md) (UX16 core and SF87). `model-games.md` states what the pantry needs from it.

## Host build status (app track, 2026-11-18)

Built: record, shelf writer and reader (header `MPSH`, matching the firmware reader on `fw/unproven2`), filter, dedupe, generator, library, refill rule, heard intake, dashboard card, and the unit link over `self.pantry.status`, `.heard` and `.deny` (`unit_link.py`), run every five minutes for each connected unit. Also built: installing a shelf through the host's asset transport (`asset_transport.py`: `self.assets.install`, then `.data` in 2,048 byte pieces, then `.commit`, `.abort` on any failure; the 128 byte `MPAH1` header; a shelf of the same name keeps its slot with a higher version). Tested against a fake unit that follows the firmware's protocol; not run on a real unit (the firmware is on `fw/unproven2`, not main). The talk games do not read the library yet.


Talk games from the library (state S1 of `model-games.md`): built for riddles and trivia in `host/maipai_packages/pantry/talk_fallback.py`. When the model cannot be reached in the middle of one of those games, the host plays the next turn from the library with fixed lines (English and Spanish; other languages fall back to English), counts the score itself, and never repeats a record to the same unit. Only `kid` records are used unless adult humor is on. Jokes have no talk game yet, and twenty questions, word chain, would you rather and the bedtime story have no library half, so they keep the usual offline line. Proven with tests against a fake turn; not yet proven on a real unit with the model switched off.

The built-in set (`host/maipai_packages/pantry/seed/`, `seed_loader.py`): loaded once per seed file for the chosen languages when the pantry starts, with no model; a marker file (`seed-loaded.json`) keeps deleted records deleted and a changed seed file adds only what is missing. Records marked never again are never added. The dashboard card shows "Built-in set" and marks each built-in row.

## Lines by situation (kind `line`, owner decision 24 extension, 2026-11-18)

Offline, with no host and no model, the robot answers from canned lines: the unit's reader picks a line for the situation, shows it as the subtitle and plays the code-made mumble (`offline-mumble.md`). The robot talks, in a small way, from a pantry set.

**The record.** Kind `line` (kind byte 5 on a shelf). `text` is the line, at most 100 bytes, in the robot's voice (short, warm, plain, no exclamation points). `extra` is the situation tag. No `answer`. Rating `kid` only. The id rule is unchanged. Dedupe works inside one situation, so a similar line under two situations is kept. The host does not write lines with the model: they ship in the built-in set (`seed/<language>-line.json`, about 6 per situation per language) and the model refill says so.

**The situations** (`record.SITUATIONS`, 20, confirmed as asked):

| Tag | When the unit uses it |
|---|---|
| `greeting_morning`, `greeting_day`, `greeting_evening` | A person appears or the wake word is heard, by the unit's own clock. |
| `goodnight` | Night mode starts, or the person says good night. |
| `touch_head`, `touch_face` | A head pet or a tap on the face. |
| `pick_up`, `put_down` | The unit is lifted, or set down again. |
| `shaken` | A shake. |
| `loud_noise` | A sudden loud sound. |
| `wake_heard_offline` | The wake word fired and no host answers (replaces the "hello" clip). |
| `cannot_reach_home` | The host or Wi-Fi is not there (replaces the no_wifi, no_host and connecting clips). |
| `back_online` | The host is back (replaces the back clips). |
| `timer_done` | A timer ends (the tone still plays first). |
| `battery_low` | A low-battery step (the recorded warning stays; this adds a friendly line). |
| `thanks` | The person says thanks. |
| `bored`, `sleepy`, `happy`, `curious` | The idle mood moves, by the pet mood. |

**The 16 offline phrases** (`host/scripts/render_unit_phrases.py`, five groups): `no_wifi` (4), `no_host` (4), `connecting` (3) and `back` (2) are link-state chatter, not alarm, safety or battery, so 13 of the 16 move to lines (`cannot_reach_home` and `back_online`). `refused` (3: "I need to be approved again") stays a recorded clip, because it tells the owner to act on pairing. Flash: the 16 ogg clips measure 76,003 bytes (about 4.7 KB each), so the 13 that move free about 62 KB of the assets image for the one voice and language shipped today, and more once the phrase pack carries six languages. The replacement costs about 8 KB per language (20 situations, 6 lines, about 70 bytes plus the 16 byte index each).
