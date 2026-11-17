# Face detection on the unit with ESP-DL: can the head track a face alone? (2026-11-17)

Status: research and design only. Nothing here is built; no firmware edit, no flash, no USB. It extends `face-seek-2026-11-17.md`
(sections 6, 7 and 11), which measured the detectors on a PC and left `MAIPAI_FACE_DETECT` as an unbuilt switch.

## 1. Answer

**Probably yes, as an experiment build; not yet for the core image.** Speed, flash and PSRAM all fit. Three things decide it, and only
the unit can settle them: internal RAM (66 to 68 KB free, largest block 25.6 to 26.6 KB, against the admission floor of 40 KB and
24 KB), crash stability of the S3 vector kernels on this exact board (an open upstream report, section 3), and the real hit rate on real
faces at 1.5 to 2 m. Everything else is a normal build task. Section 9 gives the spike and the go or no-go numbers.

## 2. What is already in the repo (read first)

- Face seek, S10 to S14: motion blob on a 40 by 30 gray picture, a first look plus five pan stops (-60, -30, 0, +30, +60 degrees),
  camera bursts with the camera cue, 4 turns a minute, the owner lease (`self.look.claim`, ttl 5 to 60 s), setting `turn_to_faces`
  (off, talk, always; default talk). The detector hooks exist and are tested with a stand-in: `want_face`, `face_valid`, `face_cx`,
  `mw_admit(..., detector=1)` (40,000 bytes free, 24,000 largest block).
- PC evaluation (section 6 of the seek note, an int8 executor of our own, not bit-exact): ESPDet-Pico 224 on a native 160 by 120 crop
  hit 98 percent at 1 m (42 px face), 88 at 1.5 m, 70 at 2 m, 40 at 2.5 m, 21 at 3 m; one false positive in 320 faceless frames.
  Dim light cut it to 55 percent at 1 m. MSR+MNP found almost nothing on the PC at QVGA (0 to 17 percent). Pico 416 is 445 ms, too slow.
- Measured on the unit: one camera grab (two reads) 87 to 154 ms; `SeekGrab` shrinks to 40 by 30 gray and frees the 150 KB copy; the
  seek task has a PSRAM stack and the lint `scripts/psram-stack-lint.py` forbids flash and NVS use in it; FOV is 52 degrees across the
  picture; the servo stops 1 to 5 degrees short and jitters 0.3 to 0.6 degrees at rest.
- Host side for comparison: `host/maipai_body/bodies/stackchan/person_tracker.py` (dead zone 0.08 of frame width, gain 0.7 to 0.8,
  steps capped at 25 to 30 degrees, a look only counts after the head settled) and `vision/yunet.py` (YuNet on ONNX Runtime at 320
  wide). The unit loop below reuses those shapes, not the host code.
- The earlier detector experiment (98 and 70 percent, 137 ms, 343 KB PSRAM) is the PC evaluation above; no unit run exists.

## 3. Research findings (web, checked 2026-11-17)

