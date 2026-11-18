"""The wake word maker: clips are validated, training runs end to end on synthetic audio, install records the model, off means off."""

import io
import json
import wave
from pathlib import Path

import numpy as np
import pytest

from maipai_packages.wake_word_maker import ClipError, WakeStore, WakeWordMaker

ROOT = Path(__file__).resolve().parents[2]


def _wav(samples: np.ndarray, rate=16000, width=2, channels=1) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes((np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes())
    return out.getvalue()


def _word(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.arange(16000) / 16000
    return (0.4 * np.sin(2 * np.pi * (500 + 40 * rng.random()) * t) * np.sin(np.pi * t)).astype(np.float32)


def _other(seed: int) -> np.ndarray:
    rng = np.random.default_rng(1000 + seed)
    return (0.2 * rng.standard_normal(16000)).astype(np.float32)


def test_only_good_clips_are_stored(tmp_path):
    store = WakeStore(tmp_path)
    assert store.add_clip("alpha", "positive", _wav(_word(1))) == 1
    for bad, why in ((b"not a wav", "not a WAV"), (_wav(_word(1), rate=8000), "mono, 16-bit"), (_wav(_word(1)[:2000]), "about one second"), (_wav(np.zeros(40000)), "about one second")):
        with pytest.raises(ClipError, match=why):
            store.add_clip("alpha", "positive", bad)
    with pytest.raises(ClipError):
        store.add_clip("../x", "positive", _wav(_word(1)))
    with pytest.raises(ClipError):
        store.add_clip("alpha", "maybe", _wav(_word(1)))


def test_training_needs_enough_clips(tmp_path):
    maker = WakeWordMaker(WakeStore(tmp_path), background=False)
    with pytest.raises(ClipError, match="at least"):
        maker.train("alpha")


def test_train_check_install_end_to_end_on_synthetic_audio(tmp_path):
    store = WakeStore(tmp_path)
    for i in range(14):
        store.add_clip("alpha", "positive", _wav(_word(i)))
        store.add_clip("alpha", "negative", _wav(_other(i)))
    maker = WakeWordMaker(store, background=False, clock=lambda: 1_000)
    state = maker.train("alpha")
    assert state["status"]["state"] == "done", state["status"]["message"]
    assert state["status"]["result"]
    record = maker.install("alpha")
    assert record["word"] == "alpha" and record["used_by_robot"] is False
    assert (tmp_path / "installed" / "alpha.npz").is_file() and (tmp_path / "installed" / "alpha.h").is_file()
    assert json.loads((tmp_path / "installed.json").read_text())["word"] == "alpha"


def test_install_before_training_is_refused(tmp_path):
    with pytest.raises(ClipError, match="Train and check"):
        WakeWordMaker(WakeStore(tmp_path)).install("alpha")


def test_the_package_copy_of_the_trainer_matches_the_scripts():
    for name in ("features", "make_dataset", "train_kws", "eval_kws"):
        script = (ROOT / "scripts" / "wakeword" / f"{name}.py").read_text()
        copy = (ROOT / "host" / "maipai_packages" / "wake_word_maker" / "engine" / f"{name}.py").read_text()
        norm = lambda text: text.replace("maipai_packages.wake_word_maker.engine.", "")  # noqa: E731
        assert norm(copy) == norm(script), f"{name}.py differs from scripts/wakeword/{name}.py: change both"


def test_it_is_off_by_default():
    from maipai_body.config import RobotConfig

    assert RobotConfig().packages.wake_word_maker.enabled is False


# ---- the settings page routes -----------------------------------------------------------------------------------

def _backend(tmp_path, on=True):
    from maipai_body.settings_sim import build

    backend, _ = build(tmp_path)
    if on:
        backend.wakeword = WakeWordMaker(WakeStore(tmp_path / "wakeword"), background=False)
    return backend


def _b64(samples):
    import base64

    return base64.b64encode(_wav(samples)).decode()


def test_the_routes_say_off_when_the_package_is_off(tmp_path):
    backend = _backend(tmp_path, on=False)
    status, _, body = backend.route_get("/api/stackchan/wakeword", "en", True)
    assert status == 200 and json.loads(body) == {"enabled": False}
    assert backend.route_post("/api/stackchan/wakeword/clip", {}, True) is None


def test_the_whole_flow_through_the_page_routes(tmp_path):
    backend = _backend(tmp_path)
    for i in range(13):
        assert backend.route_post("/api/stackchan/wakeword/clip", {"word": "alpha", "kind": "positive", "wav_b64": _b64(_word(i))}, True)[0] == 200
        assert backend.route_post("/api/stackchan/wakeword/clip", {"word": "alpha", "kind": "negative", "wav_b64": _b64(_other(i))}, True)[0] == 200
    status, payload = backend.route_post("/api/stackchan/wakeword/train", {"word": "alpha"}, True)
    assert status == 200 and payload["status"]["state"] == "done"
    status, payload = backend.route_post("/api/stackchan/wakeword/install", {"word": "alpha"}, True)
    assert status == 200 and payload["installed"]["word"] == "alpha"
    status, _, body = backend.route_get("/api/stackchan/wakeword/alpha", "en", True)
    assert json.loads(body)["installed"]["word"] == "alpha"
    assert backend.route_post("/api/stackchan/wakeword/clear", {"word": "alpha"}, True)[0] == 200


def test_only_the_host_computer_may_record_and_bad_input_is_a_plain_message(tmp_path):
    from maipai_body.settings_page import TOKEN_ACCESS

    backend = _backend(tmp_path)
    assert backend.route_post("/api/stackchan/wakeword/clip", {"word": "alpha", "kind": "positive", "wav_b64": _b64(_word(1))}, TOKEN_ACCESS)[0] == 403
    assert backend.route_get("/api/stackchan/wakeword/alpha", "en", TOKEN_ACCESS)[0] == 403
    status, payload = backend.route_post("/api/stackchan/wakeword/clip", {"word": "alpha", "kind": "positive", "wav_b64": "!!!"}, True)
    assert status == 400 and "did not arrive whole" in payload["error"]
    status, payload = backend.route_post("/api/stackchan/wakeword/clip", {"word": "Bad Word", "kind": "positive", "wav_b64": _b64(_word(1))}, True)
    assert status == 400 and "lowercase" in payload["error"]
