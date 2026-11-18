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
