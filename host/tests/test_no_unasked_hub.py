"""A host the owner did not point at a hub never discovers or pairs with one."""

from pathlib import Path

import pytest

from maipai_body import app, config


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.setenv("MAIPAI_BODY", "stackchan")
    monkeypatch.delenv("MAIPAI_HUB_HOST", raising=False)
    monkeypatch.delenv("MAIPAI_HUB_URL", raising=False)


def _config(monkeypatch, tmp_path: Path, text: str):
    path = tmp_path / "robot.toml"
    path.write_text(text)
    monkeypatch.setattr(config, "example_config_path", lambda: path)


def test_own_model_host_without_hub_flag_runs_no_hub_link(monkeypatch, tmp_path):
    monkeypatch.setenv("MAIPAI_BODY", "stackchan")
    _config(monkeypatch, tmp_path, 'brain = "llm"\n')
    assert app._no_hub_configured()


def test_home_brain_may_discover_a_hub(monkeypatch, tmp_path):
    _config(monkeypatch, tmp_path, 'brain = "home"\n')
    assert not app._no_hub_configured()


def test_explicit_hub_url_always_counts(monkeypatch, tmp_path):
    _config(monkeypatch, tmp_path, 'brain = "llm"\n')
    monkeypatch.setenv("MAIPAI_HUB_URL", "http://192.0.2.1:3000")
    assert not app._no_hub_configured()


def test_unreadable_config_means_no_hub(monkeypatch, tmp_path):
    _config(monkeypatch, tmp_path, "brain = [")
    assert app._no_hub_configured()
