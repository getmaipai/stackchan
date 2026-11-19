"""Ed25519 (RFC 8032) in plain Python, for the places the `cryptography` package is not there (the browser build runs on a core Pyodide with no packages). Slow and not constant time: it signs and
checks the virtual unit's fake test key only, never a real secret. Same results as the package (the signatures are deterministic); host/tests/test_assets_sim_ed25519.py compares them.
Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import hashlib

P = 2**255 - 19
Q = 2**252 + 27742317777372353535851937790883648493
D = -121665 * pow(121666, P - 2, P) % P
I = pow(2, (P - 1) // 4, P)


def _inv(x: int) -> int:
    return pow(x, P - 2, P)


def _x_from_y(y: int, sign: int) -> int:
    x2 = (y * y - 1) * _inv(D * y * y + 1) % P
    x = pow(x2, (P + 3) // 8, P)
    if (x * x - x2) % P:
        x = x * I % P
    if (x * x - x2) % P:
        raise ValueError("not a point")
    return P - x if (x & 1) != sign else x


BY = 4 * _inv(5) % P
B = (_x_from_y(BY, 0), BY, 1, 0)
B = (B[0], B[1], 1, B[0] * B[1] % P)


def _add(a, b):
    x1, y1, z1, t1 = a
    x2, y2, z2, t2 = b
    A, Bb, C, Dd = (y1 - x1) * (y2 - x2) % P, (y1 + x1) * (y2 + x2) % P, 2 * t1 * t2 * D % P, 2 * z1 * z2 % P
    E, F, G, H = Bb - A, Dd - C, Dd + C, Bb + A
    return (E * F % P, G * H % P, F * G % P, E * H % P)


def _mul(s: int, p):
    r = (0, 1, 1, 0)
    while s:
        if s & 1:
            r = _add(r, p)
        p = _add(p, p)
        s >>= 1
    return r


def _enc(p) -> bytes:
    zi = _inv(p[2])
    x, y = p[0] * zi % P, p[1] * zi % P
    return int(y | ((x & 1) << 255)).to_bytes(32, "little")


def _dec(b: bytes):
    y = int.from_bytes(b, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _x_from_y(y, sign)
    return (x, y, 1, x * y % P)


def _h(m: bytes) -> int:
    return int.from_bytes(hashlib.sha512(m).digest(), "little")


def _expand(secret: bytes):
    h = hashlib.sha512(secret).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def public_key(secret: bytes) -> bytes:
    return _enc(_mul(_expand(secret)[0], B))


def sign(secret: bytes, msg: bytes) -> bytes:
    a, prefix = _expand(secret)
    pub = _enc(_mul(a, B))
    r = _h(prefix + msg) % Q
    rs = _enc(_mul(r, B))
    s = (r + _h(rs + pub + msg) * a) % Q
    return rs + int(s).to_bytes(32, "little")


def verify(pub: bytes, sig: bytes, msg: bytes) -> bool:
    if len(sig) != 64 or len(pub) != 32:
        return False
    try:
        a_pt, r_pt = _dec(pub), _dec(sig[:32])
    except ValueError:
        return False
    s = int.from_bytes(sig[32:], "little")
    if s >= Q:
        return False
    h = _h(sig[:32] + pub + msg) % Q
    left = _mul(s, B)
    right = _add(r_pt, _mul(h, a_pt))
    return _enc(left) == _enc(right)
