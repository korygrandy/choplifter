"""Airport Special Ops per-tick update orchestration.

Extracted from the main game loop to keep run() focused on
mission-agnostic orchestration.  Called once per fixed-step
tick when selected_mission_id == "airport".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .. import haptics
from ..bus_ai import update_bus_ai, apply_airport_bus_friendly_fire
from ..hostage_logic import update_airport_hostage_logic
from .bus_door_flow import apply_airport_bus_door_transitions
from ..mission_tech import update_mission_tech
from .doors import check_tech_lz_door_toast, check_airport_truck_retract_toast
from ..vehicle_assets import update_airport_meal_truck, get_airport_priority_target_x
from ..enemy_spawns import update_airport_enemy_spawns
from ..objective_manager import update_airport_objectives
from ..cutscene_manager import update_airport_cutscene_state
from ..mission_ending import _end_mission
from ..mission_helpers import boarded_count
from ..math2d import clamp


def _has_remaining_elevated_passengers(hostage_state: Any | None) -> bool:
    if hostage_state is None:
        return False
    remaining = sum(max(0, int(v)) for v in (getattr(hostage_state, "terminal_remaining", []) or []))
    return remaining > 0


def _should_fail_for_tech_kia(*, tech_state: Any | None, hostage_state: Any | None) -> bool:
    tech_state_name = str(getattr(tech_state, "state", "")).strip().lower()
    if tech_state_name != "kia":
        return False
    return _has_remaining_elevated_passengers(hostage_state)


def _apply_vehicle_boundary_clamps(
    *,
    meal_truck_state: Any | None,
    bus_state: Any | None,
    world_width: float,
    bus_driver_mode: bool,
) -> None:
    """
    Keep vehicles within world boundaries.
    
    Meal truck: always clamped to [0, world_width].
    Bus: clamped to [0, world_width] if player is driving.
         If AI-controlled, allow slight overage (world_width + 200px) to complete sequences.
    """
    if meal_truck_state is not None:
        meal_truck_state.x = clamp(float(meal_truck_state.x), 0.0, world_width)
    
    if bus_state is not None:
        if bus_driver_mode:
            # Player driving: strict boundary
            bus_state.x = clamp(float(bus_state.x), 0.0, world_width)
        else:
            # AI-controlled: allow slight overage for sequence completion
            ai_max_overage = world_width + 200.0
            bus_state.x = clamp(float(bus_state.x), 0.0, ai_max_overage)


def _apply_airport_transition_haptics(
    *,
    prev_tech_state_name: str,
    tech_state_name: str,
    prev_hostage_state_name: str,
    new_hostage_state_name: str,
    prev_box_state: str,
    box_state: str,
    logger,
) -> None:
    prev_tech = str(prev_tech_state_name).strip().lower()
    tech = str(tech_state_name).strip().lower()
    prev_host = str(prev_hostage_state_name).strip().lower()
    host = str(new_hostage_state_name).strip().lower()
    prev_box = str(prev_box_state).strip().lower()
    box = str(box_state).strip().lower()

    if prev_tech == "on_chopper" and tech == "deployed_to_truck":
        haptics.rumble_airport_event(event="tech_deploy", logger=logger)
    if prev_box != "extended" and box == "extended":
        haptics.rumble_airport_event(event="lift_extended", logger=logger)
    if prev_host == "waiting" and host == "truck_loading":
        haptics.rumble_airport_event(event="load_start", logger=logger)
    if prev_host == "truck_loading" and host == "truck_loaded":
        haptics.rumble_airport_event(event="load_complete", logger=logger)
    if prev_host == "truck_loaded" and host == "transferring_to_bus":
        haptics.rumble_airport_event(event="transfer_start", logger=logger)
    if prev_host == "boarded" and host == "rescued":
        haptics.rumble_airport_event(event="rescue_complete", logger=logger)
    if prev_tech != "waiting_at_lz" and tech == "waiting_at_lz":
        haptics.rumble_airport_event(event="tech_waiting_lz", logger=logger)
    if prev_tech != "kia" and tech == "kia":
        haptics.rumble_airport_event(event="tech_kia", logger=logger)


def _maybe_show_escort_attack_toast(*, mission: Any, objective_state: Any, tech_state: Any, bus_state: Any, set_toast: Any) -> None:
    if mission is None or set_toast is None:
        return
    if bool(getattr(mission, "_airport_escort_attack_toast_shown", False)):
        return

    mission_phase = str(getattr(objective_state, "mission_phase", "")).strip().lower()
    tech_on_bus = bool(tech_state is not None and bool(getattr(tech_state, "on_bus", False)))
    bus_moving = bool(bus_state is not None and bool(getattr(bus_state, "is_moving", False)))
    if mission_phase == "escort_to_lz" and tech_on_bus and bus_moving:
        set_toast("Escort under attack: fend off drones, minesweepers, and raider mines")
        mission._airport_escort_attack_toast_shown = True


@dataclass
class AirportTickResult:
    bus_state: Any
    hostage_state: Any
    tech_state: Any
    meal_truck_state: Any
    enemy_state: Any
    objective_state: Any
    cutscene_state: Any
    meal_truck_driver_mode: bool
    meal_truck_lift_command_extended: bool


def update_airport_mission_tick(
    *,
    bus_state,
    hostage_state,
    tech_state,
    meal_truck_state,
    enemy_state,
    objective_state,
    cutscene_state,
    dt: float,
    audio,
    helicopter,
    mission,
    heli_settings,
    bus_driver_input,
    bus_driver_mode: bool,
    truck_driver_input,
    meal_truck_driver_mode: bool,
    meal_truck_lift_command_extended: bool,
    set_toast,
    logger,
    airport_total_rescue_target: int,
) -> AirportTickResult:
    """Run all airport entity updates for one fixed-step tick.

    Accepts all mutable airport states by value and returns an
    AirportTickResult with the updated copies.  Also mutates
    ``mission`` in-place for properties the rendering layer reads
    directly (mission.mission_tech, .airport_hostage_state, etc.).
    """
    mission_phase = str(getattr(objective_state, "mission_phase", "waiting_for_tech_deploy"))
    tech_on_bus = bool(getattr(tech_state, "on_bus", False))
    prev_box_state = str(getattr(meal_truck_state, "box_state", "idle")) if meal_truck_state is not None else "idle"

    # --- Bus AI ---
    if bus_state is not None:
        bus_state = update_bus_ai(
            bus_state,
            dt,
            audio=audio,
            mission_phase=mission_phase,
            tech_on_bus=tech_on_bus,
            driver_input=bus_driver_input if bus_driver_mode else None,
        )

    # --- Hostage logic ---
    prev_hostage_state_name = str(getattr(hostage_state, "state", "waiting"))
    hostage_state = update_airport_hostage_logic(
        hostage_state,
        dt,
        bus_state=bus_state,
        helicopter=helicopter,
        mission=mission,
        audio=audio,
        meal_truck_state=meal_truck_state,
        tech_state=tech_state,
    )
    new_hostage_state_name = str(getattr(hostage_state, "state", "waiting"))
    apply_airport_bus_door_transitions(
        bus_state=bus_state,
        audio=audio,
        prev_hostage_state=prev_hostage_state_name,
        new_hostage_state=new_hostage_state_name,
    )

    # --- Tech (engineer) ---
    prev_tech_state_name = str(getattr(tech_state, "state", "on_chopper"))
    tech_state = update_mission_tech(
        tech_state,
        dt,
        helicopter=helicopter,
        meal_truck_state=meal_truck_state,
        bus_state=bus_state,
        hostage_state=hostage_state,
        audio=audio,
        ground_y=heli_settings.ground_y,
        tuning=mission.tuning,
    )
    tech_state_name = str(getattr(tech_state, "state", "on_chopper"))
    tech_on_bus = bool(getattr(tech_state, "on_bus", False))
    check_tech_lz_door_toast(mission, tech_state, helicopter, set_toast)

    # Engineer just boarded meal truck → auto-enter driver mode
    engineer_just_boarded_truck = (
        prev_tech_state_name == "on_chopper" and tech_state_name == "deployed_to_truck"
    )
    if engineer_just_boarded_truck and meal_truck_state is not None:
        if not bool(getattr(mission, "_carjacked_mealtruck_played", False)):
            if hasattr(audio, "play_carjacked_mealtruck"):
                audio.play_carjacked_mealtruck()
            mission._carjacked_mealtruck_played = True
        meal_truck_driver_mode = True
        meal_truck_state.driver_mode_active = True
        meal_truck_lift_command_extended = bool(
            float(getattr(meal_truck_state, "extension_progress", 0.0)) >= 0.5
        )

    # Tech boarded bus → auto-exit truck driver mode
    if tech_on_bus and meal_truck_driver_mode:
        meal_truck_driver_mode = False
        if meal_truck_state is not None:
            meal_truck_state.driver_mode_active = False

    mission.mission_tech = tech_state  # Store for rendering

    # --- Meal truck ---
    if meal_truck_state is not None and hostage_state is not None:
        hostage_pickup_x = float(getattr(hostage_state, "pickup_x", meal_truck_state.plane_lz_x))
        meal_truck_state.plane_lz_x = hostage_pickup_x
    meal_truck_state = update_airport_meal_truck(
        meal_truck_state,
        dt,
        helicopter=helicopter,
        tech_state=tech_state,
        bus_state=bus_state,
        driver_input=truck_driver_input if meal_truck_driver_mode else None,
    )
    check_airport_truck_retract_toast(
        mission,
        meal_truck_state,
        hostage_state,
        bus_state,
        set_toast,
    )
    box_state = str(getattr(meal_truck_state, "box_state", "idle")) if meal_truck_state is not None else "idle"
    
    # Enforce vehicle boundaries (same as helicopter: 0 to world_width).
    # Allow AI-controlled bus to slightly exceed bounds to complete sequences.
    _apply_vehicle_boundary_clamps(
        meal_truck_state=meal_truck_state,
        bus_state=bus_state,
        world_width=float(getattr(mission, "world_width", 2800.0)),
        bus_driver_mode=bus_driver_mode,
    )

    # --- Enemy spawns ---
    airport_target_x = get_airport_priority_target_x(
        bus_state=bus_state,
        meal_truck_state=meal_truck_state,
        tech_state=tech_state,
    )
    enemy_state = update_airport_enemy_spawns(
        enemy_state,
        dt,
        mission=mission,
        bus_state=bus_state,
        meal_truck_state=meal_truck_state,
        target_x=airport_target_x,
    )

    # --- Friendly fire check ---
    _airport_ff_hits = apply_airport_bus_friendly_fire(
        bus_state,
        mission,
        logger=logger,
    )

    # --- Objectives ---
    objective_state = update_airport_objectives(
        objective_state,
        dt,
        mission=mission,
        hostage_state=hostage_state,
        bus_state=bus_state,
        meal_truck_state=meal_truck_state,
        tech_state=tech_state,
    )
    _maybe_show_escort_attack_toast(
        mission=mission,
        objective_state=objective_state,
        tech_state=tech_state,
        bus_state=bus_state,
        set_toast=set_toast,
    )

    # --- Cutscene ---
    cutscene_state = update_airport_cutscene_state(
        cutscene_state,
        dt,
        meal_truck_state=meal_truck_state,
        hostage_state=hostage_state,
        tech_state=tech_state,
    )

    _apply_airport_transition_haptics(
        prev_tech_state_name=prev_tech_state_name,
        tech_state_name=tech_state_name,
        prev_hostage_state_name=prev_hostage_state_name,
        new_hostage_state_name=new_hostage_state_name,
        prev_box_state=prev_box_state,
        box_state=box_state,
        logger=logger,
    )

    # Sync mission references used by rendering / other modules
    mission.airport_hostage_state = hostage_state
    mission.airport_bus_state = bus_state
    mission.airport_enemy_state = enemy_state
    mission.airport_objective_state = objective_state
    mission.airport_meal_truck_state = meal_truck_state

    # --- Win condition ---
    # Lower-level rescued (chopper bay) + elevated rescued (truck→bus) must reach target.
    if not bool(getattr(mission, "ended", False)):
        lower_rescued = int(getattr(getattr(mission, "stats", None), "saved", 0))
        elevated_rescued = (
            int(getattr(hostage_state, "rescued_hostages", 0))
            if hostage_state is not None
            else 0
        )
        boarded_not_yet_unloaded = 0
        if hasattr(mission, "hostages"):
            boarded_not_yet_unloaded = boarded_count(mission)

        if (lower_rescued + elevated_rescued) >= int(airport_total_rescue_target) and boarded_not_yet_unloaded <= 0:
            _end_mission(mission, "THE END", "RESCUE SUCCESS", logger)

    return AirportTickResult(
        bus_state=bus_state,
        hostage_state=hostage_state,
        tech_state=tech_state,
        meal_truck_state=meal_truck_state,
        enemy_state=enemy_state,
        objective_state=objective_state,
        cutscene_state=cutscene_state,
        meal_truck_driver_mode=meal_truck_driver_mode,
        meal_truck_lift_command_extended=meal_truck_lift_command_extended,
    )
