from __future__ import annotations

import ast
from pathlib import Path

import pytest

from maipai_body.brain.own_llm import NOT_INSTALLED
from maipai_body.config import RobotConfig, build_brain, load_config


def test_alias_and_defaults() -> None:
    config = RobotConfig.model_validate({"brain": "standalone"})
    assert config.brain == "llm"
    assert config.remote.enabled is False
    assert build_brain(config).stream_turn(None).__next__().reply_text == NOT_INSTALLED


def test_home_selection() -> None:
    assert build_brain(RobotConfig(brain="home")).__class__.__name__ == "HomeBrain"


def test_unknown_key_names_key_and_action(tmp_path: Path) -> None:
    path = tmp_path / "robot.toml"
    path.write_text("[llm]\nmodel = 'm'\nsecret = 'x'\n", encoding="utf-8")
    with pytest.raises(ValueError, match="llm.secret.*Correct or remove"):
        load_config(path)


def test_first_run_copies_example(tmp_path: Path, capsys) -> None:
    path = tmp_path / "robot.toml"
    assert load_config(path).brain == "llm"
    assert path.exists()
    assert str(path) in capsys.readouterr().out


def test_own_brain_has_no_home_imports() -> None:
    root = Path(__file__).parents[1] / "maipai_body" / "brain"
    for file in root.glob("own_llm*.py"):
        tree = ast.parse(file.read_text(encoding="utf-8"))
        imported = [
            node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        ]
        imported += [
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        ]
        assert not any("home" in name.lower() or "hub" in name.lower() for name in imported)
