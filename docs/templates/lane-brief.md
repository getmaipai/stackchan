# Lane brief: <slice name>

Goal (one sentence, user words): 
Lane: <cloud | codex | local-lane | local-claude>    Model and effort: <e.g. Luna low | Sonnet>
Spec to read (only these): docs/design/<component>.md, docs/design/INDEX.md
Files you may change (nothing else): 
Files you must not touch: 
Contract (types, messages, keys already decided): 
Done means (a test or check that can fail): <command>   Expected: <result>
Stop rule: after 3 failing attempts stop and report the failing output and your best guess; do not widen scope.
Output: write a short result to .runs/<slice>.result.md (what changed, test result, open questions, max 15 lines); reply with one line.
Placement (required before building): <unit | host | home-preset | Home | commons/spec> and the answers to the three questions in docs/design/repo-boundaries.md. If it is Home or commons/spec, do not build it here.
Rules: follow docs/STYLE.md writing rules; no mention of other projects or products anywhere (code, comments, commit text); do not read the whole repo; commit nothing (the dispatcher commits by file name).
