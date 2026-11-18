# Shared-spec proposals (step 4, 2026-11-18)

Four small records for `commons/spec` to adopt later, so the host, the virtual unit and a Reachy Mini implement the same concepts. Nothing here edits commons. Each has a JSON Schema (`*.schema.json`), valid and invalid fixtures (`fixtures/`), and a test (`host/tests/test_spec_proposals.py`) that the host's own code passes: its movement limiter reading, its memory admission rules, its brain capabilities and its ring indicator table.

| Record | Concept | What the host test proves |
|---|---|---|
| `movement-limiter-state` | why and how much the unit limits motion | every state name the host parses is in the enum; a real reading validates |
| `memory-admission` | what a note may hold and who may read it | the limits in the record equal the notes package's, and each refusal example is refused |
| `brain-capabilities` | what an answering brain provides | the own-LLM brain's capabilities validate; the enum is the host's feature list |
| `indicator-row` | the ring indicator table (no red, one amber meaning) | every row of the approved table validates, and the host's `LookKey` list equals the table keys |

Virtual unit: it reads these through the host today (the playground's scenarios call the same tools); a direct check of its tool output against `movement-limiter-state` is the next step on that side. The fixtures use persona and example names only.
