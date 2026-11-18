"""Moved to maipai_body.hal.envelope (shared clamping); kept so the Reachy Mini body's imports keep working."""

from maipai_body.hal.envelope import *  # noqa: F401,F403
from maipai_body.hal.envelope import axis_bounds_rad, clamp_angle  # noqa: F401
