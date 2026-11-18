# Requests for the 3D view (scripts/virtual-unit/view3d.js, view.html, view.py)

From the playground track, to the session that owns the view. Newest first. The view files stay untouched by the playground track while the 3D session works.

## 2026-11-18: the music dance (dance_sim.py, docs/dev/virtual-unit-dance.md)

The simulation is done on the unit side. The screen frames already carry the overlays, the notes, the eyes and the dance faces (the renderer draws them), the head moves through `UNIT.head()` and the lights through `UNIT.leds`. What the view needs:

1. **State.** Add `"dance": UNIT.dance.status() if UNIT._dance is not None else None` to the JSON the page polls (view.py, next to `"leds"`). Fields: `running`, `mode` (home or unit), `song`, `step` (0 to 4) and `step_name`, `down`, `bpm`, `level`, `eye` ([x, y]), `ring` (12 RGB triples), `overlays`, `notes`, `face`, `head_moves_last_minute`.
2. **Controls.** A "Music dance" row: a song list (`slow`, `fast`, `very_fast`, `loud_peak`, `quiet`, `fades`), a mode switch (Home reachable or unit alone), Start and Stop. Start is `POST` of the tool call `sim.music` with `{"action": "start", "song": ..., "mode": ...}`; Stop is `{"action": "stop"}`. `sim.music` is not a firmware tool: view.py's call path must pass names that start with `sim.` straight to the unit (VirtualUnit.call already does).
3. **The four dance buttons** already work through `self.robot.dance`; they now play the firmware's keyframes (head, eyes, face). Add `bob` to the choice list (`CHOICE['self.robot.dance']`): the nod on the beat, which runs until Stop dance.
4. **The 3D lights** should follow `dance.ring` (12 pixels, at most half of full brightness) and show the step name beside them.
