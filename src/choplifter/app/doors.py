from typing import Callable


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
