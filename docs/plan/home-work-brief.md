# Brief for a session in the Home repository: the StackChan robot side (2026-11-18)

Self-contained. Do not read this repository's chat history; read the files named here. The session works in `~/Developer/github.com/getmaipai/home` (its own worktree, its own `AGENTS.md`, `CLAUDE.md` and `docs/design/RULES.md`, which win over anything here). Nothing in this brief touches the StackChan repository.

## Goal
Make Home the other half of the StackChan host contract in `docs/plan/home-contract.md` (StackChan repo, `getmaipai/stackchan`). The host side is built and tested; Home does not yet send or serve four things. When all four work, a paired robot has the household's rules: a child near it quiets it, its answers carry who is speaking and their age band, its firmware updates are signed, and a new unit pairs with six digits.

## The four jobs

### 1. `child_present` sender
- Today: the host accepts the command (`host/maipai_body/command_bus.py`, kind `child_present`, payload `{device_id?: string, present: bool, seconds?: number}`, default 300 seconds, the note expires after `seconds`). Home sends nothing.
- Home work: while a person with role `child` is present near a robot (Home's own presence evidence, `backend/src/lib/scene.ts` already counts `child_present`), send the command through `issueDeviceCommand` or `sendEphemeralDeviceCommand` in `backend/src/lib/deviceCommands.ts`, to the robots from `listRobotsPairedUnderPerson`. Repeat before the note expires (every 240 seconds for 300) while the child stays; send `present: false` when the child is gone. Never send it from a guess: only from confirmed presence evidence.
- Spec first: `commons/spec/schemas/device-command.schema.json` is a union by `kind`; add the `child_present` member there (separate commons change, its own tag), then Home.
- Tests to mirror: `backend/tests/deviceCommands.test.ts` (command issue and replay), `backend/src/lib/scene.test.ts` (child presence counting). Add: sent when a child appears, repeated before expiry, cleared when gone, never sent with no evidence, never to a robot of another household.

### 2. Age band and speaker evidence on robot turns
- Today: a StackChan turn reaches Home without `speaker_evidence` unless Home's speech service attaches one (`host/maipai_body/speaker_evidence.py` defines the shape `{person, basis, level}`; `person` looks like `person-xxxxxx` or null; `basis` one of signed_in, voice, face, voice_and_face, claimed, unknown; `level` confirmed, tentative, unknown). The host sends no age band.
- Home work: for a turn that arrives from a paired robot, resolve the speaker with Home's own evidence (`backend/src/lib/turnMachine/speaker.ts`) and return, with the reply, the evidence and the age band from `backend/src/lib/ageBand.ts` (`speakerAgeBand`, role only: child, teen, adult; guests count as teen; birthdate is never used, owner ruling 2026-10-18). Unknown speaker means the strictest band that applies to the household's robot setting, not adult.
- Do not weaken a gate: `docs/design/RULES.md` rule 0 (age and surface gates outrank every other rule) applies to the robot path exactly as to chat.
- Tests to mirror: `backend/tests/ageBand.test.ts`, `backend/tests/minorLine.test.ts`, `backend/tests/turnSignal.test.ts`, `backend/tests/turnRouteU6a.test.ts`. Add: a robot turn from a child gets the child band and the child protections; an unknown speaker is not treated as an adult; no template, score or candidate list ever rides along in the evidence (only `{person, basis, level}`).

### 3. Signed update path
- Today: `backend/src/routes/devices.ts` serves `GET /api/devices/me/firmware-update` and `.../app.bin` (the auth allowlist is `backend/src/middleware/auth.ts` line 211). The host now requires a third route.
- Home work: add `GET /api/devices/me/firmware-update/app.bin.sig`: the raw 64-byte detached Ed25519 signature over the exact image bytes that `app.bin` serves (the release already carries its signature; the same one `stackchan flash` and the release manifest use). Status 404 with an empty body when there is no signature. Add the route to the auth allowlist beside `app.bin`. Never offer an update (step 1 `available: true`) for an image Home cannot also sign.
- Tests to mirror: `backend/tests/stackchanInstall.test.ts` (it builds a signed manifest with a throwaway Ed25519 key), `backend/tests/deviceTokens.test.ts`. Add: signature route returns bytes that verify against the manifest key; 404 with no signature; an update is not offered without one; the sha256 and size from step 1 equal the served image.
- Host side to read for the exact expectations: `host/maipai_body/bodies/stackchan/firmware_update.py`, tests `host/tests/test_stackchan_firmware_update.py` and `host/tests/test_firmware_update_signature.py` (StackChan repo).

### 4. Pairing with the six digits, and the robot record
- Pairing: the unit and the host pair by a key exchange and six digits (`docs/plan/link-key-exchange.md`; code `host/maipai_body/bodies/stackchan/xiaozhi/link_exchange.py`). The host's discovery is off unless `brain = "home"` or a hub URL is set. Home's part: the robot screen shows the six digits flow ("type the digits shown on the robot") and tells the owner to type them on the host computer's pairing card (`POST /api/stackchan/pairings/code-entry` is host computer only; a phone token cannot approve, so Home does not call it); an already paired unit is not re-paired by a code, so the repair screen says to forget the unit first. Every refusal says what went wrong and what to do.
- Robot record: Home's device row for a StackChan follows `commons/spec/schemas/device.schema.json` (`id`, `kind`, `name`, `area`, `capabilities`, `person_id`, `watermarks`, `offline_scope`, `last_seen_at`, hlc fields) and its live state follows `robot-state.schema.json` (`activity`, `muted`, `tracking`, and the optional fields). If a field the StackChan check-in sends (`host/maipai_body/link/checkin.py` and `host/tests/test_link_checkin.py`) is not in the record, propose it spec first; do not add a private field.
- Tests to mirror: `backend/tests/devices.test.ts`, `backend/tests/deviceAuth.test.ts`, `backend/tests/robotCompanion.test.ts`, `backend/tests/schemaChain.test.ts`.

## Files to read first (in this order)
StackChan repo: `docs/plan/home-contract.md`, `docs/plan/link-key-exchange.md`, `docs/plan/signed-update-anti-rollback.md`, `host/maipai_body/command_bus.py`, `host/maipai_body/speaker_evidence.py`.
Home repo: `AGENTS.md`, `docs/design/RULES.md`, `docs/design/devices-and-robot-link-2026-10-17.md`, `docs/design/robot-companions-2026-10-21.md`, `backend/src/lib/deviceCommands.ts`, `backend/src/routes/devices.ts`, `backend/src/lib/ageBand.ts`, `backend/src/lib/turnMachine/speaker.ts`.

## Must not be touched
- `docs/design/RULES.md`, any child or teen gate, credentials and tokens, `backend/rules-baseline.json` (only the owner changes a rule).
- The live hub: no ship, no install. Land on `main` per Home's own working mode.
- `commons/spec` except by a spec-first change in its own repository and tag.
- The StackChan repository, and any private or personal data: use persona names and `example.com`, never real family names, addresses or hostnames.

## Definition of done
1. The four jobs above each have tests that fail without the change, written first.
2. Home's own check (its landing script and gate) passes; the age and surface gate tests are untouched and green.
3. `docs/plan/home-contract.md` rows become "Works" with the Home commit named (a one-line edit in the StackChan repo by whoever lands the Home change).
4. A short report: what changed, the tests, what stays unverified (a real robot, a real update, a real child nearby), and any spec change that needs its own tag.
5. Plain language in anything a person reads; every error says what went wrong and what to do; no em dashes.
