# ruff: noqa: E501
"""Several robots on one host: every setting a unit uses is picked by its Device-Id.

One registry answers "what does this unit use?" for the voice link, the brain seam and the avatar
socket (docs/design/config.md, "Several robots"). A unit with no saved settings, and a Device-Id the
host has never seen, get the top-level config, exactly as a single robot always did. Each unit gets
its own brain object, so its conversation history and persona are never shared with another unit.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable, Iterator
from typing import Any

from maipai_body.brain.interface import TurnRequest
from maipai_body.config import RobotConfig
from maipai_body.unit_settings import DAYS, UnitSettingsStore

BrainFactory = Callable[[RobotConfig], Any]
DeviceCall = Callable[[str, str, dict[str, object]], object]


def _default_factory(config: RobotConfig) -> Any:
    from maipai_body.config import build_brain

    return build_brain(config)


class BrainTurn:
    """Gives a brain the `stream` and `cancel` shape the voice link's turn client has."""

    def __init__(self, brain: Any, conversation_id: str) -> None:
        self._brain, self._conversation_id = brain, conversation_id

    def stream(self, text: str, *, speaker_evidence=None, present=None, conversation_id=None, ask_answer=None) -> Iterator[Any]:
        return self._brain.stream_turn(
            TurnRequest(
                text=text,
                speaker_evidence=speaker_evidence,
                present=present,
                conversation_id=conversation_id or self._conversation_id,
                ask_answer=ask_answer,
            )
        )

    def cancel(self, turn_id: str) -> bool:
        return bool(self._brain.cancel_turn(turn_id))


class UnitRegistry:
    def __init__(
        self,
        base: RobotConfig,
        store: UnitSettingsStore | None = None,
        *,
        brain_factory: BrainFactory | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.base = base
        self.store = store or UnitSettingsStore()
        self._factory = brain_factory or _default_factory
        self._clock = clock
        self._lock = threading.Lock()
        self._brains: dict[str, tuple[str, Any]] = {}
        self._pushed: set[tuple[str, str, str]] = set()

    # -- what a unit uses -------------------------------------------------------------------

    def config_for(self, device_id: str) -> RobotConfig:
        """The top-level config with this unit's model and persona on top. Unknown unit: the base."""
        own = self.store.get(device_id)
        llm = {k: v for k, v in own.get("llm", {}).items() if v}
        if "persona" in own:
            llm["persona"] = own["persona"]
        if not llm:
            return self.base
        return self.base.model_copy(update={"llm": self.base.llm.model_copy(update=llm)})

    def has_own_llm(self, device_id: str) -> bool:
        """True when this unit chose its own model URL; only then does it leave the Home brain."""
        return bool(self.store.get(device_id).get("llm", {}).get("url"))

    def brain_for(self, device_id: str) -> Any:
        """The unit's own brain. Rebuilt when its settings change; history stays inside it."""
        config = self.config_for(device_id)
        signature = json.dumps(config.model_dump(), sort_keys=True, default=str)
        with self._lock:
            cached = self._brains.get(device_id)
            if cached is not None and cached[0] == signature:
                return cached[1]
            brain = self._factory(config)
            self._brains[device_id] = (signature, brain)
            return brain

    def turn_for(self, device_id: str) -> BrainTurn:
        return BrainTurn(self.brain_for(device_id), conversation_id=device_id)

    def volume_cap_for(self, device_id: str) -> int:
        return int(self.store.get(device_id).get("volume_cap", 100))

    def alarms_for(self, device_id: str) -> list[dict[str, Any]]:
        return list(self.store.get(device_id).get("alarms", []))

    def snapshot(self, device_id: str) -> dict[str, Any]:
        """Everything a socket needs to know about one unit, never another unit's values."""
        own = self.store.get(device_id)
        config = self.config_for(device_id)
        return {
            "device_id": device_id,
            "name": own.get("name", f"StackChan {device_id[-5:]}"),
            "model": config.llm.model,
            "persona": config.llm.persona,
            "volume_cap": self.volume_cap_for(device_id),
            "muted": bool(own.get("muted", False)),
            "alarms": self.alarms_for(device_id),
            "own_llm": self.has_own_llm(device_id),
        }

    # -- alarms, pushed to the unit that owns them ------------------------------------------

    def push_alarms(self, device_id: str, call: DeviceCall) -> int:
        """Set today's still-ahead alarms on this unit through its own timer tool; returns the count.

        The unit's alarm tool sets one alarm at a time, so a recurring alarm is pushed on the days it
        runs. An alarm already pushed today is not pushed again when the unit reconnects.
        """
        now = time.localtime(self._clock())
        today = DAYS[now.tm_wday]
        stamp = time.strftime("%Y-%m-%d", now)
        sent = 0
        for alarm in self.alarms_for(device_id):
            hour, minute = (int(part) for part in alarm["time"].split(":"))
            if today not in alarm["days"] or (hour, minute) <= (now.tm_hour, now.tm_min):
                continue
            key = (device_id, stamp, alarm["time"])
            with self._lock:
                if key in self._pushed:
                    continue
                self._pushed.add(key)
            call(
                device_id,
                "self.timer.alarm",
                {"hour": hour, "minute": minute, "label": alarm.get("label", ""), "silent": False},
            )
            sent += 1
        return sent


def registry_from_disk(store: UnitSettingsStore | None = None) -> UnitRegistry:
    """The registry for the running host: robot.toml if it exists (never created here), else defaults."""
    from maipai_body.config import example_config_path, load_config

    path = example_config_path()
    return UnitRegistry(load_config(path) if path.exists() else RobotConfig(), store)
