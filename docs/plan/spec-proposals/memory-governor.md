# Memory governor (proposal record, 2026-11-18)

Status: proposal for `commons/spec`, so StackChan, the Reachy Mini body and Home describe the same thing when a robot says "this will not fit". Nothing here edits commons. Schema: `memory-governor.schema.json`; fixtures in `fixtures/`; tests in `host/tests/test_spec_proposals.py`.

## The idea in plain words

A robot has a few small pools (working memory, a larger slow memory, flash for the program). A feature is allowed to cost some of each. The governor is the rule that keeps a few floors true all the time, and makes every optional feature say what it costs before it is switched on.

## Budget classes (the floors)

| Class | Floor | Where the number is checked today |
|---|---|---|
| Internal RAM free, median after settling | at least 40,000 bytes | `scripts/fw-stress.py` |
| Internal RAM, lowest seen | at least 24,000 bytes | `scripts/fw-stress.py` |
| Largest free internal block, median / lowest | at least 24,000 / 16,000 bytes | `scripts/fw-stress.py` |
| Task stack margin | at least 1,024 bytes | `scripts/fw-stress.py` |
| Slow memory (PSRAM) free, lowest | above 6,000,000 bytes | `scripts/fw-stress.py` |
| Program flash per slot | at least 20 percent free | `scripts/release-report.py` |

A robot without one of these pools (the Reachy Mini has no PSRAM split) states the budgets it has and the numbers it uses; the record keeps the class names so a reader knows what each number measures.

## What an optional feature must report

`features[]`: `id`, `tier` (core, optional, hub_only), `default` (on or off), the cost in KB for `flash_kb`, `psram_kb`, `internal_kb`, and three booleans: `needs_host`, `offline_ok`, `off_costs_nothing`.

- A feature that is off costs no memory: no task, no heap, no timer, no socket (`off_costs_nothing` is true, and the proof below holds).
- A core feature that cannot be turned off says so (`off_costs_nothing` false) and its cost is part of the baseline; the Latin-1 screen font is the example (86 KB flash, no RAM).

## The proof that off is off

`off_proof`: one baseline with the feature compiled out and one with it linked but off. `internal_free` and the largest block must match within 4,096 bytes at most; the working rule is about 1 KB. The schema rejects a looser match.

## What the person is told when it does not fit

`refusal_words`: one plain sentence naming the cost, what is free, and what to turn off first. Example in the fixture. No feature is switched on that would break a floor; the settings page shows the cost before the switch.

## Open

- Whether the numbers belong in the spec or only the class names and the report shape (the numbers are per body).
- A runtime report (`free now`, `lowest`, per feature) is not in this record yet; the gate reads it from the serial memory line today.

## Fixture note

In `fixtures/memory-governor.valid.example.json` the floors are the real gate numbers; the private network cost (47 KB internal RAM) is from `docs/design/firmware-memory.md` (76 KB free before the client, 29.7 KB with it) and the screen font cost (86 KB flash) is measured (87,472 bytes of object code). The face detector row is illustrative, not measured.