| Item | Finding | Source |
|---|---|---|
| ESP-DL version and license | 3.3.15 on the component registry; MIT | https://components.espressif.com/components/espressif/esp-dl , https://github.com/espressif/esp-dl |
| Chips and IDF | S3 needs IDF 5.3 or later (S31 needs 6.0). Nothing on 6.1 in the manifest | https://raw.githubusercontent.com/espressif/esp-dl/master/esp-dl/idf_component.yml |
| IDF 6 build | A v6.0 compile failure (esp-dsp 1.7 and `mbedtls/aes.h`) was reported and closed 2026-04-22 as merged; the release that carries it is not named [unverified]. Pin 3.3.15 and build | https://github.com/espressif/esp-dl/issues/295 |
| ESP-WHO | Master lists IDF 5.4, 5.5, 6.0, 6.1; S3 supported; MIT. Release tag not shown [unverified]. We would use ESP-DL directly (ESP-WHO is a camera and UI app framework we do not need) | https://github.com/espressif/esp-who |
| Face model package | `human_face_detect` 0.5.2, MIT (its LICENSE file), depends on esp-dl `~3.3.14` | https://raw.githubusercontent.com/espressif/esp-dl/master/models/human_face_detect/idf_component.yml |
| Weights license | The folder LICENSE says MIT, which covers the shipped `.espdl` files. Training data terms are not stated [unverified]; ask nothing of the owner, record it in the license table | https://raw.githubusercontent.com/espressif/esp-dl/master/models/human_face_detect/LICENSE |
| Models | MSR_S8_V1 + MNP_S8_V1 (two stage), ESPDET_PICO_224_224_FACE, ESPDET_PICO_416_416_FACE | https://github.com/espressif/esp-dl/blob/master/models/human_face_detect/README.md |
| Latency, S3, 240 MHz, octal PSRAM 80 MHz | MSR 3.7 + 32.5 + 0.3 ms (input 120x160x3); MNP 0.6 + 5.9 + 0.1 ms per candidate (48x48x3); Pico 224: 7.3 + 129.4 + 0.7 ms; Pico 416: 21.8 + 422.1 + 1.1 ms. mAP50-95: 0.367 (MSR+MNP), 0.504, 0.598 | same README |
| The "37 ms" claim | Holds for one face: MSR about 33 ms plus MNP about 6 ms per surviving candidate; the one-stage models are 132 and 437 ms; default threshold 0.5; output is box, score and five keypoints (eyes, nose tip, mouth corners) | https://developer.espressif.com/workshops/edge-ai-with-esp32-s3/assignment-2/ |
| Pixel formats | `dl::image::img_t` accepts RGB888, BGR888, gray, RGB565 (LE and BE), BGR565, YUYV, UYVY; the model input is RGB888 and the "pre" time above is the conversion plus resize | https://raw.githubusercontent.com/espressif/esp-dl/master/esp-dl/vision/image/dl_image_define.hpp |
| Memory knobs | `max_internal_size` (0 means PSRAM first), memory manager (greedy), `param_copy` (default true: weights copied from flash to RAM; false keeps them in flash and costs speed); `profile_memory()` prints internal, PSRAM and flash use per category | https://docs.espressif.com/projects/esp-dl/en/latest/tutorials/how_to_load_test_profile_model.html |
| Model location | Kconfig: flash rodata, a named partition (`human_face_det`), or SD card | face README above |
| **A crash report on this hardware** | Random panics in the TIE728 depthwise kernel during MSR+MNP on an S3 CoreS3 (StackChan), IDF 6.1, esp-dl 3.3.11, 2.5 fps continuous, 16 MB flash, quad PSRAM. Between under 1 hour and 2.5 days to crash. Maintainers could not reproduce; a hardware batch issue at 240 MHz is suspected, unconfirmed. Only workaround that held: CPU at 160 MHz (9 days clean). Pausing around Wi-Fi or pinning a core only lowered the rate. Open | https://github.com/espressif/esp-dl/issues/337 |
| Other 3.3.x traps | 3.3.13: a zero-element Resize makes `Model::load()` fail; a Swish op missing for one other model [unverified for ours] | https://github.com/espressif/esp-dl/issues/338 |
| On-chip tracking, by others | A dead zone around the frame center, a proportional correction with a capped step, sometimes PID. One project: 10 px dead zone in 320 by 240, 0.2 degree per pixel, 10 degree cap per observation; at about 3 fps the platform wanders when the box jitters, which the dead zone cures. ESP-WHO's own demo suggests N consecutive misses before an output turns off | https://www.instructables.com/ESP32-Turret-Face-Tracking-Live-Wi-Fi-Stream/ , https://robotzero.one/face-tracking-esp32-cam/ , https://github.com/MatsRobot/Face-Tracking-using-ESP32-CAM |

Not found on the web (answer from our own tests or mark unknown): minimum face size (we measured: the 224 model on a 160 by 120 crop
degrades below about 17 px, a 15 cm face at 2.5 m), lighting limits (our PC test: dim cuts hits by half), false positives on posters and
screens (no source; a printed or screen face is a face to every detector here, so it must be tested and bounded by motion, section 6),
internal RAM per run (not published; `profile_memory()` on the unit is the only authority), multi-face (MSR+MNP returns several
candidates with a per-candidate cost; Pico returns a list; we track one face, the largest near the middle).

Two cautions about the table. The Espressif numbers are for octal PSRAM at 80 MHz; the report above says the unit has quad PSRAM
[unverified for ours: read `CONFIG_SPIRAM_MODE_*` in the build], which has about half the bandwidth, so budget 1.3 to 1.6 times the latency
until measured. And the PC result for MSR+MNP (nearly nothing) disagrees with Espressif's demo; our executor approximates the second stage,
so do not drop it before the unit measures it (it is 3.5 times cheaper).

