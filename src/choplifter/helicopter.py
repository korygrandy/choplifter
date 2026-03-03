from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from .math2d import Vec2, clamp, deg_to_rad
from .settings import HelicopterSettings, PhysicsSettings


class Facing(Enum):
    LEFT = -1
    FORWARD = 0
    RIGHT = 1


@dataclass
class Helicopter:
    pos: Vec2
    vel: Vec2
    tilt_deg: float
    facing: Facing
    doors_open: bool
    grounded: bool
    damage: float
    fuel: float
    last_landing_vy: float
    skin_asset: str
    damage_flash_seconds: float
    damage_flash_rgb: tuple[int, int, int]

    @staticmethod
    def spawn(
        settings: HelicopterSettings,
        *,
        start_x: float = 1080.0,
        skin_asset: str = "chopper-one.png",
    ) -> "Helicopter":
        return Helicopter(
            pos=Vec2(start_x, settings.ground_y - 120.0),
            vel=Vec2(0.0, 0.0),
            tilt_deg=0.0,
            facing=Facing.RIGHT,
            doors_open=False,
            grounded=False,
            damage=0.0,
            fuel=100.0,
            last_landing_vy=0.0,
            skin_asset=skin_asset,
            damage_flash_seconds=0.0,
            damage_flash_rgb=(255, 60, 60),
        )

    def toggle_doors(self) -> None:
        # Prototype rule: doors are meaningful only when grounded.
        if self.grounded:
            self.doors_open = not self.doors_open

    def cycle_facing(self) -> None:
        if self.facing is Facing.LEFT:
            self.facing = Facing.FORWARD
        elif self.facing is Facing.FORWARD:
            self.facing = Facing.RIGHT
        else:
            self.facing = Facing.LEFT

    def reverse_flip(self) -> None:
        # Classic-inspired: reverse direction without killing momentum.
        if self.facing is Facing.LEFT:
            self.facing = Facing.RIGHT
        elif self.facing is Facing.RIGHT:
            self.facing = Facing.LEFT


@dataclass(frozen=True)
class HelicopterInput:
    tilt_left: bool = False
    tilt_right: bool = False
    lift_up: bool = False
    lift_down: bool = False
    brake: bool = False


def update_helicopter(
    helicopter: Helicopter,
    helicopter_input: HelicopterInput,
    dt: float,
    physics: PhysicsSettings,
    heli: HelicopterSettings,
    world_width: float = 1280.0,
    *,
    invulnerable: bool = False,
) -> None:
    ground_contact_y = heli.ground_y - heli.rotor_clearance
    on_ground_now = helicopter.pos.y >= ground_contact_y

    # Tilt control.
    tilt_target = 0.0
    if helicopter_input.tilt_left:
        tilt_target = -physics.max_tilt_deg
    elif helicopter_input.tilt_right:
        tilt_target = physics.max_tilt_deg

    if tilt_target != 0.0:
        step = physics.tilt_rate_deg_per_s * dt
        if helicopter.tilt_deg < tilt_target:
            helicopter.tilt_deg = min(tilt_target, helicopter.tilt_deg + step)
        else:
            helicopter.tilt_deg = max(tilt_target, helicopter.tilt_deg - step)
    else:
        # Return toward zero.
        step = physics.tilt_return_rate_deg_per_s * dt
        if helicopter.tilt_deg > 0:
            helicopter.tilt_deg = max(0.0, helicopter.tilt_deg - step)
        elif helicopter.tilt_deg < 0:
            helicopter.tilt_deg = min(0.0, helicopter.tilt_deg + step)

    # Lift control: simple vertical acceleration.
    lift_accel = 0.0
    if helicopter_input.lift_up:
        lift_accel += physics.engine_power
    if helicopter_input.lift_down:
        lift_accel -= physics.engine_power * float(physics.descend_power_factor)

    # Horizontal acceleration from tilt (fudged physics).
    ax = math.sin(deg_to_rad(helicopter.tilt_deg)) * physics.engine_power
    # While grounded, require lift to translate horizontally. This prevents the
    # helicopter from "sliding" left/right along the ground via stick tilt.
    if on_ground_now and not helicopter_input.lift_up:
        ax = 0.0

    # Apply accelerations.
    helicopter.vel.x += ax * dt
    helicopter.vel.y += (physics.gravity - lift_accel) * dt

    # Optional brake/hover assist.
    if helicopter_input.brake:
        helicopter.vel.x *= float(physics.brake_damping)
        helicopter.vel.y *= float(physics.brake_damping)

    # Clamp speeds.
    helicopter.vel.x = clamp(helicopter.vel.x, -physics.max_speed_x, physics.max_speed_x)
    helicopter.vel.y = clamp(helicopter.vel.y, -physics.max_speed_y, physics.max_speed_y)

    # Global friction / inertia decay.
    helicopter.vel.x *= physics.friction
    helicopter.vel.y *= physics.friction

    # Integrate.
    scale = float(physics.position_scale)
    helicopter.pos.x += helicopter.vel.x * dt * scale
    helicopter.pos.y += helicopter.vel.y * dt * scale

    # Ground / landing.
    if helicopter.pos.y >= ground_contact_y:
        if not helicopter.grounded:
            # Landing event.
            helicopter.last_landing_vy = helicopter.vel.y
            if not invulnerable and abs(helicopter.vel.y) > physics.safe_landing_vy:
                helicopter.damage = min(100.0, helicopter.damage + 12.5)
                helicopter.damage_flash_seconds = 0.12
                # Impact flash: bright/white to distinguish from bullets/mines/jets.
                helicopter.damage_flash_rgb = (245, 245, 245)
            helicopter.doors_open = False
        helicopter.grounded = True
        helicopter.pos.y = ground_contact_y
        helicopter.vel.y = 0.0
        if not helicopter_input.lift_up:
            # Extra ground friction so we don't drift/slide after landing.
            helicopter.vel.x *= float(physics.ground_damping)
            if abs(helicopter.vel.x) < float(physics.ground_stop_speed):
                helicopter.vel.x = 0.0
    else:
        helicopter.grounded = False

    # Keep within screen bounds for prototype.
    helicopter.pos.x = clamp(helicopter.pos.x, 0.0, world_width)
    helicopter.pos.y = clamp(helicopter.pos.y, 0.0, heli.ground_y - heli.rotor_clearance)
