"""Signed, ranged, cacheable asset delivery (docs/plan/offload-to-host.md, candidate 1): the unit asks for a pack when it needs it and keeps only
the active one. The id names the bytes (the payload's SHA-256), so a cache never serves the wrong content.

``AssetService`` is pure: it turns bytes into a signed manifest and answers byte ranges. The HTTP routes live in the voice server."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

CHUNK = 4096
IMMUTABLE = "private, max-age=31536000, immutable"
_RANGE = re.compile(r"^bytes=(\d*)-(\d*)$")


@dataclass(frozen=True)
class Asset:
    asset_id: str  # the SHA-256 of the payload, hex
    kind: str
    name: str
    version: int
    payload: bytes


class SigningKey:
    """An Ed25519 key kept in the host's data folder (mode 0600), made on first use. Never printed, never sent."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def _ensure(self) -> None:
        if self.path.exists():
            return
        from maipai_body.bodies.stackchan.firmware.openssl_cli import openssl_cli

        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        subprocess.run([openssl_cli(), "genpkey", "-algorithm", "Ed25519", "-out", str(self.path)], check=True, capture_output=True)
        self.path.chmod(0o600)

    def sign(self, message: bytes) -> bytes:
        from maipai_body.bodies.stackchan.firmware.openssl_cli import openssl_cli

        self._ensure()
        with tempfile.TemporaryDirectory(prefix="asset-sign-") as work:
            data = Path(work) / "m"
            data.write_bytes(message)
            return subprocess.run([openssl_cli(), "pkeyutl", "-sign", "-rawin", "-inkey", str(self.path), "-in", str(data)], check=True, capture_output=True).stdout

    def public_raw(self) -> bytes:
        from maipai_body.bodies.stackchan.firmware.openssl_cli import openssl_cli

        self._ensure()
        der = subprocess.run([openssl_cli(), "pkey", "-in", str(self.path), "-pubout", "-outform", "DER"], check=True, capture_output=True).stdout
        return der[-32:]


def canonical(manifest: dict) -> bytes:
    return json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


class AssetService:
    def __init__(self, key: SigningKey, provider: Callable[[str, str], Asset | None]) -> None:
        """``provider(device_id, asset_id)`` returns the asset the host wants that unit to have, or None (a unit gets only what the host chose for it)."""
        self._key, self._provider = key, provider

    def manifest(self, device_id: str, asset_id: str) -> tuple[bytes, str] | None:
        """(manifest JSON bytes, base64 signature) or None."""
        asset = self._provider(device_id, asset_id)
        if asset is None:
            return None
        payload = asset.payload
        manifest = {
            "v": 1, "id": asset.asset_id, "type": asset.kind, "name": asset.name, "version": asset.version, "size": len(payload), "chunk": CHUNK,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "chunks": [hashlib.sha256(payload[i : i + CHUNK]).hexdigest() for i in range(0, len(payload), CHUNK)],
            "signer": "host",
        }
        body = canonical(manifest)
        return body, base64.b64encode(self._key.sign(body)).decode()

    def data(self, device_id: str, asset_id: str, range_header: str | None) -> tuple[int, bytes, dict[str, str]] | None:
        """(status, body, headers) for the payload or one byte range of it; None when the unit may not have it."""
        asset = self._provider(device_id, asset_id)
        if asset is None:
            return None
        payload, digest = asset.payload, hashlib.sha256(asset.payload).hexdigest()
        headers = {"ETag": f'"{digest}"', "Cache-Control": IMMUTABLE, "Accept-Ranges": "bytes", "Content-Type": "application/octet-stream"}
        if not range_header:
            return 200, payload, headers
        match = _RANGE.match(range_header.strip())
        if not match or (not match.group(1) and not match.group(2)):
            return 416, b"", {**headers, "Content-Range": f"bytes */{len(payload)}"}
        if match.group(1):
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else len(payload) - 1
        else:  # the last N bytes
            start, end = max(0, len(payload) - int(match.group(2))), len(payload) - 1
        end = min(end, len(payload) - 1)
        if start > end or start >= len(payload):
            return 416, b"", {**headers, "Content-Range": f"bytes */{len(payload)}"}
        return 206, payload[start : end + 1], {**headers, "Content-Range": f"bytes {start}-{end}/{len(payload)}"}
