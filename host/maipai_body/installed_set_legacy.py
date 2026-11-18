"""The reconciler's transport over the pack tools a unit has today (`self.pack.*`, one pack per kind)."""

from __future__ import annotations

from collections.abc import Callable

from maipai_body.packs import PackError, PackService
from maipai_body.unit_tools import unwrap


class LegacyTransport:
    def __init__(self, packs: PackService, connected: Callable[[str], bool], has_assets_tools: Callable[[str], bool] = lambda unit: False) -> None:
        self._packs, self._connected, self._has_assets = packs, connected, has_assets_tools

    def connected(self, unit: str) -> bool:
        return bool(self._connected(unit))

    def multi_slot(self, unit: str) -> bool:
        return bool(self._has_assets(unit))

    def held(self, unit: str, kind: str) -> list[str]:
        reply = unwrap(self._packs.probe.call(unit, "self.pack.status", {"type": kind}))
        return [str(reply["sha256"])] if reply.get("ok") is True and reply.get("held") is True and reply.get("sha256") else []

    def install(self, unit: str, kind: str, pack_id: str) -> None:
        self._packs.active.set(unit, kind, pack_id)  # the pack service pushes what is active
        self._packs._push_type(unit, kind, None)

    def remove(self, unit: str, kind: str, sha: str | None) -> None:
        self._packs.active.set(unit, kind, None)
        self._packs._push_type(unit, kind, None)


__all__ = ["LegacyTransport", "PackError"]
