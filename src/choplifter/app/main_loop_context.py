from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MainLoopContext:
    """Mutable run-loop state that needs reassignment during reset/preview flows."""

    mission: object
    helicopter: object
    accumulator: float
    prev_stats: object
    campaign_sentiment: float
    airport_runtime: object
