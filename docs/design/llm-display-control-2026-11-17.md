# One command channel, many sources: how the model shows and feels, 2026-11-17

Status: design note, nothing built. Question from the owner: how does the language model tell the robot what to show and feel
(face, effects, screens and cards, sounds, lights, structured data like weather)? Owner correction the same day: the model is one
source among several. This note designs the one command channel first, then the model's adapter into it.

Marks: [from code] read in this repo today, [measured] measured on the unit, [from source: URL] read on the web today,
[estimate] my number, not measured, [unverified] from memory or a search snippet, not read at the source.

## Bottom line

1. The host already has one way into the unit: the tool calls (`self.*`, MCP style). Every source should go through one host
   module, a command bus, with one catalog of commands. The model's tags and function calls are an adapter that makes catalog
   commands; they get no special powers.
2. For the model, use a hybrid: inline tags for the cheap, frequent things (mood, effect, sound, light, a one-line text card), a
   function call for cards that carry data (strong models only), and no guessing: when the model sends nothing, nothing changes (owner decision 2026-11-17).
3. Data cards (weather, now playing, lists) never come from the model's words when a real source exists. In Home mode the hub's
   tool result becomes a card command, and the host only passes it through. In local mode there is no weather card, because there
   is no weather data.
4. One owner of the screen at a time, by priority and lease (the same idea as the look lease). A remote cue always wins and always
   shows. The model is the lowest-priority decorator.
5. Build in small steps: the parser and fallback first (host only), cards second (needs one new unit tool).

## 1. What exists today (10 lines)

1. Reply tags exist: eight moods and 26 overlay names (16 elements, 10 combinations) with English and Spanish aliases, intensity
   light/normal/heavy [from code: `reply_tags.py`].
2. `TagStripper` removes every `[...]` up to 60 characters before speech; an open `[` is held until `]`, a newline or 60 characters
   [from code: `speech/reply_stream.py`]. A tag longer than 60 characters is not a tag: it is spoken as plain text.
3. `ReplyTagger` turns tags into cues placed before or after the sentence they belong to; a mood tag changes the face; an overlay
   span ends with the sentence it opened in when streaming [from code].
4. No fallback: the keyword guess (`guess_mood`) was removed on 2026-11-17. The robot is told what to show; a reply with no tag leaves the face as it is.
5. `OverlayDirector` calls `self.overlay.set {name, intensity, seconds}` and `self.overlay.clear`; it skips quietly on a unit
   without the tool (probe cache, rechecked every 90 s) [from code: `overlays.py`, `unit_tools.py`].
6. Persona suffix teaches only the mood tag: "Start every reply with exactly one mood tag" [from code: `PERSONA_SUFFIX`]. Effects are
   not taught to the model yet.
7. Pages: `self.pages.set`, `self.page.show {name}`, `self.page.tiles {json}` (up to six tiles: icon of ten, label 12 characters,
   value 10); "the unit has no data source", the host or Home pushes data [from code: `swipe_pages.py`]. Weather and Music mood
   were not built as page types [from docs: `pages-2026-11-17.md`].
8. Screen zones are fixed: banner y 0 to 28, face y 28 to 184, subtitles y 184 to 240; overlays stay behind the face and out of the
   text zones, and pause while a page or the sheet is up [from docs: `overlays-2026-11-17.md`, `banner-row-2026-11-16.md`].
9. Unit tools seen in the patches: `self.overlay.*`, `self.pages.*`, `self.page.*`, `self.face.set_config`, `self.face.show_clock`,
   `self.face.thinking`, `self.audio.play_sound` (names: success, popup, vibration, exclamation, low_battery, offline in this
   build), `self.audio.speak`, `self.robot.set_led_color`, `self.robot.set_head_angles`, `self.robot.dance`, `self.timer.*`,
   `self.game.*`, `self.camera.take_photo`, `self.privacy.*`, `self.remote.*`, `self.look.*`, `self.facepic.*` [from code].
10. Sources already drive the unit without the model: the Remote page and paired controllers (`remote_activity.py`, with a cue and
    a log), Home's look lease (`look_owner.py`), rest and sleep looks (`routines.py`), the light service (`light_service.py`),
    timers and alarms, local stop phrases, and the unit's own touch. There is no common command layer or priority list across them.

## 2. How others do it

