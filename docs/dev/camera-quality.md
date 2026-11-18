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

## The sweep: how the one table is made (owner question: can resolution and rate go up?)

`self.bench.camera_probe {seconds, quality, skip, interval_ms}` (patch SF45, held by decision 11) runs through the real camera path (the camera-on cue is drawn; mute, vision off, full quiet and the lock refuse the run). `interval_ms` spaces the frames like the stream timer: **350** (today), 200, 100, 66, 50, and 0 (as fast as the camera and the encoder allow). It answers frames per second, bytes per frame and per second, capture and encode times (mean and worst), the lowest free internal RAM, the lowest largest block, the lowest free PSRAM and the share of time both cores were idle (the CPU load). `scripts/camera-sweep-table.py RESULTS.jsonl` turns the answers into one table and names what limits each row: the sensor, the stream timer, the JPEG encoder, the camera read, or memory under the gate floor. `--plan` prints the calls: qualities 10, 20, 40 and 60 and the six timer values, on the default 320 by 240 image and on the `cam640` image (640 by 480; the frame size is fixed when the camera starts, so the two sizes are two images).

| Size | Quality | Timer ms | Frames/s | Bytes/frame | Capture ms | Encode ms | Bytes/s | Free internal | Largest block | PSRAM free | CPU idle % | Limit |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 320x240 | | | | | | | | | | | | to measure |
| 640x480 | | | | | | | | | | | | to measure |

Nothing was measured yet: the table is filled by the bench (a lit room). The send-buffer need is the worst frame in bytes (the `bytes.worst` field) because the avatar socket sends one frame at a time; the Wi-Fi throughput is `bytes_per_s` against the link (a Wi-Fi 4 link carries more than 2 MB a second at the unit's distance; the host log gives the real end-to-end rate once SF44 lands).

## What the chip can and cannot do for speed

- **No picture hardware on the ESP32-S3:** the pixel processing accelerator (PPA) and the image signal processor (ISP) belong to the ESP32-P4, not the S3; the S3 has the camera interface only. There is no hardware JPEG encoder on the S3, so every frame is encoded in software (`image_to_jpeg`), and that time is the main limit above 320 by 240. Confirmed from the build: the driver offers the sensor's modes, and the IDF components in the tree contain no PPA, ISP or JPEG hardware code for this chip.
- **Grayscale is available:** the sensor driver has 320 by 240 and 640 by 480 grayscale modes (`CAMERA_GC0308_DVP_GRAY_*`, disabled in the current config). Grayscale halves the bytes on the camera bus and the JPEG has one plane to encode: expect a faster encoder and a file about 40 to 60 percent smaller; a dark-room picture loses nothing (the sensor is the limit there), a lit room loses color. Worth one probe run with a grayscale build; it is the cheapest way to a higher rate.
- **Color modes:** UYVY (current) and YUYV are the same cost; RGB565 doubles the work in the converter.

## Proposed defaults (to confirm with the table)

| Mode | Size and rate | Memory cost (decision 15: allocated while streaming, freed after) |
|---|---|---|
| Default | 320 by 240, JPEG quality 20, about 10 frames a second (timer 100 ms) if the encoder allows | frame buffer 150 KB PSRAM (already allocated by the driver), JPEG output buffer about 10 to 15 KB PSRAM per frame, no new internal block beyond the socket's receive stack |
| High, on demand | 640 by 480, quality 10 to 20, 3 to 5 frames a second | frame buffer 600 KB PSRAM, JPEG output 30 to 60 KB PSRAM; needs the 640 image and the camera restarted, so it is a bench or a deliberate setting, not a per-frame switch |
| Face steering | 320 by 240 gray or color at 2 to 3 frames a second | as today |

The unit does not switch between 320 and 640 at run time with the stock driver: a restart of the camera is needed, which also makes the first frame old. If an on-demand high mode is wanted, the restart is part of the request and is shown by the camera-on cue.

## Recording on the host

The host writes what it receives: it takes the JPEG frames of the avatar socket and writes them to a file as motion JPEG in a Matroska or MP4 container (no re-encoding: the frames are stored as they arrived), at the rate and size the unit sends, with the arrival time of each frame as its timestamp so playback runs at the real rate. The unit's cue stays exactly as it is: it is drawn for every frame the unit takes, whoever receives it; the host cannot turn it off and a recording does not ask the unit for anything but the stream. Privacy: a recording is a file on the household's computer that only the household's own settings page can start, with a visible "recording" mark on the host page; mute, vision off, full quiet and the lock stop the stream and so the recording.

## Power: does the camera or Wi-Fi power limit the rate?

The unit on a computer's USB port has about 500 mA available. The camera, the Wi-Fi radio sending a stream and the screen are the large loads; the servos are separate. A brownout shows as a reset or a camera that stops. The first bench evidence is that the back USB-C port is wired to the same USB path as the side port (`docs/plan/two-usb-ports.md`), so plugging the back port does not by itself add power; a 2 A wall charger does. The probe's lowest-VBUS reading during a high-rate run (`self.bench.power_probe`, SF48, together with the camera probe) tells whether the supply sags: run the 640 by 480 sweep once on a computer's port and once on a charger.
