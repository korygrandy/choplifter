from __future__ import annotations

from typing import Final


BOARDING_FAIL_NOT_GROUNDED: Final[str] = "not_grounded"
BOARDING_FAIL_DOORS_CLOSED: Final[str] = "doors_closed"
BOARDING_FAIL_FULL: Final[str] = "full"


def record_boarding_failure(
    mission: object,
    reason: str,
    *,
    cooldown_s: float = 0.65,
) -> None:
    """Increment per-reason boarding failure counters with debounce."""
    if not reason:
        return

    now = float(getattr(mission, "elapsed_seconds", 0.0))
    counters = getattr(mission, "boarding_failure_counts", None)
    if not isinstance(counters, dict):
        counters = {}
        setattr(mission, "boarding_failure_counts", counters)

    last_times = getattr(mission, "_boarding_failure_last_times", None)
    if not isinstance(last_times, dict):
        last_times = {}
        setattr(mission, "_boarding_failure_last_times", last_times)

    last_time = float(last_times.get(reason, -9999.0))
    if (now - last_time) < float(cooldown_s):
        return

    counters[reason] = int(counters.get(reason, 0)) + 1
    last_times[reason] = now
