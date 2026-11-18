# One privacy sentence for the settings page and the robot's first-run screen

Proposal from the app track, 2026-11-18. The playground track owns the first-run screens and the firmware wording; the app track owns the settings page. This note is the only place they coordinate.

**The sentence (English):** "Your voice and pictures stay in your home. Nothing goes to the internet unless you turn it on."

- **Settings page:** reads it from `settings.ui.fam.privacy` (`host/maipai_body/i18n_family.py`; English and Spanish written, the others read English until filled).
- **Robot first-run screen** (`docs/design/first-run-flow.md` step 5): should show the same text. Proposal: the firmware text is generated from one string table that the host catalog also reads, so the two cannot drift. Until that table exists, the firmware screen copies the English sentence above exactly, and a host test pins the sentence (below).
- **Pin:** `host/tests/test_privacy_sentence.py` fails if the host sentence changes, with the message to change the firmware text in the same commit.

Not decided here: the translations of the sentence for French, German, Portuguese and Italian (the machine drafts in `i18n_fill/` apply until a speaker reviews them).

Decision (playground track): _write one line here._
