# Hardware reference (what we know about the StackChan unit, and how we know it)

Owner decision 25, 2026-11-18. This page collects the hardware facts the repository already records. It adds no new measurement and copies no vendor text. Every row has a value, a status tag, a source and a date.

**Status tags**

- **measured**: read on the owner's unit (there is one) or taken from our own build. The date is the day it was read.
- **vendor-stated**: the maker says so on a page we link. We have not checked it on the unit. The date is the day we recorded it.
- **inferred**: worked out from code, a photo, a drawing or a data sheet. It may be wrong; the source column says how it was inferred.

Where a number has no source in the repository it is not on this page. See [Open questions](#open-questions) at the end.

The robot is the M5Stack StackChan (product K151, CoreS3 controller). The name is used here to say which hardware this is. The independent-project notice and the naming rules are in [trademark and affiliation](../plan/trademark-and-affiliation.md).

## Board and chips

| Fact | Value | Status | Source | Date |
|---|---|---|---|---|
| Controller | CoreS3, ESP32-S3 | measured (boot log) | [unit measurements](stackchan-unit-measurements.md) | 2026-10-19 |
| Chips found at boot | GC0308 camera, AXP2101 power, AW9523 I/O expander, FT6336 touch, ILI9342C display, Si12T head touch, PCF8563 clock, BMI270 motion sensor | measured | [unit measurements](stackchan-unit-measurements.md) | 2026-10-19 |
| Audio chips | ES7210 microphone codec, AW88298 speaker amplifier | inferred (maker schematic text and firmware source) | [sensor map](stackchan-sensor-map.md) | 2026-10-15 |
| Body current sensor | INA226 at I2C 0x41, 10 mOhm shunt; the pinned firmware does not use it | inferred (another project's hardware notes) | [sensor map](stackchan-sensor-map.md) | 2026-10-15 |
| Radio | Wi-Fi only; Bluetooth is removed from our build | measured (our build) | `firmware/patches/098-bluetooth-off.patch` | 2026-11-18 |
| CPU clock | 240 MHz | inferred (latency table of a face-detection study; not read from our unit) | [face detection study](../design/face-detect-esp-dl-2026-11-17.md) | 2026-11-17 |
| Maker's board repository | structure files only; no board outline, no battery size | vendor-stated | [model source record](../../scripts/virtual-unit/model/SOURCE.md) | 2026-11-18 |

## Memory

### Flash and partitions

| Fact | Value | Status | Source | Date |
|---|---|---|---|---|
| Flash size | 16 MiB (16,777,216 bytes) | measured (full read-back) | [first flash](../design/firmware-first-flash-2026-11-15.md) | 2026-11-15 |
| App slots `ota_0`, `ota_1` | 5,177,344 bytes each (0x4F0000) | measured (partition table) | [firmware strip](stackchan-firmware-strip-2026-11-13.md) | 2026-11-13 |
| `assets` partition | 6,225,920 bytes (0x5F0000) at 0xA00000, grown from 4 MiB by patch A02 | measured | [firmware strip](stackchan-firmware-strip-2026-11-13.md), `firmware/patches/A02-grow-assets-partition.patch` | 2026-11-13 |
| `nvs`, `otadata`, `phy` | 16 KB at 0x9000, 8 KB at 0xD000, 4 KB | measured | [face seek note](../design/face-seek-2026-11-17.md), [wireless update](stackchan-wireless-update-2026-11-14.md) | 2026-11-17 |
| Free partitions | none: the 16 MB layout is full | measured | [face seek note](../design/face-seek-2026-11-17.md) | 2026-11-17 |
| Plain image size | 3,721,344 bytes, 71.9 percent of a slot, 1,456,000 free | measured (build b33) | [build report b33](releases/b33-plain.md) | 2026-11-17 |
| Assets image size | 4,463,226 bytes, 71.7 percent of the partition | measured (build b33) | [build report b33](releases/b33-plain.md) | 2026-11-17 |
| Rollback on a bad image | enabled in the bootloader | measured (build sdkconfig) | [wireless update](stackchan-wireless-update-2026-11-14.md) | 2026-11-14 |

### Internal RAM and PSRAM

| Fact | Value | Status | Source | Date |
|---|---|---|---|---|
| PSRAM | 8 MB | measured (boot log) | [unit measurements](stackchan-unit-measurements.md) | 2026-10-19 |
| PSRAM free | about 7.2 MB of 8 MB (old base); lowest 7,170,496 bytes on the current base | measured | [firmware memory](../design/firmware-memory.md) | 2026-11-15 |
| Internal RAM, total | 341,760 bytes | measured (old base) | [firmware memory](../design/firmware-memory.md) | 2026-11-15 |
| Static internal RAM, plain image | 170,771 bytes (bench image 185,751) | measured (ELF sections, b44) | [memory budget](memory-budget.md) | 2026-11-18 |
| Internal free, median | 69,075 bytes (echo canceller image, turns playing); 64,093 with the servo task | measured (bench window 10) | [memory budget](memory-budget.md) | 2026-11-18 |
| Internal free, lowest | 33,484 bytes | measured (bench window 10) | [memory budget](memory-budget.md) | 2026-11-18 |
| Largest free internal block, link up | 25,600 to 25,624 bytes, 1,600 over the gate | measured (windows 10 and 11) | [memory budget](memory-budget.md) | 2026-11-18 |
| Largest free internal block, before the link | 46,804 bytes | measured (window 11) | [memory budget](memory-budget.md) | 2026-11-18 |

### Gate numbers (a build must show these on the unit)

| Gate | Number | Status | Source | Date |
|---|---|---|---|---|
| Internal free, median | at least 40,000 bytes | gate rule (we set it) | [gate numbers](gate-numbers.md) | 2026-11-18 |
| Internal free, lowest | at least 24,000 bytes | gate rule | [gate numbers](gate-numbers.md) | 2026-11-18 |
| Largest free block, median and lowest | at least 24,000 and 16,000 bytes | gate rule | [gate numbers](gate-numbers.md) | 2026-11-18 |
| PSRAM free, lowest | above 6,000,000 bytes | gate rule | [gate numbers](gate-numbers.md) | 2026-11-18 |
| Task stack margin | at least 1,024 bytes | gate rule | [gate numbers](gate-numbers.md) | 2026-11-18 |
| OTA slot free | at least 20 percent of each slot | gate rule | [gate numbers](gate-numbers.md) | 2026-11-18 |
| Face refresh while moving | at least 30 a second; 44.7 measured | measured | [gate numbers](gate-numbers.md) | 2026-11-18 |
| One face refresh, one full picture refresh | at most 8 ms (3 to 7 measured); at most 40 ms (26 to 35 measured) | measured | [gate numbers](gate-numbers.md) | 2026-11-18 |

## USB ports

| Fact | Value | Status | Source | Date |
|---|---|---|---|---|
| Number of USB-C ports | two: one on the side of the controller, one on the back of the base | inferred (product photos and the maker's structure files) | [model match record](../../scripts/virtual-unit/model/MATCH.md) | 2026-11-18 |
| Side port | the port used for flashing and serial so far; on the button side of the controller | measured (used on every bench run); position inferred from photos | [two USB ports](../plan/two-usb-ports.md), [model match record](../../scripts/virtual-unit/model/MATCH.md) | 2026-11-18 |
| Back port, on a Mac with the side port empty | the unit reports charging true and 100 percent; the Mac still lists the USB serial device; the limiter logs `usb_limited` | measured (owner's unit, bench window 14) | [two USB ports](../plan/two-usb-ports.md) | 2026-11-18 |
| What the back port feeds | not known: the servo rail only, the controller, or both | open (see below) | [two USB ports](../plan/two-usb-ports.md) | 2026-11-18 |
| Which port is plugged | cannot be told from the power chip | measured (finding of the same run) | [two USB ports](../plan/two-usb-ports.md) | 2026-11-18 |
| Firmware behavior on the back port | the stock code has nothing special for it: no supply check and no input current setting | inferred (read from the pinned tree) | [two USB ports](../plan/two-usb-ports.md) | 2026-11-18 |
| Motion limit on any cable | half the excursion, 60 percent speed, no full dance | measured (code and bench window 8: 43 to 48 percent of a large step) | [two USB ports](../plan/two-usb-ports.md), [head recording](head-recording.md) | 2026-11-18 |
| A computer port gives about 500 mA | the load budget for the camera, Wi-Fi and screen | inferred (general USB rule, not read on the unit) | [camera quality](camera-quality.md) | 2026-11-18 |
| Download mode and restart | a press of the reset button reboots; a 3 second hold enters download mode | vendor-stated (product page picture) | [model match record](../../scripts/virtual-unit/model/MATCH.md) | 2026-11-18 |

## Power and battery

| Fact | Value | Status | Source | Date |
|---|---|---|---|---|
| Power chip | AXP2101 at I2C 0x34 | measured (boot log) | [unit measurements](stackchan-unit-measurements.md) | 2026-10-19 |
| Battery capacity | 550 mAh | vendor-stated (product page) | [model match record](../../scripts/virtual-unit/model/MATCH.md) | 2026-11-18 |
| Battery size and position | 30 x 20 x 8 mm behind the holder back cover | inferred (drawn stand-in, not measured) | [model match record](../../scripts/virtual-unit/model/MATCH.md) | 2026-11-18 |
| Battery level | percent only; no battery current register on the chip | measured (the unit's gauge); the missing register is from the chip's register map | [battery and power](battery-and-power.md) | 2026-11-18 |
| On a cable (Mac, back port) | VBUS 4,961 mV, battery 4,197 mV at 100 percent, system rail 4,432 mV, charge state constant voltage | measured (bench window 14) | [battery and power](battery-and-power.md) | 2026-11-18 |
| Input current limit register | reads 1.5 A on the Mac back port | measured; it does not say what the source can give | [battery and power](battery-and-power.md) | 2026-11-18 |
| Charge current set at start | 700 mA, constant current (register 0x62) | measured (read from code) | [two USB ports](../plan/two-usb-ports.md) | 2026-11-18 |
| Servo supply at rest | 5.1 to 5.2 V; sag during a 15 degree move 0.1 V | measured (bench window 14, back port on a Mac) | [two USB ports](../plan/two-usb-ports.md) | 2026-11-18 |
| Power key | top of the left side; press for on, hold 6 seconds for off | vendor-stated (product picture) | [model match record](../../scripts/virtual-unit/model/MATCH.md) | 2026-11-18 |
| Idle sleep and shutdown | sleep after 300 s, shutdown after 600 s (power save settings read at boot) | measured (boot log) | [unit measurements](stackchan-unit-measurements.md) | 2026-10-19 |
| Drain and charge times | not measured; the tables in the battery page are empty on purpose | open | [battery and power](battery-and-power.md) | 2026-11-18 |
| Power lights | a red light in the holder back and one under the controller, both lit with USB power; the firmware does not drive them | measured (owner's unit) | [model match record](../../scripts/virtual-unit/model/MATCH.md) | 2026-11-18 |

## Screen

| Fact | Value | Status | Source | Date |
|---|---|---|---|---|
| Panel | ILI9342C, 320 by 240 pixels, 2 inch | measured (chip at boot); size in pixels from our screens | [unit measurements](stackchan-unit-measurements.md), [screen style](../design/screen-style.md) | 2026-10-19 |
| Width of the glass | 40.6 mm | inferred (from the diagonal; no ruler on the glass yet) | [screen style](../design/screen-style.md) | 2026-11-18 |
| Pixel density | 7.87 pixels a millimeter | inferred (same source; assumed until a ruler is put on the glass) | [screen style](../design/screen-style.md) | 2026-11-18 |
| Smallest target | 56 by 56 pixels (7 mm) | design rule (ours), derived from the density above | [screen style](../design/screen-style.md) | 2026-11-18 |
| Touch | FT6336 controller | measured (boot log) | [unit measurements](stackchan-unit-measurements.md) | 2026-10-19 |
| Controller and glass size | rounded block with glass; the glass ends 1.26 mm ahead of the base front | inferred (drawing and photos, good to about 1 mm) | [model match record](../../scripts/virtual-unit/model/MATCH.md) | 2026-11-18 |
| Whole robot | 54.0 by 70.5 by 61.5 mm, 187.2 g | vendor-stated (product page drawing); the model matches the size | [model match record](../../scripts/virtual-unit/model/MATCH.md) | 2026-11-18 |
| One face refresh | 3 to 7 ms | measured | [gate numbers](gate-numbers.md) | 2026-11-18 |

## Servos and limits

| Fact | Value | Status | Source | Date |
|---|---|---|---|---|
| Servos | two SCS0009, 23.2 by 12.1 by 25.25 mm, 20 tooth output of 3.95 mm; yaw is id 1, pitch is id 2 | vendor-stated (data sheet linked from the product page) | [model match record](../../scripts/virtual-unit/model/MATCH.md) | 2026-11-18 |
| Servo bus | UART 1 at 1,000,000 baud, TX pin 6, RX pin 7 | inferred (maker pin map and our tree agree) | [IR and NFC note](../plan/ir-and-nfc.md) | 2026-11-18 |
| Servo supply switch | expander pin 0 ("VM EN"), on at start | inferred (read from the pinned tree) | [two USB ports](../plan/two-usb-ports.md) | 2026-11-18 |
| Yaw limit in firmware | -128 to 128 degrees | inferred (pinned upstream code, `angleLimit` in tenths) | [model match record](../../scripts/virtual-unit/model/MATCH.md) | 2026-11-18 |
| Pitch limit in firmware | 3 to 87 degrees; no patch of ours changes it | inferred (pinned upstream code) | [model match record](../../scripts/virtual-unit/model/MATCH.md) | 2026-11-18 |
| Maker's stated range | yaw 360 degrees without restriction; pitch 5 to 85 recommended | vendor-stated (product page) | [model match record](../../scripts/virtual-unit/model/MATCH.md) | 2026-11-18 |
| Pitch travel by geometry | free from 0 to 90 degrees; 0 is level, positive looks up | inferred (the maker's structure files, swept in 3 degree steps) | [model match record](../../scripts/virtual-unit/model/MATCH.md) | 2026-11-18 |
| Zero positions | id 1 = 460, id 2 = 620 | measured (settings read at boot); stored per unit | [unit measurements](stackchan-unit-measurements.md) | 2026-10-19 |
| Head at rest after first flash | yaw -8, pitch 26 | measured | [unit measurements](stackchan-unit-measurements.md) | 2026-10-19 |
| Servo write rate | at most 50 a second; animation steps advance by real time, 20 to 50 ms | measured (build SF28) | [head speed clock](head-speed-real-time-clock.md) | 2026-11-18 |
| Limit on host head moves | 40 calls in any 60 seconds | our rule (patch 038) | `firmware/patches/038-head-move-cap.patch` | 2026-10-20 |
| What a servo reports | voltage (tenths of a volt), load 0 to 1000, current, temperature, position | inferred (driver source) | [two USB ports](../plan/two-usb-ports.md) | 2026-11-18 |
| Head readback | `get_head_angles` did not show a 3 degree move one second later; it may report the target | measured (first bench), still open | [unit measurements](stackchan-unit-measurements.md) | 2026-10-19 |
| Mass split between head, neck and base | not known; only the total is published | open | [model match record](../../scripts/virtual-unit/model/MATCH.md) | 2026-11-18 |

## Sensors

| Part | Value | Status | Source | Date |
|---|---|---|---|---|
| Motion sensor | BMI270 at I2C 0x69 | measured (boot log); address inferred | [unit measurements](stackchan-unit-measurements.md), [sensor map](stackchan-sensor-map.md) | 2026-10-19 |
| Head touch | Si12T at I2C 0x68, three zones in a line, intensity 0 to 3 | measured (chip at boot); zones inferred from source | [sensor map](stackchan-sensor-map.md) | 2026-10-19 |
| Touch pad size and place | 16 by 8 mm each, behind the top openings | inferred (assumed in the model; only the schematic is published) | [model match record](../../scripts/virtual-unit/model/MATCH.md) | 2026-11-18 |
| Clock | PCF8563 (BM8563 family) at 0x51; timezone GMT0 at boot | measured (chip at boot); address inferred | [unit measurements](stackchan-unit-measurements.md) | 2026-10-19 |
| Light and proximity | LTR-553 at 0x23 | inferred (another project's notes); unused by our firmware | [sensor map](stackchan-sensor-map.md) | 2026-10-15 |
| NFC | ST25R3916 at 0x50, interrupt line not known | inferred; vendor-stated by the maker's NFC page | [IR and NFC note](../plan/ir-and-nfc.md) | 2026-11-18 |
| Infrared | transmit GPIO 5, receive GPIO 10, receiver IRM56384 | vendor-stated (three maker documents); not used in our tree | [IR and NFC note](../plan/ir-and-nfc.md) | 2026-11-18 |
| Shake threshold | lowered by patch C04 for hand lifts | our setting | `firmware/patches/C04-shake-threshold.patch` | 2026-11-18 |
| Lift, carry and put-down thresholds | not measured (MOVE-CARRY-01) | open | [unit measurements](stackchan-unit-measurements.md) | 2026-10-19 |

## Camera

| Fact | Value | Status | Source | Date |
|---|---|---|---|---|
| Sensor | GC0308, 0.3 megapixel VGA, on an 8 bit DVP bus with a 20 MHz clock | measured (chip at boot); bus details inferred from the driver | [camera quality](camera-quality.md) | 2026-11-18 |
| Modes the driver offers | 640 by 480 at 16 frames a second; 320 by 240 at 20 frames a second | inferred (driver source) | [camera quality](camera-quality.md) | 2026-11-18 |
| Mode we use | 320 by 240, UYVY, 20 frames a second | measured (our build config) | [camera quality](camera-quality.md) | 2026-11-18 |
| Frame buffer | 150 KB at 320 by 240, 600 KB at 640 by 480, in PSRAM | inferred (size arithmetic) | [camera quality](camera-quality.md) | 2026-11-18 |
| Encoder output | 8 to 15 frames a second at 320 by 240 if the encode takes under 60 ms; 3 to 6 at 640 by 480 | inferred (estimate, not yet measured) | [camera quality](camera-quality.md) | 2026-11-18 |
| Night | no infrared light and no infrared filter control; a dark room reads as noise or black | inferred (sensor class); the dark-room test is not run | [camera quality](camera-quality.md) | 2026-11-18 |
| Face detection cost | about 33 ms plus 6 ms per face on an S3 at 240 MHz, 120 by 160 input | vendor-stated (upstream model card); not measured on our unit | [face detection study](../design/face-detect-esp-dl-2026-11-17.md) | 2026-11-17 |
| Camera at boot | the vendor camera panics on about half of cold USB boots | measured (owner's unit); cause not settled | `firmware/patches/FM01-first-boot-trial.patch` | 2026-11-16 |

## Audio

| Fact | Value | Status | Source | Date |
|---|---|---|---|---|
| Microphones | two MEMS microphones (MSM381A3729H9BPC) on ES7210 MIC1 and MIC2 | inferred (schematic text and product page) | [sensor map](stackchan-sensor-map.md) | 2026-11-12 |
| Microphone layout | stacked, not side by side: 19 mm of path up against down, 7 mm left against right (inside the noise); level difference under 1 dB | measured (owner's unit) | [sensor map](stackchan-sensor-map.md), [sound direction](stackchan-sound-direction-2026-11-12.md) | 2026-11-12 |
| Direction from the microphones | not usable for turning the head toward a speaker | measured (same run) | [sound direction](stackchan-sound-direction-2026-11-12.md) | 2026-11-12 |
| Codec mode and slots | TDM, four slots: slot 0 is MIC1, slot 1 is the speaker loopback, slot 2 is a real microphone, slot 3 is silent | measured (`self.bench.mic3_check`) | [ES7210 note](es7210-mic-gain-and-slots.md) | 2026-11-18 |
| Echo reference | slot 1 (MIC3), gain 12 dB (`CONFIG_MAIPAI_MIC3_GAIN_DB`) | measured; do not raise without a 9 to 21 dB sweep | [ES7210 note](es7210-mic-gain-and-slots.md) | 2026-11-18 |
| Echo return loss | 66.6 dB median at volumes 35 and 60; 63.9 dB at the volume cap (target 15 dB) | measured (bench window 10) | [ES7210 note](es7210-mic-gain-and-slots.md) | 2026-11-18 |
| Input sample rate | 24 kHz on the two input channels | inferred (firmware source) | [sensor map](stackchan-sensor-map.md) | 2026-11-12 |
| Built-in sounds | Ogg Opus, mono, 16 kHz, 24 kbps, 60 ms frames; twelve fixed names | measured (our own files) | [sounds](stackchan-sounds-2026-11-13.md) | 2026-11-13 |
| Speaker | grille on the controller's left side; amplifier AW88298 | inferred (photos and firmware source) | [model match record](../../scripts/virtual-unit/model/MATCH.md) | 2026-11-18 |
| Wake event to listening sound | median 5 and 17 ms; gate at most 100 ms | measured | [gate numbers](gate-numbers.md) | 2026-11-18 |

## Lights

| Fact | Value | Status | Source | Date |
|---|---|---|---|---|
| Ring | 12 LEDs, two bars of six; the stock tool sets one color for both | inferred (maker source) | [sensor map](stackchan-sensor-map.md) | 2026-10-15 |
| Ring writes | one color (green at 40, then off) worked and the owner saw the ring light; the per-pixel tool was not part of that run | measured | [unit measurements](stackchan-unit-measurements.md) | 2026-10-19 |
| Ring switch | expander pin 13 | inferred (maker support code) | [IR and NFC note](../plan/ir-and-nfc.md) | 2026-11-18 |
| Pixel order | lights 0 to 5 front to back on the left bar, 6 to 11 back to front on the right; real order and the 5 mm spacing unknown | inferred; open | [model match record](../../scripts/virtual-unit/model/MATCH.md) | 2026-11-18 |
| Light bars on the shell | slanted slots 2 mm wide and 29.6 mm long in the top corners | inferred (the maker's structure files) | [model match record](../../scripts/virtual-unit/model/MATCH.md) | 2026-11-18 |

## Ports and pins

| Fact | Value | Status | Source | Date |
|---|---|---|---|---|
| Internal I2C bus | SDA GPIO 12, SCL GPIO 11 (port 1) | inferred (maker pin map and our tree agree) | [IR and NFC note](../plan/ir-and-nfc.md) | 2026-11-18 |
| I2C devices in our code | AXP2101 0x34, AW9523 0x58, FT6336 0x38, BMI270 0x69, PY32 expander 0x6F, Si12T 0x68, PCF8563 0x51 | inferred (read from our tree) | [IR and NFC note](../plan/ir-and-nfc.md) | 2026-11-18 |
| Servo bus | TX 6, RX 7 | inferred (see Servos) | [IR and NFC note](../plan/ir-and-nfc.md) | 2026-11-18 |
| Infrared | send GPIO 5, receive GPIO 10 | vendor-stated | [IR and NFC note](../plan/ir-and-nfc.md) | 2026-11-18 |
| Top connectors | two sockets with four pins each (port A, red, among them: 5.3 by 10.5 mm) | inferred (photos) | [model match record](../../scripts/virtual-unit/model/MATCH.md) | 2026-11-18 |
| Card slot | under the controller; slot 12.9 by 1.3 mm | inferred (photos, about 0.3 mm) | [model match record](../../scripts/virtual-unit/model/MATCH.md) | 2026-11-18 |

## Boot and reconnect

| Fact | Value | Status | Source | Date |
|---|---|---|---|---|
| Boot slot | `ota_0` on the first flash; app `maipai-stackchan` 1.5.1-maipai.1 then | measured | [unit measurements](stackchan-unit-measurements.md) | 2026-10-19 |
| Wi-Fi setup | with no saved network the unit starts a hotspot and serves its setup page at 192.168.4.1; the address came in about 4 s | measured | [unit measurements](stackchan-unit-measurements.md) | 2026-10-19 |
| Rewriting NVS | wipes the saved Wi-Fi, so the hotspot step runs again | measured | [unit measurements](stackchan-unit-measurements.md) | 2026-10-19 |
| Hub link | the websocket stays connected and reconnects after a drop (patch 003); the host replaces an old session with close code 1012 | read from the patch header; host rule read from code | `firmware/patches/003-persistent-websocket.patch`, [unit protocol](../design/unit-protocol.md) | 2026-11-17 |
| Offline word | "Offline" shows after 45 s without the host, not 10 s | our setting | `firmware/patches/143-offline-label-after-45-s.patch` | 2026-11-14 |
| Without the host | the unit stays usable; Wi-Fi power save is off while the link is down | read from the patch header (not timed on the unit) | `firmware/patches/075-offline-mode.patch` | 2026-11-14 |
| First boot after a wireless update | the new image is on trial; reaching the host within about 25 s keeps it; 60 s with no crash and no host also keeps it; otherwise it goes back | our rule (patches 160 and FM01) | `firmware/patches/160-first-boot-rollback.patch`, `firmware/patches/FM01-first-boot-trial.patch` | 2026-11-16 |
| Unpaired hello | the unit shows "Waiting for response timeout" and retries every 10 to 15 s | measured | [unit measurements](stackchan-unit-measurements.md) | 2026-10-19 |
| Camera retry (host side) | every 5 s until the first frame; re-ask at 60 s, reconnect next, then a reboot request | read from host code | [unit protocol](../design/unit-protocol.md) | 2026-11-17 |
| Update backoff (host side) | 6 hours after a failure; 15 minutes to see the new version | read from host code | [unit protocol](../design/unit-protocol.md) | 2026-11-17 |
| Reconnect backoff on the unit | not written down | open | [unit protocol](../design/unit-protocol.md) | 2026-11-17 |

## Firmware base and patch families

| Fact | Value | Status | Source | Date |
|---|---|---|---|---|
| ESP-IDF | 6.1.1, built from `release/v6.1` | measured (installed and used by the build) | [firmware base](../design/firmware-base.md) | 2026-11-18 |
| Pinned bases | StackChan `28b9f0c8`, nested xiaozhi-esp32 `49b4380` (v2.5.2) | measured (`firmware/BASE`) | [firmware base](../design/firmware-base.md) | 2026-11-18 |
| Earlier base | xiaozhi-esp32 v2.2.4 on ESP-IDF 5.5.4, StackChan `1b57655` | measured (first unit) | [firmware base](../design/firmware-base.md) | 2026-10-19 |
| Patch series | 293 patches in `firmware/patches/ORDER` at the 2026-11-18 note, and a replay applied clean; the list holds more entries now | measured (replay) | [firmware base](../design/firmware-base.md) | 2026-11-18 |
| Families | numbered and older (V, P, NX, L, TN, RM, M, FI, GM, TB and others) re-ported features; UI screens; UX palette and first-run; SF safety, talk-over, power probe and update header; A, B, C base adaptation, battery and gestures; F face; FD face detection; FM first-boot trial | read from file names | [patch map](../design/patch-map.md) | 2026-11-18 |
| Build kinds | plain (release), bench, gate, talkover, linkpsk, aec, heap | measured | [firmware base](../design/firmware-base.md) | 2026-11-18 |
| Optional switches | `MAIPAI_SERIAL_TOOLS`, `MAIPAI_TALK_OVER`, `MAIPAI_TALK_OVER_AEC`, `MAIPAI_LINK_PSK`, all off by default; zero symbols when off | measured | [cost of features that are off](off-cost.md) | 2026-11-18 |
| Toolchain traps | Picolibc default, mbedTLS 4, no second `esp_wifi_init`, hotspot setup off by default upstream | vendor-stated (upstream release notes, read by us) | [firmware base](../design/firmware-base.md) | 2026-11-15 |

## Open questions

Each item has no source in the repository, or only a source that conflicts. None is guessed above.

1. How long the battery lasts under each load, and how long it takes to charge from each source. The tables in [battery and power](battery-and-power.md) are empty.
2. What the back USB port feeds, and whether it supplies the servo rail at a higher current than the side port. Cases B to F of [two USB ports](../plan/two-usb-ports.md) are not run.
3. The actual battery cell: its size, mass and any label. Only the 550 mAh figure is published.
4. The glass width in millimeters on the owner's unit. The 40.6 mm and 7.87 pixels a millimeter are assumed from the diagonal.
5. The yaw and pitch ranges the servos reach in practice, and whether positive yaw turns right. The firmware limits and the maker's figures differ for yaw.
6. Lift, carry and put-down thresholds (MOVE-CARRY-01).
7. Whether the NFC interrupt line is wired, and the real order of the 12 ring LEDs.
8. The CPU clock our firmware actually runs at, read from the unit (240 MHz is from a study, not from our boot log).
9. The unit's reconnect backoff schedule, and the cause of the camera panic on cold USB boots.
10. The speaker's power and maximum sound level, and the microphone sensitivity. No file records them.
11. Total internal RAM on the current base. The 341,760 bytes was read on the old base and has not been re-read.
12. Weight split between head, neck and base, and the mass of the owner's unit (187.2 g is the published figure).
