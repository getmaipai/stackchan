"""A pair code made by `stackchan pair` survives the CLI process."""

import json

from maipai_body.bodies.stackchan.xiaozhi import pairing as pairing_mod
from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore

DEVICE = "aa:bb:cc:dd:ee:01"
CLIENT = "11111111-2222-3333-4444-555555555555"


def test_code_made_in_one_process_redeems_in_another(tmp_path):
    path = tmp_path / "pairing.json"
    cli = PairingStore(path)
    code = cli.create_pair_code()
    server = PairingStore(path)  # a separate process would build its own store
    token = server.redeem_pair_code(DEVICE, CLIENT, code)
    assert token
    assert PairingStore(path).authorize(DEVICE, CLIENT, token)


def test_code_is_stored_as_a_digest_only(tmp_path):
    path = tmp_path / "pairing.json"
    code = PairingStore(path).create_pair_code()
    assert code not in path.read_text()


def test_code_works_once_across_processes(tmp_path):
    path = tmp_path / "pairing.json"
    code = PairingStore(path).create_pair_code()
    assert PairingStore(path).redeem_pair_code(DEVICE, CLIENT, code)
    assert PairingStore(path).redeem_pair_code("aa:bb:cc:dd:ee:02", CLIENT, code) is None


def test_expired_codes_are_pruned_and_the_list_is_capped(tmp_path):
    path = tmp_path / "pairing.json"
    store = PairingStore(path)
    store.create_pair_code(now=1000.0)
    for _ in range(pairing_mod.PAIR_CODE_LIMIT + 4):
        store.create_pair_code()
    stored = json.loads(path.read_text())["pair_codes"]
    assert len(stored) <= pairing_mod.PAIR_CODE_LIMIT
    assert all(item["expires_at"] > 2000.0 for item in stored.values())


def test_wrong_tries_are_counted_across_every_source_address(tmp_path):
    """five wrong codes close the window whoever sent them."""
    store = PairingStore(tmp_path / "p.json")
    real = store.create_pair_code()
    wrong = "000000" if real != "000000" else "000001"
    for number in range(pairing_mod.PAIR_CODE_GLOBAL_LIMIT):
        store.redeem_pair_code(DEVICE, CLIENT, wrong, source=f"198.51.100.{number}")
    assert store.redeem_pair_code(DEVICE, CLIENT, real, source="198.51.100.250") is None


def test_a_code_cannot_replace_a_paired_unit(tmp_path):
    """a redeem for an already paired Device-Id is refused; the owner unpairs it first."""
    store = PairingStore(tmp_path / "p.json")
    token = store.redeem_pair_code(DEVICE, CLIENT, store.create_pair_code())
    assert token
    assert store.redeem_pair_code(DEVICE, CLIENT, store.create_pair_code()) is None
    assert store.authorize(DEVICE, CLIENT, token)
