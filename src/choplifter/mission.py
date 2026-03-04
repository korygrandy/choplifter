from __future__ import annotations

from dataclasses import dataclass, field
import logging
import math
import random

from .burning_particles import BurningParticleSystem
from .fx_particles import DustStormSystem, ExplosionSystem, FlareSystem, HelicopterDamageFxSystem, ImpactSparkSystem, JetTrailSystem
from .game_types import EnemyKind, HostageState, ProjectileKind
from .helicopter import Facing, Helicopter
from .math2d import Vec2, clamp
from .settings import HelicopterSettings
from . import haptics


@dataclass
class Hostage:
    state: HostageState
    pos: Vec2
    health: float = 100.0
    saved_slot: int = -1
    move_speed: float = 0.0


@dataclass
class Compound:
    pos: Vec2
    width: float
    height: float
    health: float
    is_open: bool
    hostage_start: int
    hostage_count: int
    log_bucket: int = -1

    def contains_point(self, p: Vec2) -> bool:
        return (
            self.pos.x <= p.x <= self.pos.x + self.width
            and self.pos.y <= p.y <= self.pos.y + self.height
        )


@dataclass
class Projectile:
    kind: ProjectileKind
    pos: Vec2
    vel: Vec2
    ttl: float
    source: "EnemyKind | None" = None
    alive: bool = True


@dataclass
class Enemy:
    kind: EnemyKind
    pos: Vec2
    vel: Vec2
    health: float
    cooldown: float = 0.0
    ttl: float = 999.0
    alive: bool = True
    entered_screen: bool = False
    trail_enabled: bool = False
    trail_spawn_accum: float = 0.0


@dataclass(frozen=True)
class MissionTuning:
    # Fuel pacing.
    fuel_drain_base_per_s: float = 0.55
    fuel_drain_airborne_per_s: float = 0.30
    fuel_drain_speed_per_s: float = 0.35
    fuel_refuel_per_s: float = 16.0

    # Enemy pressure.
    jet_spawn_base_interval_s: float = 7.0
    jet_spawn_min_interval_s: float = 5.2
    jet_spawn_max_interval_s: float = 9.0

    tank_fire_base_cooldown_s: float = 1.20
    tank_fire_min_cooldown_s: float = 0.9
    tank_fire_max_cooldown_s: float = 1.5

    tank_health: float = 110.0
    tank_initial_cooldown_s: float = 1.5
    tank_ground_offset_y: float = 8.0
    tank_fire_range_x: float = 360.0
    tank_fire_min_altitude_clearance_y: float = 40.0

    jet_fire_base_cooldown_s: float = 0.35
    jet_fire_min_cooldown_s: float = 0.25
    jet_fire_max_cooldown_s: float = 0.45

    jet_health: float = 30.0
    jet_ttl_s: float = 6.0
    jet_spawn_y: float = 150.0
    jet_speed_x: float = 280.0
    jet_spawn_margin_x: float = 80.0
    jet_fire_range_x: float = 240.0
    jet_collision_radius: float = 30.0
    jet_touch_damage: float = 18.0

    mine_base_speed: float = 110.0
    mine_min_speed: float = 90.0
    mine_max_speed: float = 130.0
    mine_steer: float = 3.5
    mine_health: float = 1.0
    mine_ttl_s: float = 22.0
    mine_touch_radius: float = 26.0
    mine_projectile_radius: float = 14.0
    mine_damage: float = 26.0

    mine_spawn_base_interval_s: float = 28.0
    mine_spawn_min_interval_s: float = 18.0
    mine_spawn_max_interval_s: float = 40.0
    mine_spawn_margin_x: float = 260.0
    mine_spawn_y_min: float = 90.0
    mine_spawn_y_max: float = 220.0
    mine_max_alive: int = 2

    # Hostage/rescue loop.
    # The game randomly mixes a more readable/controlled style with a more chaotic style.
    hostage_controlled_move_speed: float = 40.0
    hostage_controlled_max_moving_to_lz: int = 4
    hostage_chaotic_move_speed: float = 52.0
    hostage_chaotic_max_moving_to_lz: int = 12
    hostage_chaos_probability: float = 0.35


@dataclass(frozen=True)
class LevelConfig:
    world_width: float
    compound_xs: tuple[float, ...]
    compound_width: float
    compound_height: float
    compound_health: float
    hostages_per_compound: int
    base_width: float
    base_height: float
    base_right_margin: float
    base_bottom_margin: float
    bg_asset: str
    initial_air_mine_pos: Vec2 | None
    initial_air_mine_delay_s: float
    initial_jet_spawn_delay_s: float
    tuning: MissionTuning


@dataclass(frozen=True)
class BaseZone:
    pos: Vec2
    width: float
    height: float

    def contains_point(self, p: Vec2) -> bool:
        return (
            self.pos.x <= p.x <= self.pos.x + self.width
            and self.pos.y <= p.y <= self.pos.y + self.height
        )


@dataclass
class MissionStats:
    saved: int = 0
    kia_by_player: int = 0
    kia_by_enemy: int = 0
    lost_in_transit: int = 0
    enemies_destroyed: int = 0
    tanks_destroyed: int = 0
    artillery_fired: int = 0
    artillery_hits: int = 0
    jets_entered: int = 0
    mines_detonated: int = 0


