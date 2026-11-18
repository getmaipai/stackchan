"""a standalone checkout resolves the shared spec from the vendored snapshot."""

from pathlib import Path

import pytest

from maipai_body import spec_pin


@pytest.fixture(autouse=True)
def _no_outside_spec(monkeypatch):
    monkeypatch.delenv("MAIPAI_SPEC_DIR", raising=False)


def test_spec_root_falls_back_to_vendored_snapshot():
    root = spec_pin.spec_root()
    assert (root / "vocab" / "robot-api.json").is_file()
    assert (root / "voice" / "py" / "normalize_for_speech.py").is_file()
    assert (root / "records" / "py" / "validate.py").is_file()


def test_env_override_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("MAIPAI_SPEC_DIR", str(tmp_path))
    assert spec_pin.spec_root() == Path(tmp_path)


def test_robot_api_loads_without_outside_spec():
    from maipai_body.robot.api import load_robot_api

    assert load_robot_api().parts


def test_manifest_payload_and_normalizer_work_without_outside_spec():
    from maipai_body.bodies.stackchan.firmware.flash_manifest import signing_payload
    from maipai_body.speech.normalize import load_normalizer

    assert signing_payload  # import resolves
    assert callable(load_normalizer())


def test_asset_pins_use_vendored_snapshot():
    from maipai_body.link import assets

    assert assets.SPEC_ASSETS_PATH.is_file()
