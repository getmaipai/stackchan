# Infrared and NFC for the StackChan: what is verified, what we could build, how to probe safely

Firmware track, 2026-11-18. Research from the maker's public pages and published code, plus a read of the replayed tree (`/Users/jessetorres/esp/stackchan-rebuild/b47/firmware`). Nothing here ran on a unit.

**Bottom line.** The infrared pins are well documented by the maker: transmit on GPIO 5, receive on GPIO 10, in three separate maker documents. That is "confirmed" only in the sense that the maker agrees with itself; no schematic and no outside source was read, so the firmware track still treats the pins as unverified until the input-only probe sees a real remote on GPIO 10. The NFC chip is an ST25R3916 on the internal I2C bus at address 0x50, from one maker page plus the maker's driver defaults; its interrupt pin, and whether the chip needs a power or enable line, are not stated anywhere we could read. The maker's own library does not touch any pin for either part, which is evidence that neither needs an enable line, but not proof. Both features fit as optional packages that cost nothing when off. Build the four bench probes first (about 1.5 days), then the packages (about 4 to 6 days in all).

## 1. Source check

"Maker" below means M5Stack. A fact is called confirmed only when two different documents or files state it. Three documents from one maker count as two for this purpose, and the table says so.

| Fact | Sources | Status |
|---|---|---|
| IR transmit pin is GPIO 5 | pin map on https://docs.m5stack.com/en/StackChan (G5 IR_SEND); https://docs.m5stack.com/en/arduino/stackchan/ir_nec (`IR_SEND_PIN 5`); https://raw.githubusercontent.com/m5stack/StackChan-BSP/main/examples/IR/Send/Send.ino (`kIrLed = 5`) | Confirmed by three maker documents. No outside source. No schematic read. |
| IR receive pin is GPIO 10 | pin map (G10 IR_REC); ir_nec page (`IR_RECEIVE_PIN 10`) | Confirmed by two maker documents. |
| Internal bus is SCL 11, SDA 12 | pin map (G11 I2C_SCL, G12 I2C_SDA); our tree `main/hal/board/config.h` (`AUDIO_CODEC_I2C_SDA_PIN` 12, `AUDIO_CODEC_I2C_SCL_PIN` 11) and `stackchan.cc` `InitializeI2c()` (port 1) | Confirmed (maker page plus working code that runs on the unit). |
| Servo bus is TX 6, RX 7 | pin map; our tree `hal_servo.cpp` (`_scs_bus.begin(UART_NUM_1, 1000000, 6, 7)`); BSP `M5StackChan.cpp` (same call) | Confirmed. |
| Receiver part is IRM56384, plus an IR LED | spec rows on https://docs.m5stack.com/en/StackChan ("Infrared receiver IRM56384 + infrared transmitter"); datasheet link on the same page | Single source. The LED drive (direct from the pin or through a transistor) is not stated. |
| NFC chip is ST25R3916 | spec row and parts table on https://docs.m5stack.com/en/StackChan; https://uiflow-micropython.readthedocs.io/en/develop/controllers/stackchan.html (the onboard NFC is an `ST25R3916` exposed as `stackchan.nfc`); our `docs/dev/stackchan-sensor-map.md` row | Confirmed by two maker pages. |
| NFC I2C address is 0x50 | I2C table on https://docs.m5stack.com/en/StackChan; `UnitST25R3916` default in the maker's NFC library (`0x50 /* I2C address */`, https://raw.githubusercontent.com/m5stack/M5Unit-NFC/main/src/unit/unit_ST25R3916.hpp); `docs/dev/stackchan-sensor-map.md` | Confirmed by two maker sources. The library default is for the add-on unit, so it shows the chip's usual address, not the wiring of this body. |
| NFC is on the internal bus | https://docs.m5stack.com/en/arduino/stackchan/nfc and `examples/NFC/Detect/Detect.ino` register the unit with `M5.In_I2C` and pass no pin | Confirmed by two maker pages. |
| NFC interrupt pin | The docs page and the example are silent. The library has an optional IRQ pin setting. `docs/dev/stackchan-sensor-map.md` says "IRQ not wired", with no primary source. | Unknown. Poll; do not depend on an interrupt. |
| Power or enable line for IR or NFC | The BSP `begin()` calls only `io_expander_init()` (expander pin 0 servo rail, pin 13 ring LEDs), then servo and battery-monitor setup. The pin map lists expander pins IO1, IO14, VM_EN, RGB. The NFC library lists no power pin. | Not found. IO1 and IO14 are listed with no stated use and must not be driven. |
| IR carrier, duty, drive current | None of the pages say. The NEC example relies on its library defaults (38 kHz). | Unknown for this LED. |
| ST25R3916 identity register address and values | The library header documents the decoded fields (IC type code 00101, revision 010) but not the register address in the part we could read. | Not verified here. The firmware track reads the datasheet linked from the maker page (https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1205/ST25R3916_EN.pdf); this plan gives no register value. |