@dataclass
class MissionState:
    compounds: list[Compound]
    hostages: list[Hostage]
    projectiles: list[Projectile]
    enemies: list[Enemy]
    base: BaseZone
    world_width: float = 1280.0
    bg_asset: str = "mission1-bg.jpg"
    stats: MissionStats = field(default_factory=MissionStats)
    sentiment: float = 50.0
    tuning: MissionTuning = MissionTuning()
    burning: BurningParticleSystem = field(default_factory=BurningParticleSystem)
    impact_sparks: ImpactSparkSystem = field(default_factory=ImpactSparkSystem)
    jet_trails: JetTrailSystem = field(default_factory=JetTrailSystem)
    dust_storm: DustStormSystem = field(default_factory=DustStormSystem)
    heli_damage_fx: HelicopterDamageFxSystem = field(default_factory=HelicopterDamageFxSystem)
    explosions: ExplosionSystem = field(default_factory=ExplosionSystem)
    flares: FlareSystem = field(default_factory=FlareSystem)
    elapsed_seconds: float = 0.0
    pending_air_mine_pos: Vec2 | None = None
    pending_air_mine_seconds: float = 0.0
    ended: bool = False
    end_text: str = ""
    end_reason: str = ""
    crashes: int = 0
    invuln_seconds: float = 0.0
    flare_invuln_seconds: float = 0.0

    # Cinematic feedback impulses consumed by the main loop.
    feedback_shake_impulse: float = 0.0
    feedback_duck_strength: float = 0.0

    # Crash animation state (damage >= 100 triggers crash sequence).
    crash_active: bool = False
    crash_variant: int = 0  # 0=level spin, 1=tail-spin
    crash_seconds: float = 0.0
    crash_origin: Vec2 = field(default_factory=lambda: Vec2(0.0, 0.0))
    crash_vel: Vec2 = field(default_factory=lambda: Vec2(0.0, 0.0))
    crash_impacted: bool = False
    crash_impact_seconds: float = 0.0
    crash_impact_sfx_pending: bool = False
    jet_spawn_seconds: float = 4.0
    mine_spawn_seconds: float = 24.0
    unload_release_seconds: float = 0.0
    next_saved_slot: int = 0
    _sentiment_last_saved: int = 0
    _sentiment_last_kia_player: int = 0
    _sentiment_last_kia_enemy: int = 0
    _sentiment_last_lost_in_transit: int = 0
    _last_logged_boarded: int = 0
    _last_logged_saved: int = 0
    _last_logged_kia_player: int = 0
    _last_logged_kia_enemy: int = 0
    _last_logged_enemies_destroyed: int = 0
    _last_logged_sentiment_bucket: int = -1
    _last_logged_fuel_int: int = -1

    @staticmethod
    def create_default(heli: HelicopterSettings) -> "MissionState":
        level = create_level_1_config()
        return MissionState.create_from_level_config(heli, level)

    @staticmethod
    def create_from_level_config(
        heli: HelicopterSettings,
        level: LevelConfig,
        world_width: float | None = None,
    ) -> "MissionState":
        if world_width is None:
            world_width = level.world_width
        compounds: list[Compound] = []
        hostage_index = 0
        compound_w = level.compound_width
        compound_h = level.compound_height
        compound_y = heli.ground_y - compound_h

        for x in level.compound_xs:
            compounds.append(
                Compound(
                    pos=Vec2(x, compound_y),
                    width=compound_w,
                    height=compound_h,
                    health=level.compound_health,
                    is_open=False,
                    hostage_start=hostage_index,
                    hostage_count=level.hostages_per_compound,
                )
            )
            hostage_index += level.hostages_per_compound

        hostages_total = max(64, hostage_index)
        hostages = [Hostage(state=HostageState.IDLE, pos=Vec2(-9999.0, -9999.0)) for _ in range(hostages_total)]

        base_w = level.base_width
        base_h = level.base_height
        base = BaseZone(
            pos=Vec2(world_width - base_w - level.base_right_margin, heli.ground_y - base_h - level.base_bottom_margin),
            width=base_w,
            height=base_h,
        )

        enemies: list[Enemy] = []
        # Place a tank near each compound to create landing pressure.
        for c in compounds:
            enemies.append(
                Enemy(
                    kind=EnemyKind.TANK,
                    pos=Vec2(c.pos.x + c.width * 0.5, heli.ground_y - level.tuning.tank_ground_offset_y),
                    vel=Vec2(0.0, 0.0),
                    health=level.tuning.tank_health,
                    cooldown=level.tuning.tank_initial_cooldown_s,
                )
            )

        pending_mine_pos: Vec2 | None = None
        pending_mine_seconds = 0.0
        if level.initial_air_mine_pos is not None:
            if level.initial_air_mine_delay_s <= 0.0:
                enemies.append(
                    Enemy(
                        kind=EnemyKind.AIR_MINE,
                        pos=Vec2(level.initial_air_mine_pos.x, level.initial_air_mine_pos.y),
                        vel=Vec2(0.0, 0.0),
                        health=level.tuning.mine_health,
                        ttl=level.tuning.mine_ttl_s,
                    )
                )
            else:
                pending_mine_pos = level.initial_air_mine_pos
                pending_mine_seconds = level.initial_air_mine_delay_s

        state = MissionState(
            compounds=compounds,
            hostages=hostages,
            projectiles=[],
            enemies=enemies,
            base=base,
            world_width=world_width,
            bg_asset=level.bg_asset,
            stats=MissionStats(),
            tuning=level.tuning,
        )

        state.jet_spawn_seconds = level.initial_jet_spawn_delay_s
        # Keep the first minute calmer: the level can schedule an initial mine via pending_air_mine_*.
        # Periodic mine spawns start shortly after that initial delay.
        state.mine_spawn_seconds = max(
            level.tuning.mine_spawn_base_interval_s,
            level.initial_air_mine_delay_s + 18.0,
        )
        state.pending_air_mine_pos = pending_mine_pos
        state.pending_air_mine_seconds = pending_mine_seconds
        return state


def create_level_1_config() -> LevelConfig:
    return LevelConfig(
        world_width=2200.0,
        compound_xs=(900.0, 1100.0, 1300.0, 1500.0),
        compound_width=80.0,
        compound_height=60.0,
        compound_health=120.0,
        hostages_per_compound=16,
        base_width=170.0,
        base_height=90.0,
        base_right_margin=20.0,
        base_bottom_margin=0.0,
        bg_asset="mission1-bg.jpg",
        initial_air_mine_pos=Vec2(1250.0, 180.0),
        initial_air_mine_delay_s=60.0,
        initial_jet_spawn_delay_s=18.0,
        tuning=MissionTuning(),
    )


def create_city_center_config() -> LevelConfig:
    # Current "Mission 1" content.
    return create_level_1_config()


def create_airport_special_ops_config() -> LevelConfig:
    # Wider lanes and longer travel distances.
    tuning = MissionTuning(
        jet_spawn_base_interval_s=6.6,
        jet_spawn_min_interval_s=5.0,
        jet_spawn_max_interval_s=8.4,
        mine_spawn_base_interval_s=24.0,
        mine_spawn_min_interval_s=16.0,
        mine_spawn_max_interval_s=34.0,
        mine_spawn_margin_x=320.0,
    )
    return LevelConfig(
        world_width=2800.0,
        compound_xs=(1150.0, 1500.0, 1850.0),
        compound_width=90.0,
        compound_height=60.0,
        compound_health=130.0,
        hostages_per_compound=16,
        base_width=180.0,
        base_height=90.0,
        base_right_margin=30.0,
        base_bottom_margin=0.0,
        bg_asset="mission2-bg.jpg",
        initial_air_mine_pos=Vec2(1450.0, 170.0),
        initial_air_mine_delay_s=40.0,
        initial_jet_spawn_delay_s=14.0,
        tuning=tuning,
    )


def create_worship_center_warfare_config() -> LevelConfig:
    # Higher pressure and tighter pacing for a finale-style mission.
    tuning = MissionTuning(
        jet_spawn_base_interval_s=6.0,
        jet_spawn_min_interval_s=4.7,
        jet_spawn_max_interval_s=7.5,
        tank_fire_base_cooldown_s=1.05,
        tank_fire_min_cooldown_s=0.85,
        tank_fire_max_cooldown_s=1.35,
        mine_spawn_base_interval_s=20.0,
        mine_spawn_min_interval_s=14.0,
        mine_spawn_max_interval_s=28.0,
        mine_max_alive=3,
    )
    return LevelConfig(
        world_width=2400.0,
        compound_xs=(950.0, 1120.0, 1290.0, 1460.0),
        compound_width=80.0,
        compound_height=60.0,
        compound_health=120.0,
        hostages_per_compound=16,
        base_width=170.0,
        base_height=90.0,
        base_right_margin=20.0,
        base_bottom_margin=0.0,
        bg_asset="mission3-bg.jpg",
        initial_air_mine_pos=Vec2(1180.0, 175.0),
        initial_air_mine_delay_s=25.0,
        initial_jet_spawn_delay_s=10.0,
        tuning=tuning,
    )


