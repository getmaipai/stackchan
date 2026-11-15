from __future__ import annotations

import uuid
from pathlib import Path

from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore

DEVICE = "aa:bb:cc:dd:ee:ff"
CLIENT = str(uuid.uuid4())


def test_pair_code_expiry_one_use_and_token(tmp_path: Path) -> None:
    store = PairingStore(tmp_path / "pairing.json")
    code = store.create_pair_code(now=100)
    assert store.redeem_pair_code(DEVICE, CLIENT, code, now=701) is None
    code = store.create_pair_code(now=100)
    token = store.redeem_pair_code(DEVICE, CLIENT, code, now=101)
    assert token
    assert store.authorize(DEVICE, CLIENT, token)
    assert store.redeem_pair_code(DEVICE, CLIENT, code, now=102) is None


def test_pair_code_attempt_limit(tmp_path: Path) -> None:
    store = PairingStore(tmp_path / "pairing.json")
    code = store.create_pair_code(now=100)
    for _ in range(5):
        assert store.redeem_pair_code(DEVICE, CLIENT, "bad", source="unit", now=101) is None
    assert store.redeem_pair_code(DEVICE, CLIENT, code, source="unit", now=102) is None


def test_cli_status_output(tmp_path: Path, monkeypatch, capsys) -> None:
    from maipai_body import cli
    from maipai_body.config import RobotConfig

    path = tmp_path / "robot.toml"
    path.write_text('brain = "home"\n', encoding="utf-8")
    store = PairingStore(tmp_path / "pairing.json")
    code = store.create_pair_code()
    store.redeem_pair_code(DEVICE, CLIENT, code)
    monkeypatch.setattr("sys.argv", ["stackchan", "status"])
    monkeypatch.setattr(cli, "load_config", lambda: RobotConfig(brain="home"))
    monkeypatch.setattr(cli, "default_pairing_path", lambda: tmp_path / "pairing.json")
    assert cli.main() == 0
    output = capsys.readouterr().out
    assert "Brain: home" in output
    assert "Paired units: 1" in output
    assert DEVICE in output
