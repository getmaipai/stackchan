"""Encrypted robot link: TLS 1.2 with a pre-shared key (PSK), no certificates.

Design note: docs/design/encrypted-link.md. The unit and the host both hold
the same secret from pairing, so a stranger on the network can neither read the traffic nor pose as
either side. The PSK is derived (HKDF-SHA256) from the pairing secret, never the secret itself.

Nothing here logs, returns or stores a PSK. Logs name a unit by the last five characters of its id.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import ssl
import time
from collections import OrderedDict
from typing import Any

from .link_exchange import psk_from_key
from .pairing import PairingStore

LOG = logging.getLogger(__name__)

# One place for every port of the encrypted link. Each sits next to its plain port during the
# transition (voice 8765, avatar and camera 8766, photo and notification route 8767).
VOICE_TLS_PORT = 18775
AVATAR_TLS_PORT = 18776
HTTP_TLS_PORT = 8777

MODE_REQUIRED = "required"
MODE_ALLOWED = "allowed"
MODE_OFF = "off"
MODES = (MODE_REQUIRED, MODE_ALLOWED, MODE_OFF)
DEFAULT_MODE = MODE_ALLOWED  # an existing unit keeps working until it is moved over

# The hello feature a unit sends to say it can speak the encrypted link.
FEATURE_TLS_PSK = "tls_psk"

# Public, fixed, versioned. The firmware and Home use the same bytes.
PSK_SALT = b""  # empty: RFC 5869 then uses a string of 32 zero bytes
PSK_INFO_PREFIX = b"maipai-stackchan-link-psk-v1\x00"
PSK_LENGTH = 32

# TLS 1.2 only (OpenSSL and the unit's mbedTLS speak PSK in 1.2). Forward secrecy first, then plain PSK.
PSK_CIPHERS = (
    "ECDHE-PSK-CHACHA20-POLY1305:ECDHE-PSK-AES128-CBC-SHA256:"
    "PSK-AES128-GCM-SHA256:PSK-AES256-GCM-SHA384"
)


def hkdf_sha256(ikm: bytes, salt: bytes, info: bytes, length: int) -> bytes:
    """RFC 5869 extract and expand with HMAC-SHA256."""
    prk = hmac.new(salt or b"\x00" * 32, ikm, hashlib.sha256).digest()
    out, block, counter = b"", b"", 1
    while len(out) < length:
        block = hmac.new(prk, block + info + bytes([counter]), hashlib.sha256).digest()
        out += block
        counter += 1
    return out[:length]


def normalize_identity(device_id: str) -> str:
    """The PSK identity: the unit's Device-Id (its MAC address), lower case."""
    return device_id.strip().lower()


def token_digest(token: str) -> str:
    """What the host keeps of a device token: SHA-256 of its text, as 64 hex characters.

    The unit computes the same digest from the token it holds, so both sides share the input
    material and the host never needs the token itself."""
    return hashlib.sha256(token.encode()).hexdigest()


def derive_psk(token_sha256_hex: str, device_id: str) -> bytes:
    """PSK = HKDF-SHA256(ikm = SHA-256(token) as 32 raw bytes, salt = empty,
    info = "maipai-stackchan-link-psk-v1" 0x00 identity, L = 32)."""
    ikm = bytes.fromhex(token_sha256_hex)
    info = PSK_INFO_PREFIX + normalize_identity(device_id).encode()
    return hkdf_sha256(ikm, PSK_SALT, info, PSK_LENGTH)


class ReplayGuard:
    """Refuses a session id that is stale or was never issued.

    The host issues one id per connection (in its hello reply). A frame that names any other id,
    including an id from an earlier connection, is refused. A frame with no id is tolerated (older
    units), so only a replayed or wrong id is refused."""

    def __init__(self, remember: int = 256) -> None:
        self._active: dict[str, str] = {}
        self._retired: OrderedDict[str, float] = OrderedDict()
        self._remember = remember

    def issue(self, device_id: str, session_id: str) -> None:
        old = self._active.get(device_id)
        if old is not None:
            self._retired[old] = time.monotonic()
            while len(self._retired) > self._remember:
                self._retired.popitem(last=False)
        self._active[device_id] = session_id

    def release(self, device_id: str, session_id: str) -> None:
        if self._active.get(device_id) == session_id:
            self._active.pop(device_id, None)
            self._retired[session_id] = time.monotonic()
            while len(self._retired) > self._remember:
                self._retired.popitem(last=False)

    def accepts(self, device_id: str, session_id: object) -> bool:
        if session_id is None or session_id == "":
            return True
        if not isinstance(session_id, str):
            return False
        if session_id in self._retired:
            return False
        return self._active.get(device_id) == session_id


