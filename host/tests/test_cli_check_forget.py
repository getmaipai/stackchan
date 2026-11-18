"""`stackchan check` and `stackchan forget` exist, as the user docs say."""

import sys

import pytest

from maipai_body import cli, config
from maipai_body.bodies.stackchan.xiaozhi import pairing
from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore


class _Resp:
    def __init__(self, status):
        self.status_code = status


def _run(monkeypatch, tmp_path, argv, toml):
    path = tmp_path / "robot.toml"
    path.write_text(toml)
    monkeypatch.setattr(config, "example_config_path", lambda: path)
    monkeypatch.setattr(pairing, "default_pairing_path", lambda: tmp_path / "p.json")
    monkeypatch.setattr(cli, "default_pairing_path", lambda: tmp_path / "p.json")
    monkeypatch.setattr(sys, "argv", ["stackchan", *argv])
    return cli.main()


def test_check_reports_each_address(monkeypatch, tmp_path, capsys):
    seen = []

    def fake_get(url, **kw):
        seen.append(url)
        if "9999" in url:
            raise cli.requests.ConnectionError("refused")
        return _Resp(200)

    monkeypatch.setattr(cli.requests, "get", fake_get)
    code = _run(
        monkeypatch,
        tmp_path,
        ["check"],
        '[llm]\nurl = "http://192.0.2.5:8080/v1"\nstt_url = "http://192.0.2.5:9999"\n',
    )
    out = capsys.readouterr().out
    assert seen[0] == "http://192.0.2.5:8080/v1/models"
    assert "ok" in out and "stt_url" in out and "cannot be reached" in out
    assert code == 1


def test_check_without_a_model_address_says_what_to_set(monkeypatch, tmp_path, capsys):
    code = _run(monkeypatch, tmp_path, ["check"], 'brain = "llm"\n')
    assert "url" in capsys.readouterr().out
    assert code == 1


def test_forget_unpairs_every_unit(monkeypatch, tmp_path, capsys):
    store = PairingStore(tmp_path / "p.json")
    code_value = store.create_pair_code()
    assert store.redeem_pair_code("aa:bb:cc:dd:ee:01", "11111111-2222-3333-4444-555555555555", code_value)
    assert _run(monkeypatch, tmp_path, ["forget"], 'brain = "llm"\n') == 0
    assert PairingStore(tmp_path / "p.json").paired_devices() == {}
