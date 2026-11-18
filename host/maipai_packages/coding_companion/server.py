"""The agent's endpoint: POST /status on 127.0.0.1 with the package's own token.

Its token is not the settings token and lives in its own 0600 file. A request must name this computer in
Host, carry no Origin header (a web page in a browser cannot post here), be JSON, be small, and hold the
token as a Bearer header; ten wrong tokens in a minute lock the endpoint for a minute. The endpoint sends
nothing back but a short acknowledgement. No status text is logged."""

from __future__ import annotations

import json
import logging
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from maipai_body.local_guard import SettingsAuth, host_is_local
from maipai_packages.coding_companion.state import LIGHT, LIGHT_SECONDS, AgentStatus

LOG = logging.getLogger("maipai_packages.coding_companion")
MAX_BODY = 2048


class AgentAuth(SettingsAuth):
    """The same token file and lockout as the settings token, but only a Bearer header counts (no cookie, no address)."""

    def candidate(self, headers, query: str) -> str:
        auth = headers.get("Authorization", "")
        return auth[7:].strip() if auth.lower().startswith("bearer ") else ""


class _Handler(BaseHTTPRequestHandler):
    server: AgentServer

    def log_message(self, *_args: object) -> None:
        return

    def _reply(self, status: int, message: str) -> None:
        body = json.dumps({"ok": status == 200, "message": message}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        if self.client_address[0] not in ("127.0.0.1", "::1") or not host_is_local(self.headers.get("Host", "")):
            return self._reply(HTTPStatus.FORBIDDEN, "This endpoint answers only on this computer.")
        if self.headers.get("Origin") is not None:
            return self._reply(HTTPStatus.FORBIDDEN, "A web page cannot post here.")
        if urlsplit(self.path).path != "/status":
            return self._reply(HTTPStatus.NOT_FOUND, "Post to /status.")
        if self.headers.get_content_type() != "application/json":
            return self._reply(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "Send application/json.")
        if not self.server.auth.valid(self.headers, "", self.client_address[0]):
            return self._reply(HTTPStatus.UNAUTHORIZED, "The token is missing or wrong. Read it from the coding companion token file.")
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._reply(HTTPStatus.BAD_REQUEST, "Content-Length must be a number.")
        if not 0 < length <= MAX_BODY:
            return self._reply(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, f"Send at most {MAX_BODY} bytes.")
        try:
            message = json.loads(self.rfile.read(length))
        except ValueError:
            return self._reply(HTTPStatus.BAD_REQUEST, "The body must be JSON.")
        if not isinstance(message, dict):
            return self._reply(HTTPStatus.BAD_REQUEST, "The body must be a JSON object.")
        view = self.server.status.update(message)
        if view is None:
            return self._reply(HTTPStatus.BAD_REQUEST, "state must be working, waiting or finished.")
        LOG.info("coding agent state %s", view.state)  # the state only, never the text
        self.server.present(view)
        self._reply(HTTPStatus.OK, "shown")


class AgentServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, status: AgentStatus, auth: AgentAuth, present, port: int = 8052) -> None:
        super().__init__(("127.0.0.1", port), _Handler)  # loopback only
        self.status, self.auth, self.present = status, auth, present
        self._thread: threading.Thread | None = None

    @property
    def port(self) -> int:
        return self.server_address[1]

    def start(self) -> None:
        self._thread = threading.Thread(target=self.serve_forever, name="coding-companion", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.shutdown()
        self.server_close()


def make_presenter(bus, devices) -> callable:
    """Show a state on every connected unit through the command bus, as the source `agent` (set here, never by the message)."""
    from maipai_body.command_bus import Command

    last: dict[str, tuple[str, str]] = {}

    def present(view) -> None:
        for device_id in devices():
            changed = last.get(device_id) != (view.state, view.kind)
            last[device_id] = (view.state, view.kind)
            bus.send(device_id, Command("light.look", {"color": LIGHT[view.state], "seconds": LIGHT_SECONDS}, source="agent"))
            if view.state == "waiting" and changed:  # a repeated post of the same state refreshes the light but never pings again
                bus.send(device_id, Command("sound.play", {"name": "popup"}, source="agent"))

    return present


def default_token_path() -> Path:
    from maipai_body.bodies.stackchan.xiaozhi.pairing import default_pairing_path

    return default_pairing_path().parent / "coding-companion-token"
