"""The motor bus protocol and the last commanded target, shared by the motor health check and the Reachy daemon bus.

Kept here, not in the Reachy body package, so the motor health check (a generic presence part) never imports the body."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from maipai_body.hal.seam import AntennaPositions, HeadPose


class MotorBus(Protocol):
    def motor_mode(self) -> str: ...

    def set_motor_mode(self, mode: str) -> None: ...

    def wake_up(self) -> None: ...

    def goto_sleep(self) -> None: ...

    def bus_voltage_v(self) -> float | None:
        """The servo bus voltage in volts, None when it cannot be read."""
        ...

    def error_registers(self) -> dict[str, int]:
        """Each servo's hardware error status (XL330 address 70), by servo name."""
        ...

    def reboot_motor(self, name: str) -> None: ...

    def restart_daemon(self) -> bool:
        """True when the restart was issued, False when it is not permitted here."""
        ...


@dataclass(frozen=True)
class Commanded:
    """The last target the gate let through, and when a ``goto`` of it should have arrived."""

    pose: HeadPose | None
    antennas: AntennaPositions | None
    body_yaw: float | None
    settle_until: float
