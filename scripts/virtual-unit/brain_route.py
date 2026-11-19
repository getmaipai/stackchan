"""The brain route of the virtual unit (owner decision 34): hosted (route A, the vendor's servers) or custom (route B), and what each keeps in the unit's settings store.

The model follows the firmware track's cloud-brain test (docs/plan/cloud-brain-firmware-test.md): the host pairing lives in the NVS namespace `websocket` (and `mqtt` is not built); the hosted
link's answer from the vendor is written only to `cl_websocket` and `cl_mqtt`, never over the host pairing. Joining hosted writes the cl_ namespaces; leaving it (switch to custom) wipes
them, leaves the host pairing and every other setting alone, and shows the "Hosted link removed" notice (patch UX20). Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

HOST_NS = ("websocket",)
HOSTED_NS = ("cl_websocket", "cl_mqtt")
ROUTES = ("custom", "hosted")


class BrainRoute:
    def __init__(self, host_url: str = "", host_token: str = "", lang: int = 0) -> None:
        self.nvs: dict[str, dict[str, str]] = {"websocket": {"url": host_url, "token": host_token} if host_url else {}, "cl_websocket": {}, "cl_mqtt": {}}
        self.route = "custom"
        self.lang = lang
        self.events: list[str] = []
        self.notice: str | None = None   # the screen command to draw, while the notice is up

    def join_hosted(self, url: str = "wss://hosted.example.com/ws", token: str = "t0ken") -> None:
        """Route A: the vendor's reply is written to the cl_ namespaces. The host pairing is never touched."""
        self.nvs["cl_websocket"] = {"url": url, "token": token}
        self.route = "hosted"
        self.events.append("route hosted")

    def switch_to_custom(self) -> None:
        """Leave hosted: wipe every cl_ namespace, keep the rest, show the notice. A switch while already custom changes nothing and shows nothing."""
        if self.route != "hosted":
            return
        for ns in HOSTED_NS:
            self.nvs[ns] = {}
        self.route = "custom"
        self.notice = f"bnotice {self.lang}"
        self.events.append("route custom")
        self.events.append("hosted link removed")

    def acknowledge(self) -> None:
        """OK on the notice."""
        self.notice = None

    def hosted_traces(self) -> list[str]:
        """Every saved value that belongs to the hosted link (empty after leaving it)."""
        return [f"{ns}.{k}" for ns in HOSTED_NS for k, v in self.nvs[ns].items() if v]
