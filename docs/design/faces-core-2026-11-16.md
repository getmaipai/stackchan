# Faces core, 2026-11-16 (patches X01 and X02)

Placement: unit firmware (the face runs on the robot) and the host settings page. Tree: `~/esp/stackchan-rebase/faces` (train5 plus L01 to L09, Y01 to Y03 replayed). Nothing committed.

## What was wrong with the eyes

The base element clamps a tilt to 0 to 3600, so every negative tilt became none. Under the fluid motion (H02) the right eye never tilted and the left did: one eye cut at an angle, the other flat. The happy and sad looks cut an eye with a lid on purpose; a unit that rests "happy" (high care) therefore sat with cut eyes. Fixes: the tilt is a signed value, never clamped, and the right eye mirrors the left exactly; the resting happy look is now Content (round eyes, a small smile); an open eye is a full circle at every tilt. Checked on real pixels (`host/tests/test_firmware_face_render.py`: every tilt step, every style, left against right) and on the pure geometry (`look_core_test.c`).

Blink: both eyes read ONE lid state (phase, timers and eased value), stepped once per frame by whichever eye updates first. In the stock skin the two eyes are separate objects with their own easing steps; that is where two blinks could drift apart.

## Styles, colors, states

Big eyes (default), Eyes only, Stock, Classic, Minimal. Classic is not the stock skin: Stock keeps the stock bar mouth, size 20 eyes and the stock lids and tilts, with no tint; Classic is round eyes with the new mouth. Dropped styles load as Big eyes (blob version 3, ids 3 to 8 are the dropped ones, new ids are 9 and 10). Sweat and shy decorators are dropped. Mouth options were drawn as PNG (thin line, chunky soft curve, bean); the chunky soft curve won (`hostrender/out/mouth-options.png`). The mouth is one family of strokes, so a smile, a cat mouth, a wobble line and an open O ease into each other.

Color: eyes white by default, screen color per person (palette at 26 percent brightness or a dark custom color), a gentle emotion tint on by default (red angry, blue sad, pink love, dim sleepy and tired). Shapes always differ too.

Sleep: sleepy (half lids, slow blinks that last longer), closing (1.5 s eased), shut (a thin curved line near the eye middle), waking (half, open, one stretch blink). Low battery shows tired (20 percent half lids and a yawn, 10 percent more droop, 5 percent sleepy), not sad. Thinking dots sit at the mouth position on every style.

## Measured on the unit (bench image, saved face untouched)

See the report of the run for the table; fps is from `self.face.bench_run` (talk is a synthetic level) and from a real spoken turn. Not done here: effects, overlays, speech bubble, listening cues, fillers, pack loader, mood tags (later runs). No battery icon was drawn: the status bar already has one.
