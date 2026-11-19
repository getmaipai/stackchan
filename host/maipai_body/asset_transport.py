# ruff: noqa: E501
"""Install one item in the unit's asset store (firmware SF89 and SF90, docs/plan/installed-set.md B3 and B4): header, pieces, commit.

The call order is `self.assets.install {slot, header_b64, sig_b64}`, then `self.assets.data {at, b64}` for every piece in order (2,048 raw bytes at most, `at` equal to the bytes
already sent), then `self.assets.commit`; anything that goes wrong ends with `self.assets.abort`, so a half-sent item is never left on the unit. The header is the 128 byte MPAH1 record
(positions as built in the firmware: the license id is at 120 and the author at 122). Owner kinds (look, pantry) carry no signature; the unit trusts the hash and the length over the paired link."""

from __future__ import annotations

import base64
import hashlib
import struct
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

HEADER_LEN = 128
MAGIC = b"MPAH1\0\0\0"
KINDS = {"language": 0, "font": 1, "style": 2, "look": 3, "game": 4, "sound": 5, "phrase": 6, "pantry": 7}
BOARD_ID = b"m5cores3"
PIECE = 2048
SECTOR = 4096
OWN_CONTENT_LICENSE = 1  # an index into schema/licenses.json, the owner's own content (host/tests/test_asset_transport.py checks the id against the table); non-zero is what the unit requires


