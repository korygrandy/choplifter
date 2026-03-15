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
from ..entities import Hostage
from ..game_types import HostageState
from ..math2d import Vec2


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


def _reindex_compound_hostage_ranges(*, mission: object) -> None:
    """Make compound.hostage_start contiguous with current hostage_count.

    Airport Special Ops mutates compound hostage counts at runtime.
    The authored MissionState uses a fixed hostages_per_compound when creating
    hostage_start indices; if we later assign a higher count to a compound,
    naive slicing can spill into neighboring compounds and make it look like
    more than the intended passenger total spawned.
    """
    compounds = list(getattr(mission, "compounds", []) or [])
    if not compounds:
        return

    offset = 0
    for c in compounds:
        count = max(0, int(getattr(c, "hostage_count", 0)))
        c.hostage_start = int(offset)
        offset += count

    required = max(0, int(offset))
    hostages = list(getattr(mission, "hostages", []) or [])
    if len(hostages) < required:
        missing = required - len(hostages)
        hostages.extend(
            Hostage(state=HostageState.IDLE, pos=Vec2(-9999.0, -9999.0)) for _ in range(missing)
        )
        mission.hostages = hostages


def configure_airport_passenger_distribution(
    *,
    mission: object,
    total_passengers: int = 16,
) -> tuple[list[float], list[int], int, float]:
    """Split airport civilians between lower compounds and elevated terminals.

    Returns:
        pickup_points: Sorted x-centres for elevated terminal pickup points.
        elevated_terminal_counts: Counts aligned to pickup_points.
        lower_total: Civilians assigned to lower compounds (standard mission hostages).
        raised_bunker_x: Leftmost elevated pickup x for legacy callers.
    """
    compounds = list(getattr(mission, "compounds", []))
    if not compounds:
        fallback_x = 1500.0
        # Airport authored rule: always 16 total passengers.
        return [fallback_x], [16], 0, fallback_x

    # Airport flow assumes two elevated extraction terminals.
    sorted_by_height = sorted(
        range(len(compounds)),
        key=lambda i: (float(compounds[i].pos.y), float(compounds[i].pos.x)),
    )
    if len(compounds) >= 3:
        elevated_indices = sorted_by_height[:2]
    else:
        elevated_indices = sorted_by_height[:1]

    elevated_centers_by_index = {
        i: float(compounds[i].pos.x) + float(compounds[i].width) * 0.5 for i in elevated_indices
    }

    lower_indices = [i for i in range(len(compounds)) if i not in elevated_indices]
    # Airport authored rule: always 16 total passengers.
    total = 16

    base_assignment = [0] * len(compounds)

    # Airport Special Ops authored layout: 5 rescue areas when 5+ compounds exist.
    # - 2 elevated terminals (fuselage + jetway)
    # - 2 below terminals (ground-side under the elevated lanes)
    # - 1 ground terminal compound
    #
    # Enforce: at least 1 passenger in each area, and distribute the remainder randomly.
    # For missions with fewer compounds (unit tests/custom configs), fall back to the
    # earlier 3-terminal behavior.
    active_terminal_indices: list[int]
    if len(compounds) >= 5 and len(lower_indices) >= 3 and len(elevated_indices) >= 2:
        # Authored layout: 2 elevated terminals with 2 corresponding lower LZ compounds directly beneath,
        # plus one additional ground-level terminal compound.
        elevated_centers = {
            i: float(compounds[i].pos.x) + float(compounds[i].width) * 0.5 for i in elevated_indices
        }
        lower_centers = {
            i: float(compounds[i].pos.x) + float(compounds[i].width) * 0.5 for i in lower_indices
        }

        def _nearest_lower(elev_x: float, *, exclude: set[int]) -> int | None:
            best_i: int | None = None
            best_d = 1e18
            for li, lx in lower_centers.items():
                if li in exclude:
                    continue
                d = abs(float(lx) - float(elev_x))
                if d < best_d:
                    best_d = d
                    best_i = int(li)
            return best_i

        chosen_lower: list[int] = []
        exclude: set[int] = set()
        for ei in sorted(elevated_indices, key=lambda i: float(elevated_centers[i])):
            li = _nearest_lower(float(elevated_centers[ei]), exclude=exclude)
            if li is not None:
                chosen_lower.append(int(li))
                exclude.add(int(li))

        remaining_lower = [i for i in lower_indices if i not in exclude]
        if remaining_lower:
            # Deterministic pick: rightmost remaining lower compound reads as the ground terminal.
            third = max(remaining_lower, key=lambda i: float(lower_centers.get(i, 0.0)))
            chosen_lower.append(int(third))

        # If any duplicates/missing (custom maps), fill remaining slots left-to-right.
        chosen_lower = list(dict.fromkeys(chosen_lower))
        if len(chosen_lower) < 3:
            fallback = sorted(
                [i for i in lower_indices if i not in chosen_lower],
                key=lambda i: (float(compounds[i].pos.x), float(compounds[i].pos.y)),
            )
            chosen_lower.extend(int(i) for i in fallback[: max(0, 3 - len(chosen_lower))])

        active_terminal_indices = sorted(set(list(elevated_indices) + chosen_lower[:3]))
    else:
        active_terminal_indices = list(elevated_indices)
        if lower_indices:
            active_terminal_indices.append(lower_indices[0])
        active_terminal_indices = sorted(set(active_terminal_indices))

    if active_terminal_indices:
        mandatory_by_terminal: dict[int, int] = {}

        if len(active_terminal_indices) >= 5:
            # Authored rule: once the 5 rescue areas exist, guarantee >=1 in each.
            for idx in active_terminal_indices:
                mandatory_by_terminal[idx] = max(mandatory_by_terminal.get(idx, 0), 1)
        else:
            # Legacy baseline: ensure at least 1 per elevated terminal and >=4 in the primary lower lane.
            for idx in elevated_indices:
                mandatory_by_terminal[idx] = max(mandatory_by_terminal.get(idx, 0), 1)
            if lower_indices:
                primary_lower_idx = lower_indices[0]
                mandatory_by_terminal[primary_lower_idx] = max(mandatory_by_terminal.get(primary_lower_idx, 0), 4)

        mandatory_total = sum(mandatory_by_terminal.values())

        for idx, count in mandatory_by_terminal.items():
            base_assignment[idx] = int(count)

        remaining = max(0, total - mandatory_total)
        for _ in range(remaining):
            idx = random.choice(active_terminal_indices)
            base_assignment[idx] += 1

    # Assign hostage counts.
    # Elevated terminals are handled by AirportHostageState (truck->bus rescue flow),
    # so keep their compound hostage_count at 0 to prevent double-spawning.
    for idx, c in enumerate(compounds):
        if idx in elevated_indices:
            c.hostage_count = 0
        else:
            c.hostage_count = base_assignment[idx]

    # Derive elevated pickup points + per-terminal counts in a deterministic left-to-right order.
    elevated_pairs = sorted(
        (float(elevated_centers_by_index[i]), int(base_assignment[i])) for i in elevated_indices
    )
    elevated_center_xs = [float(x) for x, _ in elevated_pairs]
    elevated_terminal_counts = [int(c) for _, c in elevated_pairs]
    raised_bunker_x = float(elevated_center_xs[0])

    lower_total = sum(int(getattr(compounds[i], "hostage_count", 0)) for i in lower_indices)

    return elevated_center_xs, elevated_terminal_counts, int(lower_total), raised_bunker_x


