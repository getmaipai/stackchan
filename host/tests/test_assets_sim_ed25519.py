"""The plain Python Ed25519 beside assets_sim gives the same keys and signatures as the `cryptography` package (the browser build has no packages), and checks them both ways."""
import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "virtual-unit"))
import ed25519_pure  # noqa: E402

crypto = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ed25519")


def test_the_plain_python_signs_and_verifies_like_the_package():
    from cryptography.hazmat.primitives import serialization

    for i in range(4):
        seed = hashlib.sha256(b"seed %d" % i).digest()
        key = crypto.Ed25519PrivateKey.from_private_bytes(seed)
        pub = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        msg = bytes(range(i * 7))
        assert ed25519_pure.public_key(seed) == pub
        sig = key.sign(msg)
        assert ed25519_pure.sign(seed, msg) == sig
        assert ed25519_pure.verify(pub, sig, msg)
        assert not ed25519_pure.verify(pub, sig, msg + b"x")
        assert not ed25519_pure.verify(pub, sig[:-1] + bytes([sig[-1] ^ 1]), msg)
