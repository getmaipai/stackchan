# Parent view on the settings page (plan step 7)

Owner of the code: the app track (host/maipai_body/settings_*.py, the page script, i18n). The playground track wrote this note and touches none of those files. App track: reply in this file under "Decision" (take it, change it, or drop it).

## What a parent needs, in plain words (from the 2026-11-18 review)

Reach: a phone can open it (the per-install token work already landed); the page opens on a short "Family and safety" group, not ten tabs.

Show, read-only, at the top:
- Online or offline, battery, muted or not, camera on or off, locked or not, in one card with a plain word each ("Listening", "Muted", "Camera off", "Locked").
- Who controlled the robot lately (the remote activity list that exists).
- The privacy promise in the same words the robot shows at first run (docs/design/first-run-flow.md step 5): "Your voice and pictures stay in your home. Nothing goes to the internet unless you turn it on." One catalog key shared by both, so they never drift.

Controls, each a big 48 px target:
- Mute and unmute, volume cap, Lock now, camera off.
- Quiet hours (bedtime): the on-robot basic, because it must work with the host off (an on-unit rule, the unit side is the firmware track's; today the page shows it as a disabled stub, so either wire it or hide it).

Say plainly, on the page, what is not there and why: "The robot does not keep what it hears or says. There is no history to read." (true by design: privacy promise). Content level and kid mode belong to the brain (MaiPai Home), not the robot or this page; when paired with Home, link to Home's own page.

Hide every "soon" stub (eleven today).

## Not decided here

Whether this is a new page `/parent` or the first group of the existing page (the review prefers five groups: Home, Look, Sound, Family and safety, Advanced). Recommendation: the first group of the existing page, so there is one page.

## Decision

Taken as written (app track, 2026-11-18): the first group of the existing page, phone reachable through the settings token, no history by design, the eleven "soon" stubs hidden, one shared privacy sentence in the catalog. Quiet hours: hidden until the unit rule exists. Built after the current safety list; the first slice is the status card and hiding the stubs.

## Built (app track, 2026-11-18)

On the home page, above the unit cards: a Family and safety card (online, microphone, camera, lock in plain words; the privacy promise; "no history to read"; who controlled the robot lately), a pairing code button (host computer only) and a phone code card (QR that logs a phone in, only when `lan = true`). The "soon" stubs are hidden by the page script. Words: `i18n_family.py` (English and Spanish; the others read English until written). Checked in the built-in browser at phone width: the cards stack in one column, the code shows large, the QR draws. Not done: quiet hours (hidden until the unit rule exists), one shared privacy sentence with the robot's first-run screen (the key is `settings.ui.fam.privacy`; the firmware side should read the same text).
