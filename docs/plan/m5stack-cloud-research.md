# M5Stack cloud and Xiaozhi service: research paper

Working paper for the owner. Not legal advice. Retrieved 2026-11-18 from public pages only. No traffic captured, no keys extracted, no server contacted.

## Summary (10 lines)

1. The StackChan firmware, its server and the Xiaozhi firmware under it are MIT. Relicensing into AGPL is allowed if the notices stay.
2. The stock robot talks to the Xiaozhi cloud. The Xiaozhi README says personal users register an account and get a Qwen real-time model for free.
3. The device side is public: an OTA endpoint, an activation code, a WebSocket. The OTA address is a setting, so a server swap needs no reverse engineering.
4. I could not read M5Stack's docs, Xiaozhi's terms or its privacy policy (network policy blocked them). Terms on third-party clients and modified firmware are UNKNOWN.
5. Self-hostable servers exist: two MIT, one modified Apache with multi-tenant and logo limits.
6. Free OpenAI-style LLM tiers exist (Groq, OpenRouter, Gemini). Limits change often.
7. Recommendation: do nothing by default. Ship bring-your-own-key first. Offer a community-server field as a plain URL setting. Do not ship the official Cloud brain until M5Stack answers the email in section 5.
8. Never default on, always labeled, always falls back to offline.
9. `docs/plan/trademark-and-affiliation.md` is not on main. Sections 4 and 5 use the README and NOTICE wording instead. Please point me at the file.
10. Seven open questions for the owner or M5Stack are in section 5.

## 1. Licenses

