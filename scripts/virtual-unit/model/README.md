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
    usb_c_port            charge and data USB-C on the back of the base
    foot_0..foot_3        the four corner mounting holes underneath (the base has no separate feet)
    sticker_bottom        label under the base, drawn for the model
    col_base              collider box
    yaw_joint             vertical axis, extras.joint: axis, limit_deg [-128, 128], source
      neck                servo holder and its two covers (turns with yaw)
      servo_yaw, servo_pitch, battery, cable    inside the holder: size of the servos from their data sheet, the rest assumed (MATCH.md)
      back_charge_led     red light in the holder back, between the screws
      col_neck            collider cylinder
      pitch_joint         horizontal axis, extras.joint: axis, limit_deg [3, 87], source
        head              shell, controller unit, front glass, board, light bars, pitch arm and bearing plate
          screen_plane    320x240 screen, flat quad, UV 0,0 top-left to 1,1 bottom-right; put the live frame on its material
          power_button, usb_c_otg, port_a    markers on the controller's right side
          ring_light_0..11   0..5 left bar front to back, 6..11 right bar back to front; each has its own material
          board           marks the boards in the head (drawn in the head mesh)
          reset_button, sd_slot, screen_bottom_led    under the controller: oval button, card slot, small light (positions from product photos)
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
The `view-*.png` files there are screenshots of the browser view (`view.py`) drawing the same model: the same sides, both joints at their limits, the lights on and the screen off.
