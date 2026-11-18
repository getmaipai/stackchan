#!/usr/bin/env python3
"""A fake host for the playground's Live mode: the routes of docs/plan/playground-live.md (under /api/playground, JSON, a bearer token of scope playground) over a few fake robots, using the host's own
lease and scope code (host/maipai_body/playground_lease.py), so the playground's client adapter (scripts/virtual-unit/backends.py) can be built and tested before the real host serves the routes.
It is a test double: loopback only, in memory, the fake robots just record the calls they get.
Usage: python3 scripts/virtual-unit/fake_host.py [port]   Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import json
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "host"))
from maipai_body.playground_lease import LEASE_TTL_S, LeaseManager  # noqa: E402

TOKEN = "playground-test-token"   # a test value for this fake only


class FakeRobot:
    def __init__(self, uid: str, name: str, online: bool = True) -> None:
        self.id, self.name, self.online = uid, name, online
        self.profile, self.version, self.battery, self.power = "stackchan", "test", 80, "battery"
        self.calls: list[tuple[str, dict]] = []
        self.sessions: dict[str, str] = {}   # session -> who


class FakeHost:
    def __init__(self, clock=None) -> None:
        self.robots = {"r1": FakeRobot("r1", "Kitchen robot"), "r2": FakeRobot("r2", "Desk robot"), "r3": FakeRobot("r3", "Garage robot", online=False)}
        kw = {"clock": clock} if clock else {}
        self.leases = LeaseManager(**kw)
        self.token = TOKEN
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self, port: int = 0) -> str:
        host = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _json(self, code: int, body) -> None:
                data = json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _auth(self) -> bool:
                if self.headers.get("Authorization") != f"Bearer {host.token}":
                    self._json(401, {"error": "The playground token is missing or wrong. Make one on the host's settings page and paste it in."})
                    return False
                return True

            def _body(self) -> dict:
                n = int(self.headers.get("Content-Length", 0))
                return json.loads(self.rfile.read(n) or b"{}")

            def do_GET(self):
                if not self._auth():
                    return
                parts = self.path.split("?")[0].strip("/").split("/")
                if parts[:2] != ["api", "playground"]:
                    return self._json(404, {"error": "not found"})
                if parts[2:] == ["units"]:
                    return self._json(200, [{"id": r.id, "name": r.name, "online": r.online, "profile": r.profile, "version": r.version, "battery": r.battery, "power": r.power,
                                             "lease": "free" if host.leases.holder(r.id) is None else f"held by {host.leases.holder(r.id)}"} for r in host.robots.values()])
                if len(parts) == 5 and parts[2] == "units" and parts[4] == "state":
                    r = host.robots.get(parts[3])
                    return self._json(200, {"head": {"yaw": 0, "pitch": 0}, "battery": r.battery, "power": r.power, "events": []}) if r else self._json(404, {"error": "no such robot"})
                if len(parts) == 5 and parts[2] == "units" and parts[4] == "snapshot":
                    data = b"\x89PNG\r\n\x1a\nfake"
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                self._json(404, {"error": "not found"})

            def do_POST(self):
                if not self._auth():
                    return
                parts = self.path.split("?")[0].strip("/").split("/")
                req = self._body()
                if parts[:2] != ["api", "playground"] or len(parts) != 5 or parts[2] != "units" or parts[3] not in host.robots:
                    return self._json(404, {"error": "no such robot"})
                r, action = host.robots[parts[3]], parts[4]
                if not r.online:
                    return self._json(409, {"error": f"{r.name} is offline. Turn it on and check its Wi-Fi."})
                if action == "lease":
                    session = req.get("session") or uuid.uuid4().hex[:8]
                    ok, why = host.leases.acquire(r.id, session, str(req.get("who", "a playground")))
                    return self._json(200, {"session": session, "ttl_s": LEASE_TTL_S}) if ok else self._json(409, {"error": why})
                if action == "heartbeat":
                    return self._json(200, {"ok": True}) if host.leases.heartbeat(r.id, str(req.get("session"))) else self._json(410, {"error": "The robot is no longer yours: another session took it or you stopped answering. Connect again."})
                if action == "tool":
                    ok, why = host.leases.check(r.id, str(req.get("session")), str(req.get("name")))
                    if not ok:
                        return self._json(403, {"error": why})
                    r.calls.append((str(req.get("name")), req.get("arguments") or {}))
                    return self._json(200, {"ok": True})
                self._json(404, {"error": "not found"})

            def do_DELETE(self):
                if not self._auth():
                    return
                parts = self.path.split("?")[0].strip("/").split("/")
                req = self._body()
                if len(parts) == 5 and parts[3] in host.robots and parts[4] == "lease":
                    host.leases.release(parts[3], str(req.get("session")))
                    return self._json(200, {"ok": True})
                self._json(404, {"error": "not found"})

        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return f"http://127.0.0.1:{self.server.server_port}"

    def stop(self) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()


if __name__ == "__main__":
    h = FakeHost()
    url = h.start(int(sys.argv[1]) if len(sys.argv) > 1 else 8797)
    print(f"fake playground host on {url}  (bearer token {TOKEN})", flush=True)
    threading.Event().wait()
