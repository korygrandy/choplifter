from dataclasses import dataclass, field
from .entities import Hostage, Compound, Projectile, Enemy, BaseZone, MissionStats
from .burning_particles import BurningParticleSystem
from .fx_particles import DustStormSystem, EnemyDamageFxSystem, ExplosionSystem, FlareSystem, HelicopterDamageFxSystem, ImpactSparkSystem, JetTrailSystem
from .game_types import HostageState, EnemyKind, ProjectileKind
from .math2d import Vec2
from .mission_configs import MissionTuning, LevelConfig
from .supply_drops import SupplyDropManager
from .settings import HelicopterSettings
from .helicopter import Helicopter, Facing

@dataclass
class MissionState:
    mission_id: str
    compounds: list[Compound]
    hostages: list[Hostage]
    projectiles: list[Projectile]
    enemies: list[Enemy]
    base: BaseZone
    world_width: float = 1280.0
    bg_asset: str = "mission1-bg.jpg"
    vip_index: int = -1
    cutscenes_played: set[str] = field(default_factory=set)
    stats: MissionStats = field(default_factory=MissionStats)
    sentiment: float = 50.0
    tuning: MissionTuning = MissionTuning()
    burning: BurningParticleSystem = field(default_factory=BurningParticleSystem)
    impact_sparks: ImpactSparkSystem = field(default_factory=ImpactSparkSystem)
    jet_trails: JetTrailSystem = field(default_factory=JetTrailSystem)
    dust_storm: DustStormSystem = field(default_factory=DustStormSystem)
    wind_dust_clouds: object = field(default_factory=lambda: None)
    heli_damage_fx: HelicopterDamageFxSystem = field(default_factory=HelicopterDamageFxSystem)
    enemy_damage_fx: EnemyDamageFxSystem = field(default_factory=EnemyDamageFxSystem)
    explosions: ExplosionSystem = field(default_factory=ExplosionSystem)
    flares: FlareSystem = field(default_factory=FlareSystem)
    supply_drops: SupplyDropManager = field(default_factory=SupplyDropManager)
    munitions_bullets: int = 240
    munitions_bombs: int = 24
    elapsed_seconds: float = 0.0
    pending_air_mine_pos: Vec2 | None = None
    pending_air_mine_seconds: float = 0.0
    ended: bool = False
    end_text: str = ""
    end_reason: str = ""
    crashes: int = 0
    invuln_seconds: float = 0.0
    flare_invuln_seconds: float = 0.0
    engineer_remote_control_active: bool = False
    player_driving_vehicle: bool = False
    post_respawn_escort_risk_seconds: float = 0.0
    engineer_off_chopper: bool = False
    barak_suppressed: bool = False
    feedback_shake_impulse: float = 0.0
    feedback_duck_strength: float = 0.0
    doors_open_maxvel_timer: float = 0.0
    next_fall_time: float = 0.0
    _prev_fall_eligible: bool = False
    _last_fall_time: float = 0.0
    crash_active: bool = False
    crash_variant: int = 0
    crash_seconds: float = 0.0
    crash_origin: Vec2 = field(default_factory=lambda: Vec2(0.0, 0.0))
    crash_vel: Vec2 = field(default_factory=lambda: Vec2(0.0, 0.0))
    crash_impacted: bool = False
    crash_impact_seconds: float = 0.0
    crash_impact_sfx_pending: bool = False
    jet_spawn_seconds: float = 4.0
    mine_spawn_seconds: float = 24.0
    tank_warning_seconds: float = 0.0
    tank_warning_from_right: bool = False
    tank_warning_cooldown_s: float = 0.0
    jet_warning_seconds: float = 0.0
    jet_warning_from_right: bool = False
    jet_warning_cooldown_s: float = 0.0
    mine_warning_seconds: float = 0.0
    mine_warning_distance: float = 9999.0
    mine_warning_cooldown_s: float = 0.0
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
        from .mission_configs import create_level_1_config
        level = create_level_1_config()
        return MissionState.create_from_level_config(heli, level, mission_id="city")

    @staticmethod
    def create_from_level_config(
        heli: HelicopterSettings,
        level: LevelConfig,
        mission_id: str = "",
        world_width: float | None = None,
    ) -> "MissionState":
        if world_width is None:
            world_width = level.world_width
        compounds: list[Compound] = []
        hostage_index = 0
        compound_w = level.compound_width
        compound_h = level.compound_height
        compound_y = heli.ground_y - compound_h
        for i, x in enumerate(level.compound_xs):
            # Airport mission: float two left compounds as elevated extraction platforms.
            y_offset = -60.0 if mission_id.lower() in ("airport", "airport_special_ops") and i in (0, 1) else 0.0
            compounds.append(
                Compound(
                    pos=Vec2(x, compound_y + y_offset),
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
        import random
        vip_index = -1
        if mission_id.lower() in ("city", "city_center", "citycenter", "mission1", "m1") and compounds:
            vip_compound = random.choice(compounds)
            start = vip_compound.hostage_start
            count = vip_compound.hostage_count
            if count > 0:
                vip_index = random.randint(start, start + count - 1)
                hostages[vip_index].is_vip = True
        base_w = level.base_width
        base_h = level.base_height
        base = BaseZone(
            pos=Vec2(world_width - base_w - level.base_right_margin, heli.ground_y - base_h - level.base_bottom_margin),
            width=base_w,
            height=base_h,
        )
        enemies: list[Enemy] = []
        for c in compounds:
            enemies.append(
                Enemy(
                    kind=EnemyKind.TANK,
                    pos=Vec2(c.pos.x + c.width * 0.5, heli.ground_y - level.tuning.tank_ground_offset_y),
                    vel=Vec2(0.0, 0.0),
                    health=level.tuning.tank_health,
                    max_health=level.tuning.tank_health,
                    cooldown=level.tuning.tank_initial_cooldown_s,
                )
            )
        enemies.append(
            Enemy(
                kind=EnemyKind.BARAK_MRAD,
                pos=Vec2(-120.0, heli.ground_y - 12.0),
                vel=Vec2(32.0, 0.0),
                health=level.tuning.barak_health,
                max_health=level.tuning.barak_health,
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
            mission_id=(mission_id or "").strip().lower() or "city",
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
        state.mine_spawn_seconds = max(
            level.tuning.mine_spawn_base_interval_s,
            level.initial_air_mine_delay_s + 18.0,
        )
        state.pending_air_mine_pos = pending_mine_pos
        state.pending_air_mine_seconds = pending_mine_seconds
        return state

