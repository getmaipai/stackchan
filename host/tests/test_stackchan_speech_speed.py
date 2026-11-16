"""Item 11: one speech speed and pitch setting per unit, on the settings page and in the speech output."""

from __future__ import annotations

import asyncio
import threading
from types import SimpleNamespace

import numpy as np
import pytest

from maipai_body.i18n import CATALOG
from maipai_body.settings_page import SettingsBackend, render_page
from maipai_body.speech.pitch import clamp_speed, shape_voice, shift_pitch
from maipai_body.unit_settings import SettingsError, UnitSettingsStore

RATE = 24000
KITCHEN = "aa:bb:cc:dd:ee:01"


def _tone(hz: float, seconds: float = 1.0) -> np.ndarray:
    t = np.arange(int(RATE * seconds)) / RATE
    return (0.5 * np.sin(2 * np.pi * hz * t)).astype(np.float32)


def _peak_hz(samples: np.ndarray) -> float:
    spectrum = np.abs(np.fft.rfft(samples * np.hanning(len(samples))))
    return float(np.argmax(spectrum) * RATE / len(samples))


def test_neutral_speed_and_pitch_return_the_same_array():
    samples = _tone(200.0)
    assert shape_voice(samples, RATE, 0.0, 1.0) is samples


def test_speed_changes_the_length_and_keeps_the_pitch():
    samples = _tone(200.0, 2.0)
    faster = shape_voice(samples, RATE, 0.0, 1.5)
    slower = shape_voice(samples, RATE, 0.0, 0.75)
    assert abs(len(faster) - len(samples) / 1.5) <= 1440
    assert abs(len(slower) - len(samples) / 0.75) <= 1440
    for out in (faster, slower):
        assert abs(_peak_hz(out) - 200.0) / 200.0 < 0.04
        assert float(np.max(np.abs(out))) <= 1.0


def test_speed_and_pitch_together_move_both():
    samples = _tone(200.0, 2.0)
    out = shape_voice(samples, RATE, 5.0, 1.25)
    expected = 200.0 * 2 ** (5 / 12)
    assert abs(_peak_hz(out) - expected) / expected < 0.04
    assert abs(len(out) - len(samples) / 1.25) <= 1440


def test_pitch_only_matches_the_existing_pitch_shift():
    samples = _tone(200.0)
    assert np.array_equal(shape_voice(samples, RATE, 3.0, 1.0), shift_pitch(samples, RATE, 3.0))


def test_speed_is_clamped():
    assert clamp_speed(9) == 1.5 and clamp_speed(0.1) == 0.75 and clamp_speed(1.0) == 1.0


def test_the_unit_stores_speed_and_pitch_and_rejects_bad_values(tmp_path):
    store = UnitSettingsStore(tmp_path / "u.json")
    store.update(KITCHEN, {"speech_speed": 1.2, "speech_pitch": -3})
    assert store.get(KITCHEN) == {"speech_speed": 1.2, "speech_pitch": -3}
    for bad, match in (
        ({"speech_speed": 3}, "speed"),
        ({"speech_speed": "fast"}, "speed"),
        ({"speech_speed": True}, "speed"),
        ({"speech_pitch": 13}, "pitch"),
        ({"speech_pitch": None}, "pitch"),
    ):
        with pytest.raises(SettingsError, match=match):
            store.update(KITCHEN, bad)


def test_the_settings_page_shows_and_saves_the_two_settings(tmp_path):
    backend = SettingsBackend(
        devices=lambda: {KITCHEN: {}}, store=UnitSettingsStore(tmp_path / "u.json")
    )
    unit = backend.state()["units"][0]
    assert unit["speech_speed"] == 1.0 and unit["speech_pitch"] == 0
    backend.save(KITCHEN, {"speech_speed": 0.9, "speech_pitch": 2})
    unit = backend.state()["units"][0]
    assert unit["speech_speed"] == 0.9 and unit["speech_pitch"] == 2
    for lang in ("en", "es"):
        page = render_page(lang).decode()
        assert "speech_speed" in page and "speech_pitch" in page


def test_both_languages_have_the_speech_strings():
    for key in ("settings.speech_speed", "settings.speech_pitch"):
        assert CATALOG["en"][key] and CATALOG["es"][key]
        assert CATALOG["en"][key] != CATALOG["es"][key]


def test_the_unit_registry_reads_the_units_own_speech_settings(tmp_path):
    from maipai_body.config import RobotConfig
    from maipai_body.units import UnitRegistry

    store = UnitSettingsStore(tmp_path / "u.json")
    store.update(KITCHEN, {"speech_speed": 1.3, "speech_pitch": 4})
    registry = UnitRegistry(RobotConfig(), store)
    assert registry.speech_speed_for(KITCHEN) == 1.3
    assert registry.speech_pitch_for(KITCHEN) == 4.0
    assert registry.speech_speed_for("aa:bb:cc:dd:ee:99") == 1.0
    assert registry.speech_pitch_for("aa:bb:cc:dd:ee:99") == 0.0


def _frames(speed: float) -> int:
    from maipai_body.bodies.stackchan.turn import StackChanAudioPlayback

    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    sent: list[bytes] = []

    class _Server:
        _loop = loop

        async def send_audio(self, device_id, frames, **kwargs):
            sent.extend(frames)

        async def stop_audio(self, device_id):
            pass

    async def no_sleep(seconds):
        return None

    playback = StackChanAudioPlayback(
        _Server(), "device", async_sleep=no_sleep, speech_speed=lambda: speed
    )
    samples = _tone(200.0, 3.0)
    for index in range(0, len(samples), 2400):
        playback.push_audio_sample(samples[index : index + 2400])
    playback.stop_playing()
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=2)
    return len(sent)


def test_playback_speed_changes_how_many_frames_go_out():
    normal, fast, slow = _frames(1.0), _frames(1.5), _frames(0.75)
    assert fast < normal < slow
    assert abs(fast - normal / 1.5) <= 3 and abs(slow - normal / 0.75) <= 3
    assert SimpleNamespace  # keep the import used


def test_robot_toml_unit_tables_take_speed_and_pitch():
    from maipai_body.config import UnitConfig

    unit = UnitConfig(device_id=KITCHEN, speech_speed=1.2, speech_pitch=-2)
    assert unit.settings() == {"speech_speed": 1.2, "speech_pitch": -2}
    with pytest.raises(ValueError, match="speed"):
        UnitConfig(device_id=KITCHEN, speech_speed=2.5)
