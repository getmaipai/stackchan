# What the docs site does not publish

The site publishes `docs/user`, `docs/playground`, a chosen list of `docs/dev` and `docs/design` pages (`DEV_PAGES` in `scripts/docs-site/build.py`), the decisions log, the ledger, the golden screens and the 3D viewer.

Not published, with the reason:

- `docs/plan/*` (owner plans, funding, trademark and legal working notes): private business material.
- Egress, protection and audit notes (`egress-table`, `egress-audit`, `egress-proof`, `software-only-protection`, `host-choices-audit`, `unit-choices-audit`, the cross-review and four-users notes): they describe how to attack or bypass protections, or are internal reviews.
- Dated working notes (`*-2026-*`, trains, integrations, benches, measurements): history for the team, not a guide for a reader.
- Anything under `data-scratch/`, `.runs/` and the private word lists: never part of the repository docs.

A link from a published page to an unpublished file stays as plain words, never a dead link. `test_docs_site.py` fails if a page whose name matches the private list is built.
