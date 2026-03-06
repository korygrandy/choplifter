"""
mission_helpers.py

Contains clear-cut mission helper functions extracted from mission.py.
"""
from .game_types import HostageState
from .entities import Hostage
from .mission_state import MissionState

def boarded_count(mission: MissionState) -> int:
    return sum(1 for h in mission.hostages if h.state is HostageState.BOARDED)

def on_foot(hostage: Hostage) -> bool:
    return hostage.state in (HostageState.PANIC, HostageState.MOVING_TO_LZ, HostageState.WAITING, HostageState.EXITING)
