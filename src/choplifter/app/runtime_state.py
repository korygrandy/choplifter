from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GameRuntimeState:
    """Mutable UI/runtime flags currently owned by main loop state."""

    pause_focus: str = "choppers"  # choppers | restart_mission | restart_game | mute | quit
    quit_confirm: bool = False
    muted: bool = False
    mission_end_return_seconds: float = 0.0
