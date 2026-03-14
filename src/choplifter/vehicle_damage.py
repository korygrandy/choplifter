from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VehicleDamageResult:
    applied_damage: float
    health_before: float
    health_after: float
    destroyed_now: bool


def _clamp01(value: float) -> float:
    if value <= 0.0:
        return 0.0
    if value >= 1.0:
        return 1.0
    return value


def ensure_vehicle_health(vehicle: object, *, default_max_health: float) -> tuple[float, float]:
    max_health = float(getattr(vehicle, "max_health", default_max_health))
    if max_health <= 0.0:
        max_health = float(default_max_health)
        setattr(vehicle, "max_health", max_health)
    health = float(getattr(vehicle, "health", max_health))
    health = max(0.0, min(max_health, health))
    setattr(vehicle, "health", health)
    return health, max_health


def vehicle_health_ratio(vehicle: object, *, default_max_health: float) -> float:
    health, max_health = ensure_vehicle_health(vehicle, default_max_health=default_max_health)
    if max_health <= 0.0:
        return 0.0
    return _clamp01(health / max_health)


def update_vehicle_damage_state(vehicle: object, *, default_max_health: float) -> str:
    ratio = vehicle_health_ratio(vehicle, default_max_health=default_max_health)
    if ratio <= 0.0:
        state = "destroyed"
    elif ratio <= 0.35:
        state = "critical"
    elif ratio <= 0.7:
        state = "damaged"
    else:
        state = "nominal"
    setattr(vehicle, "damage_state", state)
    setattr(vehicle, "destroyed", state == "destroyed")
    return state


def apply_vehicle_damage(
    vehicle: object,
    amount: float,
    *,
    default_max_health: float,
    allow_damage: bool = True,
    flash_seconds: float = 0.14,
    source: str = "",
) -> VehicleDamageResult:
    health_before, max_health = ensure_vehicle_health(vehicle, default_max_health=default_max_health)
    damage = max(0.0, float(amount))
    if not allow_damage or damage <= 0.0 or health_before <= 0.0:
        update_vehicle_damage_state(vehicle, default_max_health=max_health)
        if source:
            setattr(vehicle, "last_damage_source", source)
        return VehicleDamageResult(
            applied_damage=0.0,
            health_before=health_before,
            health_after=health_before,
            destroyed_now=False,
        )

    health_after = max(0.0, health_before - damage)
    setattr(vehicle, "health", health_after)
    if source:
        setattr(vehicle, "last_damage_source", source)
    setattr(vehicle, "damage_flash_s", max(0.0, float(flash_seconds)))
    update_vehicle_damage_state(vehicle, default_max_health=max_health)
    return VehicleDamageResult(
        applied_damage=max(0.0, health_before - health_after),
        health_before=health_before,
        health_after=health_after,
        destroyed_now=(health_before > 0.0 and health_after <= 0.0),
    )


def is_airport_bus_vulnerable(mission: object | None) -> bool:
    if mission is None:
        return False

    mission_id = str(getattr(mission, "mission_id", "")).strip().lower()
    if mission_id not in ("airport", "airport_special_ops", "airportspecialops", "mission2", "m2"):
        return True

    objective_state = getattr(mission, "airport_objective_state", None)
    mission_phase = str(getattr(objective_state, "mission_phase", "")).strip().lower()
    tech_state = getattr(mission, "mission_tech", None)
    tech_on_bus = bool(tech_state is not None and bool(getattr(tech_state, "on_bus", False)))

    if mission_phase == "escort_to_lz" and tech_on_bus:
        return True

    hostage_state = getattr(mission, "airport_hostage_state", None)
    hostage_phase = str(getattr(hostage_state, "state", "")).strip().lower()
    if hostage_phase == "rescued":
        return True

    return hostage_phase == "boarded" and tech_on_bus
