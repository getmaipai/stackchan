"""Who counts as the local administrator of the settings pages .

A request is local only when its peer is this computer, its Host header names this computer and no
proxy header is present. A page on another site that re-points its name at 127.0.0.1 fails the Host
check; a reverse proxy in front of the page fails the proxy-header check, so putting the page on a
network address does not turn every visitor into an administrator.
"""

from __future__ import annotations

from collections.abc import Mapping

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
