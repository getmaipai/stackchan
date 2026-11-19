#!/usr/bin/env python3
"""Release gate step: the web flasher only trusts the release keys pinned in flasher/trusted-keys.json, so a real release is refused
while that list is empty or does not hold the key the release is signed with.
Usage: pinned-key-check.py TRUSTED_KEYS_JSON SIGNING_KEY_PEM
Placement: repo release tool (host). Upstream: none."""

from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
from pathlib import Path

SPKI_PREFIX = bytes.fromhex("302a300506032b6570032100")


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def spki(pem: str) -> bytes:
    try:
        der = base64.b64decode(re.sub(r"-----[^-]+-----|\s+", "", pem), validate=True)
    except ValueError:
        der = b""
    if len(der) != 44 or not der.startswith(SPKI_PREFIX):
        fail("A key in flasher/trusted-keys.json is damaged (it must be an Ed25519 public key in PEM form). Paste the release key again from release-key.pub.pem.")
    return der


def main() -> None:
    if len(sys.argv) != 3:
        fail("Usage: pinned-key-check.py TRUSTED_KEYS_JSON SIGNING_KEY_PEM")
    path, signing = Path(sys.argv[1]), sys.argv[2]
    try:
        keys = json.loads(path.read_text()).get("keys", [])
    except (OSError, ValueError, AttributeError):
        fail(f"{path} is missing or is not valid JSON. Restore it with a \"keys\" list that holds the release public key.")
    if not keys:
        fail(f"The pinned key list in {path} is empty, so the web flasher would refuse every real release. Add the release public key (release-key.pub.pem) to it, then run the release again.")
    pinned = [spki(str(key)) for key in keys]
    from maipai_body.bodies.stackchan.firmware.openssl_cli import openssl_cli

    done = subprocess.run([openssl_cli(), "pkey", "-in", signing, "-pubout", "-outform", "DER"], capture_output=True)
    if done.returncode != 0:
        fail(f"The signing key file {signing} could not be read as an Ed25519 key. Pass the owner's release key file.")
    if done.stdout not in pinned:
        fail(f"The signing key is not the key pinned in {path}, so the web flasher would refuse this release. Pin this key's public half there, or sign with the pinned key.")


main()
