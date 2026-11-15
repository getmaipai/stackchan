# Firmware spike on unit, 2026-11-15

## Result

1. Target: M5Stack StackChan, ESP32-S3, 16 MB flash, `/dev/cu.usbmodem103401`.
2. StackChan commit: `28b9f0c8bd6acd81cb3c70f1a93c3e373b39d400`.
3. ESP-IDF: v6.1.1, commit `051e4c4eb20346e043cdd47bc388fde75ff8af63`, tag `v6.1.1`.
4. The build succeeded. `idf.py set-target esp32s3 build` also completed successfully. No source fixes were required. Existing `firmware/dependencies.lock` was already modified before this run and was preserved.
5. Commands: `. ~/esp/esp-idf-6.1.1/export.sh`; `idf.py set-target esp32s3 build`; `idf.py -p /dev/cu.usbmodem103401 flash`; pyserial capture at 115200 baud for 60 seconds; full image restore command below.
6. App image: 0x39f560 bytes (3,797,344 bytes). Smallest app partition: 0x4f0000 bytes. Free: 0x150aa0 bytes (27%). Assets: 2,371,294 bytes.
7. No heap print patch was needed. Existing output every 10 seconds reports `free sram` and `minimal sram`. At 14.359 s free was 18,179 B and minimum 15,660 B. After audio feature creation, free was 10,247 B and minimum 1,708 B; subsequent periodic free readings were 15,823 to 15,947 B, with minimum 1,708 B.
8. The requested `int_big` and PSRAM minimum were not available in the stock serial output. The only largest-block sample was the AFE pre-create line: 8,704 B; post-create largest block was 2,944 B. No PSRAM minimum was logged.
9. No panic, watchdog reset, or backtrace appeared during the 60-second stock capture. The connected device completed Wi-Fi activation and reached idle. A spoken interaction was not run.
10. Restore: `~/.espressif/python_env/idf6.1_py3.11_env/bin/python -m esptool --port /dev/cu.usbmodem103401 --baud 921600 write-flash 0 ~/stackchan-backups/2026-11-15/unit-flash-16MB.bin`. Esptool wrote and verified 16,777,216 bytes and hard-reset the unit. The backup SHA-256 matched `3f1611bcf18670cf96e8712c7878f9bd168b1f0a4b8d863347c246917e49e13e`. A later serial capture of the restored unit (taken by the parent session) shows project `maipai-stackchan`, App version `0.2.212`, so the restore is confirmed. An earlier check inside the run read the wrong log.

Full build log: `~/esp/stackchan-spike/build.log`. Stock 60-second serial capture: `~/esp/stackchan-spike/serial-stock.log`. Restored serial capture: `~/esp/stackchan-spike/serial-restored.log`.
