from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class MissionStatsSnapshot:
    crashes: int
    lost_in_transit: int
    saved: int
    boarded: int
    open_compounds: int
    tanks_destroyed: int
    artillery_fired: int
    artillery_hits: int
    jets_entered: int
    mines_detonated: int


def count_open_compounds(mission: object) -> int:
    compounds = getattr(mission, "compounds", [])
    return sum(1 for c in compounds if getattr(c, "is_open", False))


def take_mission_stats_snapshot(
    mission: object,
    *,
    boarded_count: Callable[[object], int],
) -> MissionStatsSnapshot:
    stats = getattr(mission, "stats", None)
    return MissionStatsSnapshot(
        crashes=int(getattr(mission, "crashes", 0)),
        lost_in_transit=int(getattr(stats, "lost_in_transit", 0)),
        saved=int(getattr(stats, "saved", 0)),
        boarded=int(boarded_count(mission)),
        open_compounds=int(count_open_compounds(mission)),
        tanks_destroyed=int(getattr(stats, "tanks_destroyed", 0)),
        artillery_fired=int(getattr(stats, "artillery_fired", 0)),
        artillery_hits=int(getattr(stats, "artillery_hits", 0)),
        jets_entered=int(getattr(stats, "jets_entered", 0)),
        mines_detonated=int(getattr(stats, "mines_detonated", 0)),
    )