Two reads that failed: the Mouser PDF of the product sheet timed out twice, and the firmware tree of https://github.com/m5stack/StackChan was too long to list fully. Neither is a source here.

What we saw in our own tree: no infrared or NFC code and no use of GPIO 5 or 10 in `main/hal` (searched `config.h`, `stackchan.cc`, the HAL sources). The only other matches in `xiaozhi-esp32/main` are another vendor's boards (an infrared camera filter and an e-paper board whose NFC chip sits at 0x55 with its own enable pin). Those are different parts and give no evidence for this body.

The I2C bus (SDA 12, SCL 11) already holds these devices in our code: the power chip AXP2101 at 0x34 and the expander AW9523 at 0x58 (both in `stackchan.cc`), the touch controller FT6336 at 0x38 (`stackchan.cc`), the IMU BMI270 at 0x69 (`hal_imu.cpp`), the servo-rail expander PY32 at 0x6F (`PY32IOExpander_Class.hpp`), the head touch chip Si12T at 0x68 (`Si12T.h`) and the clock chip at 0x51 (`PCF8563_Class.hpp`). The maker page adds the battery monitor INA226 at 0x41 (BSP `M5StackChan.cpp` agrees). The NFC chip at 0x50 collides with none of them. The expander pin 0 (servo rail) and pin 13 (ring) are the only pins our code drives, as in `hal_io_expander.cpp`.

## 2. Optional packages

Both are off by default behind Kconfig switches. Per owner decision 15, nothing is allocated until first use.

### 2.1 IR learn and send (`CONFIG_MAIPAI_IR`)

- **Split.** The host keeps the code library (device, button, protocol, timings) and does the matching: "turn the TV on" maps to a stored code. The unit does two things: record a button press as raw pulse and gap timings, and play back a code the host sends. The unit never stores codes.
- **Tools.** `self.robot.ir_learn {seconds}` returns the timings (and a decoded NEC address and command when it is NEC). `self.robot.ir_send {raw|nec, repeats}` plays one code. The host's settings page has a "Learn a button" flow: name the button, point the remote at the unit, press.
- **Mechanism.** The ESP32-S3 RMT peripheral generates the 38 kHz carrier in hardware, so no CPU timing loop is needed. The receiver (IRM56384) outputs a demodulated signal, so RX only measures pulse lengths on GPIO 10.
- **Load on demand.** The RMT channels are created on the first call and deleted after 10 seconds idle. Receive buffers come from PSRAM where the driver allows it. Whether the RMT receive path accepts PSRAM buffers in ESP-IDF 6.1.1 without DMA is not verified; the first build checks it, and the fallback is a short internal buffer (512 symbols).

Memory (estimates, not measured):

| | Switch off | Switch on, idle | While learning or sending |
|---|---|---|---|
| Flash | 0 | 6 to 10 KB (RMT driver pieces plus the NEC decoder and tools) | same |
| PSRAM | 0 | 0 | 8 to 16 KB (a capture holds up to about 1000 symbols, 4 bytes each) |
| Internal RAM | 0 | under 200 bytes (the registration of two tools) | 2 to 4 KB (driver state, one task stack of 3 KB) |

Effort: about 2.5 days (one for the unit, one for the host library and settings page, half a day for tests).

### 2.2 NFC tag actions (`CONFIG_MAIPAI_NFC`)

- **Split.** The host maps a tag UID to an action: "start the bedtime routine" or "switch to persona X". The unit reports the UID and tag type; it never decides anything, and it never writes to a tag.
- **Tools and events.** `self.robot.nfc_watch {on|off}` starts or stops polling; an event `nfc.tag {uid, type}` goes to the host once per tap (not again until the tag leaves). The unit is silent: no beep on a read, a short ring flash only if the host asks for it.
- **Mechanism.** Poll for NFC-A tags (request, anticollision, select) about every 250 ms while watch is on, using the existing bus handle with a new device at 0x50 (no second bus, 400 kHz). A tap while the unit is muted, locked or carried is dropped (see section 3).
- **Load on demand.** The reader task and its driver state exist only while watch is on. Off, nothing is allocated.
- **Not in scope:** reading or writing tag data, card emulation, writing NDEF. UID only. That is enough for the tap-a-tag feature and keeps the driver small.

Memory (estimates, not measured):

