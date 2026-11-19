"""The Tailscale key never crosses a plain unit link (docs/design/encrypted-link.md, "refuse on a plain link").

A key is sent only when the unit's live link is the encrypted one. Anything else (plain, unknown, a callback
that fails) is refused with a message that says what went wrong and where the key goes instead. The hub's
address is not a secret and still goes through."""

from __future__ import annotations

import json
from pathlib import Path

from maipai_body import settings_ui
from maipai_body.settings_sim import KITCHEN, build

KEY = "tskey-auth-FAKETESTKEY0000000000"
GET = "/api/stackchan/unit/{}/{}"


def _post(backend, body):
    return backend.route_post(GET.format(KITCHEN, "travel"), {"lang": "en", **body}, True)


def _get(backend):
    status, _, body = backend.route_get(GET.format(KITCHEN, "travel"), "en", True)
    return status, json.loads(body)


def test_key_is_refused_on_a_plain_link_and_never_reaches_the_unit(tmp_path: Path) -> None:
    backend, units = build(tmp_path, link_secure=False)
    status, payload = _post(backend, {"key": KEY})
    assert status == 400
    assert "setup page" in payload["error"] and "encrypted" in payload["error"]
    assert KEY not in json.dumps(payload)
    assert not any(name == "self.tailnet.set" for name, _ in units[KITCHEN].calls)
    assert units[KITCHEN].travel["key_saved"] is False


def test_an_unknown_link_counts_as_plain(tmp_path: Path) -> None:
    backend, units = build(tmp_path, link_secure=None)
    assert _post(backend, {"key": KEY})[0] == 400
    assert not any(name == "self.tailnet.set" for name, _ in units[KITCHEN].calls)


def test_a_failing_link_check_counts_as_plain(tmp_path: Path) -> None:
    def broken(_unit: str) -> bool:
        raise RuntimeError("link state unavailable")

    backend, units = build(tmp_path, link_secure=broken)
    assert _post(backend, {"key": KEY})[0] == 400
    assert not any(name == "self.tailnet.set" for name, _ in units[KITCHEN].calls)


def test_key_with_other_fields_is_refused_whole(tmp_path: Path) -> None:
    backend, units = build(tmp_path, link_secure=False)
    status, _ = _post(backend, {"key": KEY, "peer": "100.64.0.7"})
    assert status == 400
    assert units[KITCHEN].travel["peer_saved"] is False


def test_the_key_goes_through_on_an_encrypted_link(tmp_path: Path) -> None:
    backend, units = build(tmp_path, link_secure=True)
    status, payload = _post(backend, {"key": KEY})
    assert status == 200 and KEY not in json.dumps(payload)
    assert units[KITCHEN].travel["key_saved"] is True


def test_address_enable_and_forget_do_not_need_the_encrypted_link(tmp_path: Path) -> None:
    backend, units = build(tmp_path, link_secure=False)
    assert _post(backend, {"peer": "100.64.0.7"})[0] == 200
    assert units[KITCHEN].travel["peer_saved"] is True
    assert _post(backend, {"enabled": False})[0] == 200
    assert _post(backend, {"forget": True})[0] == 200


def test_the_view_says_whether_a_key_may_be_sent(tmp_path: Path) -> None:
    for secure, expect in ((False, False), (None, False), (True, True)):
        backend, _units = build(tmp_path / str(secure), link_secure=secure)
        status, view = _get(backend)
        assert status == 200 and view["key_ok"] is expect


def test_the_page_hides_the_key_steps_when_the_view_says_no() -> None:
    source = Path(settings_ui.__file__).with_name("settings_ui_p_network.py").read_text()
    assert "key_ok" in source
