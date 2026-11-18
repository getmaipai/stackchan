# Does the model match the owner's unit?

Short answer: the outside shape, size, parts and joint layout match the manufacturer's K151 files and published drawing to
within about 1.5 mm. Nothing has been measured on the owner's own unit yet; the checklist at the end says what to compare.

## What was checked

| Check | Result |
|---|---|
| Product | The files are for K151 (the current kit with the 2.0 inch controller, pan and tilt servos, two light bars). Only one folder and one commit exist for it. |
| Overall height | Files give 70.41 mm (base 11.1 + bottom plate 1.51 + gap + 54 mm head); drawing says 70.5. |
| Head | 54 x 54 mm face, 61.5 mm deep in the drawing; shell file 54 x 54 x 46.7 plus a 14.8 mm controller unit (not in the files, drawn as a rounded box). |
| Base | 48 x 56 mm in the file and the drawing; corner holes 32 x 48 mm apart in both. |
| Side holes | Three 6.4 mm holes 8 mm apart, 10 mm below the top: file and drawing agree. |
| Light bars | Each side of the shell has a 5.6 x 40.5 mm window right behind the controller; the light guide file (31 mm long) stands in it. Matches the vertical strip in the drawing and the photos. |
| Back | The shell is open at the back and mostly open underneath, as in the drawing's rear view: the board, the servo holder and the holder's back cover show. |
| Yaw limit | Firmware -128 to 128 degrees (`firmware/main/hal/hal_servo.cpp` in the upstream tree pinned in `firmware/BASE`, `Hal::servo_init`, yaw `angleLimit (-1280, 1280)` tenths). The product page says 360 degree pan servo; the firmware limiter is what the robot does. |
| Pitch limit | Firmware 3 to 87 degrees (same file, pitch `angleLimit (30, 870)`). The product page recommends 5 to 85. The asset uses the firmware numbers and records both. |
| Pitch travel vs geometry | Rendered at 3, 45 and 87 degrees: the shell's side walls pass outside the base (54 mm head, 48 mm base), the open bottom clears the holder, and the back edge stays about 13 mm above the table at 87. No collision found. |

## Assembly (how the separate files were put together)

Each file has its own CAD offset; all share one orientation (file +Z up, file -Y front). Offsets into the base file's frame:

- Servo holder, its two covers: x -123 (the holder's round bottom then shares the base turntable's center to 0.24 mm).
- Pitch arm and bearing plate: x -246 and -199.1, y +123 (the arm's hole lands on the 4.8 mm shaft stub on the holder, z 9.3 in both files).
- Shell: x -369, z 0 (its vertical center is the pitch axis height), y +13 (set from the drawing: screen face 1 mm ahead of the base front, which also puts the shell's back 4 mm past the base back, as drawn).
- Bottom plate: centered on the base footprint, its 1.51 mm plate under the base bottom.
- Light bars: turned upright, flush in the side windows. Bar A on the robot's left, bar B on the right (a guess: the two files differ only in small details).

## Doubts

1. The controller unit is a rounded box with the screen, glass and camera drawn on; the real front has mic holes, a light sensor and side ports only as markers.
2. The shell's front-to-back position (y +13) comes from the drawing, not from a mating feature; error up to about 1 mm.
3. Light bar order: lights 0 to 5 on the left bar top to bottom, 6 to 11 on the right bar bottom to top (the order the docs' drawings use). Real pixel order is unknown. Spacing 5 mm is assumed.
4. Joint directions: positive yaw turns to the robot's right and positive pitch tilts the face up, as the virtual unit view draws them. Not checked against the servo wiring.
5. Pitch 0 is the level pose of the drawing; the firmware never goes below 3 degrees, so the unit's lowest pose is 3 degrees up.
6. Colors are taken from photos (light gray shell, dark gray base). Units come in other colors.
7. Mass (0.25 kg) is an estimate.
8. The base has no separate feet: `foot_0..3` mark the four corner mounting holes on the underside.
9. The rear view shows a green board as a flat plate; the real board's parts, cable and battery are not drawn.

## What to compare on the unit

1. Total height with the head level (70.5 mm expected) and head depth front to back (61.5 mm).
2. Distance from the base front edge to the screen glass (about 1 mm, glass ahead) and from the base back to the head back (about 4 mm, head behind).
3. A photo of the back: is the back open with the board and the gray servo holder showing, as in `docs/dev/model-previews/rear.png`?
4. Light bars: is the strip behind the controller on each side the light, and which side lights first when set one LED at a time?
5. Which way the head turns for a positive yaw and a positive pitch command.
6. Weigh the unit to replace the mass estimate.
