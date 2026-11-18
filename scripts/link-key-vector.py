#!/usr/bin/env python3
"""Reference for the link key exchange in docs/plan/link-key-exchange.md (standard library only).

  link-key-vector.py --self-test     RFC 7748 X25519 vector, RFC 5869 HKDF vector, then the fixed fake exchange (no secrets)
  link-key-vector.py --print         print the fixed fake exchange as C-ready hex lines (used to write host/tests/firmware/linkkey_core_test.c)
"""

from __future__ import annotations

import hashlib
import hmac
import sys

P = 2**255 - 19
A24 = 121665


def _clamp(k: bytes) -> int:
    b = bytearray(k)
    b[0] &= 248
    b[31] &= 127
    b[31] |= 64
    return int.from_bytes(b, "little")


def x25519(k: bytes, u: bytes) -> bytes:
    """RFC 7748 section 5."""
    kk = _clamp(k)
    x1 = int.from_bytes(u, "little") & ((1 << 255) - 1)
    x2, z2, x3, z3, swap = 1, 0, x1, 1, 0
    for t in range(254, -1, -1):
        bit = (kk >> t) & 1
        swap ^= bit
        if swap:
            x2, x3, z2, z3 = x3, x2, z3, z2
        swap = bit
        a = (x2 + z2) % P
        aa = a * a % P
        b = (x2 - z2) % P
        bb = b * b % P
        e = (aa - bb) % P
        c = (x3 + z3) % P
        d = (x3 - z3) % P
        da = d * a % P
        cb = c * b % P
        x3 = pow(da + cb, 2, P)
        z3 = x1 * pow(da - cb, 2, P) % P
        x2 = aa * bb % P
        z2 = e * (aa + A24 * e) % P
    if swap:
        x2, x3, z2, z3 = x3, x2, z3, z2
    return (x2 * pow(z2, P - 2, P) % P).to_bytes(32, "little")


BASE = (9).to_bytes(32, "little")


def hkdf(ikm: bytes, salt: bytes, info: bytes, length: int) -> bytes:
    prk = hmac.new(salt or b"\x00" * 32, ikm, hashlib.sha256).digest()
    out, block, counter = b"", b"", 1
    while len(out) < length:
        block = hmac.new(prk, block + info + bytes([counter]), hashlib.sha256).digest()
        out += block
        counter += 1
    return out[:length]


def commit(pk_h: bytes, pk_u: bytes, n_h: bytes) -> bytes:
    return hashlib.sha256(b"mp-commit" + pk_h + pk_u + n_h).digest()


def sas(pk_u: bytes, pk_h: bytes, n_u: bytes, n_h: bytes) -> str:
    d = hashlib.sha256(b"mp-sas" + pk_u + pk_h + n_u + n_h).digest()
    return "%06d" % (int.from_bytes(d[:4], "big") % 1000000)


def link_key(z: bytes, pk_u: bytes, pk_h: bytes, n_u: bytes, n_h: bytes, device_id: str) -> bytes:
    salt = hashlib.sha256(pk_u + pk_h + n_u + n_h).digest()
    return hkdf(z, salt, b"maipai-stackchan-link-key-v2\x00" + device_id.lower().encode(), 32)


def psk(k: bytes, identity: str) -> bytes:
    return hkdf(k, b"", b"maipai-stackchan-link-psk-v2\x00" + identity.lower().encode(), 32)


# Fixed fake inputs (never real keys).
SK_U = bytes(range(1, 33))
SK_H = bytes(range(101, 133))
N_U = bytes(range(16))
N_H = bytes(range(200, 216))
DEVICE = "02:00:5E:00:53:01"


def exchange() -> dict[str, bytes | str]:
    pk_u, pk_h = x25519(SK_U, BASE), x25519(SK_H, BASE)
    z_u, z_h = x25519(SK_U, pk_h), x25519(SK_H, pk_u)
    assert z_u == z_h
    k = link_key(z_u, pk_u, pk_h, N_U, N_H, DEVICE)
    return {"pk_u": pk_u, "pk_h": pk_h, "z": z_u, "commit": commit(pk_h, pk_u, N_H), "sas": sas(pk_u, pk_h, N_U, N_H), "K": k, "psk": psk(k, DEVICE)}


def self_test() -> int:
    # RFC 7748 section 5.2, first vector
    k = bytes.fromhex("a546e36bf0527c9d3b16154b82465edd62144c0ac1fc5a18506a2244ba449ac4")
    u = bytes.fromhex("e6db6867583030db3594c1a424b15f7c726624ec26b3353b10a903a6d0ab1c4c")
    assert x25519(k, u).hex() == "c3da55379de9c6908e94ea4df28d084f32eccf03491c71f754b4075577a28552"
    # RFC 5869 test case 1
    okm = hkdf(bytes([0x0B] * 22), bytes.fromhex("000102030405060708090a0b0c"), bytes.fromhex("f0f1f2f3f4f5f6f7f8f9"), 42)
    assert okm.hex() == "3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865"
    x = exchange()
    print("self-test ok; sas", x["sas"], "psk", x["psk"].hex())  # type: ignore[union-attr]
    return 0


def main() -> int:
    if "--print" in sys.argv:
        for key, value in exchange().items():
            print(f"{key} {value.hex() if isinstance(value, bytes) else value}")
        return 0
    return self_test()


if __name__ == "__main__":
    sys.exit(main())
