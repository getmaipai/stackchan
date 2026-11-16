"""The 2026-11-16 latency patches (L01, L03 to L09): listed in ORDER, documented, and carrying the settings they promise."""
from pathlib import Path

PATCHES = Path(__file__).resolve().parents[2] / "firmware" / "patches"
NAMES = [
    "L01-wake-no-echo-reference.patch",
    "L03-followup-window-8s.patch",
    "L04-ignore-idle-host-looks.patch",
    "L05-wake-det-mode-95.patch",
    "L06-bench-latency-trace.patch",
    "L07-privacy-source-and-touch-debounce.patch",
    "L08-no-connecting-flash.patch",
    "L09-stop-word-not-probed.patch",
]


def _text(name: str) -> str:
    return (PATCHES / name).read_text()


def test_listed_in_order_after_r04():
    order = (PATCHES / "ORDER").read_text().split()
    assert order.index("R04-restart-guard-back-off.patch") < order.index(NAMES[0])
    assert order[-len(NAMES):] == NAMES


def test_each_patch_is_documented():
    for name in NAMES:
        head = _text(name).split("diff --git", 1)[0]
        for key in ("# Intent:", "# Placement:", "# Upstream:"):
            assert key in head, (name, key)


def test_wake_front_end_has_no_echo_canceller():
    body = _text(NAMES[0])
    assert "+    afe_config->aec_init = false;" in body
    assert "push_back('N')" in body


def test_followup_window_is_eight_seconds():
    body = _text(NAMES[1])
    assert "kFollowUpListenSeconds = 8;" in body
    assert "held >= kFollowUpListenSeconds" in body


def test_wake_trigger_is_stricter():
    assert "DET_MODE_95" in _text(NAMES[3])


def test_idle_host_look_is_ignored_only_when_idle_and_off():
    body = _text(NAMES[2])
    assert "IsIdleMotionEnabled()" in body and "kDeviceStateIdle" in body


def test_bench_code_is_behind_the_bench_switch():
    body = _text(NAMES[4])
    assert "CONFIG_MAIPAI_SERIAL_TOOLS" in body
    assert "self.bench.inject" in body


def test_touch_glitch_debounce_and_source_log():
    body = _text(NAMES[5])
    assert "MTC_TAP_MIN_MS 70" in body and "source %s" in body and "ESP_LOGW" in body


def test_connecting_text_only_when_channel_must_open():
    assert "IsAudioChannelOpened()" in _text(NAMES[6])


def test_stop_word_probe_is_off():
    assert "kStopWordProbe = false" in _text(NAMES[7])
