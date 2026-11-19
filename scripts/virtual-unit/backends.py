#!/usr/bin/env python3
"""The playground's backends: the Simulation (a virtual unit on this computer) or one registered robot through its host (Live), with the one-active-connection rule of owner decision 21.
Live speaks the routes of docs/plan/playground-live.md with a bearer token of scope playground; the lease must be renewed every few seconds (tick()) and the page shows the LIVE banner and the
plain refusal when another session holds the robot. Standard library only. Written against the documented routes and tested against scripts/virtual-unit/fake_host.py: the real host does not
serve the routes yet. Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid

HEARTBEAT_EVERY_S = 5.0   # a third of the host's 15 s lease


class BackendError(Exception):
    """A refusal or a failure in plain words: what went wrong and what to do."""


class Simulation:
    kind = "simulation"

    def __init__(self, unit, name: str = "Simulation") -> None:
        self.id, self.name, self.unit = "sim", name, unit

    def call_tool(self, name: str, arguments: dict) -> dict:
        return self.unit.call(name, arguments)

    def snapshot(self) -> bytes:
        return self.unit.snapshot()

    def state(self) -> dict:
        return {"clock_ms": self.unit.now_ms}

    def tick(self, now_s: float) -> None:
        pass

    def close(self) -> None:
        pass

    def banner(self) -> dict:
        return {"id": self.id, "kind": "simulation", "live": False, "message": "Simulation: nothing here touches a real robot."}


class Live:
    kind = "robot"

    def __init__(self, base_url: str, token: str, unit_id: str, name: str = "", who: str = "this playground") -> None:
        self.base, self.token, self.id, self.name, self.who = base_url.rstrip("/"), token, unit_id, name or unit_id, who
        self.session = uuid.uuid4().hex[:8]
        self.last_beat = 0.0
        self.ttl_s = 15.0
        self.held = False

    def _request(self, method: str, path: str, body: dict | None = None, raw: bool = False):
        req = urllib.request.Request(f"{self.base}/api/playground{path}", method=method, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                data = r.read()
                return data if raw else json.loads(data or b"{}")
        except urllib.error.HTTPError as e:
            try:
                why = json.loads(e.read()).get("error", "")
            except Exception:
                why = ""
            raise BackendError(why or f"The host answered {e.code}. Check that it is running and the token is right.") from None
        except (urllib.error.URLError, OSError) as e:
            raise BackendError(f"The host cannot be reached ({e.reason if hasattr(e, 'reason') else e}). Check its address and that this computer is on the same network.") from None

    def connect(self, now_s: float) -> None:
        out = self._request("POST", f"/units/{self.id}/lease", {"session": self.session, "who": self.who})
        self.session, self.ttl_s, self.last_beat, self.held = out["session"], float(out.get("ttl_s", 15)), now_s, True

    def tick(self, now_s: float) -> None:
        """Renew the lease when it is due. A lost lease ends the connection with a plain message."""
        if self.held and now_s - self.last_beat >= HEARTBEAT_EVERY_S:
            try:
                self._request("POST", f"/units/{self.id}/heartbeat", {"session": self.session})
                self.last_beat = now_s
            except BackendError:
                self.held = False
                raise

    def call_tool(self, name: str, arguments: dict) -> dict:
        if not self.held:
            raise BackendError("This playground no longer controls the robot. Connect again.")
        return self._request("POST", f"/units/{self.id}/tool", {"session": self.session, "name": name, "arguments": arguments})

    def snapshot(self) -> bytes:
        return self._request("GET", f"/units/{self.id}/snapshot", raw=True)

    def state(self) -> dict:
        return self._request("GET", f"/units/{self.id}/state")

    def close(self) -> None:
        if self.held:
            try:
                self._request("DELETE", f"/units/{self.id}/lease", {"session": self.session})
            except BackendError:
                pass   # the lease ends by itself within 15 seconds
            self.held = False

    def banner(self) -> dict:
        return {"id": self.id, "kind": "robot", "live": True, "message": f"LIVE: you are controlling {self.name}. Everything you do happens on the real robot."}


class BackendManager:
    """One active backend at a time. Simulation is always there; robots come from the host."""

    def __init__(self, simulation: Simulation, host_url: str = "", token: str = "", who: str = "this playground") -> None:
        self.sim, self.host_url, self.token, self.who = simulation, host_url, token, who
        self.active = simulation
        self.message = ""

    def _live(self, unit_id: str, name: str = "") -> Live:
        return Live(self.host_url, self.token, unit_id, name, self.who)

    def list(self) -> list[dict]:
        out = [{"id": "sim", "name": self.sim.name, "kind": "simulation", "busy_by": None}]
        if self.host_url and self.token:
            try:
                for r in Live(self.host_url, self.token, "")._request("GET", "/units"):
                    out.append({"id": r["id"], "name": r["name"], "kind": "robot", "online": r["online"], "busy_by": None if r["lease"] == "free" else r["lease"].removeprefix("held by ")})
            except BackendError as e:
                self.message = str(e)
        return out

    def connect(self, backend_id: str, now_s: float) -> dict:
        """Switch to the Simulation or take a robot. The old connection is released first. A refusal leaves the Simulation active and says why."""
        self.disconnect()
        if backend_id == "sim":
            return self.status()
        if not (self.host_url and self.token):
            self.message = "No host is set. Give the playground your host's address and a playground token first."
            return self.status()
        names = {b["id"]: b["name"] for b in self.list() if b["kind"] == "robot"}
        live = self._live(backend_id, names.get(backend_id, ""))
        try:
            live.connect(now_s)
        except BackendError as e:
            self.message = str(e)
            return self.status()
        self.active, self.message = live, ""
        return self.status()

    def disconnect(self) -> None:
        if self.active is not self.sim:
            self.active.close()
        self.active = self.sim

    def tick(self, now_s: float) -> None:
        try:
            self.active.tick(now_s)
        except BackendError as e:
            self.message = str(e)
            self.active = self.sim   # the lease is gone: back to the Simulation, with the reason on screen

    def status(self) -> dict:
        b = self.active.banner()
        if self.message:
            b = {**b, "message": self.message if self.active is self.sim else b["message"] + " " + self.message, "notice": self.message}
        return b
