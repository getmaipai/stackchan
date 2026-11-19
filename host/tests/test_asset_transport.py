"""The asset transport (firmware SF89 and SF90): the header bytes, the order of the calls, abort on any failure, and a pantry shelf reusing its slot with a higher version."""

from __future__ import annotations

import base64
import hashlib
import struct

import pytest

from maipai_body.asset_transport import HEADER_LEN, PIECE, AssetTransport, build_header


def parse(header: bytes) -> dict:
    return {
        "magic": header[:8], "version": struct.unpack_from("<I", header, 8)[0], "length": struct.unpack_from("<I", header, 12)[0], "sha": header[16:48], "board": header[48:56],
        "kind": header[56], "fmt": header[57], "flags": struct.unpack_from("<H", header, 58)[0], "min": struct.unpack_from("<I", header, 60)[0], "name": header[64:104].rstrip(b"\0").decode(),
        "code": header[104:112].rstrip(b"\0").decode(), "ram": struct.unpack_from("<I", header, 112)[0], "flash": struct.unpack_from("<I", header, 116)[0], "license": struct.unpack_from("<H", header, 120)[0],
        "author": struct.unpack_from("<H", header, 122)[0], "reserved": header[124:128],
    }


def test_the_header_has_every_field_where_the_firmware_reads_it():
    body = b"x" * 5000
    h = build_header(kind="pantry", body=body, name="pantry-joke-en", version=7, code="en", ram_bytes=160)
    assert len(h) == HEADER_LEN
    p = parse(h)
    assert p["magic"] == b"MPAH1\0\0\0" and p["version"] == 7 and p["length"] == 5000 and p["sha"] == hashlib.sha256(body).digest()
    assert p["board"] == b"m5cores3" and p["kind"] == 7 and p["fmt"] == 1 and p["name"] == "pantry-joke-en" and p["code"] == "en"
    assert p["ram"] == 160 and p["flash"] == 8192 and p["license"] == 1 and p["reserved"] == b"\0\0\0\0"
    for bad in (dict(kind="nope"), dict(name=""), dict(name="-bad"), dict(name="a" * 41), dict(version=0), dict(board_id=b"\0\0"), dict(license_id=0)):
        args = dict(kind="pantry", body=b"x", name="ok", version=1) | bad
        with pytest.raises(ValueError):
            build_header(**args)


class FakeUnit:
    def __init__(self, *, refuse_at=None, items=None, accept=100000):
        self.calls, self.received, self.refuse_at, self.items, self.accept = [], b"", refuse_at, items or [], accept

    def __call__(self, unit, tool, args):
        self.calls.append((tool, {k: (v if k not in ("header_b64", "b64") else len(v)) for k, v in args.items()}))
        if tool == "self.assets.list":
            return {"ok": True, "kinds": [{"kind": "pantry", "items": self.items}]}
        if tool == "self.assets.install":
            self.header = base64.b64decode(args["header_b64"])
            if self.refuse_at == "install":
                return {"ok": False, "code": "busy", "error": "A game is running. Try again when it ends."}
            return {"ok": True, "slot": args["slot"] if args["slot"] >= 0 else 2, "accept_bytes": self.accept, "piece_bytes": PIECE}
        if tool == "self.assets.data":
            assert args["at"] == len(self.received), "pieces arrive in order, `at` equals the bytes already sent"
            if self.refuse_at == "data" and args["at"] >= PIECE:
                raise ConnectionError("link lost")
            self.received += base64.b64decode(args["b64"])
            return {"ok": True, "got": len(self.received)}
        if tool == "self.assets.commit":
            return {"ok": False, "code": "hash", "error": "The hash did not match."} if self.refuse_at == "commit" else {"ok": True, "slot": 2}
        return {"ok": True}


def test_an_item_goes_install_then_pieces_in_order_then_commit():
    unit = FakeUnit()
    body = bytes(range(256)) * 20   # 5,120 bytes: three pieces
    header = build_header(kind="pantry", body=body, name="pantry-joke-en", version=1)
    result = AssetTransport(unit).install("u", header, body)
    assert result.ok and result.slot == 2 and unit.received == body
    assert [t for t, _ in unit.calls] == ["self.assets.install", "self.assets.data", "self.assets.data", "self.assets.data", "self.assets.commit"]
    assert unit.calls[0][1]["sig_b64"] == "", "an owner kind carries no signature"


def test_any_failure_aborts_so_no_half_item_stays_on_the_unit():
    for where in ("install", "data", "commit"):
        unit = FakeUnit(refuse_at=where)
        body = b"y" * 5000
        result = AssetTransport(unit).install("u", build_header(kind="pantry", body=body, name="p", version=1), body)
        assert not result.ok and result.message, where
        assert (unit.calls[-1][0] == "self.assets.abort") == (where != "install"), f"{where}: abort follows a started install, and a refused install has nothing to abort"
    refused = AssetTransport(FakeUnit(refuse_at="install")).install("u", build_header(kind="pantry", body=b"z", name="p", version=1), b"z")
    assert refused.code == "busy" and "game" in refused.message
    short = AssetTransport(FakeUnit(accept=100)).install("u", build_header(kind="pantry", body=b"z" * 500, name="p", version=1), b"z" * 500)
    assert not short.ok and short.code == "no_room" and "Packs page" in short.message


def test_a_pantry_shelf_reuses_its_slot_with_a_higher_version_and_a_new_one_takes_the_first_free_slot():
    unit = FakeUnit(items=[{"slot": 5, "name": "pantry-joke-en", "version": 4_000_000_000}])
    result = AssetTransport(unit, clock=lambda: 1_800_000_000).install_pantry_shelf("u", "joke", "en", b"s" * 100, record_count=10)
    install = [a for t, a in unit.calls if t == "self.assets.install"][0]
    assert install["slot"] == 5, "the same name keeps its slot"
    assert parse(unit.header)["version"] == 4_000_000_001, "a higher version than the installed one: the unit refuses a lower one"
    assert parse(unit.header)["ram"] == 160 and parse(unit.header)["name"] == "pantry-joke-en"
    fresh = FakeUnit()
    AssetTransport(fresh, clock=lambda: 1_800_000_000).install_pantry_shelf("u", "riddle", "es", b"s" * 100)
    assert [a for t, a in fresh.calls if t == "self.assets.install"][0]["slot"] == -1
    assert result.ok
    older = FakeUnit(items=[{"slot": 1, "name": "pantry-joke-en", "version": 5}])
    AssetTransport(older, clock=lambda: 1_800_000_000).install_pantry_shelf("u", "joke", "en", b"s")
    assert parse(older.header)["version"] == 1_800_000_000, "the clock when it is higher"


def test_the_license_id_sent_is_the_owner_content_id_of_the_shared_table():
    import json
    from pathlib import Path

    from maipai_body.asset_transport import OWN_CONTENT_LICENSE

    table = json.loads((Path(__file__).resolve().parents[2] / "schema" / "licenses.json").read_text())
    assert OWN_CONTENT_LICENSE in table["owner_content_ids"]
    assert OWN_CONTENT_LICENSE in {row["id"] for row in table["licenses"]} and OWN_CONTENT_LICENSE != 0
