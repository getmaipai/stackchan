"""The host half of the link key exchange (docs/plan/link-key-exchange.md), against the reference vectors in scripts/link-key-vector.py."""

import importlib.util
from pathlib import Path

import pytest

from maipai_body.bodies.stackchan.xiaozhi import link_exchange as lx

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("link_key_vector", ROOT / "scripts" / "link-key-vector.py")
ref = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ref)

DEVICE = ref.DEVICE


def test_x25519_matches_rfc_7748_and_the_reference():
    k = bytes.fromhex("a546e36bf0527c9d3b16154b82465edd62144c0ac1fc5a18506a2244ba449ac4")
    u = bytes.fromhex("e6db6867583030db3594c1a424b15f7c726624ec26b3353b10a903a6d0ab1c4c")
    assert lx.x25519(k, u).hex() == "c3da55379de9c6908e94ea4df28d084f32eccf03491c71f754b4075577a28552"
    assert lx.x25519(ref.SK_U, lx.BASE) == ref.x25519(ref.SK_U, ref.BASE)


def test_the_key_schedule_matches_the_fixed_reference_exchange():
    expected = ref.exchange()
    pk_u, pk_h = lx.x25519(ref.SK_U, lx.BASE), lx.x25519(ref.SK_H, lx.BASE)
    assert (pk_u, pk_h) == (expected["pk_u"], expected["pk_h"])
    z = lx.x25519(ref.SK_H, pk_u)
    assert z == expected["z"]
    assert lx.commit(pk_h, pk_u, ref.N_H) == expected["commit"]
    assert lx.sas(pk_u, pk_h, ref.N_U, ref.N_H) == expected["sas"]
    k = lx.link_key(z, pk_u, pk_h, ref.N_U, ref.N_H, DEVICE)
    assert k == expected["K"]
    assert lx.psk_from_key(k, DEVICE) == expected["psk"]
    assert lx.psk_from_key(k, DEVICE.upper()) == expected["psk"]  # the identity is lower-cased


def _run(ex: lx.HostExchange, device=DEVICE, sk_u=ref.SK_U, n_u=ref.N_U, sas_override=None):
    pk_u = lx.x25519(sk_u, lx.BASE)
    reply = ex.start(device, pk_u)
    pk_h, c = reply["pk_h"], reply["c"]
    n_h = ex.reveal(n_u)["n_h"]
    assert lx.commit(pk_h, pk_u, n_h) == c  # what the unit checks
    return pk_u, pk_h, n_h


def test_a_full_exchange_with_the_right_code_gives_both_sides_the_same_key():
    ex = lx.HostExchange(rand=lambda n: ref.N_H if n == 16 else ref.SK_H)
    pk_u, pk_h, n_h = _run(ex)
    code = lx.sas(pk_u, pk_h, ref.N_U, n_h)
    key = ex.approve(code)
    z = lx.x25519(ref.SK_U, pk_h)  # the unit's side
    assert key == lx.link_key(z, pk_u, pk_h, ref.N_U, n_h, DEVICE)
    assert ex.finished and not ex.keys_held()  # the host drops its ephemeral secrets


def test_a_wrong_code_aborts_counts_and_drops_the_keys():
    ex = lx.HostExchange()
    _run(ex)
    with pytest.raises(lx.ExchangeError, match="did not match"):
        ex.approve("000000" if ex.expected != "000000" else "111111")
    assert ex.aborted and not ex.keys_held()
    with pytest.raises(lx.ExchangeError):  # the same exchange cannot be tried again
        ex.approve(ex.expected)


def test_the_code_is_six_digits_with_leading_zeros_and_input_is_checked():
    assert len(lx.sas(b"\x00" * 32, b"\x01" * 32, b"\x02" * 16, b"\x03" * 16)) == 6
    ex = lx.HostExchange()
    _run(ex)
    for bad in ("12345", "1234567", "abcdef", "", " 123456"):
        with pytest.raises(lx.ExchangeError):
            ex.approve(bad)
    assert ex.aborted


