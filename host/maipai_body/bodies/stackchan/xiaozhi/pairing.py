"""Local administrator approval and per-device bearer tokens."""

from __future__ import annotations

import fcntl
import hashlib
import json
import logging
import os
import re
import secrets
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any

LOG = logging.getLogger(__name__)
_MAC = re.compile(r"^[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}$")
_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
PENDING_LIMIT = 8
PENDING_TTL = 600
ENROLLMENT_LIMIT = 32
PAIR_CODE_TTL = 600
PAIR_CODE_LIMIT = 8
PAIR_CODE_GLOBAL_LIMIT = 40  # failed tries from all non-local addresses together, per window
LOCAL_SOURCES = frozenset({"local", "127.0.0.1", "::1"})
PAIR_CODE_ATTEMPT_LIMIT = 5
PAIR_CODE_WINDOW = 600


@dataclass(frozen=True)
class PairingRequest:
    device_id: str
    client_id: str
    requested_at: float


class PairingRequired(PermissionError):
    """Raised when an unapproved device asks to connect."""


class PairingStore:
    """Stores an allowlist and one-way token digests in a local JSON file."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self._lock = RLock()
        self._devices: dict[str, dict[str, str | float]] = {}
        self._enrollments: dict[str, dict[str, object]] = {}
        self._pending: dict[tuple[str, str], PairingRequest] = {}
        self._pair_codes: dict[str, dict[str, object]] = {}
        self._code_attempts: dict[str, list[float]] = {}
        self._file_signature: tuple[int, int] | None = None
        with self._lock:
            with self._file_lock():
                self._refresh()

    @contextmanager
    def _file_lock(self):
        """Serialize read-modify-write across the service and dashboard processes."""
        if self.path is None:
            yield
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.path.with_name(self.path.name + ".lock")
        with lock_path.open("a+") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _valid_id(device_id: str) -> bool:
        return bool(_MAC.fullmatch(device_id))

    @staticmethod
    def _valid_client_id(client_id: str) -> bool:
        return bool(_UUID.fullmatch(client_id))

    def authorize(self, device_id: str, client_id: str, token: str | None) -> bool:
        if not self._valid_id(device_id) or not token:
            return False
        with self._lock:
            self._refresh()
            record = self._devices.get(device_id)
            if not record or record.get("client_id") != client_id:
                return False
            digest = hashlib.sha256(token.encode()).hexdigest()
            return secrets.compare_digest(str(record.get("token_sha256", "")), digest)

    def create_pair_code(self, *, now: float | None = None) -> str:
        """Create a displayed six digit code, valid for ten minutes and one device.

        Codes are stored as digests in the pairing file so a code made by the command
        line is redeemable by the running host."""
        now = time.time() if now is None else now
        with self._lock:
            with self._file_lock():
                self._refresh()
                self._prune_codes(now)
                code = f"{secrets.randbelow(1_000_000):06d}"
                self._pair_codes[hashlib.sha256(code.encode()).hexdigest()] = {
                    "expires_at": now + PAIR_CODE_TTL,
                    "used": False,
                }
                while len(self._pair_codes) > PAIR_CODE_LIMIT:
                    oldest = min(
                        self._pair_codes, key=lambda key: float(self._pair_codes[key]["expires_at"])
                    )
                    del self._pair_codes[oldest]
                self._save()
                return code

    def _prune_codes(self, now: float) -> None:
        self._pair_codes = {
            key: record
            for key, record in self._pair_codes.items()
            if isinstance(record, dict)
            and not record.get("used")
            and float(record.get("expires_at", 0)) > now
        }

    def redeem_pair_code(
        self,
        device_id: str,
        client_id: str,
        code: str,
        *,
        source: str = "local",
        now: float | None = None,
    ) -> str | None:
        """Consume a displayed code and return the device's one-time token.

        Tries are limited per source address. A second, slower limit counts failed tries from all
        non-local sources together; this computer's own tries are never held back by it."""
        now = time.time() if now is None else now
        token = self._redeem(device_id, client_id, code, source, now)
        if token is None and source not in LOCAL_SOURCES:
            with self._lock:
                self._code_attempts.setdefault("*", []).append(now)
        return token

    def _redeem(self, device_id: str, client_id: str, code: str, source: str, now: float) -> str | None:
        with self._lock:
            self._refresh()
            attempts = [
                stamp for stamp in self._code_attempts.get(source, [])
                if now - stamp < PAIR_CODE_WINDOW
            ]
            self._code_attempts[source] = attempts
            all_attempts = [
                stamp for stamp in self._code_attempts.get("*", []) if now - stamp < PAIR_CODE_WINDOW
            ]
            self._code_attempts["*"] = all_attempts
            if len(attempts) >= PAIR_CODE_ATTEMPT_LIMIT or (
                source not in LOCAL_SOURCES and len(all_attempts) >= PAIR_CODE_GLOBAL_LIMIT
            ):
                return None
            attempts.append(now)
            digest = hashlib.sha256(code.encode()).hexdigest()
            record = self._pair_codes.get(digest)
            if (
                not self._valid_id(device_id)
                or not self._valid_client_id(client_id)
                or record is None
            ):
                return None
            if record["used"] or float(record["expires_at"]) <= now:
                return None
        with self._lock:
            with self._file_lock():
                self._refresh()
                record = self._pair_codes.get(digest)
                if record is None or record["used"] or float(record["expires_at"]) <= now:
                    return None
                if self._find(device_id) is not None:
                    LOG.warning(
                        "A pairing code was refused for %s: that unit is already paired. "
                        "Run `stackchan forget` first to pair it again.",
                        device_id[-5:],
                    )
                    return None
                record["used"] = True
                self._prune_codes(now)
                token = secrets.token_urlsafe(32)
                self._devices[device_id] = {
                    "client_id": client_id,
                    "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
                    "approved_at": now,
                    "last_seen": now,
                    "link_new": True,
                }
                self._save()
                return token

    # -- encrypted link (link_security.py) ---------------------------------------------------
    def _find(self, device_id: str) -> tuple[str, dict[str, Any]] | None:
        wanted = device_id.strip().lower()
        for key, record in self._devices.items():
            if key.lower() == wanted and isinstance(record, dict):
                return key, record
        return None

    def link_material(self, device_id: str) -> str | None:
        """The pairing material the encrypted-link key is derived from (a digest, never the token)."""
        with self._lock:
            self._refresh()
            found = self._find(device_id)
            digest = found[1].get("token_sha256") if found else None
            return str(digest) if digest else None

    def store_link_key(self, device_id: str, client_id: str, key: bytes) -> None:
        """A unit paired with the key exchange: keep its link key (and no token digest). It starts `required`."""
        if len(key) != 32 or not self._valid_id(device_id) or not self._valid_client_id(client_id):
            raise ValueError("A link key is 32 bytes and a unit has a Device-Id and a Client-Id.")
        now = time.time()
        with self._lock:
            with self._file_lock():
                self._refresh()
                found = self._find(device_id)
                name = found[0] if found else device_id.lower()
                record = dict(found[1]) if found else {}
                record.pop("token_sha256", None)
                record.update({"client_id": client_id, "link_key_hex": key.hex(), "link_encryption": "required", "approved_at": now, "last_seen": now})
                self._devices[name] = record
                self._save()

    def link_key(self, device_id: str) -> bytes | None:
        with self._lock:
            self._refresh()
            found = self._find(device_id)
            raw = found[1].get("link_key_hex") if found else None
        try:
            return bytes.fromhex(str(raw)) if raw else None
        except ValueError:
            return None

    def authorize_link(self, device_id: str, client_id: str) -> bool:
        """A unit that paired with the key exchange is authorized by its encrypted link plus its Client-Id (no token)."""
        with self._lock:
            self._refresh()
            found = self._find(device_id)
            if not found or not found[1].get("link_key_hex"):
                return False
            return secrets.compare_digest(str(found[1].get("client_id", "")), client_id)

    def link_record(self, device_id: str) -> dict[str, Any]:
        """Link fields only: mode, seen_encrypted, new pairing flag. No key material."""
        with self._lock:
            self._refresh()
            found = self._find(device_id)
            if not found:
                return {}
            record = found[1]
            return {
                "link_encryption": record.get("link_encryption"),
                "seen_encrypted": bool(record.get("seen_encrypted")),
                "link_new": bool(record.get("link_new")),
            }

    def link_mode(self, device_id: str) -> str | None:
        return self.link_record(device_id).get("link_encryption")

    def _update_link(self, device_id: str, change: dict[str, Any]) -> bool:
        with self._lock:
            with self._file_lock():
                self._refresh()
                found = self._find(device_id)
                if not found:
                    return False
                if all(found[1].get(k) == v for k, v in change.items()):
                    return True
                found[1].update(change)
                self._save()
                return True

    def set_link_mode(self, device_id: str, mode: str) -> bool:
        return self._update_link(device_id, {"link_encryption": mode})

    def mark_seen_encrypted(self, device_id: str) -> None:
        self._update_link(device_id, {"seen_encrypted": True})

    def promote_new_link(self, device_id: str) -> bool:
        """A new pairing whose unit reports encryption support, with no choice made, becomes required."""
        with self._lock:
            with self._file_lock():
                self._refresh()
                found = self._find(device_id)
                if not found or not found[1].get("link_new") or found[1].get("link_encryption"):
                    return False
                found[1]["link_encryption"] = "required"
                self._save()
                return True

    def adopt_device(self, device_id: str, client_id: str, token_sha256: str) -> None:
        """Register a unit that Home paired: Home hands over the digest of the device token it issued.

        This is the same secret as the token, not a second one: the host derives the link key from the
        digest exactly as it does for a unit it paired itself."""
        if not self._valid_id(device_id) or not self._valid_client_id(client_id):
            raise ValueError("Device-Id must be a MAC address and Client-Id a UUID. Correct both.")
        if not re.fullmatch(r"[0-9a-f]{64}", token_sha256):
            raise ValueError("The pairing digest must be 64 lower-case hex characters.")
        with self._lock:
            with self._file_lock():
                self._refresh()
                self._devices[device_id] = {
                    "client_id": client_id,
                    "token_sha256": token_sha256,
                    "approved_at": time.time(),
                    "link_new": True,
                }
                self._save()

    def paired_devices(self) -> dict[str, dict[str, str | float]]:
        with self._lock:
            self._refresh()
            return {device_id: dict(record) for device_id, record in self._devices.items()}

    def issue_enrollment(self, ttl: int = 86400) -> tuple[str, str]:
        if ttl <= 0:
            raise ValueError("Enrollment lifetime must be positive.")
        code_id, code = secrets.token_hex(8), secrets.token_urlsafe(24)
        with self._lock:
            with self._file_lock():
                self._refresh()
                live = sum(
                    not enrollment.get("spent")
                    and float(enrollment.get("expires_at", 0)) > time.time()
                    for enrollment in self._enrollments.values()
                )
                if live >= ENROLLMENT_LIMIT:
                    raise RuntimeError(
                        "Too many unfinished installs. Cancel an unfinished install and retry."
                    )
                self._enrollments[code_id] = {
                    "code_sha256": hashlib.sha256(code.encode()).hexdigest(),
                    "expires_at": time.time() + ttl,
                    "bound_device": None,
                    "bound_client": None,
                    "spent": False,
                }
                self._save()
        return code_id, code

    def redeem_enrollment(self, device_id: str, client_id: str, code: str | None) -> str | None:
        if not self._valid_id(device_id) or not self._valid_client_id(client_id) or not code:
            return None
        digest = hashlib.sha256(code.encode()).hexdigest()
        with self._lock:
            with self._file_lock():
                self._refresh()
                now = time.time()
                for code_id, enrollment in self._enrollments.items():
                    if enrollment.get("spent") or float(enrollment.get("expires_at", 0)) <= now:
                        continue
                    if not secrets.compare_digest(str(enrollment.get("code_sha256", "")), digest):
                        continue
                    bound = enrollment.get("bound_device")
                    if bound is not None and (
                        bound != device_id or enrollment.get("bound_client") != client_id
                    ):
                        return None
                    existing = self._devices.get(device_id)
                    if existing is not None and existing.get("enrollment_id") != code_id:
                        return None
                    enrollment["bound_device"] = device_id
                    enrollment["bound_client"] = client_id
                    token = secrets.token_urlsafe(32)
                    self._devices[device_id] = {
                        "client_id": client_id,
                        "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
                        "approved_at": now,
                        "enrollment_id": code_id,
                        "link_new": True,
                    }
                    self._save()
                    return token
        return None

    def revoke_enrollment(self, code_id: str) -> bool:
        with self._lock:
            with self._file_lock():
                self._refresh()
                enrollment = self._enrollments.pop(code_id, None)
                if enrollment and enrollment.get("bound_device"):
                    device_id = str(enrollment["bound_device"])
                    device = self._devices.get(device_id)
                    if device and device.get("enrollment_id") == code_id:
                        self._devices.pop(device_id, None)
                self._save()
                return enrollment is not None

    def enrollment(self, code_id: str) -> dict[str, object] | None:
        with self._lock:
            self._refresh()
            record = self._enrollments.get(code_id)
            return dict(record) if record else None

    def spend_enrollment(self, device_id: str) -> None:
        with self._lock:
            with self._file_lock():
                self._refresh()
                device = self._devices.get(device_id)
                enrollment_id = device.get("enrollment_id") if device else None
                record = self._enrollments.get(str(enrollment_id))
                if record is not None and not record.get("spent"):
                    record["spent"] = True
                    self._save()

    @staticmethod
    def _pending_key(device_id: str, client_id: str) -> tuple[str, str]:
        return device_id, client_id

    def recognizes_device(self, device_id: str, client_id: str) -> bool:
        """Whether this identity has an approved or pending pairing record."""
        with self._lock:
            self._refresh()
            self._expire_pending()
            record = self._devices.get(device_id)
            return (record is not None and record.get("client_id") == client_id) or (
                self._pending_key(device_id, client_id) in self._pending
            )

    def request(self, device_id: str, client_id: str) -> PairingRequest:
        if not self._valid_id(device_id) or not self._valid_client_id(client_id):
            raise ValueError(
                "Device-Id must be a MAC address and Client-Id must be a UUID. Correct both "
                "headers and reconnect."
            )
        with self._lock:
            with self._file_lock():
                self._refresh()
                self._expire_pending()
                req = PairingRequest(
                    device_id=device_id, client_id=client_id, requested_at=time.time()
                )
                key = self._pending_key(device_id, client_id)
                if key not in self._pending and len(self._pending) >= PENDING_LIMIT:
                    raise ValueError(
                        "The pending pairing list is full. Approve or remove a pending device, "
                        "then reconnect."
                    )
                self._pending[key] = req
                self._save()
                return req

    def approve(self, device_id: str, client_id: str) -> str:
        """Approve a pending device and return its one-time token."""
        with self._lock:
            with self._file_lock():
                self._refresh()
                self._expire_pending()
                req = self._pending.pop(self._pending_key(device_id, client_id), None)
                if req is None:
                    raise KeyError(
                        "No pending request matches this Device-Id and Client-Id. Copy both values "
                        "from the pending list, then approve again."
                    )
                token = secrets.token_urlsafe(32)
                self._devices[device_id] = {
                    "client_id": req.client_id,
                    "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
                    "approved_at": time.time(),
                    "link_new": True,
                }
                self._save()
                return token

    def approve_to_file(self, device_id: str, client_id: str) -> Path:
        """Approve a device and place its one-time token in a private local file."""
        token = self.approve(device_id, client_id)
        base = self.path.parent if self.path else Path.home() / ".local/share/maipai-bot"
        directory = base / "stackchan-tokens"
        path = directory / f"{secrets.token_hex(12)}.token"
        try:
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            directory.chmod(0o700)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as token_file:
                token_file.write(token)
                token_file.write("\n")
        except OSError:
            self.revoke(device_id)
            raise
        return path

    def revoke(self, device_id: str) -> bool:
        with self._lock:
            with self._file_lock():
                self._refresh()
                removed = self._devices.pop(device_id, None) is not None
                for key in [key for key in self._pending if key[0] == device_id]:
                    self._pending.pop(key, None)
                self._save()
                return removed

    def pending(self) -> tuple[PairingRequest, ...]:
        with self._lock:
            self._refresh()
            self._expire_pending()
            return tuple(self._pending.values())

    def allowed_device_ids(self) -> frozenset[str]:
        with self._lock:
            self._refresh()
            return frozenset(self._devices)

    def _expire_pending(self) -> None:
        now = time.time()
        expired = [
            key
            for key, request in self._pending.items()
            if now - request.requested_at > PENDING_TTL
        ]
        for key in expired:
            self._pending.pop(key, None)

    def _refresh(self) -> None:
        if self.path is None:
            return
        try:
            stat = self.path.stat()
        except FileNotFoundError:
            signature = None
        else:
            signature = (stat.st_mtime_ns, stat.st_size)
        if signature == self._file_signature:
            return
        if signature is None:
            self._devices = {}
            self._enrollments = {}
            self._pending = {}
            self._pair_codes = {}
            self._file_signature = None
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            devices = raw.get("devices", {})
            enrollments = raw.get("enrollments", {})
            pending = {
                self._pending_key(request["device_id"], request["client_id"]): PairingRequest(
                    device_id=request["device_id"],
                    client_id=request["client_id"],
                    requested_at=float(request["requested_at"]),
                )
                for request in raw.get("pending", {}).values()
            }
            if (
                not isinstance(devices, dict)
                or not isinstance(pending, dict)
                or not isinstance(enrollments, dict)
            ):
                raise TypeError("pairing data must contain device, enrollment and pending objects")
        except (json.JSONDecodeError, KeyError, TypeError, ValueError, OSError) as exc:
            LOG.error(
                "Pairing file %s is corrupt (%s). Move it aside and reapprove devices.",
                self.path,
                type(exc).__name__,
            )
            self._devices = {}
            self._enrollments = {}
            self._pending = {}
            self._file_signature = signature
            return
        self._devices = devices
        self._enrollments = enrollments
        codes = raw.get("pair_codes", {})
        self._pair_codes = codes if isinstance(codes, dict) else {}
        self._prune_enrollments()
        self._pending = pending
        self._expire_pending()
        self._file_signature = signature

    def _save(self) -> None:
        if self.path is None:
            return
        self._prune_enrollments()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_name(f"{self.path.name}.tmp.{os.getpid()}.{secrets.token_hex(6)}")
        data = {
            "devices": self._devices,
            "enrollments": self._enrollments,
            "pair_codes": self._pair_codes,
            "pending": {
                f"{request.device_id}|{request.client_id}": {
                    "device_id": request.device_id,
                    "client_id": request.client_id,
                    "requested_at": request.requested_at,
                }
                for device_id, request in self._pending.items()
            },
        }
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as pairing_file:
            pairing_file.write(json.dumps(data, sort_keys=True) + "\n")
        temp.chmod(0o600)
        temp.replace(self.path)
        stat = self.path.stat()
        self._file_signature = (stat.st_mtime_ns, stat.st_size)

    def _prune_enrollments(self) -> None:
        now = time.time()
        referenced = {
            str(device.get("enrollment_id"))
            for device in self._devices.values()
            if isinstance(device, dict) and device.get("enrollment_id") is not None
        }
        kept = {}
        for code_id, enrollment in self._enrollments.items():
            if not isinstance(enrollment, dict):
                continue
            try:
                expires_at = float(enrollment.get("expires_at", 0))
            except (TypeError, ValueError):
                continue
            if expires_at <= now and enrollment.get("bound_device") is None:
                continue
            if enrollment.get("spent") and code_id not in referenced:
                continue
            kept[code_id] = enrollment
        self._enrollments = kept


def default_pairing_path() -> Path:
    """Return the local file shared by the service and dashboard process."""
    data_dir = Path(
        os.environ.get("MAIPAI_BOT_DATA_DIR") or Path.home() / ".local/share/maipai-bot"
    )
    return data_dir / "stackchan-pairing.json"
