from __future__ import annotations

from dataclasses import dataclass

from .math2d import Vec2


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
    barak_health: float = 143.0  # ~30% tougher than tank_health (110 * 1.3)
    tank_initial_cooldown_s: float = 1.5
    tank_ground_offset_y: float = 8.0
    tank_fire_range_x: float = 360.0
    tank_fire_min_altitude_clearance_y: float = 40.0
    tank_prefire_tell_s: float = 0.30
    tank_muzzle_flash_s: float = 0.09

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
    hostage_controlled_start_radius: float = 260.0
    hostage_chaotic_move_speed: float = 52.0
    hostage_chaotic_max_moving_to_lz: int = 12
    hostage_chaotic_start_radius: float = 340.0
    hostage_chaos_probability: float = 0.35
    hostage_boarding_radius: float = 64.0
    hostage_boarding_cadence_s: float = 0.30
    airborne_fall_delay_min_s: float = 2.0
    airborne_fall_delay_max_s: float = 3.0

    barak_deploy_angle_speed_rad_s: float = 1.5
    barak_deploy_extension_speed_s: float = 1.2
    barak_retract_angle_speed_rad_s: float = 1.9
    barak_retract_extension_speed_s: float = 1.4
    barak_reload_seconds: float = 4.0
    barak_reload_min_seconds: float = 5.0
    barak_reload_max_seconds: float = 6.0
    barak_state_fail_safe_s: float = 8.0

    # BARAK missile flare diversion behavior.
    barak_flare_diversion_chance: float = 0.66
    barak_flare_diversion_radius: float = 300.0
    barak_flare_diversion_turn_rate_deg: float = 220.0
    barak_flare_diversion_max_flare_age_s: float = 1.65
    barak_flare_near_miss_radius_px: float = 42.0
    barak_flare_spin_rate_deg: float = 520.0
    barak_flare_spin_amplitude_px: float = 10.0
    barak_flare_near_miss_arm_radius_px: float = 54.0
    barak_flare_post_pass_explode_distance_px: float = 68.0
    barak_flare_last_chance_override_radius_px: float = 92.0
    barak_destroy_second_burst_delay_s: float = 0.14


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
