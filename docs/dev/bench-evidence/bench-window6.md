<!-- Bench note copied from the bench agent's notes; paths, serial ports, hashes, addresses and ids removed. -->
# Bench window 6 (2026-11-18, script only)

R = <path> (checkout origin/main d7c6cb5)
Image recorded first: ota_0 = 1.6.2-maipai.1; backup <path> (ota_0 identical to the window-5 record). The unit's NVS had no first-run record (`mp_firstrun` absent), so in every earlier window the first-run language screen was open during the memory runs.

## (1) First-run hypothesis: CONFIRMED
fw-stress.py 600 s, host running, bench images.
| run | first-run flow | internal_free median | internal_min | int_big | frag | gate | evidence |
|---|---|---|---|---|---|---|---|
| b28 bench (window 5) | open | 65,411 | 33,484 | 25,600 | 0.39 | PASS | R/stress-b28.log |
| b28 bench, flow finished, restarted | done | 68,991 | 33,484 | 25,600 | 0.38 | PASS | R/stress-b28fr.log |
| b29 talkover (SF26), self.bench.firstrun done, restarted | done | 67,847 | 33,484 | 25,600 | 0.35 | PASS | R/stress-b29fr.log |
| bisA (earlier) | n/a | 69,533 | | | | | |
- b28: finishing the flow gives back 3,580 B, to 68,991, 542 B under bisA. So the open first-run screen explains most of the median fall seen at SF09.
- b29 talkover (a larger image: bench plus MIC3): 67,847, 1,144 B under b28-done and 1,686 B under bisA. Near 69 KB: b28 yes, b29 talkover about 1.7 KB short (it carries extra bench and MIC3 code, so it is not the same image as bisA).
- b28 bench has no self.bench.firstrun tool (it first exists in b29); on b28 I finished the flow with bench taps (language, name, how to think, Got it), which writes the same record. The flow did not return after a restart (R/w6-fr-reboot.png). b29 call: self.bench.firstrun {action: done} answered ok.

## (2) b29 build-talkover, mic3_check by slot (R/mic3-w6.txt). ch1 = the slot's tone; ch0 about 17,400 at volume 40 and 38,600 at 70, ignores gain and slot
| slot | vol 0 gain 12 | vol 40 gain 0 | vol 40 gain 24 | vol 70 gain 12 | gain step 0 to 24 |
|---|---|---|---|---|---|
| 1 | tone 2 (room 3.2) | no data (empty call) | 990 (room 3.6) | 3,106 (room 3.2) | see sweep |
| 2 | tone 1 (room 1.9) | 241 (room 2.1) | 241 (room 1.9) | 778 (room 1.8) | 0 dB (no gain effect) |
| 3 | tone 0 (room 1.0) | 0 | 0 | 0 | none, silent |
- Slot 1 gain sweep at volume 40 (the empty gain 0 call is a tool quirk: the first call after a slot change returns windows [0,0]): gain 3: 316, 6: 442, 9: 621, 12: 876, 15: 365, 18: 508, 21: 710, 24: 996, 30: 1971. Steps of 3 dB are +2.9, +3.0, +3.0 dB each. Between 12 and 15 the tone drops by 7.6 dB, then 3 dB steps continue. Gain 3 to 24 gives only +10 dB overall because of that drop; gain 12 to 24 gives +1 dB.
- Volume for slot 1: tone 2 at volume 0, about 880 at 40 (gain 12), 3,106 at 70 (gain 12): follows volume.
- Slot 2 follows volume (1, 241, 778) but ignores gain.
- Qualifier: slot 1 is the loopback slot by your rule (follows volume, moves with gain in 3 dB steps). Caveats: the 7.6 dB drop at gain 15 means the gain steps are not one continuous 0 to 24 dB range, and the earlier window-5 numbers (about 13 dB for 24 dB) came from this same effect. Slot 3 carries nothing. Slot 2 carries the tone but with fixed gain (maybe the other mic).

## (3) Head recording (b29 talkover, set_head via R/head_run5.py; the repo script at d7c6cb5 still has no set_head, no first-call warm-up and the bare-true crash)
- Limiter read before and after: state free, usb_limit limited, scale 100, speed_cap 1000, both times. The unit reports no limit active on this cable (state free), so the script did not need to lift anything and nothing needed restoring; the state is the same before and after.
- Data R/head-w6.csv (382 samples, 24 moves, 208 ms round trip, about 5 per second, whole degrees). First samples after the first step: 6, 5, 5. Readings follow the steps, so get_head_angles is servo feedback.
- Reach (settled reading, R/reach-w6.txt): pitch cmd 10 gives 5, 25 gives 10, 30 gives 12, 60 gives 27, 70 gives 32, 80 gives 38; yaw 15 gives 4, 60 gives 25, 120 gives 56, -60 gives -25, -120 gives -54. Settled value is about 0.45 to 0.5 of the command (pitch has a floor of 5 at the rest command 10). Small steps (15 to 20 degrees) reach 33 to 40 percent, large (50 to 120) 35 to 48 percent. This is a proportional shortfall that is the same with the limiter reporting free, so it is not the USB limiter and not a stop: it looks like a degree scale between the command and the servo read-back of about 0.5.
- Speed cap: no. Peak rate (limited by 5 samples a second) grows with step size: 20 deg step about 15 deg/s, 60 deg about 63, 120 deg about 134. A cap would flatten large steps. The response is a smooth first-order rise of about 0.5 s.
- Fit (calibrate.py, no --write; R/fit-w6.txt): rms 9.57 deg, yaw_kp 0.1042, yaw_kv 0.0537, pitch_kp 0.0231, pitch_kv 0.0571, joint_damping 0.0054, torque_limit 0.0046, command_delay 0.88 ms (same value in all fits: it looks like a fixed starting value, not a measured delay). The fit is poor because the model reaches the command while the unit reaches half of it; fix the scale before trusting these.

## Restore
Full flash of the backup, hash verified; ota_0 read back byte-identical. The host process (mine, started earlier) had stopped at 05:22:29 after the restore for a reason not in its log, so I started it again with start-newhost.sh (pid in <path>); the unit is online (settings API, ws_up 05:31:01). USB lock removed. The unit's NVS is back to the recorded one (no first-run record again).
