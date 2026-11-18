"""Host half of the link key exchange (docs/plan/link-key-exchange.md): X25519 plus a six-digit code the unit shows and the owner types.

Nothing here touches the network or the pairing file. `HostExchange` is one unit's exchange; `ExchangeRegistry` keeps one per unit and the
attempt limits. The key schedule matches the reference vectors in scripts/link-key-vector.py (the unit's key schedule matches them too).
The device token is not an input anywhere. No key, nonce or code is ever logged."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from collections.abc import Callable

P = 2**255 - 19
A24 = 121665
BASE = (9).to_bytes(32, "little")
EXCHANGE_TTL_S = 300.0  # the owner has five minutes to type the code
MAX_WRONG_CODES = 3  # wrong codes for one unit before it must wait
LOCK_S = 600.0
KEY_INFO = b"maipai-stackchan-link-key-v2\x00"
PSK_INFO = b"maipai-stackchan-link-psk-v2\x00"


class ExchangeError(ValueError):
    """The exchange stopped. The message is plain words for the owner; nothing secret is in it."""


def x25519(k: bytes, u: bytes) -> bytes:
    """RFC 7748 section 5 (a constant-shape Montgomery ladder; used once per pairing)."""
    b = bytearray(k)
    b[0] &= 248
    b[31] &= 127
    b[31] |= 64
    kk = int.from_bytes(b, "little")
    x1 = int.from_bytes(u, "little") & ((1 << 255) - 1)
    x2, z2, x3, z3, swap = 1, 0, x1, 1, 0
    for t in range(254, -1, -1):
        bit = (kk >> t) & 1
        swap ^= bit
        if swap:
            x2, x3, z2, z3 = x3, x2, z3, z2
        swap = bit
        a = (x2 + z2) % P
        aa = a * a % P
        bb_ = (x2 - z2) % P
        bb = bb_ * bb_ % P
        e = (aa - bb) % P
        c = (x3 + z3) % P
        d = (x3 - z3) % P
        da = d * a % P
        cb = c * bb_ % P
        x3 = pow(da + cb, 2, P)
        z3 = x1 * pow(da - cb, 2, P) % P
        x2 = aa * bb % P
        z2 = e * (aa + A24 * e) % P
    if swap:
        x2, x3, z2, z3 = x3, x2, z3, z2
    return (x2 * pow(z2, P - 2, P) % P).to_bytes(32, "little")


def hkdf(ikm: bytes, salt: bytes, info: bytes, length: int) -> bytes:
    prk = hmac.new(salt or b"\x00" * 32, ikm, hashlib.sha256).digest()
    out, block, counter = b"", b"", 1
    while len(out) < length:
        block = hmac.new(prk, block + info + bytes([counter]), hashlib.sha256).digest()
        out += block
        counter += 1
    return out[:length]


def commit(pk_h: bytes, pk_u: bytes, n_h: bytes) -> bytes:
    return hashlib.sha256(b"mp-commit" + pk_h + pk_u + n_h).digest()


def sas(pk_u: bytes, pk_h: bytes, n_u: bytes, n_h: bytes) -> str:
    digest = hashlib.sha256(b"mp-sas" + pk_u + pk_h + n_u + n_h).digest()
    return "%06d" % (int.from_bytes(digest[:4], "big") % 1000000)


def link_key(z: bytes, pk_u: bytes, pk_h: bytes, n_u: bytes, n_h: bytes, device_id: str) -> bytes:
    salt = hashlib.sha256(pk_u + pk_h + n_u + n_h).digest()
    return hkdf(z, salt, KEY_INFO + device_id.lower().encode(), 32)


def psk_from_key(key: bytes, identity: str) -> bytes:
    """The TLS pre-shared key the callbacks hand to the TLS library, from the stored link key."""
    return hkdf(key, b"", PSK_INFO + identity.lower().encode(), 32)


class HostExchange:
    """One exchange for one unit: pair_start, nonce, code, key."""

    def __init__(self, *, rand: Callable[[int], bytes] = secrets.token_bytes, clock: Callable[[], float] = time.monotonic) -> None:
        self._rand, self._clock = rand, clock
        self.device_id = ""
        self._started = 0.0
        self._sk = self._pk_u = self._pk_h = self._n_h = self._n_u = None
        self.expected = ""
        self.finished = False
        self.aborted = False
        self.start_reply: dict[str, bytes] = {}
        self._stage = "new"

    def keys_held(self) -> bool:
        return any(v is not None for v in (self._sk, self._n_h, self._n_u))

    def _drop(self) -> None:
        self._sk = self._n_h = self._n_u = None

    def start(self, device_id: str, pk_u: bytes) -> dict[str, bytes]:
        if self._stage != "new":
            raise ExchangeError("The pairing exchange is already running. Restart pairing on the robot.")
        if len(pk_u) != 32:
            raise ExchangeError("The robot's key has the wrong size. Restart pairing on the robot.")
        self._sk = self._rand(32)
        self._pk_h = x25519(self._sk, BASE)
        z = x25519(self._sk, pk_u)
        if z == b"\x00" * 32:  # a low-order point: the shared secret would not depend on the secret key
            self._drop()
            self.aborted = True
            raise ExchangeError("The robot's key is not usable. Restart pairing on the robot.")
        self.device_id, self._pk_u, self._n_h, self._started, self._stage = device_id.lower(), pk_u, self._rand(16), self._clock(), "started"
        self.start_reply = {"pk_h": self._pk_h, "c": commit(self._pk_h, pk_u, self._n_h)}
        return self.start_reply

    def reveal(self, n_u: bytes) -> dict[str, bytes]:
        if self._stage != "started":
            raise ExchangeError("The pairing messages arrived in the wrong order. Restart pairing on the robot.")
        if len(n_u) != 16:
            self._drop()
            self.aborted = True
            raise ExchangeError("The robot's number has the wrong size. Restart pairing on the robot.")
        self._n_u, self._stage = n_u, "waiting_for_code"
        self.expected = sas(self._pk_u, self._pk_h, n_u, self._n_h)
        return {"n_h": self._n_h}

    def approve(self, code: str) -> bytes:
        """The owner typed the six digits shown on the robot. Returns the link key; a wrong code ends the exchange for good."""
        if self._stage != "waiting_for_code" or self.aborted or self.finished:
            raise ExchangeError("This pairing is not waiting for a code. Restart pairing on the robot.")
        if self._clock() - self._started > EXCHANGE_TTL_S:
            self._drop()
            self.aborted = True
            raise ExchangeError("The code was not typed in time: it took too long. Restart pairing on the robot.")
        if len(code) != 6 or not code.isdigit() or not hmac.compare_digest(code, self.expected):
            self._drop()
            self.aborted = True
            raise ExchangeError("The code did not match. Nothing was paired.")
        key = link_key(x25519(self._sk, self._pk_u), self._pk_u, self._pk_h, self._n_u, self._n_h, self.device_id)
        self._drop()
        self.finished = True
        return key


class ExchangeRegistry:
    """One live exchange per unit, with a wait after too many wrong codes."""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic, rand: Callable[[int], bytes] = secrets.token_bytes) -> None:
        self._clock, self._rand = clock, rand
        self._lock = threading.Lock()
        self._live: dict[str, HostExchange] = {}
        self._wrong: dict[str, list[float]] = {}
        self.results: dict[str, str] = {}  # device id -> "paired" or "failed" once an exchange ended (read by the socket that waits)
        self.client_ids: dict[str, str] = {}

    def begin(self, device_id: str, pk_u: bytes, client_id: str = "") -> HostExchange:
        key = device_id.lower()
        with self._lock:
            now = self._clock()
            recent = [t for t in self._wrong.get(key, []) if now - t < LOCK_S]
            self._wrong[key] = recent
            if len(recent) >= MAX_WRONG_CODES:
                raise ExchangeError("Too many wrong codes for this robot. Wait 10 minutes, then pair again.")
            held = self._live.get(key)
            if held is not None and not held.aborted and not held.finished:
                if self._clock() - held._started > EXCHANGE_TTL_S:
                    self._live.pop(key, None)  # nobody finished it: it is gone
                elif held._pk_u != pk_u:
                    # Another start for the same unit while the owner reads the digits: keep the first (a peer that only knows the
                    # unit's id must not push the owner's pairing out). The same unit starting again with its own key replaces it.
                    raise ExchangeError("A pairing for this robot is already waiting for its code. Finish it, or wait a few minutes and start again.")
            exchange = HostExchange(rand=self._rand, clock=self._clock)
            exchange.start(key, pk_u)
            self._live[key] = exchange
            self.client_ids[key] = client_id
            self.results.pop(key, None)
            return exchange

    def reveal(self, device_id: str, n_u: bytes) -> dict[str, bytes]:
        return self._get(device_id).reveal(n_u)

    def _get(self, device_id: str) -> HostExchange:
        with self._lock:
            exchange = self._live.get(device_id.lower())
        if exchange is None:
            raise ExchangeError("No pairing is waiting for this robot. Restart pairing on the robot.")
        return exchange

    def approve(self, device_id: str, code: str) -> bytes:
        exchange = self._get(device_id)
        key = device_id.lower()
        try:
            result = exchange.approve(code)
            self.results[key] = "paired"
            return result
        except ExchangeError:
            if exchange.aborted:
                with self._lock:
                    self._wrong.setdefault(key, []).append(self._clock())
                self.results[key] = "failed"
            raise
        finally:
            if exchange.finished or exchange.aborted:
                with self._lock:
                    self._live.pop(key, None)

    def pending_devices(self) -> list[str]:
        """Units whose six digits are waiting to be typed (for the pairing card)."""
        with self._lock:
            now = self._clock()
            for device in [d for d, e in self._live.items() if now - e._started > EXCHANGE_TTL_S]:
                self._live.pop(device, None)  # a unit that dropped, or a made-up one, does not stay on the card
            return [d for d, e in self._live.items() if e._stage == "waiting_for_code" and not e.aborted]