def test_messages_out_of_order_or_with_bad_sizes_are_refused():
    ex = lx.HostExchange()
    with pytest.raises(lx.ExchangeError):
        ex.reveal(b"\x00" * 16)  # nonce before pair_start
    with pytest.raises(lx.ExchangeError):
        ex.start(DEVICE, b"\x00" * 31)
    ex2 = lx.HostExchange()
    ex2.start(DEVICE, lx.x25519(ref.SK_U, lx.BASE))
    with pytest.raises(lx.ExchangeError):
        ex2.reveal(b"\x00" * 15)
    with pytest.raises(lx.ExchangeError):  # a second pair_start on the same exchange
        ex2.start(DEVICE, lx.x25519(ref.SK_U, lx.BASE))


def test_a_low_order_public_key_is_refused():
    ex = lx.HostExchange()
    with pytest.raises(lx.ExchangeError, match="key"):
        ex.start(DEVICE, b"\x00" * 32)  # the all-zero point gives an all-zero shared secret


def test_exchanges_expire():
    now = [0.0]
    ex = lx.HostExchange(clock=lambda: now[0])
    _run(ex)
    now[0] += lx.EXCHANGE_TTL_S + 1
    with pytest.raises(lx.ExchangeError, match="too long"):
        ex.approve(ex.expected)


def test_the_registry_limits_tries_per_source_and_keeps_one_exchange_per_unit():
    now = [0.0]
    reg = lx.ExchangeRegistry(clock=lambda: now[0])
    for _ in range(lx.MAX_WRONG_CODES):
        ex = reg.begin(DEVICE, lx.x25519(ref.SK_U, lx.BASE))
        reg.reveal(DEVICE, ref.N_U)
        with pytest.raises(lx.ExchangeError):
            reg.approve(DEVICE, "999999" if ex.expected != "999999" else "888888", "127.0.0.1", True)
    reg.begin(DEVICE, lx.x25519(ref.SK_U, lx.BASE))
    reg.reveal(DEVICE, ref.N_U)
    with pytest.raises(lx.ExchangeError, match="Wait"):
        reg.approve(DEVICE, "123456", "127.0.0.1", True)  # this source has used its tries
    other = reg.begin("02:00:5E:00:53:02", lx.x25519(ref.SK_U, lx.BASE))
    assert other is not None  # another unit is not held back
    now[0] += lx.LOCK_S + 1
    assert reg.pending_devices() == []  # the unit's exchange timed out with nobody finishing it


def test_a_strangers_wrong_codes_never_lock_the_owner_out():
    reg = lx.ExchangeRegistry()
    ex = reg.begin(DEVICE, lx.x25519(ref.SK_U, lx.BASE))
    reg.reveal(DEVICE, ref.N_U)
    for _ in range(lx.MAX_WRONG_CODES + 2):  # a stranger guesses; it cannot end the owner's exchange either
        with pytest.raises(lx.ExchangeError):
            reg.approve(DEVICE, "000000" if ex.expected != "000000" else "111111", "192.0.2.50", False)
    assert reg.approve(DEVICE, ex.expected, "127.0.0.1", True)  # the owner's right code still pairs


def test_many_strangers_together_are_capped_and_the_owner_is_not():
    reg = lx.ExchangeRegistry()
    ex = reg.begin(DEVICE, lx.x25519(ref.SK_U, lx.BASE))
    reg.reveal(DEVICE, ref.N_U)
    wrong = "000000" if ex.expected != "000000" else "111111"
    for n in range(lx.OUTSIDE_WRONG_CODES):
        with pytest.raises(lx.ExchangeError):
            reg.approve(DEVICE, wrong, f"192.0.2.{n + 1}", False)
    with pytest.raises(lx.ExchangeError, match="other computers"):
        reg.approve(DEVICE, ex.expected, "192.0.2.99", False)  # a new stranger is refused even with the right code: the cap is reached
    assert reg.approve(DEVICE, ex.expected, "127.0.0.1", True)


# ---- storing the key and deriving the TLS key from it ---------------------------------------------------------------

