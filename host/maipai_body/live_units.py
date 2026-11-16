# ruff: noqa: E501
"""What the running host knows about each connected unit, for the settings page.

Reads the live voice connection: which units are online, each unit's firmware version (from its "fw" event) and saved
Wi-Fi networks (asked of that unit by its Device-Id), and the over-the-air push for one unit.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

LOG = logging.getLogger(__name__)


class LiveUnits:
    def __init__(self, voice: Any, *, sole_unit_version: Any = None, timeout: float = 2.0) -> None:
        self.voice = voice
        self._sole_unit_version = sole_unit_version
        self._timeout = timeout
        self._versions: dict[str, str] = {}

    def note_event(self, device_id: str, kind: str, extra: Any) -> None:
        """Keep the version a unit reports in its once-a-minute "fw" event (firmware patch 062).

        That event ({"version": "0.2.31", "rssi": -61}) is the only place the firmware reports its
        version; the status tool does not carry one.
        """
        if kind == "fw" and isinstance(extra, dict) and isinstance(extra.get("version"), str):
            self._versions[device_id] = extra["version"]

    def version_of(self, device_id: str) -> str | None:
        """This unit's reported version. With one unit connected, the host's single fact is used."""
        version = self._versions.get(device_id)
        if version is None and self._sole_unit_version is not None:
            if self.voice.connected_devices() == [device_id]:
                version = self._sole_unit_version()
        return version if isinstance(version, str) and version != "unknown" else None

    def live(self, device_id: str) -> dict[str, Any]:
        """Online state, firmware version and Wi-Fi state of one unit; offline gives only online=False."""
        if device_id not in self.voice.connected_devices():
            return {"online": False}
        out: dict[str, Any] = {"online": True}
        version = self.version_of(device_id)
        if version is not None:
            out["firmware_version"] = version
        try:
            saved = self._call(device_id, "self.wifi.list_saved")
            networks = json.loads(saved) if isinstance(saved, str) else saved
            out["wifi_configured"] = bool(networks) if isinstance(networks, list) else None
        except Exception:
            out["wifi_configured"] = None
        return out

    def push(self, device_id: str, path: Path, sha256: str, size: int, version: str) -> None:
        """Send the app image to this one unit over the air (its own self.firmware.update tool)."""
        url = self.voice.serve_firmware_once(path, device_id)
        self.voice.call_device_tool(
            "self.firmware.update",
            {"url": url, "sha256": sha256, "size": size, "version": version},
            device_id=device_id,
            timeout=10.0,
        )

    def _call(self, device_id: str, name: str) -> object:
        return self.voice.call_device_tool(name, {}, device_id=device_id, timeout=self._timeout)
