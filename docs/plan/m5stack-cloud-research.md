# M5Stack cloud and Xiaozhi service: research paper

Working paper for the owner. Not legal advice. First pass 2026-11-18, second pass the same day. Public pages and public repositories only. No traffic captured, no keys extracted, no server of theirs contacted beyond normal page fetches of public documentation.

## Summary (10 lines)

1. The StackChan firmware, its server and the Xiaozhi firmware under it are MIT. Relicensing into AGPL is allowed if the notices stay (section 1).
2. M5Stack's StackChan page says the factory AI Agent is powered by XiaoZhi and is bound through the StackChan World app, not through xiaozhi.me. The two are not interoperable (section 2).
3. The Xiaozhi README says personal users register and get a free Qwen real-time model. It states no limits (section 2).
4. The device side is public and short: one OTA POST, an activation code, a WebSocket with Opus audio and MCP tool calls (section 3).
5. The StackChan server folder is not a voice server. It handles accounts, binding, the avatar relay and calls into the Xiaozhi platform (section 3).
6. Third-party-client terms, free limits, voice-data retention, region limits and automated access are UNKNOWN. No public page answered them (section 2).
7. Four self-hostable servers exist: three MIT, one modified Apache (section 4).
8. Decision 34 (owner, 2026-11-18) sets two equal Brain routes. Route A, hosted by M5Stack/Xiaozhi, stays planned until the cloud-brain test build proves their server accepts our firmware. If it does not, A is hidden and the docs say why (section 5).
9. Each route shows one plain line about where voice goes. The offline fallback stays. Leaving hosted erases what the unit keeps and cannot erase what their servers keep (section 6).
10. Open questions that only the test build, the owner or a lawyer can settle are in section 7.

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

## 2. What we could read (2026-11-18)

All pages below were fetched on 2026-11-18 as ordinary public pages.

