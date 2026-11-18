# Funding and sponsorship

Working paper for the owner and a lawyer to review. It is not legal or tax advice. Nothing here is live: `.github/FUNDING.yml` is staged and no new account is created by this paper.

Date: 2026-11-18. Status: proposal, needs owner approval.

## What the money is for

The README already says sponsoring pays for test hardware: more robots, a computer for bigger models and a phone for travel tests. We publish what we measure on it. Keep that sentence true. Any other use (travel, time, fees) is stated before it is spent, not after.

## Platform options

Facts below come from each platform's own help pages as the author knew them. Fees, payout regions and tax forms change. Confirm each one on the official page on the day you apply, and write the date next to it.

| Option | What it is | What it needs | Fit |
|---|---|---|---|
| GitHub Sponsors | Button on the repo and profile, paid through GitHub | A GitHub account in a supported region, a payout account, two-factor sign-in, tax details, approval by GitHub | Best default. The repo already lives there, and `.github/FUNDING.yml` shows the button with no extra page |
| Ko-fi | Page with one-time and monthly tips | A free account and a payout link (card processor or PayPal, per Ko-fi's current rules) | Good second option for one-time tips. No tie to the repo |
| Open Collective | Public ledger held by a fiscal host | A collective page and a fiscal host that accepts it, which acts as the legal home of the money | Best if several people will share spending or a company wants an invoice. The most paperwork |

Others on the FUNDING.yml list (Liberapay, Patreon, Buy Me a Coffee) are not recommended: no gain over the three above for a project this size.

## Personal account or organization account

| | Personal account | Organization account |
|---|---|---|
| Setup | Fastest. One person, one payout | Needs an organization that can hold payout and tax details; check what each platform asks of an organization |
| Who is paid | The owner, personally | The organization, or its fiscal host |
| Tax and liability | Income lands on the owner's personal return and the owner is personally responsible | Depends on the entity type; a lawyer or accountant decides |
| Continuity | Tied to one person | Survives a change of maintainer |
| Public identity | Personal profile appears on the button | Organization name appears |
| Privacy | The owner's real name may be tied to payouts, depending on platform and region | Less personal, but the legal entity is public on some platforms |

Questions for the lawyer or accountant:

1. Does the owner have, or want, a legal entity before taking money? Which type, and where?
2. How is sponsorship income taxed for the owner personally, and for an entity?
3. Does taking money change any duty under the AGPL-3.0 or the third-party licenses in `THIRD-PARTY.md`? (The paid-support and hardware options in `docs/plan/monetization-options.md` raise the same question.)
4. Do sponsor perks of any kind create an obligation to deliver (support, features, dates)?
5. How should payouts be reported when the repo is owned by `getmaipai` and the account is personal?

## Recommended default

1. Start with **GitHub Sponsors on the owner's personal account**. It is already staged in `.github/FUNDING.yml` and linked in the README. It needs no new site and no extra page.
2. Move to an organization account, or add Open Collective, only when a second person shares the work or spending, or a lawyer advises an entity first. Moving later is allowed; the links stay in one file.
3. Add Ko-fi only if people ask for a one-time tip with no GitHub account.
4. Do not open an account until the owner decides. The listing stays unpublished until then and the README link stays dead (see `docs/dev/draft-names.md`, Sponsors). Do not release with a link that does not resolve: publish the listing or remove the section.

## Where links go

| Place | Wording | Notes |
|---|---|---|
| README, "Support the project" section | One plain sentence and one link | Exists. This paper does not edit it |
| Docs site footer | One line, "Support the project", one link | Add in `scripts/build-site.sh` templates once an account is live |
| Dashboard, About page | One line below the version and license lines | Static text, no banner, no badge, no icon on the main screens |
| `.github/FUNDING.yml` | The source of truth | Every link elsewhere must appear here |

Not on the robot, not in the firmware, not in a voice reply, not in a push alert, not in an error message, not in setup.

`scripts/funding-check.py` fails when the README or docs link to a funding page that `.github/FUNDING.yml` does not list. It runs in `scripts/check.sh`.

## No dark patterns

- No pop-up, banner, countdown or "supporters only" gate in the app, the dashboard or the firmware.
- No feature is held back, slowed or nagged about for people who do not pay.
- No guilt wording, no counters of what is missing, no "last chance".
- No tracking of who clicked. The links are plain links.
- No supporter names shown without their written yes.
- Money does not buy a say in the roadmap unless the owner writes that rule down first.
- Report use once a year in `docs/user/release-notes.md` or a plain note in the repo: amount in, what it bought.

## Steps when the owner decides

1. Pick the account type (personal or organization) after the lawyer's answers above.
2. Create the account on the chosen platform and finish its approval.
3. Confirm the page resolves from a signed-out browser.
4. Update `.github/FUNDING.yml` and the README link in the same change, then run `bash scripts/check.sh`.
5. Add the docs footer and dashboard About line.