| | Switch off | Switch on, watch off | Watch on |
|---|---|---|---|
| Flash | 0 | 3 KB (tool registration) | 14 to 22 KB (ST25R3916 register setup, NFC-A anticollision) |
| PSRAM | 0 | 0 | 2 KB (frame buffers) |
| Internal RAM | 0 | under 200 bytes | 3 to 4 KB (task stack 3 KB, driver state, I2C device handle) |

Effort: about 3 days (one and a half for the driver, half a day for the host mapping page and event, one for tests). The driver is the risk: the register sequence must come from the datasheet and the maker's published library, and nothing is invented here.

## 3. Safety rules

1. **No pin is driven until it is confirmed on the bench.** First step is input-only: GPIO 10 as an input, and an I2C read-only scan. GPIO 5 is driven only after the input probe has seen a real remote on GPIO 10 and `i2c_scan` has shown the expected devices, and only by the bench transmit probe, which has hard limits (below).
2. **Never write to an expander pin that the pin map does not describe as ours.** Only pin 0 (servo rail) and pin 13 (ring) are driven today. IO1 and IO14 stay untouched.
3. **Carrier limits per transmit call.** A call is refused when it holds more than 4 repeats, one frame longer than 150 ms, a total burst longer than 600 ms, or a mark duty above 50 percent of the total time. After a call, at least 500 ms must pass before the next one. A watchdog timer turns the carrier off if a call overruns by 50 ms.
4. **Refuse transmit and NFC polling when the unit is carried, on a low battery, or on a weak supply.** Use the existing pickup state (`maipai_pickup`) and battery figures (`maipai_battery_core.h`, `maipai_power_core.h`). Below 20 percent battery and not on USB power, both are refused with a plain message that says to plug the unit in.
5. **Moving the head stays separate.** Neither tool moves a servo, and neither runs during a calibration or a servo stall event.
6. **Privacy.** The unit never sends captured timings or UIDs anywhere except to the paired host over the existing link. Nothing in the packages goes to the internet.
7. **Errors say what happened and what to do**, for example: "The infrared sender did not send because the unit was being carried. Put it down and try again."
8. **Stop rule.** If a probe shows a pin does not behave as documented (no I2C answer at 0x50, no pulses on GPIO 10, the LED does not blink), stop and report; do not try neighboring pins.

## 4. Bench probes (bench builds only, `CONFIG_MAIPAI_SERIAL_TOOLS`)

All four sit beside `self.bench.power_probe` (patch SF48). They cost nothing in a release image.

1. **`self.bench.i2c_scan {}`.** Probes addresses 0x08 to 0x77 on the internal bus (the code already has `I2cDetect()` in `stackchan.cc` using `i2c_master_probe`, which only addresses a device and reads nothing). Returns a list of found addresses with names for the known ones. Pauses while the audio codec streams; refuses when the unit is playing. Expected: 0x34, 0x38, 0x41, 0x50, 0x51, 0x58, 0x68, 0x69 and 0x6F, plus devices from the CoreS3 itself that our tree does not name (do not treat those as errors).
2. **`self.bench.nfc_probe {seconds}`.** Adds a device at 0x50, reads only the ST25R3916 identity register through the library's identity call, returns the type and revision fields, then polls for NFC-A tags for the given seconds (1 to 30) and returns each UID and type once. Never writes to a tag. If 0x50 does not answer, returns "no answer at 0x50" and stops.
3. **`self.bench.ir_rx {seconds}`.** GPIO 10 as an input with no pull change. Records for 1 to 30 seconds, returns decoded NEC (address, command, repeat count) and the raw pulse and gap timings in microseconds (first 200 only), plus a count of edges. Input only.
4. **`self.bench.ir_tx {code|raw, repeats}`.** GPIO 5 with a 38 kHz carrier from RMT. `code` is a NEC address and command; `raw` is a list of up to 100 timings. `repeats` is 0 to 4. All limits from section 3 apply. Refused unless `ir_rx` has returned at least one edge since boot, so the pin map has been seen to work on the input side first. This is a guard in firmware and a rule for the person running the bench.

### Test matrix

Everything is silent: no sound, no speech. The ring may blink for status only.

