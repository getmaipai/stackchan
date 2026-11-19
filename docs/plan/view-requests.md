# Requests for the 3D view (scripts/virtual-unit/view3d.js, view.html, view.py)

From the playground track, to the session that owns the view. Newest first. The view files stay untouched by the playground track while the 3D session works.

## 2026-11-18: the music dance (dance_sim.py, docs/dev/virtual-unit-dance.md)

The simulation is done on the unit side. The screen frames already carry the overlays, the notes, the eyes and the dance faces (the renderer draws them), the head moves through `UNIT.head()` and the lights through `UNIT.leds`. What the view needs:

1. **State.** Add `"dance": UNIT.dance.status() if UNIT._dance is not None else None` to the JSON the page polls (view.py, next to `"leds"`). Fields: `running`, `mode` (home or unit), `song`, `step` (0 to 4) and `step_name`, `down`, `bpm`, `level`, `eye` ([x, y]), `ring` (12 RGB triples), `overlays`, `notes`, `face`, `head_moves_last_minute`.
2. **Controls.** A "Music dance" row: a song list (`slow`, `fast`, `very_fast`, `loud_peak`, `quiet`, `fades`), a mode switch (Home reachable or unit alone), Start and Stop. Start is `POST` of the tool call `sim.music` with `{"action": "start", "song": ..., "mode": ...}`; Stop is `{"action": "stop"}`. `sim.music` is not a firmware tool: view.py's call path must pass names that start with `sim.` straight to the unit (VirtualUnit.call already does).
3. **The four dance buttons** already work through `self.robot.dance`; they now play the firmware's keyframes (head, eyes, face). Add `bob` to the choice list (`CHOICE['self.robot.dance']`): the nod on the beat, which runs until Stop dance.
4. **The 3D lights** should follow `dance.ring` (12 pixels, at most half of full brightness) and show the step name beside them.

## 2026-11-18: the installed set (docs/dev/virtual-unit-assets.md)

State panel: add `"assets": UNIT.assets.slots() if getattr(UNIT, "_assets", None) else None` to the polled state: per kind the slots used out of available and the active item, the free pool bytes and what is loaded. A small "Installed" block with one bar per kind (used of slots) and the pool bar would show decision 17 at work. Install, swap and remove are tool calls (`sim.assets` until the firmware lists `self.assets.*`).

## 2026-11-18: dance session and host-away (SF51, SF49)

The dance state (`"dance": UNIT.dance.status()`) now also covers the unit-owned session (`mode` "session"): the ring pixels in `ring` are the unit's breath (step 2), chase (step 3) and swell (step 4). The Offline label and the notice are renderer output (no view change); `UNIT.host_away` has `label`, `notices` and `attempts` if the page wants a "host away" line.

## Answers from the view session (2026-11-18)

Done from the list above: the state carries `dance` (the name of the dance running, or empty) and `dance_sim` (your `status()`), the dance list has `bob`, the lights follow the unit's `leds` 20 times a second with the step named in the limiter table, and the **Music dance** row calls `sim.music` (song, mode, Start, Stop).

### Field names for the Utilization panel

The page reads `util` in `GET /state`. `view.py` fills what the rig knows today; add the rest under the same names and the rows appear with no change to the page.

| Field | Meaning | Filled now |
|---|---|---|
| `battery_percent`, `charging`, `powered_by` | from the body | yes |
| `supply` | `idle_v`, `load_v`, `sag_v`, `input_ma`, `brownout`, `basis` (the assumed model in `hw.py`) | yes |
| `memory` | `UNIT.memory.numbers()`, every number shown as a row | yes, once the memory model exists on the unit |
| `clock_ms`, `step_ms` | the fake clock and its step | yes |
| `hours_left` | battery hours left at the present draw (number) | **no: needs a draw model** |
| `draw_ma` | present current draw in mA | **no** |
| `cpu_percent` | the unit's CPU use | **no** |
| `gates` | a list of `{name, used, limit}` for the memory gate lines | **no: say which lines** |
| `time_scale` | how many times faster than real time the fake clock runs (1 to 20), set by `POST /hw` with key `time_scale` | yes |

### Not built yet, and what each needs from you

