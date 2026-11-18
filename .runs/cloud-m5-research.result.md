# cloud/m5-research result (2026-11-18)
Verdict: paper written, 139 lines, docs/plan/m5stack-cloud-research.md. Pushed on cloud/m5-research.
Recommendation: do nothing for the official service until M5Stack answers; ship bring-your-own-key; document a community-server URL setting.
Licenses: StackChan firmware, server, BSP, Xiaozhi firmware, 3 UI libs MIT; esp-now Apache-2.0. No root LICENSE in the StackChan repo (per-folder files).
Gap 1: network policy blocked docs.m5stack.com, xiaozhi.me, docs.xiaozhi.me, github.com pages and the GitHub API. Terms, privacy policy, rate limits, third-party-firmware rules are UNKNOWN. Items marked "via search" are search summaries, not primary reads.
Gap 2: docs/plan/trademark-and-affiliation.md is not on main. I used README and NOTICE wording. Question for you: where is it?
Gap 3: ~/.config/maipai/no-mention-words.txt is missing here, so check.sh exits 2. With an empty list: hygiene ok, boundary ok.
Allow list: none needed. hygiene-check.sh only blocks the private word list; no docs/plan file uses an allow list. Not changed.
Not checked: ArduinoJson license, StackChan app and remote-controller folder licenses, server maturity (stars, releases).
Draft email to M5Stack is in section 5. Nothing sent, nothing contacted.