| # | Step | Who | Pass when |
|---|---|---|---|
| 1 | Flash a bench build; run `i2c_scan` | Silent step (the agent) | The expected addresses appear, 0x50 included. If 0x50 is missing, stop and report. |
| 2 | Run `nfc_probe {seconds: 5}` with no tag | Silent step | The identity fields read type 00101 and revision 010 (the values the maker's library documents), no tag found. |
| 3 | Run `nfc_probe {seconds: 15}`; the person holds an NFC card on the top surface of the head | Person step | The card's UID and type come back once. Repeat with a phone in tag mode; a phone may give a random UID, which is normal. |
| 4 | Run `ir_rx {seconds: 15}`; the person points a TV remote at the unit and presses power, volume up, mute | Person step | Pulses arrive; NEC remotes decode; other protocols show raw timings. Note the distance that works (tens of centimeters expected; not verified). |
| 5 | Run `ir_rx {seconds: 5}` with nothing pointed at it | Silent step | Zero or near zero edges (sunlight and lamps can add some; note them). |
| 6 | Run `ir_tx {code, repeats: 0}` once; the person watches the front of the unit through a phone camera | Person step | The phone camera shows the IR LED flash (a purple-white dot). Phone cameras show IR; eyes do not. If the person sees nothing, stop. |
| 7 | Replay a recorded code from step 4 with `ir_tx {raw}` at a real TV or aircon | Person step | The device reacts. A miss means more tuning on timings, not a safety issue. |
| 8 | Run `ir_tx` with 5 repeats, then a 700 ms burst | Silent step | Both are refused with a plain message. The refusals prove the limits. |
| 9 | Pick the unit up and run `ir_tx` | Person step | Refused. Set it down; it works again. |
| 10 | Read the servo rail (`power_probe`) before and after steps 6 and 7 | Silent step | No servo voltage drop beyond the existing noise, no reset. |

## 5. The "X axis 360 degrees" label and our yaw limit of 128 degrees

**What our code says.** In `main/hal/hal_servo.cpp` (`servo_init`) the yaw servo has `angleLimit = (-1280, 1280)` and `rawPosLimit = (0, 1000)`, with `defaultZeroPos = 460`. Angles are in tenths of a degree, so 1280 is 128 degrees. The conversion is `raw_pos_to_angle = (raw - zero) * 5 * 10 / 16`: each raw step is 0.3125 degrees. The pitch servo has `angleLimit = (30, 870)`, which is 3 to 87 degrees. The host profile repeats the 128 figure (`docs/design/unit-protocol.md`, "Head yaw range is plus or minus 128 degrees in the host profile"). Our patches do not set the yaw limits (searched `firmware/patches/*.patch` for 1280: only unrelated patches match), so the value comes from the stock robot code, not from our choice.

**What the maker says.** The product page https://docs.m5stack.com/en/StackChan lists a "360-degree horizontal servo with feedback" and a "90-degree vertical servo with feedback", recommends the vertical axis stay within 5 to 85 degrees, and says "No angle restriction is required for the X-axis". The 5 to 85 for pitch matches our 3 to 87 limit and our host's 5 to 85.

**What the numbers show.** Raw range 0 to 1000 at 0.3125 degrees is 312.5 degrees of position scale. With zero at 460, raw 0 is -143.75 degrees and raw 1000 is +168.75 degrees. The code limit of plus or minus 128 degrees sits inside the raw range, with room left on both sides: raw 51 to 869. So 128 is a software choice, tighter than the raw range, which is itself tighter than 360.

**What we cannot say.** We could not verify whether "360 degrees" is the true mechanical travel (a free-turning axis), a servo spec (the servo's encoder range), or marketing. The yaw servo is configured for `enablePwmMode` (continuous drive mode), which hints that the servo can turn freely. We have not found any mechanical drawing, nor any word from the maker on the cable routing at the rear. We have also not found where the plus or minus 128 degrees was chosen or why.

**Is widening worth it?** Not yet. Gains: a wider turn toward a voice or face behind the unit (today the head can reach 128 degrees to either side, so an object directly behind, at 180, is out of reach by 52 degrees). Costs and risks: the rear cable loops, which is the likely reason for a limit; if the cable is pulled tight or twisted, a servo stall and cable damage follow, and the unit's stall protection (`handle_stall`) trims the limit at runtime only after the fact. If we widen, do it as a bench step: raise the limit in steps of 10 degrees from the bench build, watch the stall log and the cable by eye at each step, stop at the first sign of tension, and make the end value a setting in `robot.toml` (never a default) with the 128 default kept. A person must watch the rear cable during that bench step. Expected value is low for a household unit, so this stays behind the infrared and NFC probes in priority.

## 6. What stays unknown

- Whether the pin map is correct on this particular body (the maker's documents agree with each other; no schematic or outside source was read).
- Whether the IR LED is driven directly or through a transistor, and its safe current; the LED part number.
- The NFC interrupt pin, and whether the chip needs any enable line. The maker's library suggests none.
- The ST25R3916 identity register address and the init steps; these come from the datasheet and the maker's library, to be read in the implementation step.
- The true mechanical range of the yaw axis, and where the 128-degree limit was chosen.
- Memory costs: all figures above are estimates until the first bench build reports them (the memory gate runs on every firmware step).