def get_mission_config_by_id(mission_id: str) -> LevelConfig:
    mission_id = (mission_id or "").strip().lower()
    if mission_id in ("city", "city_center", "citycenter", "mission1", "m1"):
        return create_city_center_config()
    if mission_id in ("airport", "airport_special_ops", "airportspecialops", "mission2", "m2"):
        return create_airport_special_ops_config()
    if mission_id in ("worship", "worship_center", "worshipcenter", "mission3", "m3"):
        return create_worship_center_warfare_config()
    # Default to the current mission content.
    return create_city_center_config()


def boarded_count(mission: MissionState) -> int:
    return sum(1 for h in mission.hostages if h.state is HostageState.BOARDED)


def on_foot(hostage: Hostage) -> bool:
    return hostage.state in (HostageState.PANIC, HostageState.MOVING_TO_LZ, HostageState.WAITING, HostageState.EXITING)


def spawn_projectile_from_helicopter(mission: MissionState, helicopter: Helicopter) -> None:
    # Minimal: side-facing shoots bullets, forward-facing drops a bomb.
    if mission.ended:
        return

    if helicopter.facing is Facing.FORWARD:
        mission.projectiles.append(
            Projectile(
                kind=ProjectileKind.BOMB,
                pos=Vec2(helicopter.pos.x, helicopter.pos.y + 10.0),
                vel=Vec2(0.0, 3.0),
                ttl=2.5,
            )
        )
        return

    direction = -1.0 if helicopter.facing is Facing.LEFT else 1.0
    mission.projectiles.append(
        Projectile(
            kind=ProjectileKind.BULLET,
            pos=Vec2(helicopter.pos.x + direction * 40.0, helicopter.pos.y),
            vel=Vec2(direction * 95.0, 0.0),
            ttl=1.2,
        )
    )


def spawn_projectile_from_helicopter_logged(
    mission: MissionState,
    helicopter: Helicopter,
    logger: logging.Logger | None,
) -> None:
    spawn_projectile_from_helicopter(mission, helicopter)
    if logger is None:
        return
    if helicopter.facing is Facing.FORWARD:
        logger.info("Fire: BOMB")
    else:
        logger.info("Fire: BULLET")


def update_mission(
    mission: MissionState,
    helicopter: Helicopter,
    dt: float,
    heli: HelicopterSettings,
    logger: logging.Logger | None = None,
) -> None:
    if mission.ended:
        return

    mission.elapsed_seconds += dt

    if mission.invuln_seconds > 0.0:
        mission.invuln_seconds = max(0.0, mission.invuln_seconds - dt)

    if mission.flare_invuln_seconds > 0.0:
        mission.flare_invuln_seconds = max(0.0, mission.flare_invuln_seconds - dt)

    _update_fuel(mission, helicopter, dt, logger)
    if helicopter.fuel <= 0.0:
        _end_mission(mission, "THE END", "OUT OF FUEL", logger)
        return

    # Particle effects (world-space).
    mission.burning.update(dt)
    mission.impact_sparks.update(dt)
    mission.jet_trails.update(dt)
    mission.dust_storm.update(dt, heli_pos=helicopter.pos, heli_vel=helicopter.vel, ground_y=heli.ground_y)
    mission.heli_damage_fx.update(dt, heli_pos=helicopter.pos, heli_vel=helicopter.vel, damage=helicopter.damage)
    mission.explosions.update(dt)
    mission.flares.update(dt)

    # If we're in a crash animation, run the crash sequence and skip gameplay updates.
    if mission.crash_active:
        _update_crash_sequence(mission, helicopter, dt, heli, logger)
        return

    _update_enemies(mission, helicopter, dt, heli, logger)

    _update_projectiles(mission, dt, heli, logger, helicopter)
    _update_compounds_and_release(mission, heli, logger)
    _update_hostages(mission, helicopter, dt, heli)
    _handle_unload(mission, helicopter, heli, dt)

    _handle_crash_and_respawn(mission, helicopter, dt, heli, logger)
    if mission.ended:
        return

    _update_sentiment(mission)

    _log_progress_if_changed(mission, logger)

    if mission.stats.saved >= 20:
        _end_mission(mission, "THE END", "RESCUE SUCCESS", logger)


def _update_projectiles(
    mission: MissionState,
    dt: float,
    heli: HelicopterSettings,
    logger: logging.Logger | None,
    helicopter: Helicopter,
) -> None:
    gravity = 28.0

    for p in mission.projectiles:
        if not p.alive:
            continue

        p.ttl -= dt
        if p.ttl <= 0.0:
            p.alive = False
            continue

        if p.kind is ProjectileKind.BOMB:
            p.vel.y += gravity * dt

        p.pos.x += p.vel.x * dt
        p.pos.y += p.vel.y * dt

        # Enemy collision (player projectiles only).
        if p.kind in (ProjectileKind.BULLET, ProjectileKind.BOMB):
            for e in mission.enemies:
                if not e.alive:
                    continue
                if _projectile_hits_enemy(p, e, heli, mission.tuning):
                    if p.kind is ProjectileKind.BULLET:
                        e.health -= 10.0
                    else:
                        e.health -= 40.0
                    if e.health <= 0.0:
                        e.alive = False
                        mission.stats.enemies_destroyed += 1
                        if e.kind is EnemyKind.TANK:
                            mission.stats.tanks_destroyed += 1
                            # Persist a burning effect at the destroyed cannon/tank location.
                            mission.burning.add_site(e.pos, intensity=1.0)
                            haptics.rumble_tank_destroyed(logger=logger)
                        if logger is not None:
                            logger.info("ENEMY_DOWN: %s", e.kind.name)
                    p.alive = False
                    break

        if not p.alive:
            continue

        # Helicopter collision (enemy projectiles only).
        if p.kind in (ProjectileKind.ENEMY_BULLET, ProjectileKind.ENEMY_ARTILLERY):
            if _hits_circle(p.pos, helicopter.pos, radius=26.0):
                if p.kind is ProjectileKind.ENEMY_ARTILLERY:
                    mission.stats.artillery_hits += 1
                    mission.impact_sparks.emit_hit(p.pos, p.vel, strength=1.25)
                    _damage_helicopter(mission, helicopter, 10.0, logger, source="ARTILLERY")
                else:
                    _damage_helicopter(mission, helicopter, 10.0, logger, source="ENEMY_BULLET")
                p.alive = False
                continue

        # Ground collision.
        if p.pos.y >= heli.ground_y - 6.0:
            if p.kind is ProjectileKind.BOMB:
                _bomb_explode(mission, p.pos, logger)
            p.alive = False
            continue

        # Compound collision (player projectiles only).
        for c in mission.compounds:
            if c.health <= 0:
                continue
            if c.contains_point(p.pos):
                if p.kind is ProjectileKind.BULLET:
                    c.health -= 12.0
                elif p.kind is ProjectileKind.BOMB:
                    c.health -= 40.0
                else:
                    continue
                _log_compound_health_if_needed(c, logger, reason="hit")
                p.alive = False
                break

        if not p.alive:
            continue

        # Hostage hits.
        for h in mission.hostages:
            if not on_foot(h):
                continue
            dx = h.pos.x - p.pos.x
            dy = h.pos.y - p.pos.y
            if dx * dx + dy * dy <= 12.0 * 12.0:
                h.state = HostageState.KIA
                if p.kind in (ProjectileKind.ENEMY_BULLET, ProjectileKind.ENEMY_ARTILLERY):
                    mission.stats.kia_by_enemy += 1
                else:
                    mission.stats.kia_by_player += 1
                p.alive = False
                break

    # Compact list.
    mission.projectiles = [p for p in mission.projectiles if p.alive]