- **Talk panel** (`scripts/virtual-unit/talk.js`, built and tested against a fake bridge): it shows only what the bridge reports and never opens a microphone itself. `view.py` answers `GET /talk/state` with 404 until the bridge exists; replace that route. State fields it reads: `mic_on`, `speaker_on`, `live_mic`, `mic_level` and `speaker_level` (0 to 100), `latency_ms`, `transcript` (`[{who, text}]`), `message`. Earlier note: Proposed: `GET /talk/state` giving `{live_mic, mic_level, speaker_level, transcript: [{who, text, t_ms}], latency_ms}` and `POST /talk` with `{action: "mic_on" | "mic_off" | "speaker_on" | "speaker_off"}`. Nothing plays or listens until that exists.
- **Live mode picker**: needs the host API of `docs/plan/playground-live.md` reachable from `view.py`. Proposed: `GET /backends` giving `[{id, name, kind: "simulation" | "robot", busy_by}]`, `POST /backend` with `{id}` or `{disconnect: true}`, and `backend` in `/state` (`{id, kind, live, lease_expires_ms, message}`) for the LIVE banner and the one-session messages.
- **Face parts and game screen previews**: nothing to show yet.

Also done (2026-11-18, later): `assets` in the state (your `slots()`) with an Installed block in the Utilization panel, and `host_away` (`label`, the last notices, the number of attempts) with a line under the power table when the label shows.

## From the playground track, 2026-11-18 (power model and live adapter)

- **Power:** `hw.view()` has `power {draw_ma, hours_left, drain, basis}` and `utilization()` has `draw_ma`, `hours_left` (not on a cable), `power_basis` and `drain`. Please add a "Drain the battery" checkbox next to Clock speed (`POST /hw {key: "drain", value: true or false}`). The basis stays "assumed" until `schema/power-model.json` is measured.
- **Live backends:** `scripts/virtual-unit/backends.py` is ready for the routes proposed above: `BackendManager(Simulation(UNIT), host_url, token, who)` with `list()` (for `GET /backends`), `connect(id, now_s)` (for `POST /backend`), `disconnect()`, `tick(now_s)` (from the pump, about once a second) and `status()` (for the `backend` field and the LIVE banner: `{id, kind, live, message, notice}`). `scripts/virtual-unit/fake_host.py` serves the host routes locally to try it.

## Where the new screens are, and what to list (playground track, 2026-11-18)

Not on `main` yet: the game-over screen (UX15, UX15b), clock styles (UX14, UX14b), the games page and walls (UX13e), the control sheet (UX13c), Timers and Alarms (UX13f), first run (UX13d), the Q and A games (UX17), Dice Poker (UX18) and the mumble (UX16) are on `origin/ux/unproven-games`; the firmware track lands the patches on `main`. In `scripts/virtual-unit/scenarios.py` on that branch: `SCREENS` (screens renderer: `clock-*`, `screen-control-sheet-tiles`, `screen-alarms-app`, `screen-page-timers-*`, first-run, and the filmstrips `FILMSTRIPS`, which are merged into `SCREENS` and compose frames with `strip` steps), and `GRID_SCENARIOS` (a separate program, `.runs/vu-screens/grid/grid_render`, run like `LOCK_SCENARIOS` with `run_lock(name)`): `game-*`, `game-over-*`, `game-riddle-*`, `game-trivia-*`, `game-twenty-*`, `game-dicepoker-*`, `game-slide-*`, `game-snake-*`. The viewer lists `SCREENS`, `LOCK_SCENARIOS`, `COVER_SCENARIOS` and `GRID_SCENARIOS` the same way `main()` there does. Renderer commands: `pset cstyle N` and `pset asleep 1` (clock), `snapnow FILE` (a picture with no frame run); the grid program takes `game`, `drop`, `tap`, `swipe`, `tiles`, `over RESULT|SCORE|BEST|NEWBEST|LANG`, `qa riddle|trivia|twenty ...`, `poker ...`, `stripadd` and `stripwrite`.
## Answers from the view session (2026-11-18, later still)

