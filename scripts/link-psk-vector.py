#!/usr/bin/env python3
"""Print the encrypted-link PSK for a pairing secret and a device id (for firmware and Home tests).

Reference for the derivation in docs/design/encrypted-link.md. Standard
library only. The pairing secret is the device token the unit holds; the host keeps only its SHA-256.

  link-psk-vector.py --self-test                     fixed fake vectors (no secrets)
  link-psk-vector.py DEVICE_ID --digest HEX64        digest the host stores
  link-psk-vector.py DEVICE_ID --token-stdin         token read from standard input
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import hmac
import sys

INFO_PREFIX = b"maipai-stackchan-link-psk-v1\x00"


def hkdf_sha256(ikm: bytes, salt: bytes, info: bytes, length: int) -> bytes:
    prk = hmac.new(salt or b"\x00" * 32, ikm, hashlib.sha256).digest()
    out, block, counter = b"", b"", 1
    while len(out) < length:
        block = hmac.new(prk, block + info + bytes([counter]), hashlib.sha256).digest()
        out += block
        counter += 1
    return out[:length]


def derive(digest_hex: str, device_id: str) -> bytes:
    return hkdf_sha256(
        bytes.fromhex(digest_hex), b"", INFO_PREFIX + device_id.strip().lower().encode(), 32
    )


# Fake inputs, safe to publish. FAKE_TOKEN is not a real token.
FAKE_TOKEN = "test-token-not-a-secret-0123456789abcdefghijklmnopq"
VECTORS = [
    ("02:00:5e:00:53:01", FAKE_TOKEN),
    ("AA:BB:CC:DD:EE:FF", FAKE_TOKEN),  # upper case id: normalized to lower case first
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("device_id", nargs="?")
    parser.add_argument("--digest", help="SHA-256 of the device token, 64 hex characters")
    parser.add_argument("--token-stdin", action="store_true", help="read the device token from stdin")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        for device_id, token in VECTORS:
            digest = hashlib.sha256(token.encode()).hexdigest()
            print(f"device_id={device_id}\ntoken_sha256={digest}\npsk={derive(digest, device_id).hex()}\n")
        return 0
    if not args.device_id or bool(args.digest) == args.token_stdin:
        parser.error("give DEVICE_ID and exactly one of --digest or --token-stdin")
    if args.token_stdin:
        token = sys.stdin.readline().strip() if not sys.stdin.isatty() else getpass.getpass("Token: ")
        digest = hashlib.sha256(token.encode()).hexdigest()
    else:
        digest = args.digest
    print(derive(digest, args.device_id).hex())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
