# Twenty questions from the library (state S1 and S0)

Status: spec, no code yet. Placement: host (the game and its table), unit (a shelf kind, for a robot with no host, through the firmware track's installed-set doc). Decision 35 follows `content-pantry.md`; this is the library half of twenty questions in `model-games.md` section 4.

**Bottom line.** With no model the robot plays twenty questions the way a model plays it today: the person thinks of an animal or a thing and the robot asks yes or no questions, then guesses. The robot picks its questions from a fixed list of 12 and narrows a table of objects. One new record kind, `object`, holds the table. No new record field.

## The record

Kind `object`, the fifth kind (shelf kind byte 4). The fields are the existing ones:

| Field | Holds |
|---|---|
| `text` | The name with its article, up to 24 bytes, in the record's language ("a cat", "un gato"). |
| `answer` | The group: `animal` or `thing` (the English words in every language; the host maps them to spoken words). |
| `extra` | Twelve characters, each `0` or `1`: the answers to the 12 questions below, in order. |
| `rating` | `kid` for every shipped object. |

The id rule is unchanged (hash of kind, language, normalized text, answer), so a renamed object is a new record. The bit string is the same in every language: one table of bits, six name lists.

## The 12 questions (fixed, bit 0 to bit 11)

1. Is it alive?
2. Does it live in water?
3. Can it fly?
4. Does it have four legs?
5. Does it have fur or feathers?
6. Do people eat it?
7. Is it found in a house?
8. Is it made of metal or plastic?
9. Is it bigger than a chair?
10. Does it make a sound?
11. Is it a toy, or used to play?
12. Do you wear it or carry it?

The question words live in the host phrase table and the unit's phrase pack (six languages, grade 6 reading level, no exclamation points). A question is never generated.

## How the game plays

Round one asks "Think of an animal or a thing and keep it secret. Say ready." The robot keeps a candidate list (every `object` record in the chosen language and rating). Each turn:

1. Pick the unasked question whose yes share among the candidates is closest to one half. Ask it.
2. Read the answer: yes, no or "I do not know" (skips the question, no change).
3. Score each candidate by how many answers it disagrees with. Candidates with more than one disagreement drop out (one wrong answer is forgiven, because people answer the same question differently).
4. When one candidate is left, or the questions run out, guess the best score: "Is it a cat?". The game allows 12 questions, then two guesses.
5. A yes ends the game with the robot winning. A no after the second guess ends it with "I give up. What was it?". The answer is not stored.

The score for this game follows `model-games.md` section 6: the fewest questions used, kept to the best five. The shipped table needs at least 100 objects per language to feel fair. An object whose bits equal another's is dropped at load (the dedupe rule: same bits and same group), so every object can be told apart.

## Where it runs

- **S1 (host, no model).** `host/maipai_packages/pantry/` holds the game (`twenty_fallback.py`, same hook as `talk_fallback.py`) and reads the library like the other kinds. The built-in set grows a seed file per language, `<language>-object.json`, loaded by the existing seed loader.
- **S0 (unit alone).** The unit needs the shelf kind and the 12 questions in its phrase pack. That is the firmware track's installed-set work: the `pantry` asset kind already carries a kind byte, so the change is that the reader accepts kind 4 and a game screen reads it. Note for firmware: record `object` is at most 24 + 8 + 12 bytes of text plus the 16 byte index, about 60 bytes, so 200 objects fit in 12 KB, inside the existing 40,960 byte item.

## Content

One English table of at least 100 objects (about 60 animals and 40 things) with the 12 bits, checked so no two share all 12 bits, and name lists in Spanish, French, German, Portuguese and Italian. Every object is something a six year old knows. No people, no brands, no scary animals as the only choice of their group.

## Checks to add with the code

- Shape: `extra` is exactly 12 characters of `0` and `1`, `answer` is `animal` or `thing`, the name is 24 bytes or less.
- Table: no two objects of one language share all 12 bits and the same group.
- Game: with a known table, a person who answers for object X gets X within 12 questions, including with one wrong answer.