## 4. Placement (scope-core-vs-home.md, the App Store test)

- **Carve-out 3 applies:** turning to look at the person who speaks is a basic the robot does with no brain at all, so it belongs on the
  unit. The detector gives only a box and a score. No identity, no names, no gallery: recognition and the people list stay in Home.
- **App Store test (2026-11-17):** local (the frame is analyzed in PSRAM and freed; nothing is stored or sent), opt-in (the existing
  `turn_to_faces` setting, default talk, so the camera runs only after the wake word), cue always on while frames are analyzed (the
  existing `monitor_cue_begin` before every grab, which the seek core already asks for). Whether the stock firmware ships on-device face
  tracking is not confirmed [unverified]; the rule is satisfied by the privacy conditions, not by parity.
- **Where it lives:** its own Kconfig switch `MAIPAI_FACE_DETECT` (exists, default n). Experiment image first (`eyes` build or the
  `home` preset). It joins the core image only after the go rule in section 9, because the core image stays small. A feature that
  needs a 0.5 MB model and an extra library is a "preset" decision, not a default one.
- **Egress:** none new. The detector adds no network use; `docs/design/egress-audit.md` needs only a line saying the face box never
  leaves the unit (a host that holds the lease may read the box through `self.look.status`, a number pair, not a picture).

## 5. How it plugs into face seek and the lease

Today the motion blob says where and the pan stop confirms nothing. With the detector:

1. **Address (wake word).** Unchanged until the blob is found. At the stop where the blob sits, the detector runs on the crop
   around the blob column. A face confirms and the head turns to its center; no face with a blob keeps today's turn (a mover is
   still a person) but is marked `blob_only`, and the head does not enter tracking.
2. **Track (new state, only with a confirmed face).** After the turn the unit enters `TRACK`: detect 2 to 5 times a second while a
   talk goes on (setting talk) or while a face was seen in the last 20 s (setting always). The loop is section 6.
3. **Lost.** Three misses in a row (about 1 s at 3 Hz) holds the pose; 3 s without a face ends `TRACK`, then today's rules
   (return to center 20 s after the last sighting). The existing 3 s stale-target rule stays: never a turn for a face older than 3 s.
4. **Lease.** A host lease still wins and stops all of it: no camera, no detector, no head move, as the gates in S14 already do
   (`no host lease`). So "Home tracks" and "the unit tracks" never act together. When Home claims, the unit unloads the model.
   When the lease lapses (ttl 5 to 60 s) the unit seeks again. Home may read `face_cx`, `face_score`, `last_face_ago_ms` through
   `self.look.status` for its own logic; that is additive and needs no new tool.
5. **Limits that do not bend** carry over: 4 turns a minute for seek turns; camera bursts at least 1 s apart outside `TRACK`; mute,
   privacy sleep, vision off, full quiet, asleep, setting off, carried or blocked arm: no camera, no detector.

## 6. The control loop

Inputs per detection: face center `cx, cy` and box width `w` in the 320 by 240 frame, and the head angles read back at the moment of the
grab (average before and after, as `self.look.calibrate` already does). Using the angle at capture time, not "now", removes the lag error:
the picture is 0.25 to 0.4 s old when the result arrives.

- **Error:** `e_yaw = (cx / 320 - 0.5) * 52 degrees * x_sign`; `e_pitch = (cy / 240 - 0.5) * fov_v` with `fov_v` from calibration
  (about 39 degrees for a 4:3 picture at 52 across [unverified]). Target = angle at capture + error. Command the absolute target.
