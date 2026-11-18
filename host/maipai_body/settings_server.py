# ruff: noqa: E501
"""The core settings page served by the running StackChan host (loopback only).

The same routes the dashboard has, hosted next to the live voice link so the page shows live unit
state. Only the machine running the host can open it.
"""

from __future__ import annotations

import json
import logging
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from maipai_body import local_guard
from maipai_body.i18n import normalize
from maipai_body.settings_page import SettingsBackend

LOG = logging.getLogger(__name__)
LOOPBACK = {"127.0.0.1", "::1"}
FAILED = (
    "The host hit an unexpected problem with that action and nothing was changed. "
    "Press the button again; if it keeps failing, restart the host and check its log."
)


class _Handler(BaseHTTPRequestHandler):
    server: SettingsServer

    def log_message(self, *_args: object) -> None:
        return

    def _reply(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: int, message: str) -> None:
        self._reply(status, json.dumps({"error": message}).encode(), "application/json")

    def _local(self) -> bool:
        return local_guard.request_is_local(self.client_address[0], self.headers)

    def _host_refused(self) -> bool:
        """A name that is not this computer (a rebound hostname) reads nothing."""
        if local_guard.host_is_local(self.headers.get("Host", "")):
            return False
        self._error(
            HTTPStatus.FORBIDDEN,
            "That request named another address. Open the settings page on this host at "
            "http://127.0.0.1.",
        )
        return True

    def do_GET(self) -> None:  # noqa: N802
        if self._host_refused():
            return
        parts = urlsplit(self.path)
        lang = (parse_qs(parts.query).get("lang") or [""])[0] or self.headers.get(
            "Accept-Language", ""
        ).split(",")[0] or self.server.backend.language
        try:
            routed = self.server.backend.route_get(parts.path, normalize(lang), self._local())
        except Exception:
            LOG.warning("settings page GET %s failed", parts.path, exc_info=True)
            return self._error(HTTPStatus.INTERNAL_SERVER_ERROR, FAILED)
        if routed is None:
            return self._error(HTTPStatus.NOT_FOUND, "Open /settings on this host.")
        status, content_type, body = routed
        self._reply(status, body, content_type)

    def do_POST(self) -> None:  # noqa: N802
        host, origin = self.headers.get("Host", ""), self.headers.get("Origin")
        if host.rsplit(":", 1)[0] not in {"127.0.0.1", "localhost", "[::1]"} or (
            origin is not None and urlsplit(origin).netloc != host
        ):
            return self._error(
                HTTPStatus.FORBIDDEN,
                "That request came from another page. Open the settings page on this host.",
            )
        if self.headers.get_content_type() != "application/json":
            return self._error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "Send application/json.")
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._error(HTTPStatus.BAD_REQUEST, "The Content-Length header is not a number.")
        limit = (
            local_guard.MAX_PICTURE_BODY if "picture" in self.path else local_guard.MAX_JSON_BODY
        )
        if length < 0 or length > limit:
            return self._error(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "That request is too large. Send less data, or use a smaller picture.",
            )
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError("The body must be a JSON object.")
        except ValueError as error:
            return self._error(HTTPStatus.BAD_REQUEST, str(error))
        try:
            routed = self.server.backend.route_post(urlsplit(self.path).path, body, self._local())
        except Exception:
            LOG.warning("settings page POST %s failed", urlsplit(self.path).path, exc_info=True)
            return self._error(HTTPStatus.INTERNAL_SERVER_ERROR, FAILED)
        if routed is None:
            return self._error(HTTPStatus.NOT_FOUND, "Open /settings on this host.")
        status, payload = routed
        self._reply(status, json.dumps(payload).encode(), "application/json")


class SettingsServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, backend: SettingsBackend, host: str = "127.0.0.1", port: int = 8051) -> None:
        super().__init__((host, port), _Handler)
        self.backend = backend
        self._thread: threading.Thread | None = None

    @property
    def port(self) -> int:
        return self.server_address[1]

    def start(self) -> None:
        self._thread = threading.Thread(target=self.serve_forever, name="settings-page", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.shutdown()
        self.server_close()
