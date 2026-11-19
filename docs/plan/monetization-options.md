# Monetization options

Working paper for the owner and a lawyer to review. It is not legal advice. Nothing here is decided.

Date: 2026-11-18. Constraint from the repo: the product stays private and local (`docs/design/decisions.md`, decision 12: the host calls no address the owner did not configure). Money must not require a cloud account, telemetry or a gate on features. The code is AGPL-3.0.

## Options that fit

| Option | What it is | Pros | Cons |
|---|---|---|---|
| Sponsorship | See `docs/plan/funding-and-sponsorship.md` | No product change. Matches the README promise | Small and uneven income |
| Hardware add-ons | Printed parts, stands, cases, a lights board or other accessories, sold as plain goods | Real goods for a real robot. No software gate. Source files can stay open | Stock, shipping, returns and safety marks are real work. The robot maker's marks cannot appear as our branding (`docs/plan/trademark-and-affiliation.md`, on the legal track and not yet in this branch). Sell the part, not the robot |
| Paid help | Setup session, remote install help or a support hour, priced per session | Fits a hobby project. No code change. Customer data stays on their side | Time-boxed income that depends on one person. Needs a clear statement of what is not promised |
| Free hosted pieces | A hosted page, such as a download mirror or documentation, free to use | No account, no data collected. Costs little | Not income by itself. Any hosted service that runs our modified code for other people triggers the AGPL source offer (below) |
| Books, guides, videos | Written build guides and persona packs that are not code | Fully separate from the AGPL code | Content licenses must be stated. Persona packs shipped in the repo follow the repo license |

## Needs care

- **Pre-flashed units or firmware images for sale.** `THIRD-PARTY.md` says a prebuilt image that bundles the speech models waits for a license confirmation: the Espressif text carries a clause "for use on all ESPRESSIF SYSTEMS products". Settle that first. Selling hardware that ships M5Stack's own firmware parts also needs the maker's terms checked.
- **Trademark.** Use the wording in `docs/legal/affiliation.json` (owner approved, on the legal track and not yet in this branch). Never use the maker's marks as this project's branding.
- **Contributions.** The owner holds the copyright in code written by the owner. Code from other contributors stays theirs under the AGPL unless a contributor agreement says otherwise. Any dual-license plan needs that agreement first and a lawyer's review.

## What to avoid with AGPL

- **License keys or feature gates inside AGPL code.** Anyone may remove the gate and share the result. It also breaks the "no nag, no gate" rule above.
- **A closed paid module that links into the AGPL host.** Linking can make the module part of the same work. Do not do this without a lawyer's answer.
- **Adding "non-commercial" or "personal use only" terms to the code.** The AGPL does not allow added restrictions on top of it. Note for review: the README disclaimer reads "personal, self-hosted, non-commercial use". A lawyer should say whether that sentence is a statement about the owner's own project or reads as a license term, and fix the wording if needed. This paper does not edit the README.
- **A hosted service that runs a changed copy for other people** without offering them the source (AGPL section 13). A hosted service for sale is also against the private-and-local promise.
- **Selling user data, telemetry, ads or analytics.** Against decision 12 and the privacy page.
- **Paywalled security fixes.** Fixes ship to everyone at once.
- **Hiding the license.** `LICENSE`, `NOTICE` and `THIRD-PARTY.md` ship with every copy we distribute, including hardware sold with an image.

## Recommended order

1. Sponsorship, as set out in the funding paper.
2. Paid help, only after the owner writes down what it does and does not promise.
3. Hardware add-ons that are plain accessories, after the trademark paper is final.
4. Pre-flashed units only after the Espressif and maker terms are confirmed in writing.

## Questions for the lawyer

1. Does the README "non-commercial" sentence conflict with the AGPL?
2. What does a seller of printed accessories need to say about the maker's marks?
3. What can we ship on a pre-flashed unit given the speech-model and firmware-base terms?
4. Do we need a contributor agreement before we take outside code?
5. What does a paid support session promise by law, and how do we word what it does not?
