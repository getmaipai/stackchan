"""Who counts as the host computer's own user of the settings pages, and the settings token.

A request is local when its peer is this computer, its Host header names this computer and no
proxy header is present. The settings token (see SettingsAuth) lets a phone use the settings pages."""

from __future__ import annotations

import hmac
import os
import secrets
import threading
import time
from collections.abc import Mapping
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs

LOOPBACK_PEERS = frozenset({"127.0.0.1", "::1"})
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "[::1]"})
PROXY_HEADERS = ("forwarded", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "x-real-ip", "via")
# A JSON body larger than this is refused before it is read (pictures have their own, larger cap).
MAX_JSON_BODY = 1024 * 1024
MAX_PICTURE_BODY = 72 * 1024 * 1024  # base64 of the largest picture the host accepts (12 megapixels RGBA)


def host_is_local(host_header: str) -> bool:
    name = host_header.strip()
    if name.startswith("["):
        name = name.split("]", 1)[0] + "]"
    else:
        name = name.rsplit(":", 1)[0] if ":" in name else name
    return name.lower() in LOCAL_HOSTS


def request_is_local(peer: str, headers: Mapping[str, str]) -> bool:
    lowered = {key.lower() for key in headers.keys()}
    if any(name in lowered for name in PROXY_HEADERS):
        return False
    return peer in LOOPBACK_PEERS and host_is_local(headers.get("Host", ""))


COOKIE = "maipai_settings"
TOKEN_TRIES = 10  # wrong tokens in a window lock the login (for everyone, the right token included)
TOKEN_WINDOW_S = 60.0


class SettingsAuth:
    """A per-install secret that logs a phone in to the settings page (requests that are not local).

    The token is kept in a 0600 file next to the pairing file; `stackchan settings-token` prints it.
    It travels in a header, a cookie (set on first visit with ?token=) or the first address, and a
    run of wrong tries locks the login for a minute."""

    def __init__(self, path: Path, clock=time.monotonic) -> None:
        self._path, self._clock = Path(path), clock
        self._fails: list[float] = []
        self._lock = threading.Lock()
        self.token = self._load()

    def _load(self) -> str:
        try:
            value = self._path.read_text().strip()
            if len(value) >= 32:
                return value
        except OSError:
            pass
        value = secrets.token_urlsafe(32)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self._path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write(value + "\n")
        self._path.chmod(0o600)
        return value

    def candidate(self, headers: Mapping[str, str], query: str) -> str:
        auth = headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
        query_token = (parse_qs(query).get("token") or [""])[0]
        if query_token:  # a fresh link wins over an old cookie
            return query_token
        cookie = SimpleCookie()
        try:
            cookie.load(headers.get("Cookie", ""))
        except Exception:
            pass
        return cookie[COOKIE].value if COOKIE in cookie else ""

    def valid(self, headers: Mapping[str, str], query: str) -> bool:
        given = self.candidate(headers, query)
        if not given:
            return False
        now = self._clock()
        with self._lock:
            self._fails = [t for t in self._fails if now - t < TOKEN_WINDOW_S]
            if len(self._fails) >= TOKEN_TRIES:
                return False
            if hmac.compare_digest(given, self.token):
                return True
            self._fails.append(now)
            return False