class LinkSecurity:
    """Policy, key lookup and state for the encrypted link of every paired unit."""

    def __init__(self, pairing: PairingStore) -> None:
        self.pairing = pairing
        self.replay = ReplayGuard()
        self._current: dict[str, bool] = {}  # device id -> the live connection is encrypted

    # -- keys ----------------------------------------------------------------------------------
    def psk_for_identity(self, identity: str | None) -> bytes:
        """The PSK for a handshake identity, or empty bytes (the handshake then fails)."""
        if not identity:
            return b""
        key = self.pairing.link_key(identity)
        if key:  # paired with the key exchange: no value that crossed the network is an input
            return psk_from_key(key, identity)
        digest = self.pairing.link_material(identity)
        if not digest:
            return b""
        try:
            return derive_psk(digest, identity)
        except ValueError:
            return b""

    def ssl_context(self) -> ssl.SSLContext:
        """A server context for one encrypted listener (TLS 1.2, PSK suites, no certificate)."""
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.maximum_version = ssl.TLSVersion.TLSv1_2
        context.set_ciphers(PSK_CIPHERS)
        context.set_psk_server_callback(self.psk_for_identity)
        return context

    # -- policy --------------------------------------------------------------------------------
    def mode(self, device_id: str) -> str:
        return self.pairing.link_mode(device_id) or DEFAULT_MODE

    def refusal(self, device_id: str, encrypted: bool) -> str | None:
        """Plain words for why this connection is refused, or None when it is allowed."""
        mode = self.mode(device_id)
        if not encrypted and mode == MODE_REQUIRED:
            return (
                "This robot must use the encrypted link. Connect to the encrypted port, or set "
                "the link to allowed in Settings, Security."
            )
        if encrypted and mode == MODE_OFF:
            return (
                "The encrypted link is switched off for this robot. Turn it back on in "
                "Settings, Security, or connect to the plain port."
            )
        return None

    def note_connected(self, device_id: str, encrypted: bool) -> None:
        self._current[device_id] = encrypted
        if encrypted:
            self.pairing.mark_seen_encrypted(device_id)

    def note_disconnected(self, device_id: str) -> None:
        self._current.pop(device_id, None)

    def note_features(self, device_id: str, features: Any) -> None:
        """A unit that says it can encrypt, on a new pairing with no choice made, moves to required."""
        if isinstance(features, dict) and features.get(FEATURE_TLS_PSK) is True:
            if self.pairing.promote_new_link(device_id):
                LOG.info(
                    "StackChan link: unit ...%s reports encryption support; the link is now "
                    "required for it",
                    device_id[-5:],
                )

    # -- what the settings page shows ----------------------------------------------------------
    def state(self, device_id: str) -> str:
        """encrypted, plain_allowed, plain or never_seen."""
        mode = self.mode(device_id)
        if mode == MODE_OFF:
            return "plain"
        record = self.pairing.link_record(device_id)
        current = self._current.get(device_id)
        if current is True:
            return "encrypted"
        if record.get("seen_encrypted"):
            return "encrypted" if mode == MODE_REQUIRED else "plain_allowed"
        return "never_seen"

    def view(self, device_id: str) -> dict[str, Any]:
        """JSON for the page. Holds no key material."""
        return {
            "device_id": device_id,
            "mode": self.mode(device_id),
            "modes": list(MODES),
            "state": self.state(device_id),
            "connected": device_id in self._current,
            "connected_encrypted": self._current.get(device_id),
            "ports": {"voice": VOICE_TLS_PORT, "avatar": AVATAR_TLS_PORT, "http": HTTP_TLS_PORT},
        }

    def set_mode(self, device_id: str, mode: object) -> dict[str, Any]:
        if mode not in MODES:
            raise ValueError(
                "The link choice must be required, allowed or off. Pick one of the three."
            )
        if not self.pairing.set_link_mode(device_id, str(mode)):
            raise ValueError("This robot is not paired. Pair it first, then choose its link.")
        return self.view(device_id)
