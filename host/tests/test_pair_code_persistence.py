"""HC-2, HS-5: a pair code made by `stackchan pair` survives the CLI process."""

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
