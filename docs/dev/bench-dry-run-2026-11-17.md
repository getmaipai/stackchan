# Bench checks: virtual dry run

## Wi-Fi setup with no saved network (screen)
- ok: saved networks on a unit with none: got 0, expected 0
- ok: setup screen frame exists (drawn by the unit's own cover code): got True, expected True
- only the unit can show: whether the unit really reaches the setup branch with no saved network and shows the hotspot name and address (the review says the branch may never be reached): there is no tool to wipe Wi-Fi any more (add, forget and switch were removed by SF02): wipe it from the portal or by erasing the settings store, boot, snapshot the screen, compare with cover-wifi-setup.png.

## A wireless update is confirmed (FM01) (rule)
- ok: host answers: got KEEP_HOST at 20, expected KEEP_HOST at 20
- ok: host off: got KEEP_QUIET at 60, expected KEEP_QUIET at 60
- ok: main loop dead: got ROLLBACK at 120, expected ROLLBACK at 120
- ok: camera never settles: got ROLLBACK at 120, expected ROLLBACK at 120
- only the unit can show: that the unit's own timer calls the rule once a second, saves the record, and that the base boot loader does not roll back first: read the log for 'on trial' then 'keeping it'.

## A long sentence after wake (model)
- ok: 12 s sentence after wake: got listening ends at 8 s, expected listening ends at 8 s
- only the unit can show: whether anything else resets the guard while the person speaks (speech does not change the state in the patch text, so a model says no); say a 12 s sentence after the wake word and read the log for 'State guard returning listening to idle after 8 seconds'.

