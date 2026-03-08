from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..game_types import HostageState

if TYPE_CHECKING:
    from ..helicopter import Helicopter
    from ..mission_state import MissionState


@dataclass(frozen=True)
class BoardingUxStatus:
    state: str
    detail: str
    boarded: int
    nearby: int


@dataclass(frozen=True)
class BoardingUxVisual:
    symbol: str
    color: tuple[int, int, int]


def compute_boarding_ux_status(
    mission: MissionState,
    helicopter: Helicopter,
    *,
    capacity: int = 16,
    near_x: float = 260.0,
    near_y: float = 140.0,
) -> BoardingUxStatus:
    """Return one of: approaching, boarding, boarded, blocked."""
    boarded = sum(1 for h in mission.hostages if h.state is HostageState.BOARDED)
    nearby = sum(
        1
        for h in mission.hostages
        if h.state in (HostageState.WAITING, HostageState.MOVING_TO_LZ)
        and abs(h.pos.x - helicopter.pos.x) <= near_x
        and abs(h.pos.y - helicopter.pos.y) <= near_y
    )

    if boarded >= capacity:
        return BoardingUxStatus(state="blocked", detail="FULL", boarded=boarded, nearby=nearby)

    can_board_now = bool(helicopter.grounded and helicopter.doors_open and nearby > 0)
    if can_board_now:
        return BoardingUxStatus(state="boarding", detail="READY", boarded=boarded, nearby=nearby)

    if boarded > 0:
        return BoardingUxStatus(state="boarded", detail="PASSENGERS ONBOARD", boarded=boarded, nearby=nearby)

    if nearby > 0:
        return BoardingUxStatus(state="approaching", detail="HOSTAGES IN RANGE", boarded=boarded, nearby=nearby)

    if not helicopter.grounded:
        return BoardingUxStatus(state="blocked", detail="LAND", boarded=boarded, nearby=nearby)
    if not helicopter.doors_open:
        return BoardingUxStatus(state="blocked", detail="OPEN DOORS", boarded=boarded, nearby=nearby)
    return BoardingUxStatus(state="blocked", detail="NO HOSTAGES NEAR", boarded=boarded, nearby=nearby)


def get_boarding_ux_visual(status: BoardingUxStatus) -> BoardingUxVisual:
    """Provide color + shape token cues for accessibility/readability."""
    visual_by_state = {
        "approaching": BoardingUxVisual(symbol=">>", color=(246, 196, 92)),
        "boarding": BoardingUxVisual(symbol="+", color=(116, 224, 146)),
        "boarded": BoardingUxVisual(symbol="[]", color=(128, 186, 255)),
        "blocked": BoardingUxVisual(symbol="!", color=(255, 118, 118)),
    }
    return visual_by_state.get(status.state, BoardingUxVisual(symbol="?", color=(225, 225, 225)))
