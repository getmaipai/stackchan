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
5. **Board** under the head top is a flat green plate whose position is a guess. Its parts, the cable and the battery are not drawn.
6. **Servos and the bearing** are not in the files and not drawn. The rear view is emptier than a real unit.
7. **Arm side.** The arm is on the left because the holder's stub is on the right. Both parts are hidden inside the head.
8. **Mass split** between head, neck and base is a guess; only the 187.2 g total is published.
9. **Colors** are judged from photos. Units come in other colors.
10. **Feet.** The base has no separate feet: `foot_0..3` mark the four corner mounting holes.

## What to compare on the unit

1. With a ruler: total height with the head level (70.5 mm), base body height (8 mm), and the gap between the flat top of the base and the head bottom (8.4 mm in the model).
2. Look under the servo holder's flange: is there a gap of about half a millimeter above the base ring?
3. A photo of the back, level with the unit, against `docs/dev/model-previews/rear.png`.
4. Send pitch 3 and pitch 87: is the head level at 3 and facing the ceiling at 87?
5. Send a positive yaw: does the head turn to its own right?
6. Light one LED at a time, 0 to 11: which bar and which end lights first?
