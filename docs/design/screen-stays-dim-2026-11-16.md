# The screen that stayed dim, 2026-11-16

Placement: unit firmware (patches `W01` and `R04`, native lane), host tests `host/tests/test_stackchan_screen_wake.py`. Nothing is committed or pushed.

## Symptom

The owner, standing next to the unit: the screen goes dim and stays dim, and tapping the face does not undim it. Earlier: swipe up does nothing, the wake word does nothing, the touch bar does nothing.

## Cause

1. The host dims the screen with the stock tool `self.screen.set_brightness`: its rest stage "asleep" sets 5 after five quiet minutes, its night rule sets 15.
2. The stock tool saved the value. The saved level is what the unit boots into and what `RestoreBrightness` returns to, so the host's dim level became the person's level.
3. The host sets a level again only when its rest stage or night edge changes. A host older than the face-tool fix asks for `self.screen.set_face_background` (this firmware has none) every ten seconds, the call fails, and its night edge stops before it reaches the brightness call. A unit that restarted while dimmed came back at 5 and nothing ever raised it.
4. Nothing on the unit itself woke the screen. A touch, the touch bar, a shake, a tilt and the wake word never touched the backlight. The quick settings panel (swipe up) did open, black on a screen at 5, so it looked like nothing happened.

Also in the unit's saved state: mute is on (the wake word is off and a face tap starts no listen), and the restart guard had used its three restarts an hour.

## Fix

- `W01`: the host's brightness is live only; the saved level is the person's (the quick settings slider). A touch on the glass, a strong touch or swipe on the touch bar, a shake, a tilt or the wake word restores the saved level at once and sends the host a `head_touch` event (strong, tap, screen=1) so it wakes too. A press that only woke the screen starts no listen and toggles no mute, vision or quiet. With the hub link down for 60 s a dimmed screen comes back by itself. `Backlight::SetBrightness` no longer drops a request for the level a move in progress had just left. The AXP2101 supply register is read with `TryReadRegs` before the screen is switched. New tool `self.screen.get_level`; bench build only: `self.screen.bench_touch`.
- `R04`: after the three free restarts an hour the guard waits for 5, 10, 20, then at most 30 minutes of running instead of refusing for the rest of the hour, and the stall watch asks again every minute while the freeze lasts. The first stall logs every task's state and sends one `heal` event (`action=stall`), so the next freeze names its cause.

The pure rules are `maipai_screen_core.h` and `maipai_heal_core.h`, tested by `screen_core_test.c` and `heal_core_test.c`.
