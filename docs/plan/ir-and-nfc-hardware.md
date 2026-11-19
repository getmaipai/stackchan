# Does the base StackChan have infrared and NFC hardware?

Research on 2026-11-18 from public sources only. Nothing was run on a unit and no pin was driven.

**Bottom line.** Yes on paper, for all three parts. The maker's published schematics draw an infrared LED with its driver, an IRM-56384 receiver and an ST25R3916 NFC reader, all inside the standard robot body. None of them is an add-on module. The pins in our pin table match the schematics. The NFC interrupt pin and the touch interrupt pin are drawn as not connected, so neither reaches the ESP32-S3. No source shows a measured unit, so "on the owner's own unit" stays unproven until the tests at the end run.

"Maker" means M5Stack. A schematic shows the design, not a particular unit. A later hardware revision could differ.

## Parts

| Part | On the base robot | Add-on module | Pin or bus | Source and retrieval date | Paraphrase or short quote |
|---|---|---|---|---|---|
| IR transmitter | Yes (design) | None. It sits on the body's power board. | GPIO 5 (`IR_SEND`), bus connector pin 8. The pin drives an S8050 transistor through 4.7 kOhm. The transistor switches the LED `D1` to ground. A 51 ohm resistor feeds the LED from 5 V. | https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1205/SCH_Power.pdf (section "Infrared Transmitter" and the bus symbol), 2026-11-18. Product page https://docs.m5stack.com/en/StackChan, 2026-11-18. | Page: body includes "infrared transmitter and receiver". Spec row: "Infrared receiver IRM56384 + infrared transmitter". |
| IR receiver | Yes (design) | None. It sits on the top ("touch") board, joined to the power board by an 8-wire flat cable. | GPIO 10 (`IR_REC`), bus connector pin 2. Part `D1` is an IRM-56384 with VCC, GND and OUT; OUT is the `IR_REC` wire, no pull-up or filter drawn. | https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1205/SCH_Touch.pdf (section "Infrared Receiver"), 2026-11-18. Datasheet link on the product page: https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1205/IRM56384.pdf. | The schematic names the part "IRM-56384". The page lists the same datasheet under "Body Module". |
| NFC reader | Yes (design) | None. The chip, its antenna matching parts and a crystal sit on the top ("touch") board. | Internal I2C, SCL GPIO 11, SDA GPIO 12, address 0x50 (printed on the schematic and in the page's I2C table). The `IRQ` pin is marked not connected. `I2C_EN` is pulled to 3.3 V. | https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1205/SCH_Touch.pdf (section "NFC"), 2026-11-18. https://docs.m5stack.com/en/StackChan (I2C table), 2026-11-18. https://docs.m5stack.com/en/arduino/stackchan/nfc, 2026-11-18. | Page: the body includes "a full-featured NFC module". The example says to "Place tag on the top". |

Supporting reads, same date:

- The maker's Arduino page https://docs.m5stack.com/en/arduino/stackchan/ir_nec defines `IR_SEND_PIN` 5 and `IR_RECEIVE_PIN` 10 for this robot.
- The maker's library examples https://raw.githubusercontent.com/m5stack/StackChan-BSP/main/examples/IR/Send/Send.ino (`kIrLed = 5`) and https://raw.githubusercontent.com/m5stack/StackChan-BSP/main/examples/NFC/Detect/Detect.ino (the reader sits on `M5.In_I2C`, no pin given).
- The robot comes in two kits (K151 and K151-R). The page lists the same body for both. The remote controller in the second kit is a separate device.
- The factory firmware menu on the product page names an "App Center" with a "universal IR learning remote" among its downloadable apps. That is the maker's own sign that the body can send and receive infrared. We did not install it.

## What was read and what was not

| Source | Result |
|---|---|
| Product page and its five schematic PDFs (`SCH_Adapter`, `SCH_Power`, `SCH_Ring`, `SCH_Touch`, and the CoreS3 schematic) | Read the first four. The file `SCH_Ring.pdf` holds only a USB-C connector with a fuse and test pads, not the ring of LEDs. The 12 ring LEDs (WS2812C) are drawn in `SCH_Touch.pdf`. The CoreS3 schematic was not read; it covers the main unit, not the body. |
| https://github.com/m5stack/StackChan | Folders are `app`, `firmware`, `remote` and `server`. There is no hardware folder. A search of the file list (1030 entries, not truncated) found no infrared or NFC source file. The firmware's hardware layer lists audio, servo, IMU, touch, RTC, IO expander and others, and neither part. So the factory firmware does not appear to use them directly. |
| https://github.com/m5stack/M5_Hardware, folder `Products/K151_StackChan` | Holds only the ten `.stl` structure files that `scripts/virtual-unit/model/source` vendors. No schematic, no BOM, no pin data. These files cannot confirm or deny any chip. |
| BOM | No public BOM found for K151. The parts above come from the schematics, not from a parts list. |

## Details that matter for our firmware

- The infrared LED is not wired straight to the pin. The pin only turns the transistor on. A GPIO level of high lights the LED. Drive current is set by the 51 ohm resistor and the 5 V supply, not by the chip. Its exact value is not computed here because the LED's forward voltage is not in the files we read.
- The 5 V feeding the LED is the body's `BUS_5V`. The LED's rail is not the switched servo rail (`VM`).
- No pull-up or filter is drawn on the receiver output. Read the receiver datasheet before choosing a pin mode.
- The NFC `IRQ` pin has no connection. Polling is the only way to see a tag. This matches the note in `docs/dev/stackchan-sensor-map.md`, and now has a primary source.
- NFC sits behind the same I2C pair as the other body chips. The schematics give these addresses: INA226 0x41, NFC 0x50, Si12T 0x68, IO expander 0x6F (0x71 if `ADD_SEL` is high).

## Cheapest tests on the owner's own unit

None needs a soldering iron or a case opening. Tests 1 and 2 only read. Test 3 is the first that drives a pin.

1. **NFC reader present.** A read-only I2C scan of the internal bus (SCL 11, SDA 12) that sees 0x50, plus 0x41, 0x68 and 0x6F as a sanity check. Cost: one bench build, no moving parts. A scan sends only an address byte and reads nothing from the chip. If 0x50 answers, the reader is there. Then hold any NFC card on the top of the head and read its UID with the maker's `Detect` example or our `nfc_probe`. A UID back means the antenna works too.
2. **IR receiver present.** Set GPIO 10 as an input only, with no pull change, and read it while pointing any TV remote at the robot (front, then top) and pressing a key. The pin should sit at one level and show bursts of edges when a key is pressed. Nothing is driven.
3. **IR LED present and working.** Look at the front of the base through a phone camera, which sees infrared as a pale purple dot, and run one short transmit. Do this only after test 2 passes, as `docs/plan/ir-and-nfc.md` section 3 requires. If nothing lights, stop. The `D1` LED is on the power board in the base and may not face forward; try several sides before concluding.
4. **Unit revision.** Note the hardware revision on the unit's label and the date of the box. The product page lists a revision on 2026-08-07 that changed the LCD driver. The schematics do not carry a revision. If tests 1 to 3 pass on this unit, the pin table is verified for this unit only.

## Parts in the published pin table I could not match

I matched every pin-table line to a drawn part. These lines have no use on this body, or no part:

- Expander pins IO2 to IO13 (PY32L020) are drawn with no net name on the power board. The page lists only "IO1 IO14 VM_EN RGB". IO1 is `VM_EN` and IO14 is `RGB` in the drawing. Our code numbers the same pins 0 and 13, which fits a one-based versus zero-based naming difference. That reading is mine, not stated by the maker.
- The touch controller's interrupt (`Touch IRQ`) reaches the flat cable on the top board, but is marked not connected on the power board. No ESP32-S3 pin receives it.
- The `ALERT` pin of the battery monitor (INA226) is marked not connected.
- The expander's open-drain interrupt pin (`OD_INTOUT`) has no net on the power board.
- Port A (GPIO 2 and 1) in the page's expansion table is not drawn in any body schematic. It belongs to the CoreS3 main unit. The other two ports are drawn as Grove sockets (port B GPIO 8 and 9, port C GPIO 17 and 18).
- Most pins of the CoreS3 bus connector carry no body wire. The body uses GPIO 5, 6, 7, 10, 11, 12 and the two Grove sockets. The servo pair (GPIO 6 and 7) goes through two small buffer chips and a transistor to one shared servo signal line.