| Component | License | Source | Retrieved |
|---|---|---|---|
| m5stack/StackChan, firmware folder | MIT, copyright 2026 M5Stack Technology CO LTD | [firmware/LICENSE](https://raw.githubusercontent.com/m5stack/StackChan/main/firmware/LICENSE) | 2026-11-18 |
| m5stack/StackChan, server folder | MIT, same holder | [server/LICENSE](https://raw.githubusercontent.com/m5stack/StackChan/main/server/LICENSE) | 2026-11-18 |
| m5stack/StackChan, repo root | No LICENSE file at root (404). Per-folder files apply. Mobile app and remote controller folders: UNKNOWN, not checked | [root path](https://raw.githubusercontent.com/m5stack/StackChan/main/LICENSE) | 2026-11-18 |
| StackChan-BSP | MIT, M5Stack | [LICENSE](https://raw.githubusercontent.com/m5stack/StackChan-BSP/main/LICENSE) | 2026-11-18 |
| 78/xiaozhi-esp32 (pinned v2.5.2 plus a patch) | MIT, Shenzhen Xinzhi Future Technology and contributors | [LICENSE](https://raw.githubusercontent.com/78/xiaozhi-esp32/main/LICENSE), [pin list](https://raw.githubusercontent.com/m5stack/StackChan/main/firmware/repos.json) | 2026-11-18 |
| mooncake, mooncake_log, smooth_ui_toolkit | MIT | [mooncake](https://raw.githubusercontent.com/Forairaaaaa/mooncake/main/LICENSE), [log](https://raw.githubusercontent.com/Forairaaaaa/mooncake_log/main/LICENSE), [ui](https://raw.githubusercontent.com/Forairaaaaa/smooth_ui_toolkit/main/LICENSE) | 2026-11-18 |
| espressif/esp-now | Apache-2.0 | [LICENSE](https://raw.githubusercontent.com/espressif/esp-now/master/LICENSE) | 2026-11-18 |
| ArduinoJson | MIT by my memory. Raw LICENSE path not found, so UNKNOWN until checked | none | not retrieved |

What MIT permits, from the license text in each file: use, copy, modify, merge, publish, distribute, sublicense and sell. One duty: keep the copyright notice and permission text in all copies or substantial portions. The text says nothing about trademarks, so MIT gives no right to use a maker's marks. Apache-2.0 adds a notice duty, a patent grant, and an explicit trademark exclusion (my reading of the standard text, not re-fetched today).

Relicensing into AGPL-3.0: MIT code can sit inside an AGPL work. The MIT text stays on those files. The combined work is offered under AGPL. The MIT parts remain MIT for everyone else. Apache-2.0 code is also usable in a GPLv3 or AGPLv3 work (FSF position, from memory, not re-fetched). Both points need a lawyer's confirmation before release.

Branding limit from the stack: the StackChan name and M5Stack marks are not licensed by MIT. This project already says it is not made or endorsed by M5Stack ([NOTICE](../../NOTICE), [README](../../README.md)).

## 2. The hosted service

### What the stock robot connects to

- Xiaozhi README: "The firmware connects to the official xiaozhi.me server by default. Personal users can register an account to use the Qwen real-time model for free." ([README](https://raw.githubusercontent.com/78/xiaozhi-esp32/main/README.md), 2026-11-18)
- M5Stack's StackChan repo README lists an "AI Agent" in the factory firmware and says a mobile app does video and remote avatar control ([README](https://raw.githubusercontent.com/m5stack/StackChan/main/README.md), 2026-11-18).
- Search results quote M5Stack's docs saying the AI Agent is bound and configured through the StackChan World app (iOS, Android). I could not open docs.m5stack.com, so this is second hand. Page to confirm: [docs.m5stack.com/en/StackChan](https://docs.m5stack.com/en/StackChan).
- Whether the stock StackChan build points at xiaozhi.me or an M5Stack-run copy: UNKNOWN from public text I could read. The patch file in the StackChan repo is the place to look.

### Protocol, as documented upstream

- OTA and activation: [docs/ota.md](https://raw.githubusercontent.com/78/xiaozhi-esp32/main/docs/ota.md). A device POSTs its identity (`Device-Id` MAC, `Client-Id` UUID) to an OTA URL. The reply carries connection settings, an optional firmware URL and an optional activation object. The URL comes from a saved `wifi.ota_url` setting, else a build default.
- Voice session: [docs/websocket.md](https://raw.githubusercontent.com/78/xiaozhi-esp32/main/docs/websocket.md). WebSocket with a hello message, Opus audio, and MCP tool calls.
- Binding: the device shows a code, the owner types it into a console, the device polls until bound. Third-party guides say the code has six digits and sign-up uses a phone number ([Seeed wiki](https://wiki.seeedstudio.com/respeaker_xvf_3800_xiaozhi/), [UNIHIKER](https://www.unihiker.com/wiki/K10/Playground/XiaozhiAI/), via search, 2026-11-18). Public description only. I did not run it.

### Free or paid, limits, terms

| Question | Answer |
|---|---|
| Free for personal users | Yes for the Qwen real-time model, per the Xiaozhi README line above |
| Paid tiers | UNKNOWN. Another vendor sells a one-time license fee in its hardware ([Ai-Thinker docs](https://docs.ai-thinker.com/en/aipi-palchatv1/instructions_v2.x_commercial.html), via search), which shows paid variants exist elsewhere |
| Public rate limits | UNKNOWN. None found |
| Terms of service | UNKNOWN. Not retrieved: xiaozhi.me and docs.xiaozhi.me were blocked by this session's network policy |
| Privacy policy | UNKNOWN. Same reason. Voice goes to a third-party hosted service (location UNKNOWN), so treat it as off-device audio |
| Third-party clients and modified firmware | UNKNOWN. Neither the README nor ota.md says clients must be official. The README does list community servers, so self-hosting is welcome. That says nothing about using their hosted service from other firmware |

The MIT license covers the firmware code. It does not grant access to a hosted service. Access is governed by the service terms, which I have not read.

## 3. Community alternatives

### Self-hostable servers for the same protocol

The Xiaozhi README names four ([README](https://raw.githubusercontent.com/78/xiaozhi-esp32/main/README.md), 2026-11-18):

| Server | Language | License | Notes |
|---|---|---|---|
| [xinnan-tech/xiaozhi-esp32-server](https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/main/LICENSE) | Python | MIT | Most cited. Search results describe it as the main community server. Maturity not measured |
| [joey-zhou/xiaozhi-esp32-server-java](https://raw.githubusercontent.com/joey-zhou/xiaozhi-esp32-server-java/main/LICENSE) | Java | MIT | Maturity unknown |
| [hackers365/xiaozhi-esp32-server-golang](https://raw.githubusercontent.com/hackers365/xiaozhi-esp32-server-golang/main/LICENSE) | Go | MIT | Maturity unknown |
| [AnimeAIChat/xiaozhi-server-go](https://raw.githubusercontent.com/AnimeAIChat/xiaozhi-server-go/main/LICENSE) | Go | Modified Apache-2.0: no multi-tenant use without written permission, frontend logo must stay | Not a plain open license. Avoid as a base |

Stars, release dates and issue health were not retrievable (GitHub pages blocked). Maturity is UNKNOWN beyond "named by the upstream README". The M5Stack repo also ships its own MIT server folder, which is the closest match for the StackChan build.

### Free hosted LLM and TTS with a common API

These need the user's own key. Limits are from third-party summaries that disagree with each other, so every number is "check the console".

| Service | API shape | What sources say | Source |
|---|---|---|---|
| Groq | OpenAI-style | Free plan, no card, tight per-minute and per-day caps | [OpenRouter comparison](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/), [benchlm](https://benchlm.ai/md/free-tier.md), via search |
| OpenRouter | OpenAI-style | `:free` models, small daily cap tied to purchase history in one report | same |
| Google Gemini (AI Studio) | Partial OpenAI-compatible endpoint | Flash tiers free, Pro moved to paid April 2026 in one report, data-use terms differ by tier | same |
| Cerebras | OpenAI-style | About 1M tokens a day or a month (sources disagree) | same |
| Kokoro-FastAPI (self-run TTS) | `/v1/audio/speech` | Wrapper Apache-2.0, weights Apache-2.0, costs compute only | [mirror README](https://code.amethyst.name/public-mirrors/Kokoro-FastAPI), via search, upstream license file not read |

Hosted free TTS with an OpenAI-style endpoint: none found in this pass. UNKNOWN. Retrieved 2026-11-18.

## 4. Risks and options for MaiPai

Rules from this repo: private and local by default, opt-in, labeled, fallback to offline ([README](../../README.md), [open decision 2](OPEN-DECISIONS.md)). Independence wording: not affiliated with, endorsed by or sponsored by any platform it connects to; the maker's marks are not our branding (AGENTS.md, owner rule 2026-11-18). The trademark policy file named in the task is missing from main, so I could not check it line by line.

| Option | Effort | Privacy impact | Legal risk | What our statements require |
|---|---|---|---|---|
| A. Opt-in Cloud brain via the official activation | Medium: OTA client, activation screen, WebSocket brain adapter, labels, fallback | High. Audio and text leave the home for a third party under unread terms | Unknown to medium. Terms on third-party firmware unread. Could look like an endorsed integration | Ask first. Label "service run by a third party, not by this project". No marks as branding. Off by default, no memory cost when off |
| B. Community server route | Low: one URL setting, docs. We ship no server | Depends on the server the user picks. Home-run server stays local | Low. MIT servers. Avoid the modified-Apache one in docs as a recommendation | Say we do not run or vouch for any server. Keep credits accurate |
| C. Bring your own key | Low to medium: already the own-LLM path, add provider presets and a label | Medium. Data goes to the provider the user picks, under that provider's terms | Low. User holds the account and the terms | Visible mark on cloud addresses, plain http warning (open decision 2) |
| D. Do nothing | None | Best | None | Nothing new. Loses "stock robot parity without a hub" for people who want the free cloud |

## 5. Recommendation and open questions

Recommendation: D for the official service until M5Stack answers. Ship C now, since the own-LLM path exists. Add B as a documented URL setting, with the four servers listed neutrally and licenses stated. Revisit A only with written permission or readable terms that allow it.

Questions only the owner or M5Stack can answer:

1. Owner: is a third-party cloud acceptable at all under the "private and local" promise, even labeled and opt-in?
2. Owner: where is the trademark policy file? It is not on main.
3. M5Stack: do the service terms allow third-party or modified firmware to use the hosted service?
4. M5Stack: is the stock StackChan service run by M5Stack or by Xiaozhi's operator, and whose privacy policy applies?
5. M5Stack: are there rate limits, fees or an end date for free use?
6. M5Stack: is the activation flow open to other firmware, and may we describe it in our docs?
7. Lawyer: MIT and Apache-2.0 into AGPL, and the notice list for the combined release.

### Draft courtesy email (not sent)

Subject: Question about third-party firmware and your hosted StackChan service

Hello,

I maintain MaiPai for StackChan, an independent open-source firmware and host program for the StackChan robot. It is AGPL-3.0, built on your MIT-licensed firmware, and it is not affiliated with or endorsed by M5Stack. It runs locally by default.

Some owners ask for the free hosted AI and voice service. Before we offer anything, I would like to ask:

1. May third-party firmware connect to the hosted service if the owner turns it on?
2. If yes, is there a terms page, a rate limit or an approved way to activate a device?
3. Who runs the service and which privacy policy applies to voice data?

If the answer is no, we will not connect to it. I will not contact the service until I hear from you. Thank you for the open-source release.

Name and contact: (owner fills in)

## Retrieval gaps

Blocked by this session's network policy: docs.m5stack.com, xiaozhi.me, docs.xiaozhi.me, xiaozhi.dev, github.com pages and api.github.com. Raw file pages on raw.githubusercontent.com worked. Everything marked "via search" is a search summary of a third-party page, not a primary read.
