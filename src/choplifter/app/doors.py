from typing import Callable

def toggle_doors_with_logging(helicopter, mission, audio, logger, boarded_count: Callable[[object], int]):
    at_base = mission.base.contains_point(helicopter.pos)
    if not helicopter.grounded:
        logger.info("DOORS: toggle blocked (not grounded)")
        return

    before = helicopter.doors_open
    helicopter.toggle_doors()
    after = helicopter.doors_open
    if before != after:
        if after:
            audio.play_doors_open()
        else:
            audio.play_doors_close()
        logger.info(
            "DOORS: %s at_base=%s boarded=%d",
            "OPEN" if after else "closed",
            at_base,
            boarded_count(mission),
        )

    if after and not at_base and boarded_count(mission) > 0:
        logger.info("UNLOAD_BLOCKED: doors open but not in base zone")
    if after and at_base and boarded_count(mission) == 0:
        logger.info("UNLOAD: no boarded passengers")
