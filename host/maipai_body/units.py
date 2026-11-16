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

    def stream(
        self,
        text: str,
        *,
        speaker_evidence=None,
        present=None,
        conversation_id=None,
        ask_answer=None,
    ) -> Iterator[Any]:
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


def _norm(device_id: str) -> str:
    return device_id.lower().replace("-", ":")


class LayeredStore:
    """robot.toml `[units.<name>]` tables under the settings page file.

    The tables are the owner's defaults for a unit; anything saved on the settings page (or with
    `stackchan name`) is newer and wins. Writes go only to the page file; robot.toml is never rewritten.
    """

    def __init__(self, inner: UnitSettingsStore, tables: dict[str, Any] | None = None) -> None:
        self.inner = inner
        self._by_id = {_norm(t.device_id): (n, t) for n, t in (tables or {}).items()}

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def table_name(self, device_id: str) -> str | None:
        hit = self._by_id.get(_norm(device_id))
        return hit[0] if hit else None

    def known_ids(self) -> list[str]:
        """Device-Ids named in robot.toml, as written there."""
        return [t.device_id for _, t in self._by_id.values()]

    def get(self, device_id: str) -> dict[str, Any]:
        own = self.inner.get(device_id)
        hit = self._by_id.get(_norm(device_id))
        if hit is None:
            return own
        name, table = hit
        base = {"name": name, **table.settings()}
        merged = {**base, **own}
        if "llm" in base or "llm" in own:
            merged["llm"] = {
                **base.get("llm", {}),
                **{k: v for k, v in own.get("llm", {}).items() if v},
            }
        return merged

    def update(self, device_id: str, values: dict[str, Any]) -> dict[str, Any]:
        self.inner.update(device_id, values)
        return self.get(device_id)

    def effective(self, device_id: str, base: dict[str, Any]) -> dict[str, Any]:
        own = self.get(device_id)
        merged = {**base, "llm": dict(base.get("llm", {}))}
        for key in ("persona", "volume_cap", "muted", "alarms", "name", "speech_speed", "speech_pitch"):
            if key in own:
                merged[key] = own[key]
        for key, value in own.get("llm", {}).items():
            if value:
                merged["llm"][key] = value
        return merged


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
        self.store = LayeredStore(store or UnitSettingsStore(), base.units)
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
        if self.store.get(device_id).get("llm", {}).get("url"):
            return True
        # No Home: a top-level model URL in robot.toml is every unit's model.
        return self.base.brain != "home" and bool(self.base.llm.url)

    def brain_for(self, device_id: str) -> Any:
        """The unit's own brain. Rebuilt when its settings change; history stays inside it."""
        config = self.config_for(device_id)
        if self.store.get(device_id).get("emotion_faces", True) is not False:
            # The model starts each reply with a mood tag; the host strips it and shows the face.
            from maipai_body.reply_tags import persona_with_tags

            config = config.model_copy(
                update={"llm": config.llm.model_copy(update={"persona": persona_with_tags(config.llm.persona)})}
            )
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

    def speech_speed_for(self, device_id: str) -> float:
        return float(self.store.get(device_id).get("speech_speed", 1.0))

    def speech_pitch_for(self, device_id: str) -> float:
        return float(self.store.get(device_id).get("speech_pitch", 0.0))

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


def known_units(
    paired: dict[str, Any], store: LayeredStore, online: set[str] | None = None
) -> list[dict[str, Any]]:
    """Every unit the host knows (paired, saved on the page, or named in robot.toml), sorted by name.

    ``online`` is None when the running host could not be asked; each row then says online=None.
    """
    ids: dict[str, str] = {}
    for device_id in [*paired, *store.known_ids(), *store.inner.all_ids()]:
        ids.setdefault(_norm(device_id), device_id)
    rows = []
    for key, device_id in ids.items():
        own = store.get(device_id)
        rows.append(
            {
                "device_id": device_id,
                "name": own.get("name", f"StackChan {device_id[-5:]}"),
                "paired": any(_norm(p) == key for p in paired),
                "online": None if online is None else any(_norm(o) == key for o in online),
            }
        )
    return sorted(rows, key=lambda r: (r["name"].lower(), r["device_id"]))


def default_unit(rows: list[dict[str, Any]]) -> str | None:
    """The unit a control uses when none is named: the only unit, else the first online one."""
    if len(rows) == 1:
        return rows[0]["device_id"]
    for row in rows:
        if row["online"]:
            return row["device_id"]
    return None


def registry_from_disk(store: UnitSettingsStore | None = None) -> UnitRegistry:
    """The registry for the running host: robot.toml if it exists (never created here), else defaults."""
    from maipai_body.config import example_config_path, load_config

    path = example_config_path()
    return UnitRegistry(load_config(path) if path.exists() else RobotConfig(), store)