| Source | What it gave us |
|---|---|
| [xiaozhi.me](https://xiaozhi.me) | A JavaScript shell. The fetch returned the page title only. No terms, no limits |
| Terms and privacy pages on xiaozhi.me | Same: JavaScript shells, title only. Nothing readable |
| [docs.xiaozhi.me/en/](https://docs.xiaozhi.me/en/) | Guides only: connect and bind, flashing, hardware, console settings, MCP, protocol references, troubleshooting. The index has no terms or privacy page. I did not read the "Accounts & binding" and "Device codes / ownership" guides |
| [xiaozhi-esp32 README](https://raw.githubusercontent.com/78/xiaozhi-esp32/main/README.md) | "The firmware connects to the official xiaozhi.me server by default. Personal users can register an account to use the Qwen real-time model for free." No limits stated. It lists four open-source servers "for server deployment on personal computers" and points to `docs/ota.md` for "OTA Configuration, Activation, and Firmware Updates" |
| [docs.m5stack.com/en/StackChan](https://docs.m5stack.com/en/StackChan) | "The AI Agent feature in the factory firmware is powered by XiaoZhi. StackChan also supports other XiaoZhi-based firmware. The factory firmware is configured through the StackChan World app, while other firmware versions are typically configured through xiaozhi.me. These two systems are not interoperable." Unpair first when you switch, and the reverse. The factory firmware binds through an M5Stack account in the StackChan World app. Unbinding clears AI Agent settings and deletes conversation history |
| [M5Stack store terms](https://shop.m5stack.com/policies/terms-of-service) | Covers the web store (orders, prices, returns, site use). It does not mention the robot's AI service |
| M5Stack store privacy, shipping and refund pages | Linked from the same footer. Store scope. I read only the terms page, so the other three are not checked |

What the pages say about our question, in plain words: the hosted AI service is run through Xiaozhi's platform, M5Stack's own robot reaches it by a different binding path than a third-party firmware, and no public page sets rules for third-party firmware using the hosted service.

### Unknown

| Question | State |
|---|---|
| Terms for third-party clients and modified firmware | UNKNOWN. No readable terms page found |
| Free limits (minutes, tokens, devices per account) | UNKNOWN. The README says free and names no limit |
| Voice-data retention, location and use | UNKNOWN. No readable privacy page for the voice service. Treat voice as off-device audio |
| Region limits and sign-up requirements | UNKNOWN. Third-party guides say sign-up uses a phone number (via search, not a primary read) |
| Automated access (a script or a second firmware activating on its own) | UNKNOWN |
| Whether the stock StackChan build points at xiaozhi.me or an M5Stack-run copy | UNKNOWN. The docs say the factory binding runs through the StackChan World app and an M5Stack account |
| Paid tiers | UNKNOWN |

The MIT license covers the firmware code. It does not grant access to a hosted service. Access is governed by service terms we could not read.

## 3. How the device side works (read from public docs)

### Activation and OTA

Source: [xiaozhi-esp32 docs/ota.md](https://raw.githubusercontent.com/78/xiaozhi-esp32/main/docs/ota.md), retrieved 2026-11-18.

- The OTA endpoint "supplies connection settings, activation information and an optional firmware URL". Binaries download separately.
- Two POST endpoints: the OTA base URL (query) and the same URL plus `activate`. The prefix depends on the deployment. The device uses a saved `wifi.ota_url`, else the build default `CONFIG_OTA_URL`.
- The query request carries headers `Device-Id` (the MAC), `Client-Id` (a UUID the firmware keeps), `User-Agent` (`BOARD_NAME/version`), `Accept-Language`, `Activation-Version` (1, or 2 when a serial number exists) and `Serial-Number` when present.
- The query body (layout version 2) carries chip, flash and partition facts, the running firmware name, version and ELF hash, display size, board facts including the Wi-Fi name, signal strength and local IP address, and a map of protocol features (MCP, AEC and others). This is what leaves the unit at every check.
- The reply carries up to five parts: `mqtt` or `websocket` connection settings (the WebSocket part is a URL and a token), `server_time`, `firmware` (a version and an optional URL), and an optional `activation` object (a code, a message and a challenge). A bound device normally gets no `activation` part. The device saves the settings and reuses them.
- Activation: the device shows or speaks the code. The owner enters it in the service console. The device posts to `activate` and gets 202 while waiting and 200 once bound, then queries OTA again. Version 1 sends an empty body. Version 2 sends the serial number and an HMAC-SHA256 of the challenge made with a hardware key in the chip.
- Retries: ten failed checks at most, starting at ten seconds and doubling. Each round allows ten activation attempts.
- Firmware updates: a version and a URL in the reply. The doc says no checksum or signature field exists that current firmware reads.

### Websocket

Source: [xiaozhi-esp32 docs/websocket.md](https://raw.githubusercontent.com/78/xiaozhi-esp32/main/docs/websocket.md), retrieved 2026-11-18.

- Handshake headers: `Authorization` (usually `Bearer <token>`), `Protocol-Version`, `Device-Id`, `Client-Id`.
- The device sends a JSON `hello` with version, features (MCP, AEC and others), transport and audio parameters (Opus, 16 kHz, mono, 60 ms frames). The server answers with its own `hello` and a `session_id` within 10 seconds, or the device reports a failed connection.
- Then two kinds of frames flow. Binary frames are Opus audio in both directions (three framing variants). Text frames are JSON, chosen by `type`.
- Device to server: `listen` (start, stop, wake word detected, with a mode), `abort`, and `mcp` replies.
- Server to device: `stt` (what you said), `llm` (an emotion), `tts` (start, stop, sentence text), `mcp` tool calls, `system` (reboot), `alert`, and an optional `custom`.
- Our reading: the voice itself, the transcript and the tool calls all pass through the service. Audio leaves the home for as long as the unit listens.

### The StackChan server folder

Source: [m5stack/StackChan server README](https://github.com/m5stack/StackChan/tree/main/server), retrieved 2026-11-18. MIT.

- A single Go service for the app, the devices and an admin console, with MySQL.
- Accounts: the app's register and login calls are forwarded to "a remote M5Stack-compatible user system". The server then issues its own tokens.
- Devices: create, bind, unbind, rename, friends, posts, dances, panorama pictures, an app list and file uploads. Device calls carry an RSA-encrypted token made of the MAC, a nonce and the time. The server rejects tokens more than 10 seconds off. The keys are configuration values, not in the repo.
- A WebSocket at `/stackChan/ws` relays Opus audio, JPEG frames, avatar and motion control, call state and camera or audio switches between the app and the device. This is the avatar and remote view path, not the voice assistant.
- A Xiaozhi module: the server exchanges a secret key for a developer token, hands a token and a license token to devices, and on unbind it restores the default agent settings and unbinds the device on Xiaozhi's side. This is how the factory binding reaches Xiaozhi.
- It does not contain the voice pipeline (speech to text, model, speech to speech). That stays on Xiaozhi's side.

What this means for us: a third-party firmware that follows the public OTA and WebSocket docs binds the xiaozhi.me way (a code typed in their console). The StackChan World path needs an M5Stack account, an RSA scheme with keys we do not hold and a Xiaozhi developer secret. We do not have those and do not need them for route A.

## 4. Community alternatives

### Self-hostable servers for the same protocol

The Xiaozhi README names four ([README](https://raw.githubusercontent.com/78/xiaozhi-esp32/main/README.md), 2026-11-18):

| Server | Language | License | Notes |
|---|---|---|---|
| [xinnan-tech/xiaozhi-esp32-server](https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/main/LICENSE) | Python | MIT | Most cited. Search results describe it as the main community server. Maturity not measured |
| [joey-zhou/xiaozhi-esp32-server-java](https://raw.githubusercontent.com/joey-zhou/xiaozhi-esp32-server-java/main/LICENSE) | Java | MIT | Maturity unknown |
| [hackers365/xiaozhi-esp32-server-golang](https://raw.githubusercontent.com/hackers365/xiaozhi-esp32-server-golang/main/LICENSE) | Go | MIT | Maturity unknown |
| [AnimeAIChat/xiaozhi-server-go](https://raw.githubusercontent.com/AnimeAIChat/xiaozhi-server-go/main/LICENSE) | Go | Modified Apache-2.0: no multi-tenant use without written permission, frontend logo must stay | Not a plain open license. Avoid as a base |

Stars, release dates and issue health were not read. Maturity is UNKNOWN beyond "named by the upstream README". The M5Stack repo also ships an MIT server folder, but it is the account, binding and avatar service, not a voice server (section 3).

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

## 5. How we decide

Decision 34 (`docs/design/decisions.md`, owner, 2026-11-18) says the Brain choice has two equal routes:

- **A: Hosted by M5Stack/Xiaozhi.** Their servers answer.
- **B: Custom.** Your own key, a community server address, your own host or MaiPai Home, or a model on your computer.

Neither route is hidden behind the other.

Rule for A: it stays **planned** until the cloud-brain test build (`docs/plan/cloud-brain-firmware-test.md`, on the firmware branches, not yet in this checkout) proves their server accepts our firmware. The proof is small and public: the unit reaches the OTA address, gets an activation code, the owner binds it in his own xiaozhi.me account, the unit connects and a spoken question gets an answer. The test never sends anything beyond the stock check described in section 3 and runs only with the owner's yes.

| Test result | What we do |
|---|---|
| Binds, connects and answers | Route A becomes a normal, labeled choice. The docs say whose servers it is and keep the terms question open as UNKNOWN until a readable page exists |
| Refused at the OTA, the activation or the websocket hello | Route A is hidden. The docs say why in the words of the refusal and what we saw |
| TLS or clock failure | A build problem on our side, not a refusal. Fix and retry (the first run on 2026-11-18 showed both; fixes are in the test doc, section 9) |
| Works but later stops | Route A is marked "may stop working" on the page, and the offline fallback and route B carry on |

What does not change either way: route B works without any of this. The offline fallback stays. No MaiPai code ships a server address for route A that is not shown to the person using it.

## 6. Settings design: the Brain page (one page)

Placement: the Brain page of the host settings and the robot's first-run step share these words. Planned work, not built. Strings go through the translation pack.

**Page title:** "Where should my brain live?"

**Two routes, shown side by side, same size:**

| | Label | One line under it (the privacy line) | Status shown |
|---|---|---|---|
| A | **Hosted by M5Stack/Xiaozhi** | "Your voice leaves your home and goes to their servers. Their terms apply." | A "Planned" tag and a disabled Save until the test build passes. Hidden with a plain reason if it fails |
| B | **Custom** | "Your voice stays where you point it." | Ready. Sub-choices: MaiPai Home, my own servers, a small stack on this computer, a community server address |

Under both, in plain type: "This project is not affiliated with or endorsed by M5Stack or the original StackChan creators." (the short line from `docs/legal/affiliation.json`).

**Route A detail (when it is enabled):**
- A first screen shows the code and says: "Enter this code in your own account on the service's site. We never see your password."
- A strip on the robot's screen says that a hosted brain is on.
- Mute and full quiet still stop the microphone. Vision off still holds.
- The camera address from the service is ignored unless it is the paired host's.

**Offline fallback (both routes):** with no link, the robot keeps its face, clock, games and local cues, and shows the plain "Offline" label after 45 seconds. It never goes silent without saying so.

**Leaving hosted (the button "Switch to Custom"):** sources: `docs/plan/cloud-brain-firmware-test.md`, section 8 (the firmware path is in the tree on the firmware branches, not in this checkout).

| It removes | It leaves alone |
|---|---|
| The hosted link's address and token, activation state and any cached offer (every `cl_` namespace on the unit) | The host pairing, the privacy settings, the chip's key blocks (nothing is burned or read out) |
| The running check, activation loop and connect (stopped at once) | Face, clock, games, pantry |
| The saved route (set to Custom, so it does not activate again) | |

It also shows a one-screen notice (what was removed, where the voice goes now, one OK), pushes a `brain_route` event so the dashboard shows the change, and restarts.

**What leaving cannot remove:** the robot's binding in their account and any voice history their servers already hold. The page says so in plain words: "To stop your account keeping this robot, remove it in the service's own console. Ask the service about stored voice data. We can only stop sending and erase what the robot keeps."

**Not on this page:** any promise about limits, price or how long route A lasts. Those are UNKNOWN (section 2).

## 7. Open questions

1. Owner: where does the label "Hosted by M5Stack/Xiaozhi" stay accurate if the test build binds through xiaozhi.me, which is Xiaozhi's account and not M5Stack's? The M5Stack docs describe two binding systems. Proposed wording for now: keep "M5Stack/Xiaozhi" (decision 34) and name the account site in the code screen.
2. Test build: does their server accept our hello, which carries extra feature fields? The first connect shows it.
3. Test build: does this unit's chip hold a hardware key for activation version 2? One boot log line shows it.
4. Public pages: terms for third-party firmware, free limits, voice retention, region limits and automated access are UNKNOWN. Recheck when a readable page appears.
5. Lawyer: MIT and Apache-2.0 into AGPL, and the notice list for the combined release.

## Retrieval notes

Fetched as plain page requests on 2026-11-18: the xiaozhi-esp32 README, `docs/ota.md` and `docs/websocket.md` (raw files), the StackChan server folder on GitHub, docs.m5stack.com/en/StackChan, docs.xiaozhi.me/en/, xiaozhi.me, and the M5Stack store terms. xiaozhi.me and its terms pages returned only a title (JavaScript shells). Items marked "via search" in section 4 are search summaries of third-party pages, not primary reads. The raw `server/README.md` path returned 404, so the server section comes from the folder page on GitHub.
