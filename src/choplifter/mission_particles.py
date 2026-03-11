from __future__ import annotations

from .helicopter import Helicopter
from .mission_state import MissionState
from .settings import HelicopterSettings


def _update_world_particles(
    mission: MissionState,
    helicopter: Helicopter,
    dt: float,
    heli: HelicopterSettings,
) -> None:
    # World-space particle systems must be advanced every tick.
    mission.burning.update(dt)
    mission.impact_sparks.update(dt)
    mission.jet_trails.update(dt)
    mission.dust_storm.update(dt, heli_pos=helicopter.pos, heli_vel=helicopter.vel, ground_y=heli.ground_y)
    mission.heli_damage_fx.update(dt, heli_pos=helicopter.pos, heli_vel=helicopter.vel, damage=helicopter.damage)
    mission.enemy_damage_fx.update(dt, enemies=mission.enemies, tank_health=mission.tuning.tank_health)
    mission.explosions.update(dt)
    mission.flares.update(dt)
