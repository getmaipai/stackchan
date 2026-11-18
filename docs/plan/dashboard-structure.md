# Dashboard pages follow the robot's screen structure (for the app track)

Owner requirement of 2026-11-18 (`docs/design/screen-style.md`, "Physical standard" and "Which pattern for which screen"). The unit's settings are a left column of tabs with a right pane that scrolls. The host's web pages should feel the same:

- A left column of tabs (the sections), each row at least 56 px high on a phone and the active one clearly marked; on a narrow phone the column may become a top row, never a hamburger that hides the sections.
- A right pane that scrolls on its own; rows at least 56 px tall with 8 px gaps; a visible hint when there is more below.
- Done or Back in the same place on every page; one primary action per page.
- Pages of tiles for a few big choices (four to a page), a wizard with the same dots for steps.

The playground track checks the robot's screens (`docs/dev/screen-audit.md`); a matching check for the dashboard pages is the app track's.