- **Live picker: done** against your `backends.py` and `fake_host.py`. `view.py` builds `BackendManager(Simulation(UNIT), host, token, "the virtual unit view")` from the environment (`MAIPAI_PLAYGROUND_HOST`, `MAIPAI_PLAYGROUND_TOKEN`; never printed), serves `GET /backends` and `POST /backend`, puts `backend` in `/state`, renews the lease from its own loop and sends `/call` to the robot while live. The page has a Robot section (list, Connect with a confirmation for a real robot, Disconnect), a red LIVE banner, `LIVE:` in the tab title, and it dims and locks the Simulation's own panels. The Simulation's body controls answer with a plain refusal while live. With no `backends.py` or no host set, only the Simulation is offered.
- **Not done in Live:** the drawn head, lights and screen still show the Simulation. `Live.state()` and `Live.snapshot()` are fetched or available, but the page does not draw from them yet; the banner says so.
- **Drain: done.** A "Drain the battery" checkbox beside Clock speed (`POST /hw` key `drain`), and the Draw and hours-left rows carry the basis and the words "a placeholder until measured". They appear when `hw.py` has the power model.
- **Your three lines in `view.py`** (`utilization()`): the same fields are now set there behind `hasattr(HW, "draw_ma")`. When your branch merges, take the view's version of that function.
- **Sounds:** the action picker lists the twelve sound names for `self.audio.play_sound`. The virtual unit plays nothing aloud.
- **Tests:** `host/tests/test_vu_view_live.py` drives the picker and the drain switch with a real pointer against the fake host; it skips where `backends.py`, `fake_host.py` or the power model are absent.

## Spot check of the owner's feedback list against the viewer (view session, 2026-11-18, main at 51c44164)

Checked by screenshot and by the real-pointer tests (`host/tests/test_vu_view_pointer.py`, 15 passing).

| Item | State | How it was checked |
|---|---|---|
| Reset button | there: a flush pill-shaped key under the controller with its mark, the red light and the two slots; a click restarts the unit | close render and the reset test |
| Side USB-C | there: an open socket on the controller, a click target with its own cable | screenshot with the cable in; the two-socket click test |
| Top touch sensors | there, under the shell: the top is plain as on the real unit; the pads glow under the pointer and on a touch | top screenshot; the touch pad test |
| Rear cables | there: the folded black flat cable, its run into the holder, two white flat cables with blue print, the battery lead and the servo leads | lit open-back screenshot |
| Glowing lights | there: bars lit along their length, halos, light on the inside, the windows in the top connectors; nothing on the controller | dim-room screenshots; the lights test |
| Drag head pan and tilt | there, through the unit's limiter, with the arrow keys | the head drag test |
| Click to plug | there on both sockets | the two-socket click test |

Still missing or weaker than the real unit:

1. The small print on the rating label and on the label under the base is stand-in bars (the name, the two-character mark and two large marks are drawn).
2. The round finger recess behind the card slot is only marked by its rim; the side labels sit on the surface, not in their shallow recess.
3. The two small dots beside the camera are drawn brighter than the real pale ones.
4. The inside of the base (`base_board`) is a guess: no photo of the open base exists.
5. In Live mode the picture still shows the Simulation; drawing from the robot's own state and screen is not done.
6. The Talk panel is off until a voice bridge exists.
7. The game-over screen and the clock styles are not on main, so the viewer has nothing new to show for them; the games page (`screen-page-games`, `more-games`) is in the scenario list where the renderer build has it. Asked the playground track for the names to add.

## Still screens in the viewer (view session, 2026-11-18)

Answer to the playground's note that the game-over screens and the other grid screens are a separate program. The Scenarios list now also offers `still:<name>` for every name in `COVER_SCENARIOS`, `GRID_SCENARIOS` and `LOCK_SCENARIOS` whose program is built under `.runs/vu-screens/`. Play draws it with `scenarios.run_lock(name)` and puts it on the robot's screen for 10 seconds, then the running screen returns; `still` in `/state` names it meanwhile. So `game-over-*`, `game-riddle-*` and the rest show in the viewer as soon as they are in `GRID_SCENARIOS` on main with a built `grid/grid_render`; the clock styles and the new pages show through `SCREENS` as any other scenario. Nothing more is needed from the view for them.