def test_the_link_key_is_stored_in_the_pairing_file_and_the_token_digest_is_not_kept(tmp_path):
    import json
    import stat

    from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore

    path = tmp_path / "pairing.json"
    store = PairingStore(path)
    key = bytes(range(32))
    store.store_link_key(DEVICE, "11111111-2222-3333-4444-555555555555", key)
    record = json.loads(path.read_text())["devices"][DEVICE.lower()]
    assert record["link_key_hex"] == key.hex() and record["link_encryption"] == "required"
    assert "token_sha256" not in record
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert PairingStore(path).link_key(DEVICE) == key
    assert store.authorize_link(DEVICE, "11111111-2222-3333-4444-555555555555")
    assert not store.authorize_link(DEVICE, "99999999-2222-3333-4444-555555555555")
    assert not store.authorize_link("aa:bb:cc:dd:ee:99", "11111111-2222-3333-4444-555555555555")


def test_the_tls_key_comes_from_the_link_key_and_never_from_a_token(tmp_path):
    from maipai_body.bodies.stackchan.xiaozhi.link_security import LinkSecurity
    from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore

    store = PairingStore(tmp_path / "p.json")
    key = ref.exchange()["K"]
    store.store_link_key(DEVICE, "11111111-2222-3333-4444-555555555555", key)
    assert LinkSecurity(store).psk_for_identity(DEVICE.lower()) == ref.exchange()["psk"]
    assert LinkSecurity(store).psk_for_identity("aa:bb:cc:dd:ee:99") == b""


def test_a_unit_paired_the_old_way_still_gets_its_old_key(tmp_path):
    from maipai_body.bodies.stackchan.xiaozhi.link_security import LinkSecurity, derive_psk
    from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore

    store = PairingStore(tmp_path / "p.json")
    token = store.redeem_pair_code("aa:bb:cc:dd:ee:05", "11111111-2222-3333-4444-555555555555", store.create_pair_code())
    digest = store.link_material("aa:bb:cc:dd:ee:05")
    assert LinkSecurity(store).psk_for_identity("aa:bb:cc:dd:ee:05") == derive_psk(digest, "aa:bb:cc:dd:ee:05") and token


def test_the_page_routes_take_the_six_digits_and_report_a_mismatch(tmp_path):
    from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore
    from maipai_body.settings_page import TOKEN_ACCESS
    from maipai_body.settings_sim import build

    class Voice:
        def __init__(self):
            self.pairing = PairingStore(tmp_path / "pairing.json")
            self.exchange = lx.ExchangeRegistry()

        def waiting_exchanges(self):
            return self.exchange.pending_devices()

        def approve_exchange(self, device_id, code, source="", reserved=True):
            key = self.exchange.approve(device_id, code, source, reserved)
            self.pairing.store_link_key(device_id, self.exchange.client_ids[device_id.lower()], key)

    voice = Voice()
    backend, _ = build(tmp_path)
    backend.pair_exchange = voice
    pk_u = lx.x25519(ref.SK_U, lx.BASE)
    exchange = voice.exchange.begin(DEVICE, pk_u, "11111111-2222-3333-4444-555555555555")
    voice.exchange.reveal(DEVICE, ref.N_U)
    assert json_of(backend.route_get("/api/stackchan/pairings/waiting", "en", True)[2]) == {"waiting": [DEVICE.lower()]}
    assert backend.route_get("/api/stackchan/pairings/waiting", "en", TOKEN_ACCESS)[0] == 403  # a phone cannot see or approve
    assert backend.route_post("/api/stackchan/pairings/code-entry", {"device_id": DEVICE, "code": exchange.expected}, TOKEN_ACCESS)[0] == 403
    status, payload = backend.route_post("/api/stackchan/pairings/code-entry", {"device_id": DEVICE, "code": "12ab56"}, True)
    assert status == 400 and "did not match" in payload["error"]
    assert voice.pairing.link_key(DEVICE) is None
    exchange2 = voice.exchange.begin(DEVICE, pk_u, "11111111-2222-3333-4444-555555555555")
    voice.exchange.reveal(DEVICE, ref.N_U)
    status, payload = backend.route_post("/api/stackchan/pairings/code-entry", {"device_id": DEVICE, "code": exchange2.expected}, True)
    assert status == 200 and voice.pairing.link_key(DEVICE) is not None


def json_of(raw):
    import json

    return json.loads(raw)
