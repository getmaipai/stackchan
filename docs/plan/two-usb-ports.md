# Two USB-C ports: what feeds what, and a limiter that measures the supply

Firmware track, 2026-11-18. Static reading of the tree plus the first bench evidence (back port on a Mac). **Nothing here changes the limiter.** The proposal is a pure core and a probe; the limiter keeps its safe default (limited on any cable) until the numbers exist.

## What is known

- **The robot has two USB-C ports:** one on the side of the controller (always used so far) and one at the back on the base (the model's "base port", `scripts/virtual-unit/model/MATCH.md`).
- **First bench evidence (owner, 2026-11-18):** with a cable from the Mac in the **back port only** (side port empty) the unit logged `usb_limited` at the cable event, reports charging true and battery 100 percent, and the Mac still lists the unit's USB serial device. So the back port reaches the same USB path as the side port: data and VBUS arrive at the controller. **Which port is plugged cannot be told from the power chip.**
- **What the stock firmware does with power** (nested tree, the maker's code): the AXP2101 power chip is set up in `stackchan.cc` (charge current 700 mA, register 0x62; the display and codec supplies); the servo supply is switched by the PY32 IO expander, pin 0 "VM EN" (`Hal::setServoPowerEnabled(true)` at start in `hal_io_expander.cpp`). The tree contains no code about the base port, no supply-voltage check and no input-current setting: the stock firmware does nothing special with the back port.
- **What the limiter uses today** (`maipai_motion_limit.cc`, ML01): `on_cable = charging || !discharging`, from AXP2101 status register 0x01 bits 6..5 (current direction). Any outside power counts as "a computer cable": half the excursion, 60 percent speed, no full dance. After SF39 the unit assumes the cable is in until the first reading.
- **What the servos report** (the servo driver `SCSCL` in the tree, `hal_servo.cpp`): `ReadVoltage` (tenths of a volt), `ReadLoad` (0 to 1000), `ReadCurrent`, `ReadTemper` and `ReadPos`, from one `FeedBack` call per servo (ids 1 yaw and 2 pitch). The stall guard already uses load and current. The servo supply voltage and its sag under a move are therefore **readable directly**.

## What is unknown (the probe answers it)

1. What the back port feeds: the servo rail only, the controller, or both. The first evidence says the controller sees it; whether the servo rail is fed from the back port at higher current than from the side port is not known.
2. What the AXP2101 offers to tell a 500 mA computer port from a 2 A charger. From the datasheet (to verify by reading, the probe returns the raw bytes): VBUS voltage ADC (0x38 and 0x39, enabled by the unit in register 0x30), VBAT and VSYS ADC (0x34, 0x3A), the input current limit (0x16, from 100 mA to 2 A) and the input voltage limit (0x15), the charge state (0x01 bits 2..0). The chip has no USB-PD and no battery current register: only the current **direction** (charging, discharging, standby). A charger-type reading (BC1.2) is not part of the registers the unit reads today; whether the chip has one is to be read from the datasheet.
3. How much the servo supply sags during a move on each supply.

## The proposed limiter (not built, not used)

Replace "any cable limits" by **measured supply health**, with the safe default kept until proven:

- Inputs: VBUS present, VBUS millivolts, servo supply (tenths of a volt, both servos), the servo supply's sag during a move, the battery state (level, direction).
- Rule, a pure function: the limit applies unless the supply is proven healthy. Healthy means: the servo supply rests at 4.5 V or more **and** sags no more than 0.5 V during a controlled small move, measured in the last N minutes; weak (rests under 4.5 V or sags over 0.5 V): limited as today; poor (under 4.0 V or sag over 1.0 V): limited and no dance at all. A battery-only unit keeps its ladder. Unknown (no reading, a servo that does not answer): limited.
- The core exists as `mpw_supply_verdict` in `maipai_power_core.h` (host test `power_core_test.c`): healthy, weak, poor, unknown from a resting reading and a sag. It is not wired into `maipai_motion_limit_core.h`.
- The controlled move for the measurement is small (15 degrees of yaw at speed 300) so it is safe on any supply; it runs only when the limiter allows motion at all, never while carried.
- Re-measure on a cable event and once an hour while on a cable; never during a dance.

## The probe and the test matrix

`self.bench.power_probe {move}` (patch SF48, bench only, not landed yet) returns the power chip's decoded status, its ADC values, the input limits, the raw register bytes, each servo's bus telemetry, and the sag of the servo supply and of the cable voltage during the small move, with a plain verdict. Test matrix (a person plugs and unplugs; list for NEEDS-PERSON):

| Case | Plug | Person step |
|---|---|---|
| A | back port on the Mac (now) | none (done once: the cable event above); run the probe |
| B | back port on a wall charger (2 A) | a person plugs the charger into the back port |
| C | side port on the Mac | a person moves the cable |
| D | side port on a charger | a person plugs a charger in the side port |
| E | both ports, Mac and charger | a person plugs both |
| F | battery only (no cable) | a person unplugs everything |

Compare the supply verdicts, the resting servo volts and the sag across A to F. If a charger on the back port shows a healthy supply and the Mac does not, the limiter proposal works as a rule; if all read healthy the limit is stricter than the hardware needs; if all read weak the limit is right.

## Camera and Wi-Fi power

A brownout on the controller's USB alone is the risk behind both the limiter and the camera frame rate: the sag figure and the lowest VBUS reading in the probe during a camera run (`self.bench.camera_probe`, held) will say whether a 500 mA port browns out at VGA with Wi-Fi sending.
