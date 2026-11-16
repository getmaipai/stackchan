# ruff: noqa: E501
"""What the running host knows about each connected unit, for the settings page.

Reads the live voice connection: which units are online, each unit's own firmware version and saved
Wi-Fi networks (asked of that unit by its Device-Id), and the over-the-air push for one unit.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

LOG = logging.getLogger(__name__)
_VERSION_KEYS = ("firmware_version", "fw_version", "app_version", "version")


def _as_dict(result: object) -> dict[str, Any]:
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except ValueError:
            return {}
    return result if isinstance(result, dict) else {}


class LiveUnits:
    def __init__(self, voice: Any, *, sole_unit_version: Any = None, timeout: float = 2.0) -> None:
        self.voice = voice
        self._sole_unit_version = sole_unit_version
        self._timeout = timeout

    def live(self, device_id: str) -> dict[str, Any]:
        """Online state, firmware version and Wi-Fi state of one unit; offline gives only online=False."""
        if device_id not in self.voice.connected_devices():
            return {"online": False}
        out: dict[str, Any] = {"online": True}
        try:
            status = _as_dict(self._call(device_id, "self.get_device_status"))
        except Exception:
            LOG.info("settings page: unit %s did not answer its status", device_id[-5:])
            status = {}
        for key in _VERSION_KEYS:
            if isinstance(status.get(key), str):
                out["firmware_version"] = status[key]
                break
        else:
            if len(self.voice.connected_devices()) == 1 and self._sole_unit_version is not None:
                out["firmware_version"] = self._sole_unit_version()
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
