# Bench checks: virtual dry run

## Wi-Fi setup with no saved network (screen)
- ok: a saved network exists before the wipe: got 1, expected 1
- ok: self.wifi.forget answers: got True, expected True
- ok: saved networks after the wipe: got 0, expected 0
- ok: the model's tool list hides self.wifi.forget: got True, expected True
- ok: setup screen frame exists (drawn by the unit's own cover code): got True, expected True
- only the unit can show: whether the unit really reaches the setup branch with no saved network and shows the hotspot name and address (the review says the branch may never be reached): wipe Wi-Fi with self.wifi.forget, reboot, snapshot the screen, compare with cover-wifi-setup.png.

## A wireless update is confirmed (FM01) (rule)
- ok: host answers: got KEEP_HOST at 20, expected KEEP_HOST at 20
- ok: host off: got KEEP_QUIET at 60, expected KEEP_QUIET at 60
- ok: main loop dead: got ROLLBACK at 120, expected ROLLBACK at 120
- ok: camera never settles: got ROLLBACK at 120, expected ROLLBACK at 120
- only the unit can show: that the unit's own timer calls the rule once a second, saves the record, and that the base boot loader does not roll back first: read the log for 'on trial' then 'keeping it'.

## A long sentence after wake (SF03) (rule)
- ok: no one speaks after wake: got ends at 8, expected ends at 8
- ok: a 12 s sentence from 1 s to 13 s: got ends at 21, expected ends at 21
- ok: speech that never stops: got ends at 60, expected ends at 60
- only the unit can show: that the unit feeds the rule real voice detection every second and the host still gets the whole sentence: say a 12 s sentence after the wake word, read the log for no 'State guard returning listening to idle' until 8 s after the last word, and that the reply starts (fw-voice-bench.py ROUNDS --gate).

