"""A second robot (Reachy Mini) against the shared spec proposals and the HAL seam.

The StackChan description and the Reachy Mini stub description must both pass the robot-description
schema; the stub's joint limits must equal the host profile's axis limits (one number, one place);
the fake Reachy client must answer every method the seam protocols name; the profile must declare a
safe stop and a leased-motion verb list for every channel it drives.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from maipai_body.bodies.reachy_mini.fake import FakeReachyMiniClient
from maipai_body.bodies.reachy_mini.profile import REACHY_MINI_PROFILE
from maipai_body.hal import seam
from tests.schema_mini import errors

ROOT = Path(__file__).resolve().parents[2]
ROBOTS = ROOT / "scripts" / "virtual-unit" / "physics" / "robots"
SCHEMA = json.loads((ROOT / "docs" / "plan" / "spec-proposals" / "robot-description.schema.json").read_text())
DESCRIPTIONS = sorted(ROBOTS.glob("*.robot.json"))


def _load(name: str) -> dict:
    return json.loads((ROBOTS / f"{name}.robot.json").read_text())


def test_both_robots_have_a_description():
    assert {p.name for p in DESCRIPTIONS} >= {"stackchan.robot.json", "reachy_mini.robot.json"}


@pytest.mark.parametrize("path", DESCRIPTIONS, ids=lambda p: p.stem)
def test_every_description_passes_the_schema_and_names_real_params(path):
    description = json.loads(path.read_text())
    assert errors(SCHEMA, description) == []
    params = description["params"]
    for joint in description["joints"]:
        for key in ("range", "kp", "kv"):
            assert joint[key] in params, f"{joint['name']}: {joint[key]} is not in params"
    for name, item in params.items():
        assert item["src"] in ("measured", "assumed"), name
        assert item["note"], f"{name} needs a note saying where the number comes from"
    roles = [j["role"] for j in description["joints"]]
    assert len(roles) == len(set(roles)), "one joint per role"


def test_reachy_limits_are_the_profiles_limits():
    description = _load("reachy_mini")
    params = description["params"]
    by_role = {j["role"]: j for j in description["joints"]}
    pairs = {
        "head.yaw": ("head_yaw", 1.0),
        "head.pitch": ("head_pitch", 1.0),
        "head.roll": ("head_roll", 1.0),
        "appendage.left": ("antenna_left", 180.0 / math.pi),
        "appendage.right": ("antenna_right", 180.0 / math.pi),
    }
    for role, (axis_name, to_deg) in pairs.items():
        axis = REACHY_MINI_PROFILE.axis(axis_name)
        low, high = params[by_role[role]["range"]]["v"]
        assert low == pytest.approx(axis.min * to_deg, abs=0.01), role
        assert high == pytest.approx(axis.max * to_deg, abs=0.01), role


def test_description_capabilities_match_the_profile():
    caps = set(_load("reachy_mini")["capabilities"])
    profile = set(REACHY_MINI_PROFILE.capabilities)
    assert "head_6dof" in caps and "head_6dof" in profile
    assert ("appendages" in caps) == ("antennas" in profile)
    assert ("imu" in caps) == ("imu" in profile)


def test_measured_numbers_are_not_claimed_without_a_source():
    for item in _load("reachy_mini")["params"].values():
        if item["src"] == "measured":
            assert len(item["note"]) > 20


def _methods(protocol) -> set[str]:
    return {n for n, v in vars(protocol).items() if callable(v) and not n.startswith("_")}


@pytest.mark.parametrize(
    "protocol",
    [seam.HeadActuator, seam.Teachable, seam.AudioIO, seam.Camera, seam.Imu, seam.FaceTracker],
    ids=lambda p: p.__name__,
)
def test_the_fake_answers_every_seam_method(protocol):
    fake = FakeReachyMiniClient()
    missing = [m for m in _methods(protocol) if not callable(getattr(fake, m, None))]
    assert missing == [], f"{protocol.__name__}: the second robot's client lacks {missing}"


def test_profile_declares_a_stop_and_leased_verbs_for_each_driven_channel():
    profile = REACHY_MINI_PROFILE
    for channel in profile.leased_motion:
        assert channel in profile.channels
        assert channel in profile.safe_stop, f"{channel} has leased motion but no safe stop"
    for axis_name in profile.axis_map.values():
        profile.axis(axis_name)  # raises when the axis is not declared


def test_every_axis_limit_names_its_source_and_date():
    for axis in REACHY_MINI_PROFILE.axes:
        assert axis.source and axis.date and axis.min < axis.max, axis.name
