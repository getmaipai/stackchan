"""Configuration for the StackChan host."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from maipai_body.unit_settings import _DEVICE as DEVICE_ID
from maipai_body.unit_settings import DAYS, SettingsError
from maipai_body.unit_settings import _clean as clean_settings


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LlmConfig(StrictModel):
    url: str = ""
    model: str = ""
    stt_url: str | None = None
    tts_url: str | None = None
    api_key_env: str | None = None
    persona: str = "You are a helpful robot. Keep spoken replies concise."
    timeout_seconds: float = 30.0
    history_messages: int = 20
    stt_model_dir: str | None = None
    tts_model: str | None = None
    tts_tokens: str | None = None
    tts_data_dir: str | None = None


class HomeConfig(StrictModel):
    url: str = ""
    language: str = "en"
    quiet_hours_from: str | None = None
    quiet_hours_to: str | None = None


class RemoteConfig(StrictModel):
    # None: the settings page decides. False: remote access stays off whatever the page says.
    enabled: bool | None = None


class MemoryNotesConfig(StrictModel):
    """Local memory for several adults as plain per-person notes files (maipai_packages/memory_notes)."""

    enabled: bool = False
    people: list[str] = Field(default_factory=list)  # lowercase names of the adults who have notes
    default_person: str = ""  # whose notes a turn uses when nobody was identified
    folder: str | None = None  # default: the notes folder beside the pairing file


class HomeAssistantConfig(StrictModel):
    """Home Assistant voice and camera snapshots (maipai_packages/home_assistant)."""

    enabled: bool = False
    url: str = ""
    token_env: str = "STACKCHAN_HA_TOKEN"  # the NAME of the variable holding a long-lived access token, never the token
    trigger: str = "home assistant"  # a request that starts with these words goes to Home Assistant
    cameras: dict[str, str] = Field(default_factory=dict)  # spoken name -> camera entity, for example front door = "camera.front_door"
    allow_plain_http: bool = False  # an http:// address on your home network sends the token in clear text; off unless you accept that
    allow_unidentified: bool = False  # the robot recognizes nobody on its own: only when true may a turn with no named speaker use it
    speakers: list[str] = Field(default_factory=list)  # lowercase names allowed to use it; empty means any named speaker


class CodingCompanionConfig(StrictModel):
    """The coding companion (maipai_packages/coding_companion): the robot shows what a coding agent is doing."""

    enabled: bool = False
    show_request_text: bool = False  # off: the screen shows only "Needs you", "Working", "Finished"
    port: int = Field(default=8052, ge=1024, le=65535)  # on 127.0.0.1 only


class PackagesConfig(StrictModel):
    """Optional local packages. Every one is off by default and costs nothing while off."""

    memory_notes: MemoryNotesConfig = Field(default_factory=MemoryNotesConfig)
    home_assistant: HomeAssistantConfig = Field(default_factory=HomeAssistantConfig)
    coding_companion: CodingCompanionConfig = Field(default_factory=CodingCompanionConfig)


class SettingsPageConfig(StrictModel):
    """lan = true lets a phone on your Wi-Fi open the settings page, with the settings token."""

    lan: bool = False


class UpdateConfig(StrictModel):
    """Where signed releases come from. Nothing is fetched; a folder is read."""

    source: str | None = None
    trusted_key: str | None = None
    preset: Literal["core", "home"] = "core"


class UnitLlm(StrictModel):
    url: str = ""
    model: str = ""
    api_key_env: str | None = None


class UnitAlarm(StrictModel):
    time: str
    days: list[str] = Field(default_factory=lambda: list(DAYS))
    label: str = ""


class UnitConfig(StrictModel):
    """One robot's own settings: `[units.kitchen]`, found by its `device_id` (its Device-Id).

    Anything left out inherits the top-level value. The values are checked by the same rules the
    settings page uses (`unit_settings`), so a bad value is refused with the same plain message.
    """

    device_id: str
    name: str | None = None
    persona: str | None = None
    volume_cap: int | None = None
    speech_speed: float | None = None
    speech_pitch: float | None = None
    muted: bool | None = None
    llm: UnitLlm | None = None
    alarm: list[UnitAlarm] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_values(self):
        if not DEVICE_ID.match(self.device_id):
            raise ValueError(
                f"device_id {self.device_id!r} is not a unit address. Copy the Device-Id from "
                "`stackchan units` (like aa:bb:cc:dd:ee:ff)."
            )
        try:
            clean_settings(self.settings(), from_owner_file=True)
        except SettingsError as error:
            raise ValueError(str(error)) from error
        return self

    def settings(self) -> dict[str, object]:
        """The unit's overrides in the shape `unit_settings` stores (only what was set)."""
        out: dict[str, object] = {}
        for key in ("name", "persona", "volume_cap", "muted", "speech_speed", "speech_pitch"):
            if getattr(self, key) is not None:
                out[key] = getattr(self, key)
        if self.llm is not None:
            out["llm"] = {
                "url": self.llm.url,
                "model": self.llm.model,
                "api_key_env": self.llm.api_key_env or "",
            }
        if self.alarm:
            out["alarms"] = [a.model_dump() for a in self.alarm]
        return out