def initialize_airport_runtime(
    *,
    mission: object,
    ground_y: float,
    total_rescue_target: int = 16,
    meal_truck_spawn_x: float = 1040.0,
    hostage_deadline_s: float = 120.0,
) -> AirportRuntimeState:
    pickup_points, elevated_terminal_counts, lower_total, raised_bunker_x = configure_airport_passenger_distribution(
        mission=mission,
        total_passengers=total_rescue_target,
    )

    elevated_total = sum(max(0, int(v)) for v in (elevated_terminal_counts or []))

    # After mutating compound hostage counts, reindex ranges so hostages don't spill
    # between compounds due to the level's fixed hostages_per_compound allocation.
    _reindex_compound_hostage_ranges(mission=mission)

    bus_state = create_bus_state(start_x=2200, ground_y=ground_y)
    hostage_state = create_airport_hostage_state(
        total_hostages=elevated_total,
        pickup_x=raised_bunker_x,
        pickup_points=pickup_points,
    )

    # Enforce authored distribution across elevated terminals (min-1 per elevated area).
    # create_airport_hostage_state randomizes counts; we override with the exact plan.
    hostage_state.terminal_remaining = list(elevated_terminal_counts or [])
    hostage_state.total_hostages = int(elevated_total)
    hostage_state.terminal_kia = [0 for _ in (elevated_terminal_counts or [])]
    hostage_state.terminal_unlock_beeped = [False for _ in (elevated_terminal_counts or [])]
    hostage_state.active_terminal_index = next(
        (i for i, c in enumerate(hostage_state.terminal_remaining) if int(c) > 0),
        0,
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
        total_rescue_target=16,
        meal_truck_spawn_x=base_runtime.meal_truck_spawn_x,
        hostage_deadline_s=hostage_deadline_s,
    )
