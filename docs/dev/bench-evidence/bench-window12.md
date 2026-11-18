<!-- Bench note copied from the bench agent's notes; paths, serial ports, hashes, addresses and ids removed. -->
# Bench window 12 (2026-11-18, script only): STOPPED EARLY, all three b41 images crash-loop

R = <path> (checkout origin/main eccc9f4). Data: ./bench-w12-data/.
Recorded first: ota_0 = 1.6.2-maipai.1; backup <path> (ota_0 identical to the window-11 record). Limiter as found: usb_limit "limited" (NVS). At the end the whole flash was restored, so the saved value is the recorded one.
Images: b41 build-aec (built 08:21:32, say_test and silence_ms and peak_dps present), build-heap (08:23:28, heap_trace present, elf beside it), build-plain (08:23:46, the shipping image, peak_dps present, no bench tools).

## The blocker (found at the first barge round)
Every b41 image I flashed (build-aec, build-heap, build-plain) crashes and reboots about every 7 seconds, from the first boot, and never reaches the host (0 ws_connected in 75 s of console for heap and plain; the host log shows no unit).
- Console: `E Settings: Settings "websocket" opened from task ws_reconnect, whose stack is in PSRAM; read it on the main task (rule TC02)` followed by `assert failed: spi_flash_disable_interrupts_caches_and_other_cpu cache_utils.c:125 (esp_task_stack_is_sane_cache_disabled())`, then a reboot (HealGuard core dump line names task ws_reconnect).
- Backtrace resolved with addr2line against build-aec's elf: panic_abort, __assert_func, spi_flash_disable_interrupts_caches_and_other_cpu, esp_flash_read, esp_partition_read, nvs::NVSPartition::read, nvs::Page::findItem, nvs_get_str, Settings::GetString, WebsocketProtocol::ConnectAudioChannel() at xiaozhi-esp32/main/protocols/websocket_protocol.cc:177, WebsocketProtocol::ReconnectTask() at websocket_protocol.cc:375, vPortTaskWrapper. So the reconnect task (stack in PSRAM) reads NVS (flash) with cache disabled, which asserts. The guard line says the read should happen on the main task (rule TC02) but the read at line 177 still happens in the reconnect task.
- Counts: build-aec: 3 asserts in the first 22 s, 7 in about 2 minutes (R/barge12-serial.log); build-heap: 5 asserts and 6 resets in 75 s; build-plain: 10 asserts and 11 resets in 75 s. Full console copies: bench-w12-data/aec-crashloop-console.log, build-heap-boot75.log, build-plain-boot75.log.
- Earlier images (b29) did not do this (the ws_reconnect stack was in internal RAM in the window-11 heap map). Nothing I did triggers it: the unit crashes at idle with Wi-Fi coming up.
- The shipping plain image is affected, so b41 as built cannot be shipped.

## What was measured despite the crash loop (build-aec; tools answer between crashes)
(4) Limiter fail-closed at boot: PASS. 5 reboots, status read every 0.12 s from the reboot command on; first answer after 4.94, 1.33, 2.67, 3.0, 2.66 s: every first answer says state usb_limited, reasons "on a USB cable", usb true, usb_limit limited, scale 50, speed_cap 600. A move commanded right at the first answer (yaw 60, speed 1000): applied angle_in 600, angle_out 300, scale 50, speed_out 600, speed_pct 60, applied state usb_limited, age 704 to 933 ms, on all 5 boots. (R/boot12.txt, bench-w12-data/boot12.txt)
Note: usb stays true here because the reading is in the first seconds; the earlier "usb false at first" is gone.

## Not done (blocked by the crash loop)
- (1) barge rounds (20), no_barge rounds, 10-minute soak, --watch aec: the unit reboots every 7 s, so a reply plus two wake hits cannot run; the two inject calls land in a reboot. No silence_ms line was ever read.
- (2) heap_trace and heap_info after the link is up: the link never comes up on build-heap; the 4 KB block question needs a build that survives. The elf is <path> I did not dump a trace of the 6-second-old boot (it would be mid-boot state and the dump takes longer than the 7 s between crashes).
- (3) peak_dps: read after happy and sway with the limit on and off (R/peak12.txt): every reading 0 deg/s (yaw 0, pitch 0), because the reboot every 7 s resets the counter and the dance. No usable number.
- (5) build-plain 10-minute memory line: not run; the unit reboots every 7 s, so any median would be of a 7 s boot.

## Restore
Full flash of the backup; hash verified; ota_0 read back byte-identical. Host running, unit online (ws_up 08:37:49). USB lock removed. The recorded (non-bench) image has no serial tools, so the limiter value could not be read back; it is the recorded NVS value (limited).
