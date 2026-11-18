"""The unit tool names the host sends that no firmware patch defines, each with a stated status.

`docs/plan/undefined-host-calls-2026-11-18.md` gives the reason and the verdict for each. A test
(`tests/test_tool_parity.py`) fails when the host starts sending a new name nobody defined, and when a
name below gets a firmware definition and should leave the list.
"""

from __future__ import annotations

# Expected from the pinned base firmware (not in this repository): not checked here.
BASE_FIRMWARE = frozenset({
    "self.audio_speaker.set_volume", "self.camera.take_photo", "self.robot.get_reminders",
    "self.robot.set_led_color", "self.robot.stop_reminder",
})  # fmt: skip

# Names used only by the bench page and the simulated unit; they never reach a real unit.
SIMULATOR_ONLY = frozenset({
    "self.robot.nod", "self.robot.set_brightness", "self.robot.set_emotion", "self.robot.set_face_background",
    "self.robot.set_privacy", "self.robot.show_clock", "self.robot.simulate_touch",
})  # fmt: skip

# Host half only: the call is made, the firmware has no definition yet, the call fails as "old firmware"
# and the feature must say so plainly. Each leaves this list when a firmware patch defines it.
HOST_HALF_ONLY = frozenset({
    "self.audio.alert", "self.audio.listen", "self.audio.speak",
    "self.face.sleep_z", "self.face.song_title",
    "self.music.capture_clip", "self.music.drop_clip", "self.music.read_clip",
    "self.screen.get_ambient_light", "self.screen.set_face_background", "self.screen.set_rotation",
    "self.screen.show_symbol", "self.system.reset", "self.wifi.use_now",
})  # fmt: skip
