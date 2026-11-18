# The 3D virtual unit: body, power, axes

`python3 scripts/virtual-unit/view.py` then open the address it prints. The flat screen (`/frame.png`) stays the source of truth; the 3D model wraps it on a body.

## The body
- Overall size from the maker's data sheet (M5Stack K151): 54.0 wide, 70.5 tall, 61.5 deep millimeters; the CoreS3 head is 54 by 54 by 15.5 mm with a 2 inch screen (picture about 40.8 by 30.6 mm). Retailer listings vary by a millimeter; the M5Stack figures are used. All sizes sit in one table, `DIMS` in `scripts/virtual-unit/view3d.js`.
- The shape of the neck and base is an approximation from the public product photos, built from primitives by script (no model file). No third-party model is used, so nothing goes in THIRD-PARTY.md. The page loads three.js r128 from cdnjs, as before.
- Not from a drawing: the nod servo box, the ring of 12 lights around the neck (the real position of the 12 lights is not recorded in this repo), the USB-C port and the power button positions.

## What you can do
- Drag empty space to orbit, wheel or pinch to zoom, Reset view, Front, Side, Back (USB-C), Top. A drag on the screen is a swipe, a click is a tap, as before.
- Click the USB-C port on the back, or the Power button in the panel, to plug or unplug the cable. Click the round button on the right side, or the Power button, for power. The panel also has USB serial (needs the cable), Wi-Fi, a battery slider, Carried and an orientation list.
- What the body does (`scripts/virtual-unit/hw.py`, tested in `host/tests/test_virtual_unit_hw.py`): power off shows a black screen and refuses tools with the way out; power on runs the boot covers (Starting, Connecting to Wi-Fi, Connecting to Home; with Wi-Fi off, the Wi-Fi setup cover) drawn by the unit's own cover code; a cable means USB power and charging; the battery slider drives the status bar, the tired look at 20 and 10 percent, and a sleep after the 8 second grace at 5 percent (patch T01); carried, orientation, cable and battery feed the unit's own limiter (patch ML01), whose state, excursion percent and speed cap show in the panel.
- Axes: the green yaw arc (limits -128 to 128) and the red pitch arc (limits 0 to 90, the maker advises 5 to 85, drawn brighter) with live pointers, sliders that call `self.robot.set_head_angles`, Look left, Center, Look right, Look up, and four dances. The limiter shrinks the excursion and caps the speed of moves. The counter shows head moves in the last minute against the cap of 40 (patch 038).

## What is a stand-in
- Boot cover durations (the unit's real boot times are not measured) and what the serial cable does (only shown).
- The dance paths: simple shapes of the right size and speed class, not the unit's tables.
- The yaw sign (positive turns the head to the viewer's left) is not checked against a unit.
- There is no e-stop in the firmware (a search of the patches finds none). The panel has Stop dance and the Carried hold instead; a stall guard exists only in face tracking (FD04).
