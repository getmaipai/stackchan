# Robot 3D model

`stackchan.glb` is a rigged model of the robot for the virtual unit's 3D view, built from the official structure files in
`source/` (provenance: `SOURCE.md`; how well it matches a real unit: `MATCH.md`).

## Regenerate

```
python3 scripts/virtual-unit/model/make_body.py        # writes stackchan.glb and stackchan.params.json (byte-identical every run)
python3 scripts/virtual-unit/model/render_previews.py  # writes docs/dev/model-previews/*.png and joints.gif (about 45 s)
bash scripts/virtual-unit/model/validate.sh             # Khronos glTF validator, pinned, run locally (needs node; development only)
```

Standard library only. `softrender.py` is the small software renderer and STL reader both scripts use.

## Units and frame

Meters, Y up, the robot faces +Z, +X is the robot's left. Origin: the yaw axis on the table plane (the turntable sits 4 mm
behind the base footprint center). Rest pose: head level, facing front.

## Nodes

```
stackchan
  base                    base and bottom plate (mesh)
    usb_c_port            charge and data USB-C on the back of the base: an open socket (extras.opening: size, depth)
    screw_base_0..3       the four screws of the bottom plate
    foot_0..foot_3        the four corner mounting holes underneath (the base has no separate feet)
    sticker_bottom        label under the base, drawn for the model
    col_base              collider box
    yaw_joint             vertical axis, extras.joint: axis, limit_deg [-128, 128], source
      neck                servo holder and its two covers (turns with yaw)
      servo_yaw, servo_pitch, battery, cable    inside the holder: size of the servos from their data sheet, the rest assumed (MATCH.md)
      battery_lead, servo_wires    the battery lead and the two servo leads (assumed paths)
      back_charge_led     red light in the holder back, between the screws
      screw_back_0, screw_back_1, screw_servo    the two cover screws on the holder back and the one on the tilt servo
      col_neck            collider cylinder
      pitch_joint         horizontal axis, extras.joint: axis, limit_deg [3, 87], source
        head              shell, controller unit, front glass, board, light bars, pitch arm and bearing plate
          screen_plane    320x240 screen, flat quad, UV 0,0 top-left to 1,1 bottom-right; put the live frame on its material
          power_button, usb_c_otg, port_a    on the controller's right side: a white key in a dark gap and two open sockets (extras.opening)
          ring_light_0..11   0..5 left bar front to back, 6..11 right bar back to front; each has its own material
          board           marks the boards in the head (drawn in the head mesh)
          board_parts     chips, sockets, a ribbon and a flat cable on the upright board, as plain blocks
          screw_head_0, screw_head_1    dark screws low inside the head, seen from the back
          reset_button, sd_slot, screen_bottom_led    under the controller: white key, open card slot, light pinhole (positions from the underside photo)
          button_left_top another name for power_button (child of it, no mesh)
          sticker_side_left, sticker_side_right, sticker_top    labels drawn for the model
          touch_back_0..2 the three zones of the head touch strip on the top, front to back (outline assumed)
          col_head        collider box
```

`col_*` nodes have no mesh: the shape and size are in `extras.collider`. Joint axes follow the right-hand rule: a positive
yaw turns the head toward the robot's right, a positive pitch tilts the face up. Every dimension, the mass estimate and the
limits are in `stackchan.params.json`, each marked `measured` (from the files or the published drawing) or `assumed`.

## Limits

The joint limits are the firmware servo layer's hard limits (`firmware/main/hal/hal_servo.cpp` in the upstream tree pinned in
`firmware/BASE`): yaw -128 to 128 degrees, pitch 3 to 87. The product page recommends pitch 5 to 85; both are recorded.

## Previews

`docs/dev/model-previews/`: front, rear, left, right, top, three-quarter and rear three-quarter views, a joint contact sheet
(yaw min, center, max; pitch min, middle, max) and `joints.gif`, all drawn from the glb through its joints.
`compare-*.png` (the model beside the maker's picture of each face) are written there too when the pictures are in `.runs/ref-photos/`; git ignores them because they hold the maker's pictures.
The `view-*.png` files there are screenshots of the browser view (`view.py`) drawing the same model: the same sides, both joints at their limits, the lights on and the screen off.
