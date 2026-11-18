# Recording head moves on the unit (for the physics calibration)

`python3 scripts/fw-head-record.py OUT.csv` on the Mac that holds the cable (bench build). It sends scripted head steps through the tool path and samples `self.robot.get_head_angles` back to back, then `python3 scripts/virtual-unit/physics/calibrate.py OUT.csv --write` fits the servo parameters and marks them measured.

- Before: unit upright on the table, powered, limiter free. On a cable the limiter halves every move, so the script stops and says so; `--usb-limit-off` lifts the USB limit for the run and puts it back.
- Moves: pitch 10 to 30, 70, 80, 25, 60 and back to 10 each time (inside the maker's 5 to 85); yaw 0 to 15, 60, -60, -15, 120, -120 and back to 0 each time. Small steps show the linear gain, large ones the torque limit and the gravity offset. Each is held 1.8 s, at most 30 a minute (the unit's cap is 40). About 45 seconds for both axes.
- Output: joint, move_id, t_ms, cmd_deg, meas_deg, rtt_ms. Each step has a row at the moment it was sent; samples carry the middle of their round trip. The fit also finds the command delay.
- First thing to read in the output: the first samples after the first step. If get_head_angles reports the last target and not the servo's feedback, the angles jump at once and the recording says nothing about the servo; stop and tell the firmware track.
- Dry runs: `--dry-run` prints the move list; `--link http://127.0.0.1:PORT/` records from the virtual unit's browser view; `host/tests/test_head_record_and_dryrun.py` records a simulated servo and checks the fit recovers its gains.
- The carried and dance-stop check (the bench item that needs hands): the Physics section of the browser view has "Run the carried and dance-stop check". It lifts the simulated robot while it dances, tilts it past 70 degrees, and checks the host's own answers: carried, dance stopped, limiter holding still, moves refused, free again when put down.
