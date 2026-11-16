# Strip results

Placement: unit firmware, native. The baseline was built from pristine commit `28b9f0c8` in `/Users/jessetorres/esp/stackchan-rebase/strip`. No unit was flashed, so runtime heap, soak, audio, and network throughput are unmeasured. All sizes below are build reports dated 2026-11-15.

## Build steps

App slot capacity was 5,177,344 B (0x4f0000). DIRAM total is 341,760 B. `App bin` and `free slot` come from the partition size check. `Image size` is from `idf.py size`.

| Step | App bin B, before to after | Free slot B, before to after | DIRAM used B, before to after | Image B after | Result |
|---|---:|---:|---:|---:|---|
| Pristine build | - to 3,779,856 | - to 1,397,488 | - to 208,723 | 3,779,747 | Pass; freshly generated sdkconfig. |
| Log level WARN | 3,779,856 to 3,732,800 | 1,397,488 to 1,444,544 | 208,723 to 208,591 | 3,732,683 | Pass; binary -47,056 B, DIRAM -132 B. |
| IPv6 off | 3,732,800 to 3,707,696 | 1,444,544 to 1,469,648 | 208,591 to 206,975 | 3,707,587 | Pass; binary -25,104 B, DIRAM -1,616 B. |
| Dynamic Wi-Fi RX buffers 6 to 4 | 3,707,696 to 3,707,696 | 1,469,648 to 1,469,648 | 206,975 to 206,975 | 3,707,587 | Pass; no linked size change. |
| Static Wi-Fi RX buffers 3 to 2 | 3,707,696 to 3,707,712 | 1,469,648 to 1,469,632 | 206,975 to 206,975 | 3,707,603 | Pass; binary +16 B, no DIRAM change. Reverted from final defaults. |
| Remove Home-only app sources and registrations | 3,707,712 to 3,496,320 | 1,469,632 to 1,681,024 | 206,975 to 187,843 | 3,496,211 | Pass; binary -211,392 B, DIRAM -19,132 B. |
| Bluetooth off with disabled-state methods | 3,496,320 to 3,256,768 | 1,681,024 to 1,920,576 | 187,843 to 162,651 | 3,256,659 | Pass; binary -239,552 B, DIRAM -25,192 B. |
| Remove MQTT protocol source | 3,256,768 to 3,256,768 | 1,920,576 to 1,920,576 | 162,651 to 162,651 | 3,256,659 | Pass; zero linked size change. |
| Remove modem board source files | 3,256,768 to 3,256,768 | 1,920,576 to 1,920,576 | 162,651 to 162,651 | 3,256,659 | Pass; zero linked size change. Package remains required for shared headers. |
| Remove modem package manifest entries, reverted | 3,256,768 to no image | 1,920,576 to no image | 162,651 to no image | No image | Build failed at missing http.h; restored manifest entries. |
| Final clean defaults build | 3,256,768 to 3,256,768 | 1,920,576 to 1,920,576 | 162,651 to 162,651 | 3,256,655 | Pass with sdkconfig.core.defaults and S01 source edits; 4 B generated image variation. |

The app binary fell by 523,088 B from pristine to final. Free app slot rose by the same amount. DIRAM use fell by 46,072 B. The final image has 37% free app slot capacity. Build-time DIRAM is not a runtime free-heap measurement.

## Final totals

- App binary: 3,256,768 B (0x31b1c0).
- Free app slot: 1,920,576 B (37%).
- DIRAM: 162,651 B used of 341,760 B; 179,109 B remains.
- `idf.py size` image total: 3,256,655 B.
- Build: pass with `SDKCONFIG_DEFAULTS=sdkconfig.defaults;sdkconfig.core.defaults` and S01 edits.

## Pristine top contributors

Static RAM is `.bss + .data`. Flash is linked `Flash Code + Flash Data`. Component figures are per-archive contributions. Object figures are per-object contributions.

