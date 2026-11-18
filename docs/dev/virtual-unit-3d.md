# The 3D virtual unit: body, power, axes

`python3 scripts/virtual-unit/view.py` then open the address it prints. The flat screen (`/frame.png`) stays the source of truth; the 3D model wraps it on a body.

## The body
- The body is the rigged model `scripts/virtual-unit/model/stackchan.glb`, built from the maker's official structure files (provenance in `model/SOURCE.md`, license notice in `THIRD-PARTY.md`). It matches the published 54.0 x 70.5 x 61.5 mm; what is measured and what is a stand-in is in `model/MATCH.md`.
- `scripts/virtual-unit/view3d.js` reads the file with its own small reader and takes every position from the model's nodes: the two joints and their axes, the screen quad, the 12 lights, the USB-C port and the power button. The page still loads only three.js r128 from cdnjs; the model comes from this Mac (`/model/stackchan.glb`).
- The live screen is drawn on `screen_plane`. Lights 0 to 5 are the left bar front to back and 6 to 11 the right bar back to front, tinted by `self.robot.set_led_colors`.
- The head is held inside 0 to 90 degrees of pitch, the range where the model's parts do not touch.

## What you can do
- Drag empty space to orbit, wheel or pinch to zoom, Reset view, Front, Side, Back (USB-C), Top. A drag on the screen is a swipe, a click is a tap, as before.
- Click the USB-C port on the back, or the Power button in the panel, to plug or unplug the cable. Click the power button on the side of the head (left of the screen as you face it), or the Power button, for power. The panel also has USB serial (needs the cable), Wi-Fi, a battery slider, Carried and an orientation list.
- What the body does (`scripts/virtual-unit/hw.py`, tested in `host/tests/test_virtual_unit_hw.py`): power off shows a black screen and refuses tools with the way out; power on runs the boot covers (Starting, Connecting to Wi-Fi, Connecting to Home; with Wi-Fi off, the Wi-Fi setup cover) drawn by the unit's own cover code; a cable means USB power and charging; the battery slider drives the status bar, the tired look at 20 and 10 percent, and a sleep after the 8 second grace at 5 percent (patch T01); carried, orientation, cable and battery feed the unit's own limiter (patch ML01), whose state, excursion percent and speed cap show in the panel.
- Axes: the green yaw arc (limits -128 to 128) and the red pitch arc (limits 0 to 90, the maker advises 5 to 85, drawn brighter) with live pointers, sliders that call `self.robot.set_head_angles`, Look left, Center, Look right, Look up, and four dances. The limiter shrinks the excursion and caps the speed of moves. The counter shows head moves in the last minute against the cap of 40 (patch 038).

- Drag the head to move it: across turns it (yaw), up and down nods it (pitch), inside the firmware limits (yaw -128 to 128, pitch 3 to 87). The drawn head follows the hand at once and the unit is sent `self.robot.set_head_angles`, so its limiter decides; a refusal or a held angle is shown in the corner and under the sliders. The arrow keys nudge the head 5 degrees. Untick **Drag moves the head** to make every drag turn the view.
- Drag on the background or the base to turn the view; hold Alt to turn it from the head or the screen too. Shift-drag or right-drag slides the view, the wheel or a trackpad pinch zooms, a double click puts it back. The arrow, plus and minus buttons do the same without a drag, and **Under** looks up at the underside.
- Hover over a switch to see its name. Click the reset button under the controller to restart the unit (the boot covers run again). Click one of the three pads on the head top for a touch on the head: it brings the face back from a page.
- The red light in the holder back is on while the unit charges (cable in, battery not full). The small light beside the reset button stays off: nothing in the firmware drives it.
- **Show inside** turns the shell, controller and servo holder to glass so the two servos, the battery, the boards and the cable show. **Show motion** colors what turns with the pan servo green and what tilts with the tilt servo red, with a label on each. **Demo sweep** pans the drawn head left and right, then nods it up and down, over 16 seconds; it moves the drawing only and sends the unit nothing.

## What is a stand-in
- Boot cover durations (the unit's real boot times are not measured) and what the serial cable does (only shown).
- The dance paths: simple shapes of the right size and speed class, not the unit's tables.
- The yaw sign (positive turns the head to the viewer's left) is not checked against a unit.
- Physics mode keeps its own simple description (`physics/robots/stackchan.robot.json`); only its pose drives the drawn model.
- There is no e-stop in the firmware (a search of the patches finds none). The panel has Stop dance and the Carried hold instead; a stall guard exists only in face tracking (FD04).

## Physics mode (optional)
See `docs/plan/physics-playground.md`. The panel's Physics section loads the engine on demand; with it on, the model's head and base follow the physics body, and its IMU decides carried and orientation for the unit's own movement limiter.

## Side panel (2026-11-18)

- A slider belongs to the hand while it is held and for up to 2.5 seconds after, so the state poll cannot write over a drag. This does not depend on keyboard focus, which some browsers never give a slider on a click. The value is sent while dragging and again on release.
- The ports and buttons on the model glow yellow under the pointer and have generous click targets. The cable's plug is the size of a real USB-C plug.
- **Quick actions**: a color box and buttons set the 12 lights (the tool takes 36 numbers, `led_0_red` to `led_11_blue`), and **Say it** runs the three steps speech from outside needs (`self.remote.session`, `self.remote.action` for a one-use token, `self.remote.say`).
- **Make the robot do something**: pick an area (robot, face, audio and so on), then an action, then fill in its values; a number with a known range gets a slider, a yes or no gets a switch, a known set of names gets a list. A refusal is explained in plain words with the unit's reason code.
- The numbers have a fixed width and **Stop dance** is the first button of its row, so nothing moves while a dance changes the angles.
- `host/tests/test_vu_view_pointer.py` drives these with a real pointer in headless Chrome.

## Two USB-C ports (2026-11-18)

The unit has two USB-C ports and the virtual unit models both, each with its own cable: the **side port** on the controller (power and serial data) and the **back port** on the base (power). Both sockets are click targets in the picture, and the **Power and ports** panel has a button and a source list for each.

- A cable's source is a computer's USB port (5 V, 500 mA, carries data), a 5 V 2 A charger, or a 12 V supply. The 12 V supply is the mistake case: the port gives no power and the log says to unplug it.
- Derived state, in `hw.py` and in `GET /state` under `hw`: `powered_by` (battery, side, back, both), `vbus`, `charging`, `supply` (the servo rail with nothing moving and with both servos moving), `serial` and `serial_possible`, and `ports` with each cable. `usb` stays as the old name of the side port's cable.
- The supply numbers are an **assumed** model (`POWER` in `hw.py`: a 5.0 V rail, a series resistance per feed, a 500 mA ceiling for a computer port). Nothing in it is measured; the panel says so beside the value.
- The head limiter is told "a cable is present" by one rule, `LIMITER_CABLE_PORTS` in `hw.py`. Today a 5 V cable in either port counts. If the bench shows that power on the back port should lift the limit, that tuple is the one place to change. The panel line **What limits the head now** gives the reason, the swing and speed left, and which port the limiter saw.
- Scripted scenarios, in the Scenarios list and in `scenarios.py` (`PORTS`): none, side only, back only, both, a 12 V cable refused, a cable plugged in during a dance, a cable pulled during a dance. `host/tests/test_virtual_unit_ports.py` plays each one through the running view and checks `/state`, `self.motion.status` and `self.battery.get_status`; `host/tests/test_vu_view_pointer.py` clicks both sockets with a real pointer.