def _bomb_explode(mission: MissionState, pos: Vec2, logger: logging.Logger | None) -> None:
    # Small AoE for collateral + compound damage.
    radius = 42.0
    r2 = radius * radius

    for c in mission.compounds:
        if c.health <= 0:
            continue
        cx = clamp(pos.x, c.pos.x, c.pos.x + c.width)
        cy = clamp(pos.y, c.pos.y, c.pos.y + c.height)
        dx = pos.x - cx
        dy = pos.y - cy
        if dx * dx + dy * dy <= r2:
            c.health -= 30.0
            _log_compound_health_if_needed(c, logger, reason="blast")

    for h in mission.hostages:
        if not on_foot(h):
            continue
        dx = h.pos.x - pos.x
        dy = h.pos.y - pos.y
        if dx * dx + dy * dy <= r2:
            h.state = HostageState.KIA
            mission.stats.kia_by_player += 1

    for e in mission.enemies:
        if not e.alive:
            continue
        dx = e.pos.x - pos.x
        dy = e.pos.y - pos.y
        if dx * dx + dy * dy <= r2:
            e.health -= 55.0
            if e.health <= 0.0:
                e.alive = False
                mission.stats.enemies_destroyed += 1
                if e.kind is EnemyKind.TANK:
                    mission.stats.tanks_destroyed += 1
                    mission.burning.add_site(e.pos, intensity=1.0)
                    haptics.rumble_tank_destroyed(logger=logger)
                if logger is not None:
                    logger.info("ENEMY_DOWN: %s", e.kind.name)


def _update_compounds_and_release(mission: MissionState, heli: HelicopterSettings, logger: logging.Logger | None) -> None:
    for c in mission.compounds:
        if c.is_open:
            continue
        if c.health > 0.0:
            continue

        c.is_open = True
        if logger is not None:
            logger.info(
                "Compound opened: x=%.0f hostages=%d..%d",
                c.pos.x,
                c.hostage_start,
                c.hostage_start + c.hostage_count - 1,
            )
        # Spawn hostages at the compound entrance area.
        start = c.hostage_start
        end = start + c.hostage_count
        for i, h in enumerate(mission.hostages[start:end]):
            spread = (i % 8) * 10.0
            row = i // 8
            h.state = HostageState.PANIC
            h.pos = Vec2(c.pos.x + 10.0 + spread, heli.ground_y - 10.0 - row * 10.0)


