"""Who counts as the host computer's own user of the settings pages, and the settings token.

A request is local when its peer is this computer, its Host header names this computer and no
proxy header is present. The settings token (see SettingsAuth) lets a phone use the settings pages."""

from __future__ import annotations

import hmac
import re
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


_PORT = re.compile(r"^[0-9]{1,5}$")


def host_is_local(host_header: str) -> bool:
    """The Host header names this computer: 127.0.0.1, localhost or [::1], with at most a port after it."""
    value = host_header.strip().lower()
    if value.startswith("["):
        name, _, rest = value.partition("]")
        name += "]"
        if rest and not (rest.startswith(":") and _PORT.match(rest[1:])):
            return False
    else:
        name, sep, port = value.partition(":")
        if sep and not _PORT.match(port):
            return False
    return name in LOCAL_HOSTS


def request_is_local(peer: str, headers: Mapping[str, str]) -> bool:
    lowered = {key.lower() for key in headers.keys()}
    if any(name in lowered for name in PROXY_HEADERS):
        return False
    return peer in LOOPBACK_PEERS and host_is_local(headers.get("Host", ""))


COOKIE = "maipai_settings"
TOKEN_TRIES = 10  # wrong tokens from one address in a window lock that address only
TOKEN_TRIES_TOTAL = 200  # wrong tokens from all addresses together in a window lock every address that has not logged in before
TOKEN_WINDOW_S = 60.0


class SettingsAuth:
    """A per-install secret that logs a phone in to the settings page (requests that are not local).

    The token is kept in a 0600 file next to the pairing file; `stackchan settings-token` prints it.
    It travels in a header, a cookie (set on first visit with ?token=) or the first address, and a
    run of wrong tries locks the login for a minute."""

    def __init__(self, path: Path, clock=time.monotonic) -> None:
        self._path, self._clock = Path(path), clock
        self._fails: dict[str, list[float]] = {}
        self._total: list[float] = []
        self._known: set[str] = set()  # addresses that logged in with the right token: the spray lock does not apply to them
        self._lock = threading.Lock()
        self.token = self._load()

    def _load(self) -> str:
        try:
            value = self._path.read_text().strip()
            if len(value) >= 32:
                try:
                    if self._path.stat().st_mode & 0o077:  # made by hand or restored from a backup: tighten it (review fix)
                        self._path.chmod(0o600)
                except OSError:
                    pass
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

    def valid(self, headers: Mapping[str, str], query: str, source: str = "") -> bool:
        """True when a token in the request is the right one. Wrong tries are counted per source address (ten a
        minute locks that address, so one device guessing never blocks the owner's phone) and in total (a spray from
        many addresses locks the page for a minute for addresses that never logged in; an address that has logged in keeps its own budget)."""
        given = self.candidate(headers, query)
        if not given:
            return False
        now = self._clock()
        with self._lock:
            self._total = [t for t in self._total if now - t < TOKEN_WINDOW_S]
            mine = [t for t in self._fails.get(source, []) if now - t < TOKEN_WINDOW_S]
            spray = len(self._total) >= TOKEN_TRIES_TOTAL and source not in self._known
            if spray or len(mine) >= TOKEN_TRIES:
                self._fails[source] = mine
                return False
            if hmac.compare_digest(given.encode("utf-8", "replace"), self.token.encode("utf-8")):
                self._fails[source] = mine
                if source and len(self._known) < 256:
                    self._known.add(source)
                return True
            mine.append(now)
            self._fails[source] = mine
            self._total.append(now)
            if len(self._fails) > 1024:  # forget quiet addresses
                self._fails = {k: v for k, v in self._fails.items() if v and now - v[-1] < TOKEN_WINDOW_S}
            return False
