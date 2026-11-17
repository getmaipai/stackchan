# ruff: noqa: E501
"""Per-unit settings for the core settings page, keyed by the unit's Device-Id.

The name is a label for people; the Device-Id (the unit's MAC address) is the key
(docs/design/config.md, "Several robots"). Only core settings live here. Keys are never stored:
the model entry names an environment variable.
"""

from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Any

from maipai_body.spelling_aliases import upgrade_keys

MAX_PERSONA = 2000
MAX_ALARMS = 12
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_ENV = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
_DEVICE = re.compile(r"^[0-9A-Fa-f:\-]{6,32}$")


class SettingsError(ValueError):
    """A rejected setting; the message says which field and what to do."""


def default_path() -> Path:
    return Path.home() / ".config" / "maipai" / "stackchan-units.json"


def _clean_alarm(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise SettingsError(
            "An alarm must be a time, days and a label. Fix the alarm and save again."
        )
    when = str(raw.get("time", ""))
    if not _TIME.match(when):
        raise SettingsError(
            f"Alarm time {when!r} is not HH:MM in 24 hour time. Use a time like 07:30."
        )
    days = raw.get("days", list(DAYS))
    if not isinstance(days, list) or not days or any(d not in DAYS for d in days):
        raise SettingsError(
            "Alarm days must be from mon, tue, wed, thu, fri, sat, sun. Fix the days and save again."
        )
    label = str(raw.get("label", ""))[:60]
    return {"time": when, "days": [d for d in DAYS if d in days], "label": label}


def _clean(values: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if "name" in values:
        name = str(values["name"]).strip()
        if not name or len(name) > 40:
            raise SettingsError("The unit name must be 1 to 40 characters. Type a shorter name.")
        out["name"] = name
    if "persona" in values:
        persona = str(values["persona"])
        if len(persona) > MAX_PERSONA:
            raise SettingsError(
                f"The persona is over {MAX_PERSONA} characters. Shorten it and save again."
            )
        out["persona"] = persona
    if "llm" in values:
        llm = values["llm"]
        if not isinstance(llm, dict):
            raise SettingsError("The model choice must be a URL, a name and a key variable name.")
        cleaned = {k: str(llm.get(k, "")).strip() for k in ("url", "model", "api_key_env")}
        if cleaned["url"] and not cleaned["url"].startswith(("http://", "https://")):
            raise SettingsError(
                "The model URL must start with http:// or https://. Fix the URL and save again."
            )
        if cleaned["api_key_env"] and not _ENV.match(cleaned["api_key_env"]):
            raise SettingsError(
                "Type the NAME of the environment variable that holds the key, not the key itself."
            )
        out["llm"] = cleaned
    if "volume_cap" in values:
        cap = values["volume_cap"]
        if isinstance(cap, bool) or not isinstance(cap, int) or not 0 <= cap <= 100:
            raise SettingsError(
                "The volume cap must be a whole number from 0 to 100. Pick a number in that range."
            )
        out["volume_cap"] = cap
    if "muted" in values:
        if not isinstance(values["muted"], bool):
            raise SettingsError("Mute must be on or off.")
        out["muted"] = values["muted"]
    if "speech_speed" in values:
        speed = values["speech_speed"]
        if isinstance(speed, bool) or not isinstance(speed, (int, float)) or not 0.75 <= speed <= 1.5:
            raise SettingsError(
                "The speech speed must be a number from 0.75 to 1.5. Pick a speed in that range."
            )
        out["speech_speed"] = speed
    if "speech_pitch" in values:
        pitch = values["speech_pitch"]
        if isinstance(pitch, bool) or not isinstance(pitch, (int, float)) or not -12 <= pitch <= 12:
            raise SettingsError(
                "The speech pitch must be a number from -12 to 12 semitones. Pick a pitch in that range."
            )
        out["speech_pitch"] = pitch
    if "alarms" in values:
        alarms = values["alarms"]
        if not isinstance(alarms, list) or len(alarms) > MAX_ALARMS:
            raise SettingsError(f"Keep the alarm list to {MAX_ALARMS} alarms or fewer.")
        out["alarms"] = [_clean_alarm(a) for a in alarms]
    if "volume" in values:
        volume = values["volume"]
        if isinstance(volume, bool) or not isinstance(volume, int) or not 0 <= volume <= 100:
            raise SettingsError("The volume must be a whole number from 0 to 100. Pick a number in that range.")
        out["volume"] = volume
    if "brightness" in values:
        brightness = values["brightness"]
        if isinstance(brightness, bool) or not isinstance(brightness, int) or not 10 <= brightness <= 100:
            raise SettingsError("The brightness must be a whole number from 10 to 100. Pick a number in that range.")
        out["brightness"] = brightness
    if "idle_motion" in values:
        if not isinstance(values["idle_motion"], bool):
            raise SettingsError("Idle motion must be on or off.")
        out["idle_motion"] = values["idle_motion"]
    if "idle_movement" in values:
        if values["idle_movement"] not in ("off", "calm", "lively"):
            raise SettingsError("Idle movement must be off, calm or lively. Pick one and save again.")
        out["idle_movement"] = values["idle_movement"]
    if "face_owner" in values:
        if values["face_owner"] not in ("robot", "hub", "off"):
            raise SettingsError("Who turns toward faces must be this robot, my Home hub or off. Pick one and save again.")
        out["face_owner"] = values["face_owner"]
    for flag in ("look_speaker", "look_faces"):
        if flag in values:
            if not isinstance(values[flag], bool):
                raise SettingsError("That setting must be on or off.")
            out[flag] = values[flag]
    if "wait_after_talking" in values:
        if values["wait_after_talking"] not in ("quick", "normal", "patient"):
            raise SettingsError("Wait after you stop talking must be quick, normal or patient.")
        out["wait_after_talking"] = values["wait_after_talking"]
    if "ignore_noise" in values:
        if values["ignore_noise"] not in ("low", "medium", "high"):
            raise SettingsError("Ignore background noise must be low, medium or high. Pick one and save again.")
        out["ignore_noise"] = values["ignore_noise"]
    if "led" in values:
        led = values["led"]
        if led != "off" and not (isinstance(led, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", led)):
            raise SettingsError("The light ring color must be off or a code like #40c0ff. Pick a color and save again.")
        out["led"] = led.lower()
    from maipai_body import unit_prefs

    out.update(unit_prefs.clean(values, SettingsError))
    unknown = set(upgrade_keys(values)) - set(unit_prefs.PREFS) - {"name", "persona", "llm", "volume_cap", "muted", "alarms", "speech_speed", "speech_pitch", "volume", "brightness", "idle_motion", "idle_movement", "ignore_noise", "look_speaker", "look_faces", "face_owner", "wait_after_talking", "led"}
    if unknown:
        raise SettingsError(f"Unknown setting {sorted(unknown)[0]}. Remove it and save again.")
    return out


class UnitSettingsStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else default_path()
        self._lock = threading.Lock()

    def _load(self) -> dict[str, dict[str, Any]]:
        try:
            data = json.loads(self.path.read_text())
        except FileNotFoundError:
            return {}
        except ValueError as error:
            raise SettingsError(
                f"{self.path} is not valid JSON. Fix or delete the file and reload."
            ) from error
        return data if isinstance(data, dict) else {}

    def all_ids(self) -> list[str]:
        """Every Device-Id that has saved settings."""
        with self._lock:
            return list(self._load())

    def get(self, device_id: str) -> dict[str, Any]:
        with self._lock:
            return upgrade_keys(self._load().get(device_id, {}))

    def update(self, device_id: str, values: dict[str, Any]) -> dict[str, Any]:
        if not _DEVICE.match(device_id):
            raise SettingsError("That Device-Id is not a unit address. Pick a unit from the list.")
        cleaned = _clean(values)
        with self._lock:
            data = self._load()
            merged = {**upgrade_keys(data.get(device_id, {})), **cleaned}
            data[device_id] = merged
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
            os.replace(tmp, self.path)
            return merged

    def effective(self, device_id: str, base: dict[str, Any]) -> dict[str, Any]:
        """Top-level values with this unit's overrides on top; no table means no change."""
        own = self.get(device_id)
        merged = {**base, "llm": dict(base.get("llm", {}))}
        for key in ("persona", "volume_cap", "muted", "alarms", "name", "speech_speed", "speech_pitch"):
            if key in own:
                merged[key] = own[key]
        for key, value in own.get("llm", {}).items():
            if value:
                merged["llm"][key] = value
        return merged