class RobotConfig(StrictModel):
    brain: Literal["llm", "home", "standalone"] = "llm"
    units: dict[str, UnitConfig] = Field(default_factory=dict)
    llm: LlmConfig = Field(default_factory=LlmConfig)
    home: HomeConfig = Field(default_factory=HomeConfig)
    packages: PackagesConfig = Field(default_factory=PackagesConfig)
    settings: SettingsPageConfig = Field(default_factory=SettingsPageConfig)
    remote: RemoteConfig = Field(default_factory=RemoteConfig)
    update: UpdateConfig = Field(default_factory=UpdateConfig)

    @model_validator(mode="after")
    def check_unit_ids_differ(self):
        seen: dict[str, str] = {}
        for name, unit in self.units.items():
            key = unit.device_id.lower().replace("-", ":")
            if key in seen:
                raise ValueError(
                    f"[units.{seen[key]}] and [units.{name}] use the same device_id. "
                    "Give each unit its own Device-Id."
                )
            seen[key] = name
        return self

    @model_validator(mode="before")
    @classmethod
    def normalize_brain_alias(cls, value):
        if isinstance(value, dict) and value.get("brain") == "standalone":
            value = dict(value)
            value["brain"] = "llm"
        return value


def build_brain(config: RobotConfig, **home_dependencies):
    """Select the configured answering brain."""
    if config.brain == "home":
        from maipai_body.brain.home import HomeBrain

        return HomeBrain(**home_dependencies)
    from maipai_body.brain.own_llm import OwnLLMBrain

    brain = OwnLLMBrain(config.llm, **home_dependencies)
    notes = config.packages.memory_notes
    if notes.enabled:  # imported only when switched on
        from maipai_body.bodies.stackchan.xiaozhi.pairing import default_pairing_path
        from maipai_packages.memory_notes import Notes, NotesStore

        folder = Path(notes.folder) if notes.folder else default_pairing_path().parent / "notes"
        brain.memory = Notes(NotesStore(folder), notes.people, notes.default_person)
        brain.handlers.append(brain.memory)
    coding = config.packages.coding_companion
    if coding.enabled:  # the spoken status request; the endpoint is started by the host app
        from maipai_packages.coding_companion import shared_status
        from maipai_packages.coding_companion.handler import CodingStatusHandler

        shared_status().show_request_text = coding.show_request_text
        brain.handlers.append(CodingStatusHandler(shared_status()))
    ha = config.packages.home_assistant
    if ha.enabled:
        from maipai_body import child_gate
        from maipai_packages.home_assistant import HomeAssistant
        from maipai_packages.home_assistant.client import image_question

        brain.handlers.append(
            HomeAssistant(
                ha.url,
                token_env=ha.token_env,
                trigger=ha.trigger,
                cameras=ha.cameras,
                language=config.home.language,
                allow_plain_http=ha.allow_plain_http,
                allow_unidentified=ha.allow_unidentified,
                speakers=ha.speakers,
                child_present=child_gate.any_present,
                ask_model=image_question(config.llm.url, config.llm.model, config.llm.api_key_env) if config.llm.url else None,
            )
        )
    return brain


def example_config_path() -> Path:
    return Path.home() / ".config" / "maipai" / "robot.toml"


def example_template_path() -> Path:
    """robot.example.toml: inside the installed package, or beside it in a checkout."""
    here = Path(__file__).resolve()
    for candidate in (here.parent / "robot.example.toml", here.parents[1] / "robot.example.toml"):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("robot.example.toml is missing from this install; reinstall the host")


def load_config(path: str | Path | None = None) -> RobotConfig:
    config_path = Path(path) if path else example_config_path()
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        example = example_template_path()
        config_path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Created {config_path}. Edit this file to choose your brain and settings.")
    try:
        raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
        return RobotConfig.model_validate(raw)
    except Exception as exc:
        if hasattr(exc, "errors"):
            first = exc.errors()[0]
            loc = first.get("loc", ())
            if loc and loc[0] == "units":
                raise ValueError(_unit_error(first, loc, config_path)) from exc
            if not loc and "device_id" in str(first.get("msg", "")):
                message = str(first["msg"]).removeprefix("Value error, ")
                raise ValueError(f"{message} Fix it in {config_path}.") from exc
            key = ".".join(str(part) for part in first.get("loc", ())) or "configuration"
            raise ValueError(
                f"Unknown or invalid key {key}. Correct or remove this key in {config_path}."
            ) from exc
        raise ValueError(
            f"Could not read {config_path}. Fix its TOML syntax and try again."
        ) from exc


def _unit_error(error: dict, loc: tuple, config_path: Path) -> str:
    name = loc[1] if len(loc) > 1 else "?"
    message = str(error.get("msg", "")).removeprefix("Value error, ")
    if error.get("type") == "extra_forbidden":
        message = f"{loc[-1]} is not a unit setting"
    elif error.get("type") == "missing":
        message = f"{loc[-1]} is missing"
    if not message.rstrip().endswith("."):
        message += "."
    return (
        f"[units.{name}] in {config_path} is not valid: {message} "
        "Correct or remove it, then run the command again."
    )
