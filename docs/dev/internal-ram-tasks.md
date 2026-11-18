# Internal RAM: tasks with an internal stack, and what could move (static reading, 2026-11-18)

Made from a replayed tree by `scripts/internal-tasks.py TREE` (every `xTaskCreate` and `xTaskCreatePinnedToCore`, not the PSRAM forms; the test apps, demo applications and other boards of the base tree are left out). The measured part (which blocks sit where in the heap) needs `self.bench.heap_trace` and `self.bench.heap_info` on a unit; this note is the reading half.

## Tasks with an internal stack (stack bytes)

| Task | Stack (bytes or the expression) | Where |
|---|---|---|
| opus_codec | 24576 | `xiaozhi-esp32/main/audio/audio_service.cc:193` |
| avatar_lan | 8192 | `main/hal/utils/local_network/local_avatar_client.cpp:65` |
| activation | 8192 | `xiaozhi-esp32/main/application.cc:392` |
| pack_boot | 6144 | `main/hal/maipai_packs.cc:221` |
| pack_write | 6144 | `main/hal/maipai_packs.cc:363` |
| stackchan | 5120 | `main/hal/hal.cpp:248` |
| tailnet | 5120 | `main/hal/maipai_tailnet.cc:381` |
| heal_restart | 4096 | `main/hal/maipai_heal.cc:256` |
| mp_reset | 4096 | `main/hal/maipai_reset.cc:156` |
| avatar_rx | 4096 | `main/hal/utils/local_network/avatar_socket.cpp:86` |
| audio_input | 4096 | `xiaozhi-esp32/main/audio/audio_service.cc:134` |
| audio_output | 4096 | `xiaozhi-esp32/main/audio/audio_service.cc:143` |
| audio_input | 4096 | `xiaozhi-esp32/main/audio/audio_service.cc:152` |
| wifi_cfg_delay | 4096 | `xiaozhi-esp32/main/boards/common/wifi_board.cc:207` |
| ws_reconnect | 4096 | `xiaozhi-esp32/main/protocols/websocket_protocol.cc:55` |
| servo_step | 3072 | `main/hal/hal.cpp:249` |
| LedEvent | 2048 | `xiaozhi-esp32/main/led/gpio_led.cc:85` |
| audio_output | 2048 | `xiaozhi-esp32/main/audio/audio_service.cc:161` |
| tone_stream_sender_task | 2048 | `managed_components/espressif__esp_audio_effects/example/esp_audio_effects_demo/main/esp_audio_effects_demo.c:737` |
| fwupdate | kTaskStackBytes | `main/hal/maipai_update.cc:149` |
| notify_http | kNotifyTaskStackSize | `xiaozhi-esp32/main/notify/notify_player.cc:65` |

`opus_codec` (24,576) runs on a PSRAM static stack when one can be allocated at start; the internal form is the fallback. `bench_say`, `benchspeak` and the bench rows exist only in bench images. The rows for other transports (ml307, ethernet, mqtt, usb) are not built into the CoreS3 image or run only when that transport is used.

## What can move, and what cannot

A task may take a PSRAM stack only if nothing it calls reaches flash, saved settings or the partition API (a flash read with the stack in PSRAM asserts and reboots the unit; the 2026-11-18 `ws_reconnect` crash loop). `scripts/psram-stack-lint.py` checks tasks created through a named function; it does not see a task created with a lambda, so a lambda task needs a hand reading.

| Task | Stack | Verdict |
|---|---|---|
| `ws_reconnect` | 4096 | cannot move: `ConnectAudioChannel` reads saved settings (the lint now flags it) |
| `stackchan` (screen and logic) | 5120 | cannot move: it reads and writes settings |
| `servo_step` | 3072 | could not be proven flash-free (the servo update reaches the battery read over I2C and logging); left internal |
| `audio_input`, `audio_output` | 4096 each | audio hardware path, latency sensitive: leave |
| `tcp_receive`, `ssl_receive` | 4096 each, one per open socket | created and self-deleted per connection inside the vendor network component: moving them needs a vendor patch that keeps one persistent task (IDF advises against self-deleting a task with a PSRAM stack). Worth it only if the heap dump shows these stacks splitting the free area |
| `avatar_lan` | 8192 | best single candidate (8 KB): its body is mDNS and sockets and the two avatar files read no saved settings, but it is created through a lambda, so it needs a hand reading of everything `run()` calls before it moves |
| `pack_boot`, `pack_write` | 6144 each | transient (boot and a pack write); a pack write touches the pack store (flash): cannot move |
| `tailnet` | 5120 | only when the private network client is built; reads settings: cannot move |
| `activation` | 8192 | transient at start, reads settings: cannot move |

## Order to try when the heap dump arrives

1. `avatar_lan` to PSRAM after a hand reading (saves 8 KB of internal RAM while the avatar link is up).
2. The unowned 4 KB block at `3fcf0bc0`: resolve it from the `heap_trace` dump with `addr2line` on the heap image's ELF; if it is a socket or TLS buffer, `CONFIG_MBEDTLS_EXTERNAL_MEM_ALLOC` style options may move it.
3. A persistent `tcp_receive` only if steps 1 and 2 do not reach a largest block above 32 KB.
