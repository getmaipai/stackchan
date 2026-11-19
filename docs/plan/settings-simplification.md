# Settings simplification and the dashboard makeover

Owner request, 2026-11-19: the dashboard has ten tabs, long pages, many words and no real search. Make it simple, sleek and calm, like System Settings on a Mac or Settings on an iPhone. Rule: offer a choice only when it is needed (decision 20, `docs/dev/settings-justification.md`).

## What there is today (counted from the page code)

| Page | Cards | Toggles | Segmented | Sliders | Selects | Buttons | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| Home | 4 | 1 | 0 | 0 | 0 | 5 | Replace: robot at a glance, 4 big actions, checklist |
| Remote | 9 | 2 | 1 | 0 | 4 | 16 | Move: Robot > Remote control |
| Look | 11 | 5 | 2 | 2 | 1 | 2 | Move: Robot > Look and feel (style, color, name first; the rest behind More) |
| Voice | 4 | 4 | 2 | 5 | 1 | 0 | Move: Robot > Voice (volume first) |
| Network | 4 | 1 | 0 | 0 | 0 | 9 | Move: Robot > Wi-Fi (one guided step; Tailscale behind More) |
| Behavior | 8 | 11 | 3 | 1 | 2 | 16 | Split: quiet, camera and mute go to Safety; the rest behind More |
| Games | 5 | 0 | 0 | 0 | 2 | 8 | Move: More > Games |
| System | 16 | 12 | 12 | 3 | 1 | 19 | Move: More > System; Brain items go to Brain |
| Packs | 6 | 0 | 1 | 2 | 2 | 25 | Move: More > Packs |
| Security | 1 | 0 | 1 | 0 | 0 | 0 | Move: Safety > Lock |

Ten tabs, 60 cards, about 40 toggles and 25 sliders and selects in all.

## The new shape

Five sidebar items: **Home, Robot, Brain, Safety, More**. A wide search field sits at the top of every page. A robot picker (a name and a dot) sits beside it. One column of rounded groups. A control row has a label on the left and the value on the right. A chevron opens a detail view with a back arrow. No cards in a grid, no side panels.

Budgets (checked by `scripts/dashboard-words-check.py` in `check.sh`):

- At most 6 visible controls on a front page. Everything else is behind **More settings** on that page.
- A page has a title and at most one help sentence of 12 words or fewer. A front page has at most 60 words in all.
- A control label is 1 to 3 words. Help text shows only behind the **i** on a row or inside More settings.
- No front-page word from this list: psk, token, namespace, firmware, codec, jitter, passphrase, endpoint, json.

## The must-do flows (each is one short screen with a success line and a "what's next")

1. **Select your robot.** The picker at the top: pick a robot, or **Add a robot** (Pair). Success: "Kitchen is online". Next: Wi-Fi.
2. **Connect to Wi-Fi.** One step. It shows the network the robot is on and runs the check. Success: "Connected to Wi-Fi: Home". Next: Brain. (Joining a new network from the host is not built; the page says to use the robot's own screen.)
3. **Look and feel.** Face style, eye color, name. Success: the live preview changes. Next: Remote control.
4. **Remote control.** Say something, look around, quick actions. Success: "Sent".
5. **Brain.** Hosted or your own (hosted is marked planned). Success: "Using your own model".

Home shows a **first-run checklist** (Pair robot, Wi-Fi, Brain, Look). It disappears when all four are done.

## Page by page (what is visible, what hides)

**Home** (no settings): robot name, online line, battery bar; the checklist; four big actions: Wi-Fi, Look, Remote control, Quiet now.

**Robot** (6 visible): Look and feel >, Volume (slider), Screen brightness (slider), Wi-Fi >, Remote control >, Voice and listening >. More settings: Behavior and movement, Packs, Pictures, Lights.

**Brain** (4 visible): Where it thinks (Hosted, planned / Your own), Model address, Test, Leave hosted. More settings: speech and voice service addresses, timeout, history.

**Safety** (6 visible): Quiet now (switch), Quiet hours >, Microphone off (switch), Camera off (switch), Lock >, Parent view >. More settings: who may remote control, activity log.

**More**: Packs, Games, Languages, Network (Tailscale), Updates, About and support, System, Advanced. Every old page stays reachable here until it is migrated, then it is removed.

## Search

The field at the top of every page searches a list of every setting by plain words and synonyms ("quiet", "sleep", "volume", "wifi", "name", "camera", "update"). A result is the setting row itself, so one click changes it right there. Settings not yet in the list are found by the older page search and open their old page.

## First run

At most three questions: name, language, brain. Everything else keeps its default.

## Order of work

1. Shell (sidebar, search, grouped rows, detail view, dark mode) with Home, Robot and Safety as the reference.
2. Brain, More and the flows.
3. Move each old page behind More, in the new look, one worker per page.
4. Docs and screenshots (`docs/user/settings.md`), docs-site header.

Progress: `side-session-notes/.../app-state.md`.
