# Host calls with no firmware definition (2026-11-18)

Checked against `firmware/` (all patches). The host sends 14 unit tools that no patch defines. Today each call fails as "old firmware" and the feature says so. `host/maipai_body/bodies/stackchan/tool_parity.py` lists them, and `tests/test_tool_parity.py` fails when a new undefined name appears or when a listed name gets a definition.

Verdicts use the repository's rule (PORT, REBUILD or SKIP). The firmware track owns the patches.

| Tool | Used for | Verdict |
|---|---|---|
| `self.system.reset` | Factory reset from the settings page | REBUILD: small patch (confirm word, wipe settings, reboot). Until then the page says reset needs a newer image. |
| `self.wifi.use_now` | Home's `wifi_use` command | REBUILD: switch to a saved network now. |
| `self.music.capture_clip`, `read_clip`, `drop_clip` | Song naming | SKIP for the core: song naming is a Home feature (`local-vs-home-features-2026-11-17.md`). The host half stays for Home mode. |
| `self.screen.set_rotation` | Tilted-unit screen rotation | REBUILD with the display patches, low priority. |
| `self.screen.show_symbol` | Reaction symbol | SKIP: reactions are drawn by the overlay engine now. Remove the call when the host path is next touched. |
| `self.screen.get_ambient_light` | Room light reading on the Look page | REBUILD only if the sensor path is wanted; otherwise hide the reading. |
| `self.screen.set_face_background` | Face background color | SKIP: the face styles own their colors. |
| `self.face.song_title` | Title line while a song plays | SKIP with song naming. |
| `self.face.sleep_z` | Sleeping letters | SKIP: the sleeping overlay covers it. |
| `self.audio.speak`, `listen`, `alert` | Bench page and the tool list | SKIP: speech runs over the audio stream, not tools. Remove from the bench page when it is next changed. |

Also in the host and not in the firmware, on purpose: 5 names the pinned base firmware provides (`self.robot.set_led_color`, `self.camera.take_photo`, `self.audio_speaker.set_volume`, `self.robot.get_reminders`, `self.robot.stop_reminder`) and 7 names only the bench page and the simulated unit use.
