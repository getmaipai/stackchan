"""Configuration for the StackChan host."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LlmConfig(StrictModel):
    url: str = ""
    model: str = ""
    stt_url: str | None = None
    tts_url: str | None = None


class HomeConfig(StrictModel):
    url: str = ""
    language: str = "en"
    quiet_hours_from: str | None = None
    quiet_hours_to: str | None = None


class RemoteConfig(StrictModel):
    enabled: bool = False


class RobotConfig(StrictModel):
    brain: Literal["llm", "home", "standalone"] = "llm"
    llm: LlmConfig = Field(default_factory=LlmConfig)
    home: HomeConfig = Field(default_factory=HomeConfig)
    remote: RemoteConfig = Field(default_factory=RemoteConfig)

    @model_validator(mode="before")
    @classmethod
    def normalize_brain_alias(cls, value):
        if isinstance(value, dict) and value.get("brain") == "standalone":
            value = dict(value)
            value["brain"] = "llm"
        return value


def build_brain(config: RobotConfig, **home_dependencies):
    """Select the configured adapter; the own-LLM implementation is phase five."""
    if config.brain == "home":
        from maipai_body.brain.home import HomeBrain

        return HomeBrain(**home_dependencies)
    from maipai_body.brain.own_llm import NotYetBuilt

    return NotYetBuilt(config.llm)


def example_config_path() -> Path:
    return Path.home() / ".config" / "maipai" / "robot.toml"


def load_config(path: str | Path | None = None) -> RobotConfig:
    config_path = Path(path) if path else example_config_path()
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        example = Path(__file__).resolve().parents[1] / "robot.example.toml"
        config_path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Created {config_path}. Edit this file to choose your brain and settings.")
    try:
        raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
        return RobotConfig.model_validate(raw)
    except Exception as exc:
        if hasattr(exc, "errors"):
            first = exc.errors()[0]
            key = ".".join(str(part) for part in first.get("loc", ())) or "configuration"
            raise ValueError(
                f"Unknown or invalid key {key}. Correct or remove this key in {config_path}."
            ) from exc
        raise ValueError(
            f"Could not read {config_path}. Fix its TOML syntax and try again."
        ) from exc
