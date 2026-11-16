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

from maipai_body.i18n import normalize
from maipai_body.settings_page import SettingsBackend

LOG = logging.getLogger(__name__)
LOOPBACK = {"127.0.0.1", "::1"}


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
        return self.client_address[0] in LOOPBACK

    def do_GET(self) -> None:  # noqa: N802
        parts = urlsplit(self.path)
        lang = (parse_qs(parts.query).get("lang") or [""])[0] or self.headers.get(
            "Accept-Language", ""
        ).split(",")[0] or self.server.backend.language
        routed = self.server.backend.route_get(parts.path, normalize(lang), self._local())
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
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            if not isinstance(body, dict):
                raise ValueError("The body must be a JSON object.")
        except ValueError as error:
            return self._error(HTTPStatus.BAD_REQUEST, str(error))
        routed = self.server.backend.route_post(urlsplit(self.path).path, body, self._local())
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