def build_header(
    *,
    kind: str,
    body: bytes,
    name: str,
    version: int,
    code: str = "",
    board_id: bytes = BOARD_ID,
    fmt: int = 1,
    flags: int = 0,
    min_build: int = 0,
    ram_bytes: int = 0,
    license_id: int = OWN_CONTENT_LICENSE,
    author: int = 0,
) -> bytes:
    """The 128 byte header for a body. Raises ValueError, in plain words, for a value the unit would refuse."""
    if kind not in KINDS:
        raise ValueError(f"The kind {kind!r} is not one the unit installs.")
    if not 1 <= len(name) <= 40 or not name[0].isalnum() or not all(c.isalnum() or c in " .-_" for c in name):
        raise ValueError("The item name is 1 to 40 letters, digits, spaces, dots, dashes or underscores, starting with a letter or digit.")
    if not 1 <= version <= 0xFFFFFFFF:
        raise ValueError("The item version must be 1 or more.")
    if not board_id or not board_id.isascii() or len(board_id) > 8 or board_id.strip(b"\0") == b"":
        raise ValueError("The board id must be 1 to 8 ASCII characters.")
    if license_id == 0:
        raise ValueError("The license id must not be zero.")
    flash = -(-(len(body)) // SECTOR) * SECTOR
    return (
        MAGIC
        + struct.pack("<II", version, len(body))
        + hashlib.sha256(body).digest()
        + board_id.ljust(8, b"\0")
        + struct.pack("<BBHI", KINDS[kind], fmt, flags, min_build)
        + name.encode("ascii").ljust(40, b"\0")
        + code.encode("ascii")[:8].ljust(8, b"\0")
        + struct.pack("<IIHH", ram_bytes, flash, license_id, author)
        + b"\0" * 4
    )


@dataclass
class InstallResult:
    ok: bool
    message: str = ""
    slot: int = -1
    code: str = ""


def _reply(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    import json

    try:
        data = json.loads(raw) if isinstance(raw, (str, bytes)) else {}
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


class AssetTransport:
    # The unit holds one install session, so every writer to one unit (a pantry shelf, the installed-set reconciler) takes this lock first.
    _unit_locks: dict[str, threading.RLock] = {}
    _unit_locks_guard = threading.Lock()

    @classmethod
    def lock_for(cls, unit: str) -> threading.RLock:
        """The one install lock of a unit. Re-entrant, so a caller that holds it may call ``install`` itself."""
        with cls._unit_locks_guard:
            return cls._unit_locks.setdefault(unit, threading.RLock())

    def __init__(self, call: Callable[[str, str, dict], Any], *, clock: Callable[[], float] = time.time) -> None:
        self._call, self._clock = call, clock

    def _tool(self, unit: str, name: str, args: dict) -> dict:
        return _reply(self._call(unit, name, args))

    def install(self, unit: str, header: bytes, body: bytes, *, slot: int = -1, sig: bytes = b"") -> InstallResult:
        """Send one item. Never raises: a refusal or a lost link comes back as a result with a plain message, and the unit's half-install is aborted."""
        if len(header) != HEADER_LEN:
            return InstallResult(False, "The item header is not 128 bytes. Rebuild the item.")
        with self.lock_for(unit):
            return self._install_locked(unit, header, body, slot, sig)

    def _install_locked(self, unit: str, header: bytes, body: bytes, slot: int, sig: bytes) -> InstallResult:
        try:
            start = self._tool(unit, "self.assets.install", {"slot": slot, "header_b64": base64.b64encode(header).decode(), "sig_b64": base64.b64encode(sig).decode() if sig else ""})
            if start.get("ok") is not True:
                return InstallResult(False, self._why(start), code=str(start.get("code", "")))
            piece = int(start.get("piece_bytes") or PIECE)
            if int(start.get("accept_bytes") or 0) and int(start["accept_bytes"]) < len(body):
                self._abort(unit)
                return InstallResult(False, "The unit has no room for this item. Remove a pack on the Packs page, then try again.", code="no_room")
            sent = 0
            while sent < len(body):
                chunk = body[sent : sent + min(piece, PIECE)]
                got = self._tool(unit, "self.assets.data", {"at": sent, "b64": base64.b64encode(chunk).decode()})
                if got.get("ok") is not True:
                    self._abort(unit)
                    return InstallResult(False, self._why(got), code=str(got.get("code", "")))
                sent += len(chunk)
            done = self._tool(unit, "self.assets.commit", {})
            if done.get("ok") is not True:
                self._abort(unit)
                return InstallResult(False, self._why(done), code=str(done.get("code", "")))
            return InstallResult(True, "Installed.", slot=int(done.get("slot", start.get("slot", slot))))
        except Exception as error:
            self._abort(unit)
            return InstallResult(False, f"The unit did not finish the install ({type(error).__name__}). It was canceled and the unit keeps what it had.")

    def _abort(self, unit: str) -> None:
        try:
            self._tool(unit, "self.assets.abort", {})
        except Exception:
            pass

    @staticmethod
    def _why(reply: dict) -> str:
        return str(reply.get("error") or "The unit refused the install. Try again when it is idle and unlocked.")

    def items(self, unit: str) -> list[dict]:
        """The items on the unit: [{kind, slot, name, version}], from self.assets.list."""
        listing = self._tool(unit, "self.assets.list", {})
        out = []
        for kind in listing.get("kinds", []) if listing.get("ok") is True else []:
            for item in kind.get("items", []) or []:
                out.append({"kind": kind.get("kind"), "slot": item.get("slot"), "name": item.get("name"), "version": int(item.get("version") or 0)})
        return out

    def install_pantry_shelf(self, unit: str, kind: str, language: str, body: bytes, record_count: int | None = None) -> InstallResult:
        """A pantry shelf: the same name takes the same slot with a higher version (the unit refuses a lower one); a new name takes the first free slot."""
        name = f"pantry-{kind}-{language}"
        with self.lock_for(unit):  # the slot and version are read and used under one lock
            existing = next((i for i in self.items(unit) if i["kind"] == "pantry" and i["name"] == name), None)
            version = max(int(self._clock()), (existing["version"] + 1) if existing else 1)
            header = build_header(kind="pantry", body=body, name=name, version=version, code=language, ram_bytes=16 * (record_count or 0))
            return self.install(unit, header, body, slot=int(existing["slot"]) if existing and existing["slot"] is not None else -1)
