from __future__ import annotations

import logging
from typing import Callable

from .mission_helpers import boarded_count
from .mission_state import MissionState


def _end_mission(
    mission: MissionState,
    end_text: str,
    reason: str,
    logger: logging.Logger | None,
    *,
    boarded_count_fn: Callable[[MissionState], int] | None = None,
) -> None:
    boarded_count_fn = boarded_count_fn or boarded_count

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
            boarded_count_fn(mission),
            mission.stats.kia_by_player,
            mission.stats.kia_by_enemy,
            mission.stats.lost_in_transit,
            mission.stats.enemies_destroyed,
            mission.crashes,
        )
