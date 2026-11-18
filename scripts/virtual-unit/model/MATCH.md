# Does the model match the owner's unit?

Short answer: the shell, base and servo holder are the manufacturer's own K151 geometry, and the assembled model lands on the published size (54.0 x 70.5 x 61.5 mm). The controller unit on the front, the screen, the board, the buttons and the light order are drawn stand-ins. Nothing has been measured on the owner's own unit yet; the checklist at the end says what to compare.

Sources are named in `SOURCE.md`. "Drawing" below means the dimension drawing on the product page.

## What was checked

| Check | Result |
|---|---|
| Product | The files are for K151 (the kit with the 2.0 inch controller, pan and tilt servos, two light bars). Only one folder and one commit exist for it, with no revision letters. |
| Size | Model 54.08 x 70.50 x 61.55 mm (the button marker adds 0.08); published 54.0 x 70.5 x 61.5. |
| Base | 47.96 x 55.96 mm, body 8.0 mm tall, corner holes 32 x 48 mm apart with 4.86 mm bores: the drawing says 48, 8, 32 and 48. |
| Front overhang | The glass ends 1.26 mm ahead of the base front; the drawing shows about 1.3. |
| Side holes | Three 6.4 mm holes 8 mm apart, 10 mm below the top: file and drawing agree. |
| Light bars | Each top corner of the shell has a slanted slot 2 mm wide and 29.6 mm long. The light guide's stem is 2.06 mm wide and 29.6 mm long and fits it. The product photos show the lit strip along the top edges. |
| Back | The shell is open at the back. The servo holder, its back cover with two screws and the base port show, as in the product's rear photo. |
| Pitch travel | Sweeping the head about the nod axis in 3 degree steps, the official parts touch nothing from 0 to 93 degrees. Below 0 and from 96 up the shell runs into the servo holder. With the drawn board the free range is 0 to 90. So 0 is level, positive looks up, and the geometry allows the published 90 degrees. |
| Yaw limit | Firmware -128 to 128 degrees (`firmware/main/hal/hal_servo.cpp` in the upstream tree pinned in `firmware/BASE`, https://github.com/m5stack/StackChan at commit `28b9f0c8bd6acd81cb3c70f1a93c3e373b39d400`, `Hal::servo_init`, yaw `angleLimit (-1280, 1280)` tenths). The product page says 360 degrees with no restriction. The files show no end stop. The asset uses the firmware numbers. |
| Pitch limit | Firmware 3 to 87 degrees (same function, pitch `angleLimit (30, 870)`). No patch in this repository changes it. The product page recommends 5 to 85. The asset uses the firmware numbers and records both. |

## Assembly (how the separate files were put together)

The files are exported side by side, 123.0 mm apart in X and 123.05 mm in Y, all in one orientation (file +Z up, file -Y front). Each offset in `make_body.py` comes from fitting circles to the parts' own holes and bosses:

- **Turn axis.** The servo holder's round flange and the base's turntable share a center to 0.01 mm once the 123.0 mm is taken off. The turntable sits 4 mm behind the base footprint center.
- **Servo cover.** It is lifted 12.0 mm in the files. Its two screw holes meet the holder's at that offset, so it sits on the holder, 20.8 mm below the head top.
- **Bottom plate.** It seats on the base's four screw posts and then stands 0.15 mm below the base body, as the drawing shows.
- **Shell.** Offset 13.0 mm front to back. Its inner arm pockets (radius 5.58 mm) then center on the holder's side stub, at the height where the arm's spline and the bearing plate's arc also center (9.3 mm in the files). This is a mating feature, not a reading from the drawing.
- **Arm and bearing plate.** Pressed into the shell's two pockets, the arm on the robot's left.
- **Light bars.** Seated in the slanted corner slots with the stem tip flush with the rounded corner. Bar A on the left, bar B on the right.

## What the second pass changed (2026-11-18)

The first build on `main` had four assembly errors. Each is fixed and has a test.

1. The light bars stood upright on the shell sides behind the controller. They belong in the top corner slots; the tall recess on each side is where the name label sits.
2. The servo cover floated 12 mm above the holder.
3. The bottom plate hung 1.51 mm under the base. It seats inside, 0.15 mm proud.
4. The mass was a 250 g guess. The published figure is 187.2 g.

Added: speaker grille on the controller's left side, the camera ring and the four small openings under the screen, a red port A, a metal base port, larger previews.

## Doubts

1. **Height needs a 1.45 mm correction.** Stacked as exported, the files give 69.05 mm, not 70.5. The drawing shows the head 16.3 to 16.6 mm above the base bottom where the files give 14.9. The model lowers the base 1.45 mm, which leaves a 0.65 mm gap under the holder's flange. On a real unit that space may hold a bearing, or the base may be taller. Marked `assumed`.
2. **Zero and direction.** That firmware angle 0 means "level", and that positive yaw turns the head to the robot's right, are assumptions. The zero position is stored per unit (`zero_pos_1`, `zero_pos_2`), so a unit can differ by a few degrees.
3. **Light order.** Two bars of six is published. Lights 0 to 5 run front to back on the left bar and 6 to 11 back to front on the right. The real order and the 5 mm spacing are unknown.
4. **Controller unit** is a rounded block with glass, screen, camera ring, openings, speaker grille, button and ports drawn on from the drawing, to about 1 mm. No logo, labels, card slot or reset button.
5. **Boards** are two flat green plates: one under the head top, one upright behind the controller. Only the schematics of the adapter, power, ring and touch boards are published, so size and position are guesses.
6. **Servos, battery and cable** are drawn from what is published and are otherwise assumed; see the next section. The bearing is not drawn.
7. **Arm side.** The arm is on the left because the holder's stub is on the right. Both parts are hidden inside the head.
8. **Mass split** between head, neck and base is a guess; only the 187.2 g total is published. The physics description (`physics/robots/stackchan.robot.json`) keeps the published 187.2 g as its measured total and splits it by the model's shares (assumed); weigh a unit to replace the split.
9. **Colors** are judged from photos. Units come in other colors.
10. **Feet.** The base has no separate feet: `foot_0..3` mark the four corner mounting holes.

## Inside the body (added 2026-11-18)

Published: both servos are the SCS0009, 23.2 x 12.1 x 25.25 mm with a 20 tooth, 3.95 mm output (servo data sheet linked from the product page); the body holds a 550 mAh battery (product page). The maker's repository has only the structure files for this product: no assembly drawing, no board outline, no battery size.

Measured in the structure files: the base has a socket of 3.95 mm on the turn axis and the servo arm has one on the nod axis. So the pan servo's case sits in the holder and turns with it, with its shaft down in the base; it is not in the base. The two servo sizes stacked (25.25 + 12.1 = 37.35 mm) match the holder with its cover (37.8 mm), and the cover's C-shaped opening is the length of a servo.

| Part (node) | Rides on | Size | Position |
|---|---|---|---|
| Pan servo (`servo_yaw`) | yaw | measured (data sheet) | assumed: upright on the turn axis, shaft in the base socket |
| Tilt servo (`servo_pitch`) | yaw | measured (data sheet) | assumed: lying on the pan servo in the cover's opening, shaft on the nod axis into the arm |
| Battery (`battery`) | yaw | assumed: 30 x 20 x 8 mm, a common 550 mAh cell | assumed: behind the holder's back cover, where the product photo shows blue through the cover's notch |
| Boards (`board`, in the head mesh) | pitch | assumed | assumed |
| Flat cable (`cable`) | yaw | assumed | assumed: from the holder up toward the head |

Sweep with these parts in: free from 0 to 90 degrees of pitch. The only contact is the tilt servo's shaft inside the arm's socket, the same at every angle, which is where they join.

## Reset button and head touch pads (added 2026-11-18)

- **Reset button** (`reset_button`). The product page puts it "next to the microSD card slot on the bottom side" of the controller, and its picture says a press reboots and a 3 second hold enters download mode. The model draws the card slot and a dark button beside it under the controller, on the right as you face the robot. The exact spot is assumed. In the view a click restarts the virtual unit (the boot covers run again); it has no download mode.
- **Head touch pads** (`touch_back_0` to `touch_back_2`). The product page lists three touch pads and a touch controller. The firmware's head touch code reads three intensities in a row and reports press, release, swipe forward and swipe backward. So there are three zones in a line, front to back. The pads sit under the shell and cannot be seen on a real unit; only the touch board's schematic is published. Their outline (16 x 8 mm each), their place on the top behind the two connector openings, and which end is zone 0 are assumed. In the view a click sends the unit's head tap event, which brings the face back from a page. The petting reaction of the real firmware is not in the virtual unit.
- **The rest of the top.** The two connector openings and the round hole between them are in the official shell and were already drawn. The shell file has no vents, logo recess or other marks on top.

## Compared with the maker's photos (2026-11-18)

The 17 product photos on the product page were set beside screenshots of the model from the same angles. The photos are not in this repository; they are at `https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1205/K151_stack_chan_main_pictures_NN.webp`, NN from 01 to 17 (05 front, 06 and 08 the speaker side, 07 the open back, 09 the underside of the controller, 10 the button side, 11 the top, 12 the underside of the base).

Seen on the real unit and now drawn (all positions read off the photos, so assumed):

| Feature | Node | In the view |
|---|---|---|
| Red light in the holder back, between the two screws | `back_charge_led` | red while the unit charges. The firmware does not drive it (`BUILTIN_LED_GPIO` is not connected), so "lit while charging" is an assumption |
| Pinhole between the card slot and the reset button | `screen_bottom_led` | stays off: the product picture says green in download mode, and nothing in the firmware drives it |
| Card slot under the controller | `sd_slot` | named on hover |
| Reset button to the right of the slot: a white key in a dark gap, with a pinhole and two short slots between | `reset_button` | restarts the unit |
| Button at the top of the left side (as you face the screen) | `power_button`, also named `button_left_top` | power: the product picture says press for on, hold 6 s for off |
| Name label on each side of the shell, white with a dark end | `sticker_side_left`, `sticker_side_right` | the product's name in drawn strokes, a dark end with a small face |
| Rating label on top of the controller | `sticker_top` | a gray end band, stand-in bars and two large stand-in marks, no real text |
| Large label under the base | `sticker_bottom` | a dark header band, an orange square, a gray outline of the robot and stand-in bars |
| Black and teal connectors in the two top openings | in the head mesh | open sockets with four pins each |

Seen and not drawn: the embossed maker's logo on the speaker side and under the base label, the real text, codes and compliance marks on the labels, the finger scoop behind the card slot, the cap in one of the side holes, and the fine print on the boards.

## Second look at the photos, face by face (2026-11-18)

Each face was rendered at the angle of its photo and set beside it. The pairs are written to `docs/dev/model-previews/compare-*.png` by `render_previews.py` when the photos are in `.runs/ref-photos/`; they hold the maker's pictures, so git ignores them. Sizes were read in pixels and scaled by the 54 mm head (about 10.5 to 11 pixels per millimeter), so they are good to about 0.3 mm and marked assumed.

| Face | Difference found | Now |
|---|---|---|
| Under the controller | card slot, light and reset button sat 9.8 mm behind the glass | 7.0, 6.6 and 6.6 mm behind the glass (47, 44 and 44 percent of the depth in the photo); slot 12.9 x 1.3 mm at 6.8 mm right of the middle; button at 15.0 mm left |
| Under the controller | reset button was a dark oval | a white key 7.6 x 5.4 mm in a dark gap, with the restart mark beside it |
| Under the controller | the light was drawn where the restart mark is printed | moved to the pinhole; the two short slots are real pockets |
| Button side | ports were flat colored patches | real openings cut through the controller wall: USB-C 3.3 x 9.2 mm, 5.5 mm deep, metal rim and tongue; port A 5.3 x 10.5 mm, 5 mm deep, red, four pins |
| Button side | button was a plain box, tinted green by the view while the unit was on | a white key 8.7 x 6.1 mm in a dark gap 9.7 x 7.1 mm, power mark above it, no tint |
| Both sides | the shapes between the three round openings showed the gray inside | filled dark, as in the photos; they are openings through the 1 mm wall in the shell file |
| Both sides | label 5.4 mm wide with block letters and a short dark end | 5.6 x 41 mm with round corners, the name in strokes, a slanted dark end 11.4 to 12.6 mm long with a small face |
| Back | no screws | two bright screws in the cover's recesses (centers from the cover file), two dark ones in the shell's lower front holes, one on the tilt servo |
| Back | holder dark, cover lighter | holder light gray, back cover darker gray, as in the photo |
| Back | USB-C was a flat plate | an open socket with a metal shell and a tongue, in the base file's 12 x 5 mm opening |
| Back, inside | bare boards | chips, sockets, pin pads, a dark ribbon and a pale flat cable on the upright board; the battery lead and the two servo leads in the holder |
| Top | connectors were solid blocks | open sockets with four pins; dark behind the two small windows between them |
| Top | label 22 x 9 mm | 16.3 x 12.3 mm with a gray end band, placed from the photo |
| Bottom | no screws, label square | four screws in the plate's holes (centers from the plate file), label 32.5 x 35.4 mm with cut corners, the two dark strips along the sides |
| Front | holder and base too dark | lighter, from the photos |

Only the 17 maker pictures and the published drawing were used. No other gallery or video was read.

## What to compare on the unit

1. With a ruler: total height with the head level (70.5 mm), base body height (8 mm), and the gap between the flat top of the base and the head bottom (8.4 mm in the model).
2. Look under the servo holder's flange: is there a gap of about half a millimeter above the base ring?
3. A photo of the back, level with the unit, against `docs/dev/model-previews/rear.png`.
4. Send pitch 3 and pitch 87: is the head level at 3 and facing the ceiling at 87?
5. Send a positive yaw: does the head turn to its own right?
6. Light one LED at a time, 0 to 11: which bar and which end lights first?
7. Look under the front: is the card slot 7 mm behind the glass and the reset button 15 mm to the right of the middle as you face the robot?
8. Stroke the head top front to back: where do the three pads start and end?
9. Plug in the cable: does the red light in the back come on, and does it go out when the battery is full?
10. Is the pinhole between the card slot and the reset button a light, and when is it lit?
11. Count the screws on the back: two bright ones on the holder cover, two dark ones low inside the head, one on the tilt servo.
12. Open the back: do the plug, the dark ribbon and the pale flat cable sit where the model draws them?
