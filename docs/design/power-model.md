# The power model of the virtual unit

How much current the virtual robot draws, how long its battery lasts, how fast it drains and charges, and a day-of-use planner. Code: `scripts/virtual-unit/power_model.py`, data: `schema/power-model.json`, hook: `Hardware` in `scripts/virtual-unit/hw.py`, tests: `host/tests/test_power_model.py`.

## Every number is a placeholder

The real unit reads a battery percent and no battery current, and the battery's capacity is not in the code (`docs/dev/battery-and-power.md`). So each figure in `schema/power-model.json` has the status `placeholder`, the model reports `basis: assumed`, and the Utilization panel marks the rows. When the bench has measured a load, the firmware track replaces the value, sets its status to `measured` and names the source. When every figure is measured, the model reports `measured`. Nothing else changes.

## What it computes

- **Draw** in mA for a state: a base (processor, face, Wi-Fi on, the screen at half brightness) plus a term for each thing that is on: screen brightness, Wi-Fi off, microphones, the speaker, both servos holding, each moving servo, the camera, the light ring, the screen off. States in the table: idle, listening, talking, moving, dance, camera, asleep, idle with the screen dim and no Wi-Fi.
- **Hours left** from a percent and a draw: `usable_mah * percent / 100 / draw`. With the placeholders a full battery lasts about three hours of ordinary use, under one hour of dancing and over five asleep. These are the right order of size, not measurements.
- **Drain** on the battery and **charge** on a cable as the fake clock runs: a cable gives back at most the charger limit (700 mA) minus what the unit draws, at half that rate above 80 percent. The drain is **off by default** (the battery stays where the person put it; set it with the `drain` key of the hardware controls); on, the clock-speed control makes a drain visible in seconds.
- **Day planner:** hours spent in each state give the average draw and how long a full battery lasts at that mix (`python3 scripts/virtual-unit/power_model.py usual`). Profiles: usual, always listening, desk.
- A flat battery runs the unit's own low-battery ladder (chirp at 20, the spoken ask at 10, sleep at 5 after the grace), which `hw.py` already implements.

## Where it shows

`GET /state` utilization carries `draw_ma`, `hours_left` (left out on a cable) and `power_basis`; the panel already has rows for them. The hardware view carries `power {draw_ma, hours_left, drain, basis}`. A checkbox for the drain and a row for the day planner are for the view's owner to add (`docs/plan/view-requests.md`).

## Not here

The CPU percent row (needs a measured load), a charging curve beyond the taper, battery temperature, and ageing. Each would be a number to measure first.
