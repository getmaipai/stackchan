"""No-speech gate, local speech client and idle head movement (owner reports, 2026-11-16)."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from maipai_body.bodies.stackchan.head_gate import HeadMotionGate
from maipai_body.bodies.stackchan.power_idle import PowerIdle
from maipai_body.bodies.stackchan.turn import StackChanTurnBridge
from maipai_body.speech import noise_gate as gate
from maipai_body.speech.local_speech import LocalSttClient
from maipai_body.speech.stt_stream import SttStreamResult
from maipai_body.unit_settings import SettingsError, UnitSettingsStore

RATE = 16000
SECONDS = 3


def _rng():
    return np.random.default_rng(7)


def fan_white():
    return _rng().normal(0, 0.05, RATE * SECONDS).astype(np.float32)


def fan_rumble():
    walk = np.cumsum(_rng().normal(0, 0.01, RATE * SECONDS))
    return (walk - np.convolve(walk, np.ones(800) / 800, "same")).astype(np.float32)


def voice():
    t = np.arange(RATE * SECONDS) / RATE
    phase = np.cumsum(120 + 20 * np.sin(2 * np.pi * 3 * t)) / RATE * 2 * np.pi
    tone = sum(np.sin(k * phase) / k for k in range(1, 12))
    envelope = np.clip(np.sin(2 * np.pi * 2.5 * t), 0, 1) ** 0.7
    return (0.12 * tone * envelope + _rng().normal(0, 0.004, t.size)).astype(np.float32)


@pytest.mark.parametrize(
    ("noise", "level"),
    [(fan_white, lv) for lv in gate.LEVELS] + [(fan_rumble, "medium"), (fan_rumble, "high")],
)
def test_steady_fan_noise_is_dropped(noise, level):
    # "low" lets a rumbling fan through on purpose: it only drops hiss and flat noise.
    verdict = gate.check_audio(noise(), level)
    assert not verdict.keep
    assert "steady" in verdict.reason or "voiced" in verdict.reason


@pytest.mark.parametrize("level", gate.LEVELS)
def test_speech_is_kept_and_a_blip_is_not(level):
    assert gate.check_audio(voice(), level).keep
    assert not gate.check_audio(voice()[:3000], level).keep


def test_speech_over_a_fan_is_kept():
    assert gate.check_audio(voice() + fan_white() * 0.5, "medium").keep


@pytest.mark.parametrize(
    "text",
    ["Thank you.", "you", "Bye!", "...", "  ", "okay okay okay", "Thanks for watching"],
)
def test_noise_phrases_are_dropped(text):
    assert not gate.check_text(text).keep


def test_real_sentences_and_spanish_list():
    assert gate.check_text("what is the weather today").keep
    assert not gate.check_text("Gracias.", "es").keep
    assert gate.check_text("gracias por la ayuda con la cena", "es").keep


class _Capture:
    """Hands out 32 ms blocks of a prepared signal, then reports closed."""

    def __init__(self, samples):
        self.blocks = [samples[i : i + 512] for i in range(0, len(samples) - 511, 512)]
        self.closed = False

    def poll_blocks(self):
        if not self.blocks:
            self.closed = True
            return [np.zeros(512, dtype=np.float32)]
        out, self.blocks = self.blocks[:8], self.blocks[8:]
        return out


def test_local_stt_never_sends_fan_noise(monkeypatch):
    posts = []
    session = SimpleNamespace(post=lambda *a, **k: posts.append(k))
    client = LocalSttClient("http://127.0.0.1:1", session=session)
    result = client.run(_Capture(fan_white()), patience_s=0.05)
    assert result.kind == "no_speech" and posts == []


def test_local_stt_sends_speech_once_and_returns_text():
    seen = []

    def post(url, **kwargs):
        seen.append(url)
        return SimpleNamespace(
            raise_for_status=lambda: None, json=lambda: {"text": "turn on the light"}
        )

    client = LocalSttClient("http://127.0.0.1:1/v1", session=SimpleNamespace(post=post))
    quiet = np.zeros(RATE // 2, dtype=np.float32)
    result = client.run(
        _Capture(np.concatenate([quiet, voice(), quiet, quiet, quiet])), patience_s=30
    )
    assert result.kind == "final" and result.text == "turn on the light"
    assert seen == ["http://127.0.0.1:1/v1/audio/transcriptions"]


def _bridge(level="medium"):
    store = SimpleNamespace(get=lambda _d: {"ignore_noise": level})
    return SimpleNamespace(
        units=SimpleNamespace(store=store),
        language="en",
        dropped_utterances=0,
        audio_noise_gate=True,
        _noise_level=lambda d: StackChanTurnBridge._noise_level(
            SimpleNamespace(units=SimpleNamespace(store=store)), d
        ),
    )


def test_bridge_drops_and_counts_a_noise_utterance(caplog):
    bridge = _bridge()
    caplog.set_level("INFO")
    dropped = StackChanTurnBridge._gate_result(
        bridge, SttStreamResult(kind="final", text="Thank you.", audio=voice()), "aa:bb:cc:dd:ee:01"
    )
    assert dropped.kind == "no_speech" and bridge.dropped_utterances == 1
    assert "dropped an utterance" in caplog.text
    kept = StackChanTurnBridge._gate_result(
        bridge,
        SttStreamResult(kind="final", text="what time is it", audio=voice()),
        "aa:bb:cc:dd:ee:01",
    )
    assert kept.kind == "final"
    steady = StackChanTurnBridge._gate_result(
        bridge,
        SttStreamResult(kind="final", text="what time is it", audio=fan_white()),
        "aa:bb:cc:dd:ee:01",
    )
    assert steady.kind == "no_speech"


def test_noise_and_idle_settings_are_checked(tmp_path):
    store = UnitSettingsStore(tmp_path / "units.json")
    unit = "aa:bb:cc:dd:ee:01"
    store.update(unit, {"ignore_noise": "high", "idle_movement": "lively"})
    assert store.get(unit)["ignore_noise"] == "high"
    with pytest.raises(SettingsError):
        store.update(unit, {"idle_movement": "wild"})
    with pytest.raises(SettingsError):
        store.update(unit, {"ignore_noise": "max"})


def _idle_run(level, busy=""):
    now = [0.0]
    clock = lambda: now[0]  # noqa: E731
    writes = []
    state = {"level": level}
    power = PowerIdle(writes.append, configured_level=lambda: state["level"], clock=clock)
    head_gate = HeadMotionGate(
        must_be_still=lambda: power.still, busy=lambda: busy, clock=clock, log_every_s=1e9
    )
    power.on_battery_status(charging=False)
    moves = 0
    for second in range(600):  # ten simulated minutes
        now[0] = float(second)
        if second % 60 == 0:
            power.on_battery_status(charging=False)
        power.tick()
        if head_gate.allow("ambient:wander"):  # the idle looks ask every second
            moves += 1
    return moves, writes


def test_ten_idle_minutes_off_sends_no_head_command():
    moves, writes = _idle_run("still")
    assert moves == 0
    assert True not in writes  # the unit's own idle motion is never switched on


def test_lively_moves_when_free_but_never_while_busy():
    moves, writes = _idle_run("lively")
    assert moves > 0 and True in writes
    busy_moves, _ = _idle_run("lively", busy="a turn is listening or speaking")
    assert busy_moves == 0


def test_a_turn_still_gets_its_answering_moves():
    gate_ = HeadMotionGate(must_be_still=lambda: True, busy=lambda: "a turn")
    assert gate_.allow("turn:listening", response=True)


TIRED = ["I'm tired", "I am so tired", "I need rest", "I'm retired", "are you tired"]


@pytest.mark.parametrize("sentence", TIRED)
def test_tired_sentences_fire_no_local_command(sentence):
    from maipai_body.bodies.stackchan import brightness, head_commands, stop_phrases, volume
    from maipai_body.link.commands import route_phrase

    assert route_phrase(sentence) is None
    assert volume.parse_volume_command(sentence) is None
    assert brightness.parse_brightness_command(sentence) is None
    assert head_commands.parse_head_command(sentence) is None
    assert not stop_phrases.is_stop_phrase(sentence)


def test_a_command_phrase_needs_high_confidence():
    from maipai_body.link.commands import LocalCommand, route_phrase

    assert route_phrase("What time is it?", 0.95) is LocalCommand.TIME
    assert route_phrase("what time is it", 0.4) is None
    assert route_phrase("what time is it going to be") is None
    assert route_phrase("I'm tired, what time is it") is None


def test_the_route_of_a_tired_sentence_is_chat():
    bridge = SimpleNamespace(volume_control=object(), brightness_control=object(), head_control=object())
    route, _why = StackChanTurnBridge._route_of(bridge, "I am so tired", "speech")
    assert route == "chat"
