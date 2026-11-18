"""The robot.toml switches [remote] enabled and [home] url do something."""

from maipai_body import app, config
from maipai_body.remote_activity import RemoteStore


def _toml(monkeypatch, tmp_path, text):
    path = tmp_path / "robot.toml"
    path.write_text(text)
    monkeypatch.setattr(config, "example_config_path", lambda: path)


def test_remote_enabled_false_in_robot_toml_keeps_remote_access_off(monkeypatch, tmp_path):
    _toml(monkeypatch, tmp_path, "[remote]\nenabled = false\n")
    store = RemoteStore(tmp_path / "r.json", forced_off=app._remote_forced_off)
    store.update({"enabled": True})
    assert store.settings()["enabled"] is False


def test_remote_unset_lets_the_settings_page_decide(monkeypatch, tmp_path):
    _toml(monkeypatch, tmp_path, 'brain = "llm"\n')
    store = RemoteStore(tmp_path / "r.json", forced_off=app._remote_forced_off)
    store.update({"enabled": True})
    assert store.settings()["enabled"] is True


def test_home_url_in_robot_toml_is_the_hub_address(monkeypatch, tmp_path):
    monkeypatch.setenv("MAIPAI_BODY", "stackchan")
    monkeypatch.delenv("MAIPAI_HUB_URL", raising=False)
    monkeypatch.delenv("MAIPAI_HUB_HOST", raising=False)
    _toml(monkeypatch, tmp_path, 'brain = "llm"\n[home]\nurl = "http://192.0.2.9:3000"\n')
    assert app._configured_hub_url() == "http://192.0.2.9:3000"
    assert not app._no_hub_configured()
