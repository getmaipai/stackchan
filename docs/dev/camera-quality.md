# Camera quality: what the CoreS3 StackChan camera can record or stream

Firmware track, 2026-11-18. Read from the build tree (`sdkconfig`, `managed_components/espressif__esp_cam_sensor`, `main/hal/board/stackchan.cc`, `hal_ws_avatar.cpp`, `esp_video.cc`). The figures marked **to measure** come from `self.bench.camera_probe` (patch SF45) and, for the end-to-end numbers, from `self.avatar.status` with the host (patch SF44). Nothing in this note was measured on a unit yet.

## The sensor

- **GC0308**, a 0.3 megapixel VGA CMOS sensor (auto-detected on the DVP interface: `CONFIG_CAMERA_GC0308`). A VGA sensor of this class has a small pixel and no infrared sensitivity control: it is a daylight and room-light camera, noisy in dim light.
- **Formats the driver offers** (`gc0308.c`): 640 by 480 at 16 frames a second (UYVY, YUYV, RGB565 or grayscale) and 320 by 240 at 20 frames a second (a sub-sampled mode, same four formats). The DVP bus is 8 bits at a 20 MHz input clock; that bus, not the CPU, is why 640 by 480 stops at 16 frames a second.
- **What is configured today:** the default is 320 by 240, UYVY, 20 frames a second (`CAMERA_GC0308_DVP_DEFAULT_FMT_YUV422_320X240_20FPS`, format index 3). The 640 by 480 YUYV mode is built in and can be chosen with the build overlay `firmware/configs/sdkconfig.cam640.defaults` (kind `cam640` is the bench image with it).
- The driver keeps one frame buffer in PSRAM (`CAMERA_PSRAM_DMA`, patch M06): 320 by 240 by 2 bytes is 150 KB, 640 by 480 by 2 bytes is 600 KB. The first read after a pause returns an old frame, so the camera path reads twice and keeps the second.

## What limits the rate today

| Stage | Limit |
|---|---|
| Sensor and bus | 20 frames a second at 320 by 240, 16 at 640 by 480 |
| Avatar stream timer (`hal_ws_avatar.cpp`) | one frame per 350 ms (about 2.9 a second); 700 ms (1.4 a second) in video mode |
| JPEG encode | software encoder in `image_to_jpeg`: quality 20, then 10, then 5 until the frame fits the payload limit (the LAN limit is 64 KB). **To measure:** encode ms at each size |
| Network | Wi-Fi to the host; a 320 by 240 frame at quality 20 is expected at roughly 8 to 15 KB (**to measure**), so 3 frames a second is about 30 to 45 KB a second, far below the link |
| Privacy | no frame while muted, vision off, full quiet or locked (SF44); the camera-on cue is drawn by the capture path for every frame |

So the stream today is **320 by 240 at about 3 frames a second**: enough to steer the head to a face, to look at a room and to take a photo, and clearly not video.

## What the best achievable looks like (to confirm with the probe)

| Mode | Sensor can give | Expected through this firmware | Notes |
|---|---|---|---|
| QVGA 320 by 240 | 20 fps | 8 to 15 fps if the stream timer is lowered to 70 ms and the encode takes under 60 ms | memory and Wi-Fi are not the limit; the encoder is |
| VGA 640 by 480 | 16 fps | 3 to 6 fps (software JPEG of 4 times the pixels) | needs the 640 image; frame buffer 600 KB of PSRAM; payload limit may force quality 10 or 5 |
| Grayscale | same | the encoder is faster and files are smaller | useful for a dark room |

Run `self.bench.camera_probe {seconds: 10, quality: 20, skip: 1}` on the default image and on the `cam640` image for the rows above; `skip: 4` shows the sensor rate with the encoder mostly out of the way.

## Baby monitor viability

A baby monitor needs, in order of importance: a picture in the dark (infrared light and a sensor that sees it), a steady stream of at least 10 to 15 frames a second at 640 by 480, hours of unattended running, alerts and a camera that is not owned by the cloud.

- **Night:** this unit has no infrared light and no infrared filter control; the GC0308 reads a dark room as noise or black. The probe's brightness and noise figures put a number on it (a lit room, then a dark room, then a covered lens). Expect the dark-room picture to be unusable without room light or a night light.
- **Rate and size:** the sensor allows VGA at 16 fps; this firmware's encoder and stream timer give less (table above). A baby-monitor-grade stream would need the hardware path limits lifted (a faster encoder or a different format such as motion JPEG from a sensor that makes it) and a stream timer matched to the encode time.
- **Privacy:** every frame draws the camera-on cue, mute and the lock stop the stream, frames go only to the paired host (encrypted when the link key is stored), nothing is kept on the unit. These match a monitor's trust rules and are stricter than most.
- **Conclusion (before measuring):** usable today as a "look at the room" camera in normal light at QVGA a few frames a second; not a night-time baby monitor. The probe results and the dark-room test decide how far the rate can be raised; the night limit is the sensor and the missing infrared, not the software.

## Bench test list (needs a person)

1. Lit room, default image: `camera_probe {seconds: 10, quality: 20, skip: 1}` and `{seconds: 10, quality: 40, skip: 4}`.
2. Dark room (lights off, no light on the unit's face), same two calls; then the same with a hand covering the lens: the brightness reading should be near 0 and the noise reading is the sensor floor.
3. `cam640` image in the lit room, the same calls.
4. With SF44 on (the `avatar` image) and the host running: `self.avatar.status` for frames sent and last frame age over 60 seconds; the host log gives the end-to-end frame rate and delay.