- **Deadband:** 4 degrees yaw (about 8 percent of the width, equal to the host's `AIM_DEAD_ZONE`), 5 degrees pitch. Inside it: no command.
  Leave it only after 2 detections in a row beyond it (hysteresis, so a jittering box does not walk the head).
- **PD:** `step = Kp * e + Kd * d(e)/dt`, `Kp` 0.6 yaw and 0.4 pitch (stops short of the target, which the servo does anyway by 1 to 5
  degrees), `Kd` small (0.1) on an EMA of the error with alpha 0.5. No integral term: the servo already settles short and an integral
  would wind up against it. Step cap 12 degrees (host uses 25 to 30, for one slow move; here moves are many and small).
- **Rate limit:** one move per 600 ms at most, and a new frame counts only after the head has settled (the same 300 ms settle test as
  seek). Speed 100 at night and in quiet hours (the existing 55 percent rule), 150 otherwise.
- **Smoothing of the box:** EMA of the center, alpha 0.6; reject a jump over 40 percent of the width in one frame unless it repeats.
- **Servo wear:** tracking spends from the existing wear counter. Add a tracking budget of 20 moves in any 60 s and a ceiling per hour
  of tracking time (start at 10 minutes, a Kconfig number), after which the unit holds the pose and says nothing. The remote cap (40
  host moves in 60 s, patch 038) stays as it is; the seek task goes through the same gate as a person's head move
  (`maipai_remote_gate`), so the wear counter and the stall guard apply with no new code path.
- **Stall guard:** reused. A head that does not move 4 degrees for a move that asked for 14 or more ends `TRACK` and returns to
  today's behavior; carried, blocked arm and pickup stop it at once.
- **Yaw first, pitch last.** Yaw only until the spike shows the camera tilt range matters; the unit's tilt range is small and a seated
  person's face sits above it (`person_tracker.py`, `TILT_MAX_DEG`).

## 7. Duty cycle and power

- Off at rest. In `TRACK`: one grab (87 to 154 ms) plus one detect (Pico 224 about 137 ms on octal; expect 180 to 220 ms on quad) is
  about 0.3 to 0.4 s per cycle, so 2.5 to 3 Hz is the ceiling without overlap; set 3 Hz, drop to 2 Hz in quiet mode. The camera is
  powered about 30 to 40 percent of the time and the cue is lit the whole time (it is "analyzing frames").
- Gate the detector with the motion blob when setting is `always`: the idle watch (1 frame a second at 40 by 30) runs the detector only
  when a blob appears. An empty room costs the idle watch only (measured: camera on 4 percent of the time at night).
- Task: the seek task is priority 1 on core 0 with a PSRAM stack. The model run goes in the same task (never in the audio or servo
  tasks), so a long run delays only seek. ESP-DL kernels hold the core for 35 to 130 ms at a time, so the audio tasks (higher priority)
  keep running but Wi-Fi on core 0 may see jitter; measure `loop_gap_max_ms` (it was 406 ms) against the 450 ms lateness limit.
- Power: not measured. Draw rises while the CPU is busy about 40 percent of the time plus the camera. Measure at the USB meter or from
  the AXP2101 current register; the idle numbers exist in the unit measurements file. A hard stop after 30 s of `TRACK` with no
  speech, then back to rest.
- **CPU clock:** the upstream crash report says 160 MHz fixed it. If the soak crashes at 240 MHz, request 160 MHz while the detector is
  loaded only (`esp_pm_lock`), not for the whole image (audio and LVGL headroom would shrink and Pico 224 would take about 1.5 times
  longer, 200 to 330 ms).

## 8. Memory and flash budget

Internal RAM is the hard limit: steady free 66 to 68 KB, largest block 25.6 to 26.6 KB, low-water mark 33,484 bytes (all measured).

| Item | Where | Size | Note |
|---|---|---|---|
| Model weights, Pico 224 | flash, in the app image (`MODEL_LOCATION_IN_FLASH_RODATA`) | 480 KB | no partition change, no pack cache change |
| Model weights, MSR + MNP | flash, same | 61 + 130 = 191 KB | the cheaper candidate |
| ESP-DL library and model glue in the app | flash | a few hundred KB [unverified] | read from the link map in the spike |
| Weights copy (`param_copy` true) | PSRAM | about 480 KB (Pico) or 191 KB (MSR+MNP) | set `false` only if PSRAM is short: costs speed |
| Activations, Pico 224 | PSRAM | at least 343 KB | lower bound from the graph |
| Activations, MSR + MNP | PSRAM | 141 KB + 50 KB | |
| Camera frame QVGA RGB565 | PSRAM | 150 KB | exists today in `SeekGrab`; held through one detect, then freed |
| Detector task stack | PSRAM | 6 to 8 KB | same rule as seek; lint applies |
| ESP-DL objects, descriptors, kernel scratch | **internal** | unknown, plan 6 to 12 KB | cap with `max_internal_size = 0`; read `profile_memory()` |
| `Model` and wrapper objects | internal | plan 2 to 4 KB | allocate once, lazily, free after the run |

- PSRAM: peak about 1.0 to 1.1 MB for Pico (weights 0.48, activations 0.35, frame 0.15), well inside the 7.0 MB that stayed free at worst
  in the seek windows. PSRAM is not the problem.
- Internal RAM: today's seek bursts leave 66 KB free and a 25.6 KB block. The admission floor for the detector is 40,000 free and a
  24,000 byte block. The block margin is only 1.6 KB, so one new internal allocation of 2 KB elsewhere would refuse the detector for good.
  Rules for the build: (1) call `dl::Model` with `max_internal_size` 0 and the greedy manager; (2) load lazily at the first
  `want_face`, unload 10 s after the last use (the model objects are the only internal cost, and they go away); (3) run only when no
  turn is speaking and no LAN video stream holds the frame lock (existing busy answer); (4) if the largest block is under 24,000
  at load, refuse and stay on the blob path, as today.
- What to free or move if the spike shows the block too small: move the camera DMA ring and the LCD draw buffer to PSRAM where the
  driver allows it (a few KB each, listed in `firmware-memory.md` item 7); trim a Wi-Fi buffer count (patch 058 style); make the avatar
  task's stack PSRAM. Each is its own measured patch; none is in this design.
- Flash: app image 3,445,184 bytes now (slot 5,177,344). With Pico weights and the library: about 4.1 to 4.5 MB, 80 to 87 percent of the
  slot. The bench image was already 4,063,152. OTA download grows by the same 0.6 to 1.0 MB, one more reason it is a preset, not
  default. The assets partition has 189,830 bytes of margin and the pack cache is protected, so neither can hold the model; a named
  `human_face_det` partition would mean a layout change, which this design rejects.
- Build size: no effect when the switch is off (the component is under `if CONFIG_MAIPAI_FACE_DETECT` in `idf_component.yml`).

## 9. Spike plan (an experiment build behind `MAIPAI_FACE_DETECT`)

Build: `esp-dl` 3.3.15 and `human_face_detect` 0.5.2 pinned and locked, model in rodata, `maipai_face_detect.cc` lazily loading and
unloading, `SeekGrab` giving a second output (QVGA RGB565 in PSRAM for the call only), the detector wired into `ms_init(..., 1)`. A
serial-only bench tool `self.look.detect_bench {model, n, crop}` that runs n detections on the live camera and prints one line per run.
Nothing else runs in the bench window beyond the normal tasks (Wi-Fi, audio, LVGL), so the numbers are honest.

Measure (one line per run, tag `MAIPAI-DET`):

1. Time per frame: pre, model, post, and the whole grab-to-box time, for Pico 224 on a 160 by 120 crop and on the whole frame, and
   MSR+MNP on 160 by 120; 200 runs each; median and p95; at 240 MHz, and at 160 MHz.
2. Internal free and largest block before load, after load, during a run (a sampling task), after unload; PSRAM the same;
   `profile_memory()` output verbatim; low-water mark.
3. Pixel format: print which of YUYV, UYVY or RGB565 (and LE or BE) the GC0308 delivers (the seek note never printed it); test the
   preprocess on both orders, since a wrong channel order halves the hit rate; conversion cost is in the "pre" time (7.3 ms for 224).
4. Accuracy with real people, one volunteer at a time, a marked floor at 0.5, 1, 1.5, 2 and 3 m, 20 runs each, in normal and dim light,
   frontal, 20 degrees off, with glasses, with a cap. Scored by a person watching the log. (Owner is not asked: any household adult at
   the desk during a bench window; no pictures stored, the log keeps only a hit, score and box.)
5. False positives: 10 minutes each of a poster with a large face, a face on a monitor, a TV, a mirror, an empty dark room, a plant;
   count boxes above 0.5 and 0.6 per 1,000 frames.
6. Servo: run the control loop with a head on a stand and a printed face moved by hand; log commanded and read-back angles, moves per
   minute, overshoot, jitter inside the deadband, and the wear counter.
7. Camera power and heat: meter in USB line for idle, seek, and 5 minutes of `TRACK`; case temperature by hand and by the chip sensor.
8. Soak, **required by the crash report:** 24 hours of 3 Hz detection at 240 MHz with Wi-Fi, audio and the avatar on; the same at 160 MHz
   if it panics. Coredump kept by the existing partition, one summary line per panic.

Go (all of them): Pico 224 on the crop hits 90 percent at 1 m, 80 at 1.5 m, 60 at 2 m in normal light with real faces; a run is at
most 250 ms median and the cycle 3 Hz; the detector is admitted (free at least 40,000 and the block at least 24,000) after a loaded
unload cycle, with no new low-water mark below 30,000 bytes; zero panics in the 24 hour soak (or none at 160 MHz and the audio and
LVGL checks still pass there); false positives under 1 per 1,000 frames on the poster and screen cases with the motion gate on; the
servo moves no more than 20 times a minute and stays inside the wear budget; no task watchdog, no `late_loops` beyond today's.
**No-go if:** the soak panics at both clocks, or the block cannot reach 24,000 without a measured patch that costs more than it
earns, or hits at 1.5 m stay under 60 percent in real light. Then the answer is: stay on the blob path, and let Home (host look
lease with its own detector) do face following, which is today's behavior.

If only MSR+MNP clears (it is faster and smaller), take it: the design above does not change except the box source and the 191 KB.

## 10. Risks

1. **S3 vector kernel crash** (esp-dl issue 337): the same hardware and IDF as ours. Mitigation: soak first, 160 MHz while loaded.
2. **Internal block margin of 1.6 KB.** Mitigation: lazy load, admission check, free-list in section 8.
3. **Posters and screens:** the detector sees faces, not people. Mitigation: require a motion blob nearby at the first confirmation, a
   score of 0.6 or more, two hits in a row to start, and a cap on how long a face that never moves can hold the head (20 s). A still
   poster ends `TRACK` by the cap. Report honestly in the setting text: "turns toward faces"; it cannot tell a picture from a person.
4. **Dim light and distance:** 3 m is out of reach (21 percent). The setting text says about 2 m. A VGA crop (640 by 480 center
   window) would double the range at the cost of 614 KB PSRAM and a camera mode switch; spike item for later, not now.
5. **Privacy surprise:** a camera running 3 times a second with the cue lit. Mitigation: setting default talk, cue on from the first grab,
   hard stop 30 s after speech ends, mute and full quiet stop it completely (already tested for seek).
6. **OTA size and flash wear** from a larger image: preset only.
7. **IDF 6.1.1 build break** (issue 295 history): fix by pinning; the cost is one build iteration, not a design change.
8. **Latency makes the head chase a stale picture:** handled by using the angle at capture time and the settle test.
9. **Servo wear:** budget and ceiling in section 6; reuse of the stall guard.

## 11. Phased build order

| Phase | Work | Size | Exit |
|---|---|---|---|
| 0 | Read `CONFIG_SPIRAM_MODE_*`, print camera pixel format, read the link map of the bench image for library cost (no new feature) | about 40 lines in a bench patch, 1 hour | quad or octal known; format known |
| 1 | Components pinned, model in rodata, `maipai_face_detect.cc` load, run, unload, bench tool, `profile_memory` line | about 350 lines C++ and a Kconfig block, 1 to 2 days | numbers 1, 2, 3 of section 9 |
| 2 | Real-face accuracy and false-positive windows, soak at 240 and 160 MHz | no code; one day plus 24 h soak | go or no-go on thresholds |
| 3 | `TRACK` state in the seek core (PD loop, deadband, hysteresis, budgets) with PC tests using the stand-in detector | about 300 lines C and 15 test groups, 1 to 2 days | tests pass; servo run (item 6) |
| 4 | Wire detector into the seek task, `self.look.status` fields, lease behavior, status line | about 150 lines, 1 day | bench window: lease takes over, unit tracks alone |
| 5 | Settings text, `docs/design/egress-audit.md` line, preset decision (experiment, `home` preset, or core) | docs only, half a day | owner is told the result, no question needed unless it goes into the core image |

Phases 3 and 4 are optional if phase 2 says no-go; the PC tests of phase 3 can be written earlier since they need no unit.

## 12. Decisions made here (so they can be overturned)

- Track yaw first, pitch with half gain; no integral term.
- Detector stays out of the core image until the soak passes; it lives under the existing switch.
- One face tracked (largest near the middle); no recognition on the unit.
- Pico 224 on the native crop is the primary; MSR+MNP is measured as the cheap alternative because the PC executor cannot judge it.
- A host lease always wins; the unit never detects while Home owns looking.
