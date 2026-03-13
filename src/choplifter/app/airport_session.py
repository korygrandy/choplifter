from __future__ import annotations

from dataclasses import dataclass
import random

from ..bus_ai import create_bus_state
from ..cutscene_manager import create_airport_cutscene_state
from ..enemy_spawns import create_airport_enemy_state
from ..hostage_logic import create_airport_hostage_state
from ..mission_tech import create_mission_tech_state
from ..objective_manager import create_airport_objective_state
from ..vehicle_assets import create_airport_meal_truck_state


@dataclass
class AirportRuntimeState:
    bus_state: object
    hostage_state: object
    enemy_state: object
    tech_state: object
    objective_state: object
    cutscene_state: object
    meal_truck_state: object
    raised_bunker_x: float
    meal_truck_spawn_x: float
    total_rescue_target: int


def create_empty_airport_runtime() -> AirportRuntimeState:
    return AirportRuntimeState(
        bus_state=None,
        hostage_state=None,
        enemy_state=None,
        tech_state=None,
        objective_state=None,
        cutscene_state=None,
        meal_truck_state=None,
        raised_bunker_x=1500.0,
        meal_truck_spawn_x=1060.0,
        total_rescue_target=16,
    )


def configure_airport_passenger_distribution(*, mission: object, total_passengers: int = 16) -> tuple[list[float], int, float]:
    """Split airport civilians between lower compounds and elevated terminals."""
    compounds = list(getattr(mission, "compounds", []))
    if not compounds:
        fallback_x = 1500.0
        return [fallback_x], int(total_passengers), fallback_x

    min_y = min(float(c.pos.y) for c in compounds)
    elevated_indices = [i for i, c in enumerate(compounds) if abs(float(c.pos.y) - min_y) <= 1.0]
    if not elevated_indices:
        elevated_indices = [min(range(len(compounds)), key=lambda i: float(compounds[i].pos.y))]

    elevated_center_xs = sorted(
        float(compounds[i].pos.x) + float(compounds[i].width) * 0.5 for i in elevated_indices
    )
    raised_bunker_x = float(elevated_center_xs[0])

    lower_indices = [i for i in range(len(compounds)) if i not in elevated_indices]
    total = max(1, int(total_passengers))
    if lower_indices:
        elevated_total = random.randint(4, max(4, total - 2)) if total >= 6 else max(1, total // 2)
    else:
        elevated_total = total
    lower_total = max(0, total - elevated_total)

    for c in compounds:
        c.hostage_count = 0

    if lower_indices and lower_total > 0:
        if len(lower_indices) == 1:
            compounds[lower_indices[0]].hostage_count = lower_total
        else:
            first = random.randint(0, lower_total)
            second = lower_total - first
            compounds[lower_indices[0]].hostage_count = first
            compounds[lower_indices[1]].hostage_count = second

    for i in elevated_indices:
        compounds[i].hostage_count = 0

    return elevated_center_xs, elevated_total, raised_bunker_x


def initialize_airport_runtime(
    *,
    mission: object,
    ground_y: float,
    total_rescue_target: int = 16,
    meal_truck_spawn_x: float = 1060.0,
    hostage_deadline_s: float = 120.0,
) -> AirportRuntimeState:
    pickup_points, elevated_total, raised_bunker_x = configure_airport_passenger_distribution(
        mission=mission,
        total_passengers=total_rescue_target,
    )

    bus_state = create_bus_state(start_x=2200, ground_y=ground_y)
    hostage_state = create_airport_hostage_state(
        total_hostages=elevated_total,
        pickup_x=raised_bunker_x,
        pickup_points=pickup_points,
    )
    enemy_state = create_airport_enemy_state()
    tech_state = create_mission_tech_state()
    objective_state = create_airport_objective_state(hostage_deadline_s=hostage_deadline_s)
    cutscene_state = create_airport_cutscene_state()
    meal_truck_state = create_airport_meal_truck_state(
        start_x=meal_truck_spawn_x,
        ground_y=ground_y,
        plane_lz_x=float(getattr(hostage_state, "pickup_x", raised_bunker_x)),
    )

    mission.mission_tech = tech_state
    mission.airport_hostage_state = hostage_state
    mission.airport_meal_truck_state = meal_truck_state

    return AirportRuntimeState(
        bus_state=bus_state,
        hostage_state=hostage_state,
        enemy_state=enemy_state,
        tech_state=tech_state,
        objective_state=objective_state,
        cutscene_state=cutscene_state,
        meal_truck_state=meal_truck_state,
        raised_bunker_x=raised_bunker_x,
        meal_truck_spawn_x=meal_truck_spawn_x,
        total_rescue_target=total_rescue_target,
    )


def configure_airport_runtime_for_mission(
    *,
    selected_mission_id: str,
    mission: object,
    ground_y: float,
    previous_runtime: AirportRuntimeState | None = None,
    hostage_deadline_s: float = 120.0,
) -> AirportRuntimeState:
    """Return mission-appropriate airport runtime state for setup/reset paths."""
    normalized_mission_id = str(selected_mission_id or "").strip().lower()
    if normalized_mission_id != "airport":
        return create_empty_airport_runtime()

    base_runtime = previous_runtime or create_empty_airport_runtime()
    return initialize_airport_runtime(
        mission=mission,
        ground_y=ground_y,
        total_rescue_target=base_runtime.total_rescue_target,
        meal_truck_spawn_x=base_runtime.meal_truck_spawn_x,
        hostage_deadline_s=hostage_deadline_s,
    )
