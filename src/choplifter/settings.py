from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WindowSettings:
    width: int = 1280
    height: int = 720
    title: str = "Choplifter Returns - Middle East Rescue"
    vsync: bool = True


@dataclass(frozen=True)
class FixedTickSettings:
    hz: int = 60

    @property
    def dt(self) -> float:
        return 1.0 / float(self.hz)


@dataclass(frozen=True)
class PhysicsSettings:
    gravity: float = 18.0
    engine_power: float = 22.0
    descend_power_factor: float = 0.60
    friction: float = 0.985
    max_speed_x: float = 35.0
    max_speed_y: float = 35.0

    # Converts the internal velocity units into screen pixels.
    position_scale: float = 10.0

    max_tilt_deg: float = 35.0
    tilt_rate_deg_per_s: float = 160.0
    tilt_return_rate_deg_per_s: float = 90.0

    # Multipliers (0..1) applied to velocity in special cases.
    brake_damping: float = 0.92
    ground_damping: float = 0.65
    ground_stop_speed: float = 0.02

    # Vertical speed threshold above which a landing counts as "hard".
    # This is in the same internal velocity units as `helicopter.vel.y`.
    safe_landing_vy: float = 10.0


@dataclass(frozen=True)
class HelicopterSettings:
    capacity: int = 16
    ground_y: float = 620.0
    rotor_clearance: float = 18.0


@dataclass(frozen=True)
class DebugSettings:
    show_overlay: bool = False
