"""The signed update header (docs/plan/signed-update-header.md): 64 bytes, Ed25519-signed, so the unit can stream the image through SHA-256,
check the hash against a 64-byte signed message, and refuse a build number that is not higher than its own (anti-rollback).

Layout (big endian):  0 "MPUH"  4 format (1)  5..7 zero  8 build number u32  12 version, 16 ASCII bytes NUL padded
                      28 image size u32  32 SHA-256 of the image (32 bytes)   -> 64 bytes.
Package = header (64) || Ed25519 signature over the header (64) = 128 bytes, served as `<image>.mph`."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from pathlib import Path

from maipai_body.bodies.stackchan.firmware.flash_manifest import verify_detached
from maipai_body.bodies.stackchan.firmware.openssl_cli import openssl_cli

MAGIC = b"MPUH"
FORMAT = 1
HEADER_LEN = 64
PACKAGE_LEN = 128
VERSION_LEN = 16


def build_header(version: str, build_number: int, image: bytes) -> bytes:
    if not version.isascii() or not version or len(version.encode()) > VERSION_LEN or "\0" in version:
        raise ValueError(f"The version must be 1 to {VERSION_LEN} plain characters.")
    if not 1 <= build_number < 2**32:
        raise ValueError("The build number must be a whole number from 1 up (it only ever goes up).")
    if len(image) >= 2**32:
        raise ValueError("The image is too large.")
    return (
        MAGIC + bytes([FORMAT, 0, 0, 0]) + build_number.to_bytes(4, "big") + version.encode().ljust(VERSION_LEN, b"\0")
        + len(image).to_bytes(4, "big") + hashlib.sha256(image).digest()
    )


def parse_header(header: bytes) -> dict:
    if len(header) != HEADER_LEN or header[:4] != MAGIC or header[4] != FORMAT or any(header[5:8]):
        raise ValueError("This is not a StackChan update header.")
    return {
        "version": header[12:28].rstrip(b"\0").decode("ascii"),
        "build_number": int.from_bytes(header[8:12], "big"),
        "size": int.from_bytes(header[28:32], "big"),
        "sha256": header[32:64].hex(),
    }


def sign_package(header: bytes, key_path: str | Path) -> bytes:
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory(prefix="stackchan-header-") as work:
        path = Path(work) / "header.bin"
        path.write_bytes(header)
        signature = subprocess.run(
            [openssl_cli(), "pkeyutl", "-sign", "-rawin", "-inkey", str(key_path), "-in", str(path)], check=True, capture_output=True
        ).stdout
    if len(signature) != 64:
        raise ValueError("The signature has the wrong size.")
    return header + signature


@dataclass(frozen=True)
class Verdict:
    ok: bool
    reason: str = ""
    header: dict | None = None


def verify_package(package: bytes, image: bytes, public_key_path: str | Path, *, installed_build: int | None) -> Verdict:
    """What the unit checks, in the unit's order: size, signature over the header, header fields, image size and hash, then the build
    number against the one it has installed (None means the unit has none yet, so any build is accepted)."""
    if len(package) != PACKAGE_LEN:
        return Verdict(False, "The update package has the wrong size.")
    header, signature = package[:HEADER_LEN], package[HEADER_LEN:]
    if not verify_detached(header, signature, public_key_path):
        return Verdict(False, "The update's signature is not valid.")
    try:
        fields = parse_header(header)
    except ValueError as error:
        return Verdict(False, str(error))
    if fields["size"] != len(image) or not hmac.compare_digest(fields["sha256"], hashlib.sha256(image).hexdigest()):
        return Verdict(False, "The image does not match its signed header.", fields)
    if installed_build is not None and fields["build_number"] <= installed_build:
        return Verdict(False, f"This update is not newer than the one installed (build {fields['build_number']} is not higher than {installed_build}).", fields)
    return Verdict(True, "", fields)
