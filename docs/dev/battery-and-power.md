# Battery and power: what the unit can measure, how to log a drain and a charge, and the tables to fill

Firmware track, 2026-11-18. The tool is `self.bench.power_log {seconds, interval_s}` (patch SF61, bench images only). Nothing below is a measured curve yet: the tables are empty on purpose, and every number in them comes from a log run with the steps in section 4. **Measured** means read from a bench run (window 14, 2026-11-18); **read** means read from the code; **datasheet** means from the power chip's register map and is not verified on this unit.

## 1. What the unit can read

| Reading | How | Notes |
|---|---|---|
| Battery level, percent | the AXP2101 fuel gauge (register 0xA4) through the stock battery call | a percent, no milliamp-hours |
| Charging, on a cable | status registers 0x00 and 0x01 (direction bits 6..5: 1 charging, 2 discharging, 0 standby) | measured on the Mac back port: charging true, 100 percent |
| Battery voltage (`vbat_mv`) | ADC registers 0x34 and 0x35 (enabled by the unit in 0x30) | measured: 4,197 mV at 100 percent on a cable |
| Cable voltage (`vbus_mv`) | ADC 0x38 and 0x39 | measured: 4,961 mV on the Mac back port |
| System rail (`vsys_mv`) | ADC 0x3A and 0x3B | measured: 4,432 mV |
| Charge state | register 0x01 bits 2..0 (0 tri-charge, 1 pre-charge, 2 constant current, 3 constant voltage, 4 done, 5 stopped) | measured: 3 (constant voltage) at 100 percent |
| Charge current limit | the unit sets 700 mA constant current at start (register 0x62, `Pmic` constructor) | read |
| Input current limit | register 0x16: reads 1.5 A on the Mac back port | measured; it does not say what the source can give |
| Servo supply, load, current, temperature | the servo bus (SF48) | measured: 5.1 to 5.2 V at rest |
| Battery current | **not available**: the chip has no battery current register | datasheet and `power_probe` note |

Because there is no battery current, the drain is estimated from the level against time at a known load, never from a current. Milliamp-hours are not known: the battery capacity is not in the code. **Ask the owner or read the label; do not assume the maker's figure.**

## 2. What `power_log` returns

One call logs for `seconds` (1 to 300) at one row every `interval_s` (1 to 60), at most 40 rows. A row is `[t_s, level_pct, charging, on_cable, vbat_mv, vbus_mv, vsys_mv, direction, charge_state, servo1_tenths, servo2_tenths, servo1_temp, servo2_temp, heap_free]`; a reading that failed is -1. The head does not move. A long drain is a chain of calls (a 40 row call at 60 s covers 40 minutes; chain them from the host).

## 3. The tables to fill

### Drain: minutes from 100 to 20 percent, by load (on the battery, no cable)

| Load | Minutes 100 to 20 percent | Level slope, percent per hour | Notes |
|---|---:|---:|---|
| Face only, screen at the saved brightness, Wi-Fi up, no host | to measure | to measure | the baseline |
| Face, host paired, link up | to measure | to measure | the usual use |
| Listening for the wake word (voice on) | to measure | to measure | |
| Camera look every 30 s (SF55 net) | to measure | to measure | |
| Dance running (servos moving, speaker) | to measure | to measure | the worst case for the servo rail |
| Screen off, face asleep | to measure | to measure | the floor |

### Charge: minutes from 20 to 100 percent, by source

| Source and port | Minutes 20 to 100 percent | Charge state at 80 percent | Notes |
|---|---:|---|---|
| Mac, back port | to measure | to measure | window 14 read 100 percent and constant voltage |
| Mac, side port | to measure | to measure | |
| 2 A wall charger, either port | to measure | to measure | compare with the 700 mA setting: is the chip the limit |
| Unit running a dance while charging | to measure | to measure | does the level still rise |

Derived once both tables exist: the level cost of one minute of dance, of one hour of camera watching, and the lowest level that still allows a safe dance (feeds the limiter's battery rule in `docs/plan/two-usb-ports.md`).

## 4. Person steps (the owner, with the bench agent at the host)

**The script:** `scripts/fw-power-run.py --load "face only" --minutes 120 --out .runs/drain-face.csv` chains the `power_log` calls of steps 2 and 3, writes one CSV row per reading with the load name, stops by itself on a hot servo, a low battery voltage or a level under the floor, and prints the first and last level, the slope in percent per hour and the minutes from 100 to 20 percent. `--call` takes the command that reaches the unit (the default is the cable helper `scripts/fw-serial.py`; a drain run on the battery needs the host link instead). Its checks are in `host/tests/test_fw_power_run.py`.

Quiet rules apply to every step: volume 0 and hard mute before a run, no sound tests.

1. **Prepare:** charge to 100 percent on the Mac back port (measured source) and wait until `charge_state` reads 4 (done) or the level holds at 100 for 10 minutes.
2. **Drain run, one load at a time:** unplug the cable (the serial line drops: the bench agent reads the log through the host link, which a bench image keeps up over Wi-Fi). The bench agent starts a chain of `power_log` calls (`seconds` 300, `interval_s` 30 gives 11 rows per call: a call every 5 minutes, joined by the host) and sets the load of the table row. The person does nothing but leave the unit alone, and plugs the cable in again at 20 percent or after 3 hours, whichever comes first.
3. **Charge run:** from 20 percent, plug the named source in and run the same chain until the level reads 100 or `charge_state` reads 4.
4. **Between runs:** one `power_probe {move: 0}` to record the source's readings.
5. **Safety:** stop a run if a servo temperature reaches 55 degrees (to confirm against the servo's data sheet) or `vbat_mv` falls under 3,300 (datasheet cut-off region of a single-cell battery; to confirm). Never run below 10 percent.

## 5. What the logs will decide

- the battery rule of the movement limiter (the level under which dances stop), from the servo supply against the level;
- whether the 700 mA charge setting is the limit on a 2 A charger (a candidate for a higher charge current: a decision for the owner, since it changes charging, `RULES.md` territory is not touched but a cell's charge rate is a safety matter);
- the battery floor under which games and held-motion games do not start (`docs/plan/more-games-engine.md`, section 8.3);
- the figures for the user guide: "the robot plays for about N hours".
