from __future__ import annotations

from dataclasses import dataclass

from .game_types import EnemyKind
from .mission_configs import MissionTuning


@dataclass(frozen=True)
class ThreatTell:
    cue: str
    lead_time_s: float
    effective_range_px: float


_DEFAULT_TUNING = MissionTuning()


# Threat readability reference matrix used for balancing and debug visibility.
THREAT_TELL_MATRIX: dict[EnemyKind, ThreatTell] = {
    EnemyKind.TANK: ThreatTell(
        cue="Turret pre-fire tell then muzzle flash before artillery shot",
        lead_time_s=float(_DEFAULT_TUNING.tank_prefire_tell_s),
        effective_range_px=float(_DEFAULT_TUNING.tank_fire_range_x),
    ),
    EnemyKind.JET: ThreatTell(
        cue="Inbound warning and flyby audio before first attack window",
        lead_time_s=1.2,
        effective_range_px=float(_DEFAULT_TUNING.jet_fire_range_x),
    ),
    EnemyKind.AIR_MINE: ThreatTell(
        cue="Proximity warning pulse when mine is closing on helicopter",
        lead_time_s=0.45,
        effective_range_px=170.0,
    ),
}
