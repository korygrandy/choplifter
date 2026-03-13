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
        meal_truck_spawn_x=970.0,
        total_rescue_target=16,
    )


def configure_airport_passenger_distribution(*, mission: object, total_passengers: int = 16) -> tuple[list[float], int, int, float]:
    """Split airport civilians between lower compounds and elevated terminals."""
    compounds = list(getattr(mission, "compounds", []))
    if not compounds:
        fallback_x = 1500.0
        total = max(1, int(total_passengers))
        return [fallback_x], total, 0, fallback_x

    # Airport flow assumes two elevated extraction terminals and at least one
    # lower-compound rescue lane when 3+ compounds are present.
    sorted_by_height = sorted(
        range(len(compounds)),
        key=lambda i: (float(compounds[i].pos.y), float(compounds[i].pos.x)),
    )
    if len(compounds) >= 3:
        elevated_indices = sorted_by_height[:2]
    else:
        elevated_indices = sorted_by_height[:1]

    elevated_center_xs = sorted(
        float(compounds[i].pos.x) + float(compounds[i].width) * 0.5 for i in elevated_indices
    )
    raised_bunker_x = float(elevated_center_xs[0])

    lower_indices = [i for i in range(len(compounds)) if i not in elevated_indices]
    total = max(1, int(total_passengers))

    base_assignment = [0] * len(compounds)

    # Airport Special Ops has three active rescue terminals:
    # two elevated + one lower lane. Guarantee >=1 each when total allows.
    active_terminal_indices = list(elevated_indices)
    if lower_indices:
        active_terminal_indices.append(lower_indices[0])
    active_terminal_indices = sorted(set(active_terminal_indices))

    if active_terminal_indices and total >= len(active_terminal_indices):
        for idx in active_terminal_indices:
            base_assignment[idx] = 1
        remaining = total - len(active_terminal_indices)
        for _ in range(remaining):
            idx = random.choice(active_terminal_indices)
            base_assignment[idx] += 1
    elif active_terminal_indices:
        # Not enough total passengers to guarantee one per terminal.
        # Fill terminals left-to-right until we run out.
        for idx in active_terminal_indices[:total]:
            base_assignment[idx] += 1

    # Assign hostage counts
    for idx, c in enumerate(compounds):
        c.hostage_count = base_assignment[idx]

    # For return values, sum up elevated and lower
    elevated_total = sum(compounds[i].hostage_count for i in elevated_indices)
    lower_total = sum(compounds[i].hostage_count for i in lower_indices)

    return elevated_center_xs, elevated_total, lower_total, raised_bunker_x


def initialize_airport_runtime(
    *,
    mission: object,
    ground_y: float,
    total_rescue_target: int = 16,
    meal_truck_spawn_x: float = 1040.0,
    hostage_deadline_s: float = 120.0,
) -> AirportRuntimeState:
    pickup_points, elevated_total, lower_total, raised_bunker_x = configure_airport_passenger_distribution(
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
