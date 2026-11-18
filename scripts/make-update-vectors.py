#!/usr/bin/env python3
# Intent: write the signed-update test vectors (host/tests/fixtures/update-signature-vectors.json) from a fixed TEST seed, so the host and
# the firmware's Ed25519 check (patch 155/159 update_verify.cc) can be tested against the same bytes. Ed25519 signatures are deterministic.
# Usage: python3 scripts/make-update-vectors.py   (needs OpenSSL with Ed25519; the seed below is public and signs only these vectors)
# Placement: host test tooling. Upstream: none.
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "host"))
from maipai_body.bodies.stackchan.firmware.openssl_cli import openssl_cli  # noqa: E402

SEED = bytes(range(32))  # a published test seed: never a real key
PKCS8_PREFIX = bytes.fromhex("302e020100300506032b657004220420")
IMAGES = {"empty": b"", "tiny": b"app", "ramp": bytes(range(256)) * 4}


def main() -> int:
    cli = openssl_cli()
    with tempfile.TemporaryDirectory() as work:
        key = Path(work) / "k.pem"
        der = Path(work) / "k.der"
        der.write_bytes(PKCS8_PREFIX + SEED)
        subprocess.run([cli, "pkey", "-inform", "DER", "-in", str(der), "-out", str(key)], check=True, capture_output=True)
        pub_der = subprocess.run([cli, "pkey", "-in", str(key), "-pubout", "-outform", "DER"], check=True, capture_output=True).stdout
        pub_pem = subprocess.run([cli, "pkey", "-in", str(key), "-pubout"], check=True, capture_output=True).stdout.decode()
        vectors = []
        for name, data in IMAGES.items():
            img = Path(work) / f"{name}.bin"
            img.write_bytes(data)
            sig = subprocess.run([cli, "pkeyutl", "-sign", "-rawin", "-inkey", str(key), "-in", str(img)], check=True, capture_output=True).stdout
            flipped = bytearray(data or b"x")
            flipped[0] ^= 1
            bad_sig = bytes([sig[0] ^ 1]) + sig[1:]
            vectors += [
                {"name": f"{name}: good", "image_hex": data.hex(), "signature_hex": sig.hex(), "valid": True},
                {"name": f"{name}: image changed by one bit", "image_hex": bytes(flipped).hex() if data else "78", "signature_hex": sig.hex(), "valid": False},
                {"name": f"{name}: signature changed by one bit", "image_hex": data.hex(), "signature_hex": bad_sig.hex(), "valid": False},
                {"name": f"{name}: signature too short", "image_hex": data.hex(), "signature_hex": sig[:63].hex(), "valid": False},
            ]
    out = {
        "note": "TEST vectors from a published seed (bytes 0 to 31). Never a real key. Ed25519, raw detached signature over the image bytes.",
        "public_key_raw_hex": pub_der[-32:].hex(),
        "public_key_pem": pub_pem,
        "vectors": vectors,
    }
    target = Path(__file__).resolve().parents[1] / "host" / "tests" / "fixtures" / "update-signature-vectors.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {target} ({len(vectors)} vectors)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
