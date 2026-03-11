from typing import Callable

from ..boarding_telemetry import BOARDING_FAIL_NOT_GROUNDED, record_boarding_failure


def _set_toast_debounced(mission, set_toast: Callable[[str], None] | None, message: str, *, cooldown_s: float = 0.65) -> None:
    if set_toast is None or not message:
        return

    now = float(getattr(mission, "elapsed_seconds", 0.0))
    last_message = str(getattr(mission, "_last_readability_toast_message", ""))
    last_time = float(getattr(mission, "_last_readability_toast_time", -9999.0))

    if message == last_message and (now - last_time) < float(cooldown_s):
        return

    set_toast(message)
    mission._last_readability_toast_message = message
    mission._last_readability_toast_time = now

def toggle_doors_with_logging(
    helicopter,
    mission,
    audio,
    logger,
    boarded_count: Callable[[object], int],
    set_toast: Callable[[str], None] | None = None,
):
    at_base = mission.base.contains_point(helicopter.pos)
    if not helicopter.grounded:
        if logger is not None:
            logger.info("DOORS: toggle blocked (not grounded)")
        record_boarding_failure(mission, BOARDING_FAIL_NOT_GROUNDED)
        _set_toast_debounced(mission, set_toast, "Cannot open doors while airborne")
        return

    before = helicopter.doors_open
    helicopter.toggle_doors()
    after = helicopter.doors_open
    if before != after:
        if after:
            audio.play_doors_open()
        else:
            audio.play_doors_close()
        if logger is not None:
            logger.info(
                "DOORS: %s at_base=%s boarded=%d",
                "OPEN" if after else "closed",
                at_base,
                boarded_count(mission),
            )

    boarded_now = boarded_count(mission)
    if set_toast is not None:
        if after:
            mission_id = str(getattr(mission, "mission_id", "")).lower()
            tech_state = getattr(mission, "mission_tech", None)
            tech_on_chopper = bool(tech_state is not None and str(getattr(tech_state, "state", "")) == "on_chopper")
            if mission_id in ("airport", "airport_special_ops", "airportspecialops", "mission2", "m2") and not tech_on_chopper:
                _set_toast_debounced(mission, set_toast, "Boarding blocked: pick up mission tech at tower LZ")
                return
            if at_base and boarded_now > 0:
                _set_toast_debounced(mission, set_toast, f"Doors OPEN: unloading {boarded_now} passenger(s)")
            elif at_base and boarded_now == 0:
                _set_toast_debounced(mission, set_toast, "Doors OPEN: no passengers to unload")
            elif boarded_now > 0:
                _set_toast_debounced(mission, set_toast, "Doors OPEN: land at base to unload")
            else:
                _set_toast_debounced(mission, set_toast, "Doors OPEN: ready for boarding")
        else:
            _set_toast_debounced(mission, set_toast, "Doors CLOSED")

    if logger is not None:
        if after and not at_base and boarded_now > 0:
            logger.info("UNLOAD_BLOCKED: doors open but not in base zone")
        if after and at_base and boarded_now == 0:
            logger.info("UNLOAD: no boarded passengers")


def check_airport_truck_retract_toast(
    mission,
    meal_truck_state,
    hostage_state,
    bus_state,
    set_toast: Callable[[str], None] | None,
) -> None:
    """Emit a guidance toast when the meal truck is extended and loaded, and is near the bus transfer LZ.

    Fires each tick; debounced internally so the player sees the message at most once every 5 s.
    """
    if set_toast is None:
        return
    if meal_truck_state is None or hostage_state is None:
        return
    if str(getattr(hostage_state, "state", "")) != "truck_loaded":
        return
    if float(getattr(meal_truck_state, "extension_progress", 0.0)) < 0.5:
        return
    truck_x = float(getattr(meal_truck_state, "x", 0.0))
    # Use bus stop_x as the transfer LZ anchor; fall back to current bus x.
    if bus_state is not None:
        lz_x = float(getattr(bus_state, "stop_x", float(getattr(bus_state, "x", truck_x))))
    else:
        return
    if abs(truck_x - lz_x) > 350.0:
        return
    _set_toast_debounced(
        mission,
        set_toast,
        "Retract the box truck lift to transfer passengers",
        cooldown_s=5.0,
    )
