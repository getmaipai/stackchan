# The choices rule (owner decision 20)

Offer a choice only when it is needed. We decide, with good defaults.

A new setting, option, page, command-line flag or `robot.toml` key needs one line of justification in the change that adds it:

1. **Who needs it** (which person, doing what).
2. **What it costs** (a question to answer, a thing to understand, a way to get it wrong).
3. **Why the default is not enough.**

Ask the person only when the answer changes something they care about, cannot be worked out, or has a real cost. Everything else is automatic, or behind the one collapsed Advanced section. When two options are close, pick one.

## The check

`scripts/choices-check.py` (run by `scripts/check.sh`) lists every key of `robot.toml` (from the schema in `host/maipai_body/config.py`) and fails when one has no row in `docs/dev/settings-justification.md`. Add the row in the same commit as the key: key, who needs it, cost, why the default is not enough, and its disposition (keep, automatic, advanced).
