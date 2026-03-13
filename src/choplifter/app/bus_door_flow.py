from __future__ import annotations

from src.choplifter.bus_ai import close_bus_doors, open_bus_doors


def apply_airport_bus_door_transitions(*, bus_state: object | None, audio: object, prev_hostage_state: str, new_hostage_state: str) -> None:
    """Apply bus door transitions for airport passenger board/deboard flow."""
    if bus_state is None or new_hostage_state == prev_hostage_state:
        return

    if new_hostage_state == "transferring_to_bus":
        # Boarding transfer begins.
        open_bus_doors(bus_state, audio=audio)
    elif new_hostage_state == "boarded":
        # Transfer complete, close doors for escort.
        close_bus_doors(bus_state, audio=audio)
    elif new_hostage_state == "rescued":
        # Deboard at tower LZ: open briefly, then auto-close.
        open_bus_doors(bus_state, audio=audio, auto_close_delay_s=0.28)