| System | How the model drives the output | Gets right | Wrong or costly for a small local model with streaming speech |
|---|---|---|---|
| Xiaozhi / StackChan stock | A separate `llm` message with an `emotion` name and an emoji text; tools registered on the device and called with `tools/call` (JSON-RPC 2.0) [from source: https://github.com/78/xiaozhi-esp32/blob/main/docs/websocket.md, https://github.com/78/xiaozhi-esp32/blob/main/docs/mcp-usage.md] | Device lists its own tools with schemas (`tools/list`); a user-only tool class hides risky ones | The emotion is chosen by the server, not by words in the stream; the name list is not in the docs I read; no cards |
| Home Assistant Assist | An "LLM API" is a set of tools plus a prompt; the agent passes the tools to the model and runs the calls; only exposed entities are visible; the same API is served over MCP [from source: https://contributors.home-assistant.io/core/internals/llm-api/, https://www.home-assistant.io/voice_control/voice_remote_expose_devices/] | An exposure list is a clean permission model; tools carry their own prompt text | Pure function calling: every action costs a round trip; small models need the tools list in context each turn |
| OpenAI function calling and Realtime | Model emits `function_call` with JSON arguments; the app runs it and returns `function_call_output`; arguments stream as deltas and are complete only at the done event; `strict: true` keeps calls on the schema [from source: https://developers.openai.com/api/docs/guides/function-calling, https://developers.openai.com/api/docs/guides/realtime-function-calling] | Schema checking, enums, one place for validation | Complete only when the call ends, so a card cannot be shown before the sentence is spoken; strict mode needs server support a local server may lack |
| Smart-speaker screen markup | A JSON layout document plus separate data fields; the layout binds fields by name | Layout and data are separate; the skill, not speech, supplies data | The model never writes the layout; a developer does. A full markup language is far too big for 320x240 and our RAM |
| Google Assistant visual responses | Cards and rich responses sit beside the spoken answer [unverified: not read this session] | Speech and visual are two parallel fields | Same as APL: authored by developers, not a model |
| Anki Vector and Cozmo | The program calls an animation trigger by name; a trigger is a family of animations and the robot picks one; the docs advise triggers over single animations [from source: https://cozmosdk.anki.bot/generated/cozmo.anim.html and the Vector SDK docs, via search] | Names stay stable while art changes; variation without the caller caring | Hundreds of names (603 triggers in one Cozmo SDK) is too many for a small model; we need a short list |
| Reachy Mini | A `play_emotion` tool plays a recorded clip by name from a dataset; tools are enabled per profile in a text file [from source: https://github.com/pollen-robotics/reachy_mini_conversation_app] | Per-profile tool allow list; one tool with a name argument | Long name list; tool round trip |
| SillyTavern expressions | A small local classifier (DistilBERT, 28 labels) reads the reply and picks a sprite; an optional mode asks the main model for a JSON label [from source: https://docs.sillytavern.app/extensions/expression-images/] | The model never has to learn a format; works with any model | Reads text after the fact; costs a second model and RAM; no effects or cards |
| Role-play front ends with inline tags | Models write `*smiles*` or `[happy]` in the text; the front end strips and maps them [unverified: common practice, not sourced here] | Zero extra latency; streams naturally; failure is harmless | Models forget, invent names, and speak the tag if the front end misses it |
| Other consumer companion robots | [unverified] I found no public source for how their output is driven. One has a built-in emotion engine with no language model; I do not claim more. | n/a | n/a |
| Small-model tool calling | Tool-tuned 7B to 8B models score close to larger ones on BFCL; one test found Qwen the best open family, and a quantized 8B Watt model had weak argument accuracy [from source: https://arxiv.org/pdf/2410.04587, https://www.docker.com/blog/local-llm-tool-calling-a-practical-evaluation/] | Tool calls are usable on a good local model | Most numbers are single calls; reliability with a long persona prompt and streaming is not measured. We must bench our own (section 11) |

What to take: stable short names (Vector), data apart from layout (APL), allow lists per source (Assist, Reachy), a classifier only
as a fallback (SillyTavern), tags for the frequent cases and calls for the structured ones.

## 3. The shape: sources, one bus, one catalog, the unit

```
 sources                        host command bus                        unit
 (1) LLM adapter (tags, calls)  -> validate -> permit -> arbitrate  -+
 (2) Settings page, Remote      -> (catalog entry, limits, cost)     |
 (3) Home hub (data, commands)                                       +-> self.* tool calls
 (4) host routines, presence                                         |   (one link, one stamp point)
 (5) local voice, no model                                           |
 (6) unit touch and sensors  <------ events, and its own commands ---+
```

- One module, `host/maipai_body/command_bus.py` (new), is the only place that names `self.*` tools for display, light, sound and
  cards. Today `overlays.py`, `swipe_pages.py`, `unit_remote.py`, `routines.py`, `light_service.py` each call the probe directly
  [from code]. They keep their rules and become catalog entries behind the bus (no rewrite of the rules in one step).
- A command is `{cmd, args, source, lease?, ttl_s?}`. The bus returns `{ok, shown, reason}`. `source` is set by the host from the
  channel the command arrived on. A source cannot set it, the same rule as `remote_trust.reserved_in` [from code].
- The unit stays the final floor: it applies its own clamps, quiet and mute rules, and refuses cued kinds without the host token
  [from code: `remote_trust.py`]. The bus never relaxes any unit rule.
- Cost of everything is in the catalog so the bus can refuse or shed work when the unit is busy (the governor sheds overlays first
  [from docs: `overlays-2026-11-17.md`]).

## 4. The catalog (one vocabulary)

Group, command, args and limits, unit tool today, cost. "New" means a firmware tool to add (section 9). Limits are ceilings the
bus clamps to; the unit clamps again.

| Group | Command | Args and limits | Unit tool | Cost / notes |
|---|---|---|---|---|
| Face | `face.mood` | mood of 8; `ttl_s` 1 to 60 (default: until the next mood) | expression path (`face_set`, avatar frame) [from code] | cheap; a face frame |
| Face | `face.look` | gaze x,y -1..1 | gaze (`gaze.py`) [from code] | cheap |
| Effect | `fx.set` | name of 26, intensity 3, seconds 1 to 600 (model: at most 20) | `self.overlay.set` | rain 12% of SPI time at normal, 17% heavy [from docs]; shed by the governor |
| Effect | `fx.clear` | none | `self.overlay.clear` | none |
| Card | `card.show` | type, payload (section 6), `hold_s` 3 to 60, `zone` fixed to face zone | new `self.card.show` | about 6 KB PSRAM while showing [estimate] |
| Card | `card.clear` | none | new `self.card.clear` | none |
| Page | `page.show` | clock, timers, games, actions, frame, tiles, sheet, face | `self.page.show` | exists |
| Page | `page.tiles` | up to 6 tiles: icon of 10, label 12, value 10 | `self.page.tiles` | exists; tiles older than 1 hour dim [from docs] |
| Banner | `banner.say` | text up to 60 characters, `ttl_s` 2 to 10 | banner path (`self.remote.say_status` is the remote form) [from code] | the row exists; a plain notice tool is [unverified] |
| Subtitle | `caption` | the spoken words, set by the speech path only | caption markers (N01, N04) [from code] | not a model command |
| Light | `light.look` | name of a fixed list (calm, warm, blue, green, red-alert, rainbow-slow), `seconds` 1 to 120, no flash faster than 1 Hz | light service (`light_service.py`); raw color is `self.robot.set_led_color` [from code] | cheap; "no fast flashing in any light option" [from docs: `safety-and-privacy.md`] |
| Sound | `sound.play` | name of the unit's list (success, popup, vibration, exclamation, low_battery, offline), not `find`, `urgent` false | `self.audio.play_sound` | obeys sound policy, quiet, mute |
| Speech | `speak` | text up to 200, the cue kind says who asked | `self.audio.speak` | gated, rate 3 per minute [from code: `SAY_PER_MINUTE`] |
| Motion | `head.move` | yaw, pitch inside the profile limits, speed 100 to 1000 | `self.robot.set_head_angles` | cued kind: needs the host token or a cue [from code] |
| Motion | `dance.start` / `dance.stop` | one of 10 built-ins | `self.robot.dance`, `stop_dance` | cued kind |
| Timer | `timer.set` / `alarm` / `cancel` / `stop` / `snooze` | seconds, label | `self.timer.*` | exists; the unit owns the countdown |
| Game | `game.start` / `stop` | game id | `self.game.*` | cued kind |
| Camera | `camera.photo` | none | `self.camera.take_photo` | cued kind, 3 s countdown on screen for remote [from code] |
| Volume, screen | `volume.set`, `screen.level` | 20 to 100, 10 to 100 | sheet and prefs tools [from docs] | owner or voice only |
| Privacy | `privacy.set` | mute, vision off, full quiet | `self.privacy.set` | never from the model; voice command may only do what the unit already allows [from docs] |
| Look lease | `look.claim` / `release` | owner, ttl 15 s | `self.look.*` | Home only |
| Picture | `picture.show` | id from an owner-approved library, never a URL or path | `self.facepic.*` (begin, frame, data, commit) | 150 KB PSRAM only while shown [from docs] |

Rule for new commands: one entry, a name in the unit's tool list, a clamp, a cost, a permission row, a test. Nothing else may
name a `self.*` display tool.

## 5. Who may send what (source by permission)

Y = allowed, C = allowed only with a cue the unit shows, O = owner action only (a settings page click or a paired controller the
owner allowed), N = never, L = limited as written.

| Command group | (1) LLM | (2) Settings, Remote | (3) Home hub | (4) Host routines | (5) Local voice | (6) Unit touch |
|---|---|---|---|---|---|---|
| Face mood, gaze | Y | Y | Y | Y (rest, drowsy) | N | Y |
| Effects | L: 1 per reply, 20 s, not during sleep or a card | Y, cue if remote | Y (weather) | Y (night, sleeping) | N | N |
| Cards | L: text, timer, list, countdown, now playing; no picture | Y | Y (all types) | Y (timer, alarm) | N | N |
| Pages, tiles | N (model asks for a card, not a page) | Y | Y (tiles) | Y | Y ("show the clock") | Y (swipe) |
| Banner notice | N | Y | Y | Y | N | N |
| Light | L: the fixed list, not during sleep | Y, cue if remote | Y | Y (rest, charging) | Y | Y |
| Sound | L: 1 per reply, never `urgent`, never `find` | Y | Y | Y | Y (beep, find) | Y |
| Speech | Y (that is the reply) | C (remote say asks the person at the robot) | Y | Y (announcements) | N | N |
| Head, dance, game, photo | N from tags; tool call only if the owner enabled "model may move the robot" | C | Y (follow, look lease) | Y | Y (stop, dance by phrase) | Y |
| Timer, alarm | Y through the timer tool (the unit shows its page) | Y | Y | Y | Y | Y (cancel, snooze) |
| Volume, screen level | N | Y | Y | Y (night) | Y | Y |
| Privacy, Wi-Fi, pairing, safety, settings | N | O | N | N | stop and mute words only; never unmute from hard mute [from docs] | Y |
| Camera frames | N | C | Y | Y (presence) | N | N |

Why the model is limited: its text may repeat untrusted words (a web page, a message, a user trying to inject a tag). The model
can decorate and speak. It cannot move the body, take photos or change privacy by a tag. Moving the head by model request is an
owner opt-in because the unit has servos and a wear limit [from docs: body safety].

## 6. Arbitration: who wins when sources disagree

Priority, highest first. A higher level may interrupt a lower one at once; a lower one waits or is dropped.

1. Privacy and safety state of the unit (hard mute, full quiet, sleep, low battery tired look, child and teen gates from Home).
   Nothing outranks these; `decoration_blocked()` already stops overlays under them [from code: `turn.py`].
2. Remote cue: the glyph, banner and message bubble. It always wins the banner row and is always shown [from code: `remote_activity.py`].
3. Ringing alarm or timer, find-me, low battery, errors (host routines and unit safety).
4. Owner touch on the unit (a swipe, the sheet, a page).
5. Settings page and Remote actions.
6. Home hub commands and data cards.
7. Host routines for ambience (rest looks, night, music dance, idle).
8. The model's decoration (tags, calls).
9. Host fallback guesses.

Ownership is by lease per surface, so two sources never half-draw:

| Surface | Lease holder rule | Release |
|---|---|---|
| Face expression | highest priority wins; ties go to the newest; the model's mood expires with the reply | when the holder ends, the next lower returns |
| Effect layer | one holder; a combination replaces everything (existing rule) [from docs] | `ttl_s` or `fx.clear`; sleep clears it |
| Card zone (y 28 to 184) | one card; a higher priority card replaces and the old one is queued once if its hold is not over; a lower one is dropped | hold time, a touch, speech start of a new turn, or `card.clear` |
| Banner row | existing priority list (privacy, notices, captions; 1.5 s minimum) [from docs] | existing |
| Ring light | the light service picks one look from facts; model look is a low-priority fact with ttl | ttl |
| Head | the look lease (unit, host or none) [from code]; the model has none | n/a |
| Sound | the unit's sound policy and queue | n/a |

Disagreement rules:

- A tag and a call in the same reply disagree: the validated call wins for cards, because it carries more detail; for mood the
  last one in reply order wins; for effects the first wins (one effect per reply).
- A model card against a Home data card: Home wins. A model card never replaces a Home card that is still holding.
- A source asks while its lease is lost: the bus returns `{ok: false, reason: "lower priority"}`; the source drops it. No queues
  of stale decoration (a card for a sentence spoken 20 s ago is wrong).
- Cards and effects: overlays pause while a page or the sheet is up [from docs]. A card is a page, so a weather card pauses
  rain behind it. Design choice: the weather card is drawn in the face zone with its own icon; the overlay returns when the card ends.
- A new user turn starts: model-owned face, effect and card are cleared at the first sentence of the new reply unless the new reply
  names its own.

## 7. The model's adapter: options compared

Latency is added time before the unit shows something, on top of the reply. [estimate] unless noted.

| Option | Added latency | Small-model reliability | Streaming fit | Safety | Complexity |
|---|---|---|---|---|---|
| A. Inline tags (today) | 0 ms; shown when its sentence is spoken | Good for 1 to 3 short names; fails by forgetting, rarely by harm | Excellent: stripped as the text streams | Tag text never spoken if parser is right; tags can come from echoed untrusted text | Low, mostly built |
| B. Tool calls (OpenAI style) | one extra model round trip if the host must return a result (seconds on a local model); none if treated as fire and forget | Fair to good on tool-tuned 7B to 8B; poor on a general small model with a long persona [unverified] | Poor: arguments are complete only at the end of the call, the call usually ends the turn | Best: schema, enum, strict validation | Medium; needs server support for `tools` |
| C. JSON side channel (a final JSON line or block) | 0 on the speech; the card appears at the end of the reply | Poor: small models break JSON and put it before the speech | Poor: the last line arrives last, and the host must hold text to know | Same as A | Medium |
| D. Tiny classifier on the reply text | 5 to 30 ms on the host [estimate] | Does not depend on the model; only gives mood, not data | Good: runs per sentence | Safe: output is a fixed label | Medium; model file and RAM on the host |
| E. Hybrid (recommended) | 0 for tags; fire and forget for calls; fallback on host | Tags carry the load; calls only for strong models; fallback covers silence | Good | Gates sit in the bus, one place | Medium, built in phases |

Recommended: E. Tags for mood, effect, sound, light and the short card. A function call, `show_card`, offered only when the server
and the model are known to handle tools (an owner setting, probed once). A host fallback for mood and for a few safe effects.
Home data cards bypass the model altogether.

## 8. The protocol

### 8.1 Tag grammar

One tag is `[` name, optional arguments `]`, at most 60 characters for the type-name forms and at most 90 for `[card:...]`.
Names are lowercase English with the existing Spanish aliases. Spaces, `:` and `=` are all accepted as separators (existing).

```
[mood]                       happy sad surprised angry doubt love sleepy neutral          (bare, exists)
[effect]  [effect heavy]     any of the 26 overlay names; intensity light|normal|heavy   (bare, exists)
[effect]text[/effect]        span (exists); streaming: ends with its sentence
[overlay:love]               when a name is both a mood and an effect (exists)
[sound:success]              success popup vibration exclamation   (prefix required)
[light:blue]  [light:blue 30]    name of the fixed list, optional seconds (prefix required)
[card:text Dinner at six]    a one-line text card
[card:timer 5m pasta]        shows the unit's timer page after the model also called timer.set (see 8.3)
[card:countdown 2026-12-25 Christmas]   host computes days left from its clock
[card:list Milk | Eggs | Bread]         up to 5 items
[card:np Song title | Artist]           now playing; only from a source that said so (8.4)
[clear]                      clears model-owned effect and card
```

Rules:

- Prefix forms (`sound:`, `light:`, `card:`) are required for the new kinds. A bare `[success]` or `[blue]` stays unknown and is
  dropped, so a stray word in brackets never fires a command.
- `card:` arguments are plain text and pipes. JSON is never put in a tag (60 and 90 character limits would cut it and the rest
  would be spoken).
- Unknown tag, bad argument, too long: dropped, never spoken, counted in `tags_dropped` for the bench.
- Lenient lead-in: at the very start of a reply the host also accepts `(happy)`, `<happy>`, `*happy*` and `:happy:` when it is
  exactly a mood name. Elsewhere those characters are spoken as written. Emoji are removed from speech and map to a mood
  (a table of about 20 emoji, [estimate]); they are never spoken.

### 8.2 Card types and payload shapes

A card is a catalog command, whatever its source. Payload is JSON with these ceilings. The face zone is 320 by 156 pixels; the unit
draws with its 20 px text font and Montserrat 14, 16, 20 and 24 [from docs: `pages-2026-11-17.md`]. Character limits are for Latin
text at those sizes [estimate, to be measured on the unit before they are final].

| Type | Payload | Limits |
|---|---|---|
| `text` | `{"title":"","body":""}` | title 24, body 90 (three lines of 30) |
| `weather` | `{"icon":"sun|cloud|rain|snow|storm|wind|fog|moon","temp":72,"unit":"F|C","label":"","hi":null,"lo":null,"place":"","src":"hub"}` | label 20, place 16; temp -99 to 199; `src` must be `hub` or `local` (8.4) |
| `timer` | `{"seconds":300,"label":""}` | 1 to 86400; label 16; the unit's own timer shows; this card type only selects the page |
| `countdown` | `{"to":"YYYY-MM-DD","label":""}` | host computes; label 16; shows days, or hours under a day |
| `list` | `{"title":"","items":["",""]}` | title 20, items 5, each 28 |
| `now_playing` | `{"title":"","artist":"","state":"playing|paused"}` | title 28, artist 24; no cover art in v1 |
| `picture` | `{"id":"","caption":""}` | id from the owner's library; caption 28; hub or owner source only (never the model) |
| `tiles` | up to 6 `{icon,label,value}` | existing limits (icon of ten, label 12, value 10) |

Common: `hold_s` 3 to 60 (default 12), after which the face returns. All text is cleaned by the same `_plain` rules as tiles
(control characters out, length cut, no markup) [from code: `swipe_pages.py`]. A card is pushed as one JSON string through
`self.card.show {"json": "..."}`; the unit parses it with a fixed small parser into a fixed layout per type. There is no layout
language and no model-written layout (that is the lesson of APL: data apart from layout).

### 8.3 Which things are tags, which are tool calls

| Thing | Model path | Why |
|---|---|---|
| Mood | tag | highest frequency, no data |
| Effect, sound, light | tag | short fixed names, harmless if lost |
| Text, list, countdown, now playing card | tag for small models, `show_card` call for strong models | tags keep text short; the call is valid JSON |
| Timer, alarm | the existing timer tool (a real function with a real result the model should confirm) | the unit must own the countdown; a tag cannot make a timer |
| Weather and other fetched data | no model path at all in Home mode; the hub's tool result becomes the card | the model must not retype numbers (section 9) |
| Head, dance, game, photo | not available to the model by default | section 5 |
| Page switching, privacy, volume | never | section 5 |

`show_card` function schema (offered only when enabled):

```json
{"name":"show_card","description":"Show a small card on the robot screen while you speak.",
 "parameters":{"type":"object","additionalProperties":false,
   "properties":{"type":{"enum":["text","list","countdown","now_playing"]},
                 "title":{"type":"string","maxLength":24},
                 "body":{"type":"string","maxLength":90},
                 "items":{"type":"array","maxItems":5,"items":{"type":"string","maxLength":28}}},
   "required":["type"]}}
```

The host runs it as fire and forget: it executes the command and does not send a second model request, because nothing in the result
changes the answer. If a stream carries both text and a call, the text is spoken as it arrives and the call is executed when it
completes. If a server rejects the `tools` field, the host drops it for this model and remembers (tags only).

### 8.4 Parsing a stream without speaking a tag

The path already exists (`TagStripper` then `SentenceSplitter`) [from code]. Changes:

1. A held `[` that starts a known prefix (`[card:`, `[sound:`, `[light:`) may grow to 90 characters; past that it is dropped to the
   next `]` or newline, up to 200 characters, and never spoken. Today anything over 60 is spoken [from code]; that is the one
   hole to close.
2. `]` missing and the stream ends: the held text is dropped when it starts with a known name or prefix, else spoken as text.
3. A tag split across chunks is held until its `]` (exists); a test feeds one character at a time.
4. Tags inside code fences or after a backslash are not tags (the model is quoting). Models told to avoid brackets in the persona
   text, but a user may ask for brackets; escaped `\[` is spoken as `[`.
5. Cues attach to the sentence they were in: before it for opening tags, after it for the end of a span (exists). Card, sound and
   light cues fire when that sentence's audio starts, not when the text arrives, so the picture and the voice match.
6. The first mood cue may fire before speech; effect, sound, light and card cues wait for the first sentence's audio.

### 8.5 Validation, clamping, rate limits

Every command passes the bus in this order: catalog lookup (alias to name), argument parse, clamp to the catalog limits, source
permission (section 5), gate check (section 10), arbitration (section 6), rate limit, then the unit call.

Rate limits for the model source (the host's own cap, below the unit's):

| Thing | Per reply | Per minute | Other |
|---|---|---|---|
| Mood changes | 1 per sentence, at most 4 | 20 | none |
| Effects | 1 | 6 | `seconds` at most 20; no restart of the same effect within 10 s |
| Cards | 1 | 6 | hold at most 30 s; none while a Home card holds |
| Sounds | 1 | 4 | at least 10 s apart |
| Lights | 1 | 4 | no flashing; seconds at most 30 |

Over the limit: dropped, counted, never spoken, never an error to the person. Photosensitivity: no light or card animation faster
than 3 changes per second (the common web guideline) [unverified: general knowledge, not read this session], and the org rule is
stricter for the ring: no fast flashing [from docs].

### 8.6 When the model sends nothing (no fallback, no guessing)

| Case | Rule |
|---|---|
| No mood tag in the first sentence | Nothing changes. No guessing from the words (owner decision 2026-11-17); the cure is a better instruction, a tool call for strong models, or Home's separate events |
| No mood from words | keep the current face (exists) |
| Emoji in the reply | stripped from speech; not mapped to a mood (that would be guessing) |
| Effect | none. Words never start an effect by themselves ("it is not raining" would be wrong) |
| Card | none; a card without data is worse than none |
| Sound, light | none |
| The model speaks a tag as words (parser miss) | detected by the bench; the speech path also drops any `[word]` of at most 24 letters from speech even if unknown (exists) |

### 8.6a Scenes: one tag that sets the whole look (owner question 2026-11-17, recommendation)

The design had mood, effect, sound and light as separate tags and no scene. A scene is one named preset that expands on the host into several catalog commands, so a model sends one tag instead of four, which small models do more reliably.

- **Grammar:** `[scene rainy_day]` at the start of a sentence, closed by the next scene tag, `[scene off]` or the end of the reply. Parsed and stripped like every other tag, never spoken.
- **What a scene holds:** an optional mood, a back-layer effect (rain, snow, sun, stars), an optional front effect, a ring light color, an optional quiet sound, and a hold time. Example: `rainy_day` = calm mood, rain, a cool blue ring, a soft rain sound.
- **Start set (about 10):** rainy_day, snowy_day, sunny_day, bedtime, party, birthday, cozy, spooky, focus, celebrate. A preset table, one definition in the host (and the unit's overlay names), editable on the settings page.
- **Not a new command:** `scene.set name` is one more catalog entry. It expands to commands that pass the same permission and priority checks as if each had been sent alone; a scene can never carry a body move, a photo or a privacy change.
- **Mixing:** an explicit mood tag after a scene tag wins for the face; a remote cue, privacy and the child and teen gates always win over a scene. A scene is a lease at the same priority as the model's own effects and ends with the turn unless it names a hold time.
- **Sources:** the model (tag or function), Home (event, so the hub can send scenes it owns, such as a weather scene with a card), and the owner's controls. No guessing from the words.
- **Home packages:** scenes can be shipped as catalog packages later; the host holds the local table.
- **Build:** a small host table and parser (about one day with tests), no firmware change if every part of a scene already maps to existing overlay, light and sound commands.
- **Not to be confused with:** the camera scene-awareness work in Home (what the robot sees); this is only how the robot looks and sounds.

### 8.7 Teaching the model

Short snippet, for small models (about 70 words), appended to the persona. It replaces today's `PERSONA_SUFFIX`:

```
Start every reply with one mood tag: [happy] [sad] [surprised] [angry] [doubt] [love] [sleepy] [neutral].
Optional, at most one each, only when it fits: an effect like [rain] [snow] [hearts] [confetti] [stars],
a sound like [sound:success], a card like [card:timer 5m pasta]. Tags are never spoken.
Never write a tag you are not sure of. Never make up weather, scores or other facts for a card.
Example: [happy] Nice choice! [hearts] I love that song.
```

Long snippet, for strong models (about 250 words): adds the full effect and light lists, the five card forms with one example
each, when to use a card ("show a card when the answer is a number, a list or a timer"), and, if enabled, the `show_card` schema
with "use a tag or the call, not both". Both snippets are built by the host from the catalog (names come from `reply_tags.py`
and the card table), so the prompt cannot drift from what the host accepts. Home mode sends a minimal snippet because the hub's
persona and tools already exist; the hub adds the card lines only when the unit has the card tool.

## 9. Where data comes from

Data cards are commands whose payload comes from a tool result, not from the model's sentence.

Home mode:

1. The model asks the hub's weather tool (a hub tool, owner-enabled). The hub fetches, with its own policy, and returns a
   structured result.
2. The hub's turn stream carries the result as a `card` event next to the text (a small addition to `/api/turn/stream`; the
   hub already supplies "ordered cues" to the host [from docs: `brain-seam.md`]). The hub makes the card, so the model's retyping
   cannot make a wrong number.
3. The host passes the card to the bus with source `hub`. It validates and clamps; it does not fetch, convert or add data.
4. The model's spoken text and the card are matched by the stream order: the card is shown when the sentence that follows it
   starts.
5. If the unit has no card tool, the host sends the same data as tiles (icon, label, value) on the dashboard page, or only speaks.

Local mode (the model is a local server, no hub):

- The host never fetches. There is no weather source. The `weather` card needs `src` of `hub`, or `local` when the owner put the
  data in the model's context (a block the host injects from the owner's own file or sensor, which the host reads and the owner
  configured). With neither, a `[card:weather ...]` from the model is downgraded to a `text` card marked "from the model" or
  dropped (open question 1). The model is told: "You have no weather data unless it is written in this prompt."
- Local facts that do exist: the clock and date (the unit has a clock), timers and alarms (the unit owns them), battery, and the
  names of the games. A countdown card is computed on the host from its clock, so it is safe.
- Now playing: shown only when a source says so (the host's music identify path or the hub); the model cannot start a now
  playing card from nothing.

Nothing here adds an outbound connection (zero phone-home) [from docs: `safety-and-privacy.md`].

## 10. Safety gates

- Child and teen gates: this repo adds no content filter; "a brain such as MaiPai Home may add its own age and household gates.
  Those belong to the brain and are not weakened by this repo" [from docs: `safety-and-privacy.md`]. So in Home mode the hub's
  gate filters the reply and every card payload it makes, before the host sees either. The host never creates content, only
  passes and clamps it. Card text from the model in Home mode is part of the same filtered reply.
- The bus has a `gates` hook that Home can fill with the household's state (profile of the person present, adult unlock off).
  When Home says a child is present: picture and now playing cards from outside the hub are dropped, model sounds are limited to
  the quiet set, model effects stay on. Nothing in the host can turn this hook off from the model or from a card.
- Local mode: content safety is the connected model's and the owner's persona [from docs]. The bus still clamps size, rate and
  flashing, which are body safety, not content.
- Privacy and sleep outrank decoration (exists: `muted_reason()` and `decoration_blocked()` [from code]); under hard mute no model
  sound, light or camera command passes.
- Prompt injection: only assistant output is parsed for tags. A user or a fetched page cannot put a command into the stream
  unless the model repeats it, and the model has no power over body, camera or settings (section 5). A tag in a tool result is not
  parsed.
- Remote cue is unchanged and always wins [from code]. The model never sets `source`, `token` or a cue.
- A picture card shows only an id from the owner's library or a hub image; the host never fetches an image from a URL.

## 11. What the unit needs

| Addition | What | RAM cost [estimate] |
|---|---|---|
| `self.card.show {json}` and `self.card.clear` and `self.card.status` (probe) | one tool pair, fixed layouts for text, weather, timer, countdown, list, now playing, picture frame; built on the pages code (P12) so fonts and zones are shared | state under 1 KB internal; LVGL objects about 5 to 8 KB in PSRAM, only while a card shows |
| 4 more drawn icons (snow, storm, wind, moon, fog) in the icon table | shapes only, no asset | under 1 KB flash |
| `self.light.look {name, seconds}` (only if the ring is not already a tool; check `light_service.py` path) | fixed looks, no flash faster than 1 Hz | under 200 bytes |
| Card cue in `self.remote.*` rules | a remote card shows its banner; a controller card is a cued kind | none |
| Card priority byte in the tool | so the unit can refuse a lower priority card while a higher one holds (belt and braces next to the host) | 1 byte |

Everything else (moods, effects, sounds, timers, pages) is built. Internal free RAM is tight (steady median about 37 to 90 KB
across builds [from docs: `memory-headroom-2026-11-16.md`]), so cards are PSRAM-only and allocated when shown, as the overlays
and the picture page do. A card must pass the same `fx_cost` style model before it ships.

## 12. Test plan

1. Parser fuzz (host, no unit): random strings with brackets, nested and unclosed tags, 59, 60, 61, 90 and 91 character tags, tags
   at chunk edges, emoji, `\[`, code fences, Spanish aliases. Invariants: no output contains `[` of a tag or any known tag name
   as a word; the spoken text equals the input minus tags; no exception. Also a property test: cutting the stream at every
   character gives the same cues as one chunk.
2. Streaming split tags: feed one character at a time, and by random sizes; compare cues and speech with the whole-string run.
3. Catalog tests: every command has a clamp, a permission row for all six sources, a cost; a table-driven test fails if a source
   not in the row gets through. A test that nothing outside the bus names a display `self.*` tool (a grep-style lint).
4. Arbitration tests: remote cue over model card; Home card over model card; sleep clears effects; a new turn clears model state;
   a lease lost mid-card; the same tests with a fake clock.
5. Gate tests: child present drops outside pictures; hard mute drops model sounds; rate limits per reply and per minute.
6. Unit bench (when the card tool exists): each card type at its limit and one over; a card during an overlay; RAM before and
   after (`internal_free`, `psram_min`) over 30 minutes; the pixel compare used for overlays.
7. Small-model bench (host script, `bench.py` style), run on each candidate local model and the Home model:
   - 60 prompts in five groups: plain chat (expect a mood only), emotional (sad, happy, love), weather questions with no data
     (expect no weather card), requests for a timer, list or count-down (expect a card or tool), and adversarial (the user asks the
     model to say "[rain]" aloud, to repeat a page that contains tags, to send a very long tag).
   - Metrics per model: mood tag present rate, mood matches a human label rate (200 labeled sentences), effect precision (tag
     fired when the content fits), card format valid rate, tag spoken aloud rate (target 0), fabricated weather rate (target 0),
     tool call valid rate with and without `tools`, added time to first sentence, tokens added by the snippet.
   - Gate to ship a snippet on a model: mood present at least 90 percent, tag spoken 0, fabricated data 0. Below that the model gets
     mood only and the host fallback.
8. Tag-rate bench: measure how often each model sends a correct tag, to decide whether the prompt, a tool call or a stricter instruction is needed. No words-based guessing.

## 13. Phases, with sizes

| Phase | What | Where | Size |
|---|---|---|---|
| 1 | Close the 60 character hole, emoji and lenient lead-in, per-sentence fallback, the parser fuzz and split-stream tests | host | S, 1 to 2 days |
| 2 | The command bus and catalog: wrap overlays, pages, remote and light behind it; the permission matrix as data; arbitration for face, effect, card zone; the lint | host | M, 4 to 6 days |
| 3 | Tag adapter for `sound:`, `light:`, rate limits, the generated snippets (short and long), persona wiring, the small-model bench | host | M, 3 to 4 days |
| 4 | `self.card.*` firmware tool, five icons, layouts for text, list, countdown, timer, now playing; bench the RAM | firmware | L, 6 to 9 days |
| 5 | Card tags and the `show_card` function (fire and forget), tool probe | host | S to M, 2 to 3 days |
| 6 | Home pass-through: a `card` event in the turn stream, weather card from the hub's tool, tiles fallback | hub + host | M, 3 to 5 days |
| 7 | Picture card, now playing sources, gates hook with Home's household state | host + hub | M, 3 to 4 days |

Phase 1 and 3 give the owner most of what is felt (moods, effects, sounds) with no firmware change. Phase 4 is the one that needs
a flash.

## 14. Open questions for the owner

1. Local mode and a model that writes a weather card on its own: drop it, or show it as a text card marked "from the model"?
   (Recommended: drop it.)
2. Cards from small models by tag (`[card:timer 5m pasta]`) in addition to the function call: yes or no? (Recommended: yes.)
3. Display function calls run fire and forget (no second model request, so no added delay): yes or no? (Recommended: yes.)
4. May the model move the robot (head, dance) at all, as an owner setting that is off by default: yes or no? (Recommended: no for v1.)
5. How long a card holds before the face returns: 8, 12 or 20 seconds? (Recommended: 12, with a tap to dismiss.)

## Decisions taken (2026-11-17, by the build session; the owner can reverse any of them)

1. A data card (weather and the like) shows only when its numbers came from a tool result, from Home or from a tool the owner gave their own model. A card the model invents from memory is dropped; the model still says it in words, and mood and effect tags (rain, snow) work in every mode. (Revised 2026-11-17 after the owner asked how an internet-connected local model should behave.)
2. Card tags are allowed for short cards: yes.
3. Display calls from the model run fire and forget: yes (a failed card never fails the answer).
4. The model may move the robot: no (body moves stay with the owner, remote controllers and local voice commands).
5. Card hold time: 8 seconds by default, a touch dismisses it.

6. No guessing, anywhere (owner, 2026-11-17): the robot only does what a source tells it, through the message or command stream. The design question is when and how each source (model tag, tool call, Home event, owner control) sends each command, not how the host can infer one. The keyword mood guess is deleted.

7. Scenes: yes, add `[scene name]` presets that expand into catalog commands (section 8.6a); started by a source, never inferred.
