# Translation review pack

For a native speaker. One file per language (`es.csv`, `fr.csv`, `de.csv`, `pt.csv`, `it.csv`); open it in a spreadsheet and keep the first row (the column names).

Each row is one thing a person reads on the robot or on the settings page. The columns:

| Column | What it is |
|---|---|
| `key` | The name of the string. Do not change it. |
| `english` | The English the translation follows. |
| `translation` | The current translation. **Correct it here.** |
| `context` | Where the text appears (settings page, parent view, update messages, robot screen, language pack, document title). |
| `max_chars` and `limit` | How long it may be. `hard` is a rule (the robot refuses a longer word); `soft` is a layout estimate (about the English length plus a margin): a longer line may be cut or wrapped on a small screen, so shorter is better. |
| `screenshot` | A picture of the screen the text belongs to (a path in this repository). |
| `status` | `machine draft` (written by a model, not read by a person), `missing` (no translation yet), or `reviewed`. Put `ok` here when you read a row and it is right as it is. |
| `note` | Say anything we should know: a word you are unsure of, a choice between two. |

Rules for a good line: the same meaning as the English and the same tone (plain, friendly, no jargon); keep every `{placeholder}` exactly as it is, in any place in the sentence; no markup, no square brackets; no em dash. Text drawn on the robot (`unit.` and `pack.` rows) can use the letters of Western European languages with accents, but not curly quotes or the oe ligature; the language pack words are plain letters with no accents at all and a short length (a weekday or month at most 7 letters, the alarm and timer words at most 11).

When you send the file back, we check it: `python3 scripts/translation-pack.py check FILE.csv` lists every problem with the row it is in. A row you changed, or marked `ok`, becomes `reviewed`.

Status of every language: see `STATUS.md`. Rows for the robot screen, the language packs and the document titles are passed to the people who own those parts (`pending/<language>.csv`); the settings page and message rows go live as soon as they are imported.
