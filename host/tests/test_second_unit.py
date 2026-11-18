"""A second connected unit must not break every call that names no unit."""

import pytest

from maipai_body.bodies.stackchan.xiaozhi.server import XiaozhiServer
from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore


def _server(tmp_path, sessions):
    server = XiaozhiServer(PairingStore(tmp_path / "p.json"), robot=None)
    server._sessions = dict(sessions)
    return server


def test_no_unit_named_with_two_connected_uses_the_longest_connected(tmp_path):
    server = _server(tmp_path, {"aa:bb:cc:dd:ee:01": "ws1", "aa:bb:cc:dd:ee:02": "ws2"})
    assert server._resolve_unit(None) == ("aa:bb:cc:dd:ee:01", "ws1")


def test_a_named_unit_is_used_even_when_it_is_the_second(tmp_path):
    server = _server(tmp_path, {"aa:bb:cc:dd:ee:01": "ws1", "aa:bb:cc:dd:ee:02": "ws2"})
    assert server._resolve_unit("aa:bb:cc:dd:ee:02") == ("aa:bb:cc:dd:ee:02", "ws2")


def test_no_unit_connected_and_unknown_unit_say_what_to_do(tmp_path):
    server = _server(tmp_path, {})
    with pytest.raises(ConnectionError, match="No StackChan is connected"):
        server._resolve_unit(None)
    server = _server(tmp_path, {"aa:bb:cc:dd:ee:01": "ws1"})
    with pytest.raises(ConnectionError, match="not connected"):
        server._resolve_unit("aa:bb:cc:dd:ee:09")