| Rank | Component by RAM | RAM B | Component by flash | Flash B | Object by RAM | RAM B | Object by flash | Flash B |
|---:|---|---:|---|---:|---|---:|---|---:|
| 1 | libmain.a | 14356 | libmain.a | 627500 | dl_nn_activation.c.obj | 9210 | stdio_vfs.c.obj | 211427 |
| 2 | libdl_lib.a | 9218 | liblvgl__lvgl.a | 339980 | spi_flash_os_func_app.c.obj | 6112 | font_noto_sans_basic_20_4.c.obj | 122896 |
| 3 | libnet80211.a | 9182 | libdl_lib.a | 212537 | wl_cnx.o | 4163 | dl_tie728_sr_s8_conv2d.S.obj | 102926 |
| 4 | libspi_flash.a | 8252 | libesp_stdio.a | 211427 | single_led.cc.obj | 3720 | x509_crt_bundle.S.obj | 66144 |
| 5 | libstdc++.a | 4481 | libstdc++.a | 183575 | locale_init.o | 3544 | imgfx_color_convert_lib.c.obj | 44961 |
| 6 | libfreertos.a | 4204 | libesp_audio_codec.a | 171223 | port.c.obj | 3132 | format.cc.obj | 40713 |
| 7 | libpp.a | 3914 | lib78__xiaozhi-fonts.a | 160381 | dios_ssp_share_subband_dlfft.c.obj | 3072 | wlocale-inst.o | 35075 |
| 8 | liblwip.a | 3790 | libnet80211.a | 158190 | app_avatar.cpp.obj | 2552 | locale-inst.o | 34818 |
| 9 | libesp_audio_processor.a | 3136 | libtfpsacrypto.a | 115821 | screensaver.cpp.obj | 2540 | jpeg_dec_process.c.obj | 32182 |
| 10 | libwpa_supplicant.a | 1711 | libc.a | 106071 | hal_servo.cpp.obj | 2388 | lv_font_montserrat_24.c.obj | 29965 |
| 11 | libphy.a | 1363 | libbt.a | 97674 | ieee80211_nvs.o | 1492 | lodepng.c.obj | 24939 |
| 12 | libbtdm_app.a | 1210 | liblwip.a | 86069 | dns.c.obj | 1323 | font_material_symbols_30_4.c.obj | 24684 |
| 13 | libc.a | 1132 | libesp_audio_processor.a | 78225 | wpa.c.obj | 1244 | lv_font_montserrat_20.c.obj | 23067 |
| 14 | libxtensa.a | 1060 | libwpa_supplicant.a | 68888 | pp.o | 1170 | hal_ble.cpp.obj | 22730 |
| 15 | libesp_system.a | 874 | libmbedtls.a | 68059 | xtensa_intr_asm.S.obj | 1024 | mcp_server.cc.obj | 22708 |
| 16 | libesp_hw_support.a | 822 | libbtdm_app.a | 66648 | nd6.c.obj | 940 | app_avatar.cpp.obj | 22704 |
| 17 | libesp_new_jpeg.a | 640 | libpp.a | 61178 | phy_init.o | 822 | ieee80211_ioctl.o | 20553 |
| 18 | libtfpsacrypto.a | 588 | libesp_new_jpeg.a | 55890 | ieee80211.o | 760 | application.cc.obj | 20328 |
| 19 | libesp-now.a | 534 | libesp_image_effects.a | 51006 | tasks.c.obj | 732 | port.c.obj | 19372 |
| 20 | libesp_wifi.a | 524 | libmooncake_log.a | 42997 | trc.o | 688 | cxx11-locale-inst.o | 18674 |
| 21 | liblvgl__lvgl.a | 480 | libmultinet.a | 39971 | pm.o | 668 | cxx11-wlocale-inst.o | 18446 |
| 22 | libefuse.a | 424 | libfreertos.a | 33252 | stackchan.cpp.obj | 668 | ieee80211_scan.o | 18058 |
| 23 | libbt.a | 415 | lib78__esp-ml307.a | 30704 | sockets.c.obj | 608 | hal_ws_avatar.cpp.obj | 17839 |
| 24 | libesp_libc.a | 388 | libphy.a | 28022 | wl_chm.o | 592 | hal_ezdata.cpp.obj | 17289 |
| 25 | libesp_driver_uart.a | 361 | libmbedtls.a | 25796 | esf_buf.o | 556 | wl_cnx.o | 17206 |

## Skips and retained defaults

- Wi-Fi IRAM optimizations and enterprise support were already off in pristine defaults. The report does not claim a measured savings for these defaults. Throughput needs a unit test.
- LVGL widgets such as keyboard, list, menu, message box, span, spinbox, tabview, tileview, window, and animation image were already off in pristine defaults. Core setup uses Montserrat 14, 16, 20, and 24, so these fonts remain.
- The speech configuration selects one wake model. Other wake models and recognition-language models were off in pristine defaults.
- Dynamic RX buffers 6 to 4 yielded no linked size change. Static RX buffers 3 to 2 added 16 B and no DIRAM savings. Both edits were left out of `sdkconfig.core.defaults`.
- MQTT protocol source removal built with no linked size change. The unused protocol was already absent from the linked image.
- Modem board source removal built with no linked size change. Removing package manifest entries broke compilation because the common board interface lost `http.h`; those entries were restored. The linked modem archive remains at about 29.8 KB in the final map.
- The app trim removes camera/avatar, app center, EzData and remote-control apps. It keeps the voice app, setup, launcher, and dance app.
- The vendor update path remains because signed wireless updates are a CORE-V1 requirement. Cert roots were not narrowed because there is no approved root list for the configured host and update server.
- The Wi-Fi portal page and stock sounds were not separately changed. They require source/resource mapping to avoid removing setup or CORE-V1 sound cues.

## Needs unit test, ordered by estimated gain

Estimates below come from the memory design note and are not measured on this build. Runtime heap and latency require the physical unit. Changes needing a new optional path must stay behind a Kconfig switch that defaults off.

1. Opus task stack in PSRAM, up to 24 KB. The earlier experiment was cut from v1; only reconsider with a fresh opt-in switch and a 30-minute soak.
2. Start the private-network client only after the LAN path fails, about 20 KB and 220 wakeups per second. Verify a clean stop and a full ten-minute memory gate.
3. Move wake-engine allocations to PSRAM, estimated 5 to 20 KB. Keep disabled by default until stop-word creation and spoken-turn tests pass.
4. Wi-Fi and lwIP IRAM options, estimated 10 to 25 KB static, with throughput risk. Current build already has these options off; confirm network stability on the unit.
5. Lower the internal allocation threshold from 512 B to 256 B, estimated 3 to 8 KB. No safe opt-in threshold switch was present, so it was not applied.
6. Wi-Fi buffers, LVGL draw buffer, camera DMA buffer, and task stacks, a few KB each. Measure heap high-water and latency before changing.

## Verification limits

No physical flash, 10-minute run, 30-minute soak, latency comparison, stop-word heap allocation, or PSRAM minimum check was performed. App size and static DIRAM are linker measurements only.
