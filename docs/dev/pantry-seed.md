# Pantry seed library

The files in `host/maipai_packages/pantry/seed/` are the built-in records for the offline pantry (see `docs/design/content-pantry.md`). They are original writing, kid-safe, rating `kid`, and cost nothing until the pantry package is switched on.

- **Files:** one JSON list per language and kind, named `<language>-<kind>.json`. English has 100 jokes, 100 riddles and 100 trivia. Spanish, French, German, Portuguese and Italian have 40 of each.
- **Record fields:** `kind`, `language`, `rating`, `text`, `answer`, `extra`, exactly as in `record.py`. A joke is `setup | punchline` with one pipe. A riddle has an answer. Trivia has the right answer and two wrong ones in `extra`, split by `|`.
- **Add a record:** append an object to the right file, keep the text inside the caps (joke 160, riddle 140, trivia 140 bytes; answer 40; extra 80), then run `python3 -m pytest host/tests/test_pantry_seed.py -q`. The test counts the records, so change the counts in the test when you add or drop any.
- **Rules for new lines:** original wording, true and checkable trivia, no politics, religion, violence, romance, food allergies, body shaming or real people.
- **Review before release:** a native speaker must read the Spanish, French, German, Portuguese and Italian files (puns, grammar, tone, and whether each accented letter shows on the unit). The English files need a read for taste only. Do not ship a non-English file as reviewed until that is done.
