"""The documented install path: `stackchan run` starts the host; the first-run config template ships."""

import sys

from maipai_body import cli, config


def test_example_config_template_is_found():
    assert config.example_template_path().is_file()


def test_first_run_creates_robot_toml(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "example_config_path", lambda: tmp_path / "robot.toml")
    cfg = config.load_config()
    assert (tmp_path / "robot.toml").is_file()
    assert cfg.brain == "llm"


def test_run_command_starts_the_stackchan_host(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        cli.os, "execv", lambda exe, argv: seen.update(exe=exe, argv=argv, body=cli.os.environ.get("MAIPAI_BODY"))
    )
    monkeypatch.setattr(sys, "argv", ["stackchan", "run"])
    cli.main()
    assert seen["argv"][1:] == ["-m", "maipai_body.app"]
    assert seen["body"] == "stackchan"