def _update_hostages(mission: MissionState, helicopter: Helicopter, dt: float, heli: HelicopterSettings) -> None:
    capacity = heli.capacity
    boarded = boarded_count(mission)

    lz_available = helicopter.grounded and helicopter.doors_open and boarded < capacity

    # Boarding radius around helicopter.
    load_radius = 58.0
    load_r2 = load_radius * load_radius

    controlled_speed = mission.tuning.hostage_controlled_move_speed
    controlled_cap = max(1, int(mission.tuning.hostage_controlled_max_moving_to_lz))
    chaotic_speed = mission.tuning.hostage_chaotic_move_speed
    chaotic_cap = max(1, int(mission.tuning.hostage_chaotic_max_moving_to_lz))
    chaos_p = clamp(mission.tuning.hostage_chaos_probability, 0.0, 1.0)
    moving_to_lz = sum(1 for h in mission.hostages if h.state is HostageState.MOVING_TO_LZ)

    def saved_slot_pos(slot: int) -> Vec2:
        # Pack saved hostages inside the base zone.
        slot = max(0, int(slot))
        padding_x = 14.0
        padding_y = 16.0
        spacing_x = 14.0
        spacing_y = 14.0

        usable_w = max(1.0, mission.base.width - padding_x * 2.0)
        cols = max(1, int(usable_w // spacing_x))
        col = slot % cols
        row = slot // cols

        x = mission.base.pos.x + padding_x + col * spacing_x
        floor_y = heli.ground_y - 6.0
        y = max(mission.base.pos.y + padding_y, floor_y - row * spacing_y)
        return Vec2(x, y)

    for h in mission.hostages:
        if h.state is HostageState.SAVED:
            if h.saved_slot >= 0:
                h.pos = saved_slot_pos(h.saved_slot)
            continue

        if h.state is HostageState.EXITING:
            if h.saved_slot < 0:
                h.saved_slot = mission.next_saved_slot
                mission.next_saved_slot += 1
            target = saved_slot_pos(h.saved_slot)

            h.pos.y = heli.ground_y - 6.0
            direction = -1.0 if h.pos.x > target.x else 1.0
            h.pos.x += direction * 62.0 * dt

            if abs(h.pos.x - target.x) <= 2.0:
                h.pos = target
                h.state = HostageState.SAVED
                mission.stats.saved += 1
            continue

        if h.state is HostageState.PANIC:
            h.state = HostageState.WAITING

        if h.state is HostageState.WAITING:
            if lz_available:
                # Mix both behaviors: sometimes a controlled "queue", sometimes a chaotic rush.
                is_chaotic = random.random() < chaos_p
                cap = chaotic_cap if is_chaotic else controlled_cap
                start_radius = 320.0 if is_chaotic else 240.0

                if moving_to_lz >= cap:
                    continue

                # If close enough horizontally, start moving to LZ.
                if abs(h.pos.x - helicopter.pos.x) <= start_radius:
                    h.state = HostageState.MOVING_TO_LZ
                    moving_to_lz += 1

                    base_speed = chaotic_speed if is_chaotic else controlled_speed
                    if is_chaotic:
                        # Small per-hostage variation so they don't march in lockstep.
                        base_speed *= random.uniform(0.9, 1.15)
                    h.move_speed = base_speed

        if h.state is HostageState.MOVING_TO_LZ:
            if not lz_available:
                h.state = HostageState.WAITING
                h.move_speed = 0.0
                moving_to_lz = max(0, moving_to_lz - 1)
                continue

            direction = -1.0 if h.pos.x > helicopter.pos.x else 1.0
            speed = h.move_speed if h.move_speed > 0.0 else controlled_speed
            step = speed * dt
            dx_to_heli = helicopter.pos.x - h.pos.x
            if abs(dx_to_heli) <= step:
                h.pos.x = helicopter.pos.x
            else:
                h.pos.x += direction * step

            # Snap to helicopter and board.
            dx = h.pos.x - helicopter.pos.x
            dy = h.pos.y - helicopter.pos.y
            if dx * dx + dy * dy <= load_r2:
                boarded = boarded_count(mission)
                if boarded < capacity:
                    h.state = HostageState.BOARDED
                    h.pos = Vec2(-9999.0, -9999.0)
                    h.move_speed = 0.0
                    moving_to_lz = max(0, moving_to_lz - 1)
                else:
                    h.state = HostageState.WAITING
                    h.move_speed = 0.0
                    moving_to_lz = max(0, moving_to_lz - 1)


def _handle_unload(mission: MissionState, helicopter: Helicopter, heli: HelicopterSettings, dt: float) -> None:
    # Unload rule: must be grounded at base and doors open.
    if not helicopter.grounded or not helicopter.doors_open:
        mission.unload_release_seconds = 0.0
        return

    if not mission.base.contains_point(helicopter.pos):
        mission.unload_release_seconds = 0.0
        return

    mission.unload_release_seconds = max(0.0, mission.unload_release_seconds - dt)
    if mission.unload_release_seconds > 0.0:
        return

    # Release one passenger at a time so the player can see them exit.
    boarded = next((h for h in mission.hostages if h.state is HostageState.BOARDED), None)
    if boarded is None:
        return

    door_offset_x = 0.0
    if helicopter.facing is Facing.LEFT:
        door_offset_x = -18.0
    elif helicopter.facing is Facing.RIGHT:
        door_offset_x = 18.0

    boarded.state = HostageState.EXITING
    boarded.saved_slot = mission.next_saved_slot
    mission.next_saved_slot += 1
    boarded.pos = Vec2(helicopter.pos.x + door_offset_x, heli.ground_y - 6.0)

    mission.unload_release_seconds = 0.22


def hostage_crush_check(
    mission: MissionState,
    helicopter: Helicopter,
    last_landing_vy: float,
    *,
    safe_landing_vy: float,
) -> None:
    # Called on a landing event. If the landing was hard and a hostage is under the helicopter, crush them.
    if mission.ended:
        return

    if abs(last_landing_vy) <= safe_landing_vy:
        return

    crush_radius = 28.0
    r2 = crush_radius * crush_radius

    for h in mission.hostages:
        if not on_foot(h):
            continue
        dx = h.pos.x - helicopter.pos.x
        dy = h.pos.y - helicopter.pos.y
        if dx * dx + dy * dy <= r2:
            h.state = HostageState.KIA
            mission.stats.kia_by_player += 1


def hostage_crush_check_logged(
    mission: MissionState,
    helicopter: Helicopter,
    last_landing_vy: float,
    *,
    safe_landing_vy: float,
    logger: logging.Logger | None,
) -> None:
    before = mission.stats.kia_by_player
    hostage_crush_check(mission, helicopter, last_landing_vy, safe_landing_vy=safe_landing_vy)
    if logger is None:
        return
    if mission.stats.kia_by_player != before:
        logger.info("CRUSH: hard landing killed %d hostage(s)", mission.stats.kia_by_player - before)


def _log_progress_if_changed(mission: MissionState, logger: logging.Logger | None) -> None:
    if logger is None:
        return

    boarded = boarded_count(mission)
    if boarded != mission._last_logged_boarded:
        mission._last_logged_boarded = boarded
        logger.info("BOARDING: boarded=%d", boarded)

    if mission.stats.saved != mission._last_logged_saved:
        delta = mission.stats.saved - mission._last_logged_saved
        mission._last_logged_saved = mission.stats.saved
        logger.info("UNLOAD: +%d saved (total=%d)", delta, mission.stats.saved)

    if mission.stats.kia_by_player != mission._last_logged_kia_player:
        delta = mission.stats.kia_by_player - mission._last_logged_kia_player
        mission._last_logged_kia_player = mission.stats.kia_by_player
        logger.info("COLLATERAL: +%d KIA_by_player (total=%d)", delta, mission.stats.kia_by_player)

    if mission.stats.kia_by_enemy != mission._last_logged_kia_enemy:
        delta = mission.stats.kia_by_enemy - mission._last_logged_kia_enemy
        mission._last_logged_kia_enemy = mission.stats.kia_by_enemy
        logger.info("ENEMY_FIRE: +%d KIA_by_enemy (total=%d)", delta, mission.stats.kia_by_enemy)

    if mission.stats.enemies_destroyed != mission._last_logged_enemies_destroyed:
        delta = mission.stats.enemies_destroyed - mission._last_logged_enemies_destroyed
        mission._last_logged_enemies_destroyed = mission.stats.enemies_destroyed
        logger.info("ENEMIES: +%d destroyed (total=%d)", delta, mission.stats.enemies_destroyed)

    # Log sentiment as it crosses buckets (keeps logs readable).
    bucket = int(clamp(mission.sentiment, 0.0, 100.0) // 10)
    if bucket != mission._last_logged_sentiment_bucket:
        mission._last_logged_sentiment_bucket = bucket
        logger.info("SENTIMENT: %.0f", clamp(mission.sentiment, 0.0, 100.0))


def _difficulty_scale(sentiment: float) -> float:
    # Map sentiment 0..100 to a difficulty scalar -1..+1.
    # Low sentiment => more pressure; high sentiment => slightly less.
    return clamp((50.0 - clamp(sentiment, 0.0, 100.0)) / 50.0, -1.0, 1.0)


def _update_sentiment(mission: MissionState) -> None:
    # Minimal MVP interpretation:
    # - Rescues increase sentiment
    # - Any hostage deaths decrease sentiment (player-caused more severe)
    # - Lost-in-transit decreases sentiment
    saved = mission.stats.saved
    kia_player = mission.stats.kia_by_player
    kia_enemy = mission.stats.kia_by_enemy
    lost = mission.stats.lost_in_transit

    dsaved = saved - mission._sentiment_last_saved
    dkia_player = kia_player - mission._sentiment_last_kia_player
    dkia_enemy = kia_enemy - mission._sentiment_last_kia_enemy
    dlost = lost - mission._sentiment_last_lost_in_transit

    if dsaved or dkia_player or dkia_enemy or dlost:
        mission.sentiment += dsaved * 2.5
        mission.sentiment -= dkia_player * 4.0
        mission.sentiment -= dkia_enemy * 2.5
        mission.sentiment -= dlost * 3.5
        mission.sentiment = clamp(mission.sentiment, 0.0, 100.0)

    mission._sentiment_last_saved = saved
    mission._sentiment_last_kia_player = kia_player
    mission._sentiment_last_kia_enemy = kia_enemy
    mission._sentiment_last_lost_in_transit = lost


def _log_compound_health_if_needed(c: Compound, logger: logging.Logger | None, reason: str) -> None:
    if logger is None:
        return

    health = max(0.0, c.health)

    # Log only when health crosses buckets of 20 (avoids log spam).
    bucket = int(health // 20.0)
    if bucket == c.log_bucket:
        return

    c.log_bucket = bucket
    logger.info("Compound %s: x=%.0f health=%.0f", reason, c.pos.x, health)


def _update_fuel(mission: MissionState, helicopter: Helicopter, dt: float, logger: logging.Logger | None) -> None:
    if mission.ended:
        return

    # Minimal MVP-lite: fuel drains over time, refuels at base.
    tuning = mission.tuning
    # Tune: make hovering/landing feel less punishing, but fast flight costs.
    drain_base_per_s = tuning.fuel_drain_base_per_s
    drain_airborne_per_s = tuning.fuel_drain_airborne_per_s
    drain_speed_per_s = tuning.fuel_drain_speed_per_s
    refuel_per_s = tuning.fuel_refuel_per_s

    at_base = mission.base.contains_point(helicopter.pos) and helicopter.grounded
    if at_base:
        helicopter.fuel = min(100.0, helicopter.fuel + refuel_per_s * dt)
    else:
        speed = abs(helicopter.vel.x) + abs(helicopter.vel.y)
        speed_factor = clamp(speed / 50.0, 0.0, 1.0)
        drain = drain_base_per_s
        if not helicopter.grounded:
            drain += drain_airborne_per_s
            drain += drain_speed_per_s * speed_factor
        helicopter.fuel = max(0.0, helicopter.fuel - drain * dt)

    fuel_int = int(helicopter.fuel)
    if logger is not None and fuel_int != mission._last_logged_fuel_int:
        if fuel_int in (75, 50, 25, 10, 5, 0):
            logger.info("FUEL: %d", fuel_int)
    mission._last_logged_fuel_int = fuel_int


def _update_enemies(
    mission: MissionState,
    helicopter: Helicopter,
    dt: float,
    heli: HelicopterSettings,
    logger: logging.Logger | None,
) -> None:
    difficulty = _difficulty_scale(mission.sentiment)
    tuning = mission.tuning

    # Time-based pressure ramp:
    # - First 60s: easier
    # - Next 60s: ramp back to normal
    # pressure > 1 => more frequent threats; < 1 => less.
    ramp_t = clamp((mission.elapsed_seconds - 60.0) / 60.0, 0.0, 1.0)
    pressure = (0.75 * (1.0 - ramp_t)) + (1.00 * ramp_t)

    # Spawn a delayed initial air mine (used to keep the first minute calmer).
    if mission.pending_air_mine_pos is not None:
        mission.pending_air_mine_seconds -= dt
        if mission.pending_air_mine_seconds <= 0.0:
            mission.enemies.append(
                Enemy(
                    kind=EnemyKind.AIR_MINE,
                    pos=Vec2(mission.pending_air_mine_pos.x, mission.pending_air_mine_pos.y),
                    vel=Vec2(0.0, 0.0),
                    health=tuning.mine_health,
                    ttl=tuning.mine_ttl_s,
                )
            )
            if logger is not None:
                logger.info("MINE: spawned")
            mission.pending_air_mine_pos = None

    # Periodic air mine spawns.
    mission.mine_spawn_seconds -= dt
    if mission.mine_spawn_seconds <= 0.0:
        alive_mines = sum(1 for e in mission.enemies if e.alive and e.kind is EnemyKind.AIR_MINE)
        if alive_mines < max(0, int(tuning.mine_max_alive)):
            interval = (tuning.mine_spawn_base_interval_s / pressure) * (1.0 - 0.10 * difficulty)
            mission.mine_spawn_seconds = clamp(
                interval,
                tuning.mine_spawn_min_interval_s,
                tuning.mine_spawn_max_interval_s,
            )

            # Deterministic pseudo-random spawn height (keeps behavior stable without adding RNG state).
            # Uses elapsed time as input; returns value in [0, 1).
            r01 = math.sin(mission.elapsed_seconds * 12.9898) * 43758.5453
            r01 = r01 - math.floor(r01)
            y = tuning.mine_spawn_y_min + (tuning.mine_spawn_y_max - tuning.mine_spawn_y_min) * r01
            y = clamp(y, 60.0, heli.ground_y - 80.0)

            # Spawn ahead of the helicopter's facing direction.
            sign = 1.0 if helicopter.facing is Facing.RIGHT else -1.0
            x = helicopter.pos.x + sign * tuning.mine_spawn_margin_x
            x = clamp(x, 40.0, mission.world_width - 40.0)

            mission.enemies.append(
                Enemy(
                    kind=EnemyKind.AIR_MINE,
                    pos=Vec2(x, y),
                    vel=Vec2(0.0, 0.0),
                    health=tuning.mine_health,
                    ttl=tuning.mine_ttl_s,
                )
            )
            if logger is not None:
                logger.info("MINE: spawned")
        else:
            # Try again soon once the mine count drops.
            mission.mine_spawn_seconds = 1.0

    # Periodic jet spawns.
    mission.jet_spawn_seconds -= dt
    if mission.jet_spawn_seconds <= 0.0:
        # Slight scaling based on sentiment.
        interval = (tuning.jet_spawn_base_interval_s / pressure) * (1.0 - 0.22 * difficulty)
        mission.jet_spawn_seconds = clamp(interval, tuning.jet_spawn_min_interval_s, tuning.jet_spawn_max_interval_s)
        y = tuning.jet_spawn_y
        if helicopter.pos.x > mission.world_width * 0.5:
            x = -tuning.jet_spawn_margin_x
            vx = tuning.jet_speed_x
        else:
            x = mission.world_width + tuning.jet_spawn_margin_x
            vx = -tuning.jet_speed_x
        mission.enemies.append(
            Enemy(
                kind=EnemyKind.JET,
                pos=Vec2(x, y),
                vel=Vec2(vx, 0.0),
                health=tuning.jet_health,
                cooldown=0.6,
                ttl=tuning.jet_ttl_s,
                trail_enabled=(int(mission.elapsed_seconds * 1.7) % 2 == 0),
            )
        )
        if logger is not None:
            logger.info("JET: spawned")

    for e in mission.enemies:
        if not e.alive:
            continue

        e.ttl -= dt
        if e.ttl <= 0.0:
            e.alive = False
            continue

        e.cooldown = max(0.0, e.cooldown - dt)

        if e.kind is EnemyKind.TANK:
            dx = helicopter.pos.x - e.pos.x
            if (
                abs(dx) <= tuning.tank_fire_range_x
                and helicopter.pos.y <= heli.ground_y - tuning.tank_fire_min_altitude_clearance_y
                and e.cooldown <= 0.0
            ):
                tank_cd = (tuning.tank_fire_base_cooldown_s / pressure) * (1.0 - 0.12 * difficulty)
                e.cooldown = clamp(tank_cd, tuning.tank_fire_min_cooldown_s, tuning.tank_fire_max_cooldown_s)
                _spawn_enemy_bullet_toward(
                    mission,
                    e.pos,
                    helicopter.pos,
                    kind=ProjectileKind.ENEMY_ARTILLERY,
                    source=EnemyKind.TANK,
                )
                mission.stats.artillery_fired += 1
                if logger is not None:
                    logger.info("TANK_FIRE")

        elif e.kind is EnemyKind.JET:
            e.pos.x += e.vel.x * dt
            e.pos.y += e.vel.y * dt

            if not e.entered_screen and 0.0 <= e.pos.x <= mission.world_width:
                e.entered_screen = True
                mission.stats.jets_entered += 1
                if logger is not None:
                    logger.info("JET: entered")

            if abs(helicopter.pos.x - e.pos.x) <= tuning.jet_fire_range_x and e.cooldown <= 0.0:
                jet_cd = (tuning.jet_fire_base_cooldown_s / pressure) * (1.0 - 0.10 * difficulty)
                e.cooldown = clamp(jet_cd, tuning.jet_fire_min_cooldown_s, tuning.jet_fire_max_cooldown_s)
                _spawn_enemy_bullet_toward(mission, e.pos, helicopter.pos, source=EnemyKind.JET)

            if e.entered_screen and e.trail_enabled:
                e.trail_spawn_accum += dt * 18.0
                while e.trail_spawn_accum >= 1.0:
                    e.trail_spawn_accum -= 1.0
                    mission.jet_trails.emit_trail(e.pos, e.vel)

            if _hits_circle(e.pos, helicopter.pos, radius=tuning.jet_collision_radius):
                _damage_helicopter(mission, helicopter, tuning.jet_touch_damage, logger, source="JET")

        elif e.kind is EnemyKind.AIR_MINE:
            to_heli = Vec2(helicopter.pos.x - e.pos.x, helicopter.pos.y - e.pos.y)
            dist = math.hypot(to_heli.x, to_heli.y)
            if dist > 0.001:
                nx = to_heli.x / dist
                ny = to_heli.y / dist
            else:
                nx, ny = 0.0, 0.0

            desired_speed = clamp(
                (tuning.mine_base_speed * pressure) * (1.0 + 0.15 * difficulty),
                tuning.mine_min_speed,
                tuning.mine_max_speed,
            )
            desired_vx = nx * desired_speed
            desired_vy = ny * desired_speed
            steer = tuning.mine_steer
            e.vel.x += (desired_vx - e.vel.x) * steer * dt
            e.vel.y += (desired_vy - e.vel.y) * steer * dt

            e.pos.x += e.vel.x * dt
            e.pos.y += e.vel.y * dt

            # Keep mines in the playable air space.
            e.pos.x = clamp(e.pos.x, 20.0, mission.world_width - 20.0)
            e.pos.y = clamp(e.pos.y, 50.0, heli.ground_y - 60.0)

            if _hits_circle(e.pos, helicopter.pos, radius=tuning.mine_touch_radius):
                _mine_explode(mission, e.pos, helicopter, logger)
                e.alive = False

    mission.enemies = [e for e in mission.enemies if e.alive]


def _mine_explode(
    mission: MissionState,
    pos: Vec2,
    helicopter: Helicopter,
    logger: logging.Logger | None,
) -> None:
    if logger is not None:
        logger.info("MINE: detonate")

    mission.stats.mines_detonated += 1

    _damage_helicopter(mission, helicopter, mission.tuning.mine_damage, logger, source="AIR_MINE")

    radius = 40.0
    r2 = radius * radius
    for h in mission.hostages:
        if not on_foot(h):
            continue
        dx = h.pos.x - pos.x
        dy = h.pos.y - pos.y
        if dx * dx + dy * dy <= r2:
            h.state = HostageState.KIA
            mission.stats.kia_by_enemy += 1


def _spawn_enemy_bullet_toward(
    mission: MissionState,
    start: Vec2,
    target: Vec2,
    *,
    kind: ProjectileKind = ProjectileKind.ENEMY_BULLET,
    source: EnemyKind | None = None,
) -> None:
    dx = target.x - start.x
    dy = target.y - start.y
    dist = math.hypot(dx, dy)
    if dist <= 0.001:
        dist = 1.0
    speed = 140.0
    vx = (dx / dist) * speed
    vy = (dy / dist) * speed
    mission.projectiles.append(
        Projectile(
            kind=kind,
            pos=Vec2(start.x, start.y - 10.0),
            vel=Vec2(vx, vy),
            ttl=2.0,
            source=source,
        )
    )


def _hits_circle(a: Vec2, b: Vec2, radius: float) -> bool:
    dx = a.x - b.x
    dy = a.y - b.y
    return dx * dx + dy * dy <= radius * radius


def _projectile_hits_enemy(p: Projectile, e: Enemy, heli: HelicopterSettings, tuning: MissionTuning) -> bool:
    if e.kind is EnemyKind.TANK:
        w, h = 44.0, 18.0
        left = e.pos.x - w * 0.5
        top = heli.ground_y - h
        return left <= p.pos.x <= left + w and top <= p.pos.y <= top + h

    if e.kind is EnemyKind.JET:
        return _hits_circle(p.pos, e.pos, radius=20.0)

    if e.kind is EnemyKind.AIR_MINE:
        return _hits_circle(p.pos, e.pos, radius=tuning.mine_projectile_radius)

    return False


def _damage_helicopter(
    mission: MissionState,
    helicopter: Helicopter,
    amount: float,
    logger: logging.Logger | None,
    source: str,
) -> None:
    if mission.ended or mission.crash_active:
        return

    # Respawn i-frames (blocks all damage).
    if mission.invuln_seconds > 0.0:
        return

    # Flare i-frames (blocks only projectile/artillery damage).
    if mission.flare_invuln_seconds > 0.0 and source in ("ENEMY_BULLET", "ARTILLERY"):
        return

    before = helicopter.damage
    helicopter.damage = min(100.0, helicopter.damage + amount)
    if helicopter.damage > before:
        # Cinematic feedback: stash a short-lived impulse for the renderer/audio layer.
        # (We only store the strongest impulse seen in a tick; the main loop consumes + clears it.)
        # Normalize damage amounts (10 is common) so bullets don't feel overly punchy.
        base = clamp(float(amount) / 25.0, 0.0, 1.0)
        if source in ("ENEMY_BULLET",):
            shake = 0.10 + 0.18 * base
        elif source in ("ARTILLERY",):
            shake = 0.35 + 0.35 * base
        elif source in ("AIR_MINE",):
            shake = 0.48 + 0.42 * base
        elif source in ("JET",):
            shake = 0.28 + 0.32 * base
        else:
            shake = 0.18 + 0.30 * base

        mission.feedback_shake_impulse = max(mission.feedback_shake_impulse, clamp(shake, 0.0, 1.0))

        # Subtle audio "duck" only for bigger impacts.
        if source in ("ARTILLERY", "AIR_MINE", "JET") and shake >= 0.50:
            mission.feedback_duck_strength = max(mission.feedback_duck_strength, clamp(shake, 0.0, 1.0))

        # Screen flash: set a short timer + color based on damage source.
        # (Rendering is gated by accessibility.flashes_enabled.)
        helicopter.damage_flash_seconds = 0.12
        if source in ("ENEMY_BULLET", "ARTILLERY"):
            helicopter.damage_flash_rgb = (255, 40, 40)
        elif source == "JET":
            helicopter.damage_flash_rgb = (120, 120, 255)
        elif source == "AIR_MINE":
            helicopter.damage_flash_rgb = (255, 170, 60)
        else:
            helicopter.damage_flash_rgb = (255, 60, 60)

        if logger is not None:
            logger.debug(
                "FLASH: kind=damage source=%s amount=%.2f damage=%.1f->%.1f rgb=%s",
                source,
                float(amount),
                float(before),
                float(helicopter.damage),
                helicopter.damage_flash_rgb,
            )
        if source == "ARTILLERY":
            haptics.rumble_artillery_hit(logger=logger)
        else:
            haptics.rumble_hit(amount=amount, source=source, logger=logger)
    if logger is not None and int(before) != int(helicopter.damage):
        logger.info("HIT: %s damage=%.0f", source, helicopter.damage)


def _handle_crash_and_respawn(
    mission: MissionState,
    helicopter: Helicopter,
    dt: float,
    heli: HelicopterSettings,
    logger: logging.Logger | None,
) -> None:
    if mission.ended:
        return
    # If a crash animation is already running, advance it.
    if mission.crash_active:
        _update_crash_sequence(mission, helicopter, dt, heli, logger)
        return

    # Start crash sequence when damage maxes out.
    if helicopter.damage < 100.0:
        return

    mission.crashes += 1
    if logger is not None:
        logger.info("CRASH: count=%d", mission.crashes)

    # Consequence: any boarded hostages are lost when the aircraft goes down.
    lost_this_crash = 0
    for h in mission.hostages:
        if h.state is HostageState.BOARDED:
            h.state = HostageState.KIA
            lost_this_crash += 1
    if lost_this_crash:
        mission.stats.lost_in_transit += lost_this_crash
        if logger is not None:
            logger.info("LOST_IN_TRANSIT: +%d (total=%d)", lost_this_crash, mission.stats.lost_in_transit)

    if mission.crashes >= 3:
        _end_mission(mission, "THE END", "AIRCRAFT LOST", logger)
        return

    # Begin crash animation.
    mission.crash_active = True
    mission.crash_seconds = 0.0
    mission.crash_impacted = False
    mission.crash_impact_seconds = 0.0
    mission.crash_impact_sfx_pending = False
    mission.crash_origin = Vec2(float(helicopter.pos.x), float(helicopter.pos.y))
    mission.crash_vel = Vec2(float(helicopter.vel.x) * 0.45, float(helicopter.vel.y))
    mission.crash_variant = 0 if random.random() < 0.5 else 1

    # Lock helicopter visuals/controls.
    helicopter.crashing = True
    helicopter.crash_variant = mission.crash_variant
    helicopter.crash_seconds = 0.0
    helicopter.crash_hide = False


def _update_crash_sequence(
    mission: MissionState,
    helicopter: Helicopter,
    dt: float,
    heli: HelicopterSettings,
    logger: logging.Logger | None,
) -> None:
    if not mission.crash_active or mission.ended:
        return

    ground_contact_y = float(heli.ground_y - heli.rotor_clearance)

    mission.crash_seconds += dt
    helicopter.crash_seconds = mission.crash_seconds

    if not mission.crash_impacted:
        # Midair phase: spin + descend.
        vx, vy = float(mission.crash_vel.x), float(mission.crash_vel.y)
        vy = min(420.0, vy + 520.0 * dt)
        vx *= 0.995

        mission.crash_vel = Vec2(vx, vy)
        t = mission.crash_seconds

        if mission.crash_variant == 0:
            # Level, fast spins with a gentle horizontal swirl.
            helicopter.crash_roll_deg = (t * 720.0) % 360.0
            swirl = math.sin(t * 3.4) * 55.0
            helicopter.pos = Vec2(mission.crash_origin.x + swirl, float(helicopter.pos.y) + vy * dt)
        else:
            # Tail-spin: angled, wobble + spin.
            base = -32.0 if vx >= 0.0 else 32.0
            wobble = math.sin(t * 9.0) * 14.0
            helicopter.crash_roll_deg = base + wobble + (t * 420.0) % 360.0
            helicopter.pos = Vec2(float(helicopter.pos.x) + vx * dt, float(helicopter.pos.y) + vy * dt)

        # Clamp into world bounds.
        helicopter.pos = Vec2(clamp(float(helicopter.pos.x), 0.0, float(mission.world_width)), float(helicopter.pos.y))

        if float(helicopter.pos.y) >= ground_contact_y:
            mission.crash_impacted = True
            mission.crash_impact_seconds = 0.0
            mission.crash_impact_sfx_pending = True
            helicopter.pos = Vec2(float(helicopter.pos.x), ground_contact_y)
            helicopter.vel = Vec2(0.0, 0.0)
            mission.crash_vel = Vec2(0.0, 0.0)

            # Explosion on impact.
            impact_pos = Vec2(float(helicopter.pos.x), float(heli.ground_y) - 10.0)
            mission.explosions.emit_explosion(impact_pos, strength=1.0)
            mission.burning.add_site(impact_pos, intensity=1.0)
            mission.impact_sparks.emit_hit(impact_pos, incoming_vel=Vec2(0.0, 220.0), strength=2.0)

            helicopter.crash_hide = True
            if logger is not None:
                logger.info("CRASH_IMPACT: variant=%d", mission.crash_variant)
        return

    # Post-impact delay, then respawn.
    mission.crash_impact_seconds += dt
    if mission.crash_impact_seconds < 0.85:
        return

    # Respawn.
    mission.crash_active = False
    mission.crash_impact_sfx_pending = False
    helicopter.crashing = False
    helicopter.crash_hide = False
    helicopter.crash_roll_deg = 0.0
    helicopter.crash_variant = 0
    helicopter.crash_seconds = 0.0

    helicopter.damage = 0.0
    helicopter.fuel = max(0.0, helicopter.fuel - 20.0)
    helicopter.vel = Vec2(0.0, 0.0)
    helicopter.tilt_deg = 0.0
    helicopter.doors_open = False
    helicopter.facing = Facing.LEFT
    helicopter.pos = Vec2(mission.base.pos.x + mission.base.width * 0.5, heli.ground_y - 120.0)
    mission.invuln_seconds = 2.0
    mission.flare_invuln_seconds = 0.0

    if logger is not None:
        logger.info("RESPAWN: invuln=%.1fs fuel=%.0f", mission.invuln_seconds, helicopter.fuel)


def _end_mission(mission: MissionState, end_text: str, reason: str, logger: logging.Logger | None) -> None:
    if mission.ended:
        return

    mission.ended = True
    mission.end_text = end_text
    mission.end_reason = reason

    if logger is not None:
        logger.info("END: %s", reason)
        logger.info(
            "END_STATS: saved=%d boarded=%d kia_by_player=%d kia_by_enemy=%d lost_in_transit=%d enemies_destroyed=%d crashes=%d",
            mission.stats.saved,
            boarded_count(mission),
            mission.stats.kia_by_player,
            mission.stats.kia_by_enemy,
            mission.stats.lost_in_transit,
            mission.stats.enemies_destroyed,
            mission.crashes,
        )
