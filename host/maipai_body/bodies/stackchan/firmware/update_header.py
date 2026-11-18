"""The signed update header (docs/plan/signed-update-anti-rollback.md, agreed with the firmware track): 56 bytes, Ed25519-signed, so the unit
streams the image through SHA-256, checks the hash and length against a small signed message, and refuses a build number that is not higher
than the one it has accepted (anti-rollback).

Layout (little endian, as the unit reads it):
  0  magic "MPUH1\0\0\0" (8)   8  build number u32   12  image length u32   16  SHA-256 of the image (32)   48  board id (8 ASCII bytes, zero padded; all zero is refused)   -> 56 bytes.
Files: `<image>.hdr` (the 56 bytes) and `<image>.hdr.sig` (Ed25519 over those 56 bytes, 64 bytes). A package is header || signature = 120 bytes.
The version text is not signed: the host sends it with the update call, and the unit trusts only the signed build number."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from pathlib import Path

from maipai_body.bodies.stackchan.firmware.flash_manifest import verify_detached
from maipai_body.bodies.stackchan.firmware.openssl_cli import openssl_cli

MAGIC = b"MPUH1\0\0\0"
HEADER_LEN = 56
SIGNATURE_LEN = 64
PACKAGE_LEN = HEADER_LEN + SIGNATURE_LEN
BOARD_ID = b"m5cores3"  # the CoreS3 StackChan: the unit refuses a header whose board id is not its own (CONFIG_MAIPAI_BOARD_ID)


MAX_BUILD = 2**31  # the unit stores the build number as a signed 32-bit value and refuses 2^31 or more


def build_header(build_number: int, image: bytes, board_id: bytes = BOARD_ID) -> bytes:
    if not 1 <= build_number < MAX_BUILD:
        raise ValueError("The build number must be a whole number from 1 up to 2147483647 (it only ever goes up).")
    if len(image) >= 2**32:
        raise ValueError("The image is too large.")
    if not 1 <= len(board_id) <= 8 or not board_id.isascii():
        raise ValueError("The board id must be 1 to 8 ASCII characters.")
    return MAGIC + build_number.to_bytes(4, "little") + len(image).to_bytes(4, "little") + hashlib.sha256(image).digest() + board_id.ljust(8, b"\0")


def parse_header(header: bytes) -> dict:
    if len(header) != HEADER_LEN or header[:8] != MAGIC:
        raise ValueError("This is not a StackChan update header.")
    if not any(header[48:56]):
        raise ValueError("The update header has no board id. Build the release with a board id.")
    return {
        "build_number": int.from_bytes(header[8:12], "little"),
        "size": int.from_bytes(header[12:16], "little"),
        "sha256": header[16:48].hex(),
        "board_id": header[48:56].rstrip(b"\0").decode("ascii", "replace"),
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
    if len(signature) != SIGNATURE_LEN:
        raise ValueError("The signature has the wrong size.")
    return header + signature


@dataclass(frozen=True)
class Verdict:
    ok: bool
    reason: str = ""
    header: dict | None = None


def verify_package(package: bytes, image: bytes, public_key_path: str | Path, *, installed_build: int | None, board_id: bytes = BOARD_ID) -> Verdict:
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
    if fields["board_id"].encode("ascii") != board_id:
        return Verdict(False, f"This update is for another board ({fields['board_id']}, not {board_id.decode('ascii', 'replace')}). Publish a release built for this board.", fields)
    if fields["size"] != len(image) or not hmac.compare_digest(fields["sha256"], hashlib.sha256(image).hexdigest()):
        return Verdict(False, "The image does not match its signed header.", fields)
    if fields["build_number"] >= MAX_BUILD:
        return Verdict(False, "The update's build number is too large for the unit. Ask for a release with a build number below 2147483648.", fields)
    if fields["build_number"] == 0:
        return Verdict(False, "The update's build number is 0, which the unit refuses. Ask for a release with a build number of 1 or more.", fields)
    if installed_build is not None and fields["build_number"] <= installed_build:
        return Verdict(False, f"This update is not newer than the one installed (build {fields['build_number']} is not higher than {installed_build}).", fields)
    return Verdict(True, "", fields)
