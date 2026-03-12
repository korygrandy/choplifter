from __future__ import annotations

from .main_loop_context import MainLoopContext


def load_frame_locals_from_context(
    *,
    loop_ctx: MainLoopContext,
) -> tuple[object, object, float, object, float, object]:
    """Return frame-local loop values from shared main-loop context."""
    return (
        loop_ctx.mission,
        loop_ctx.helicopter,
        loop_ctx.accumulator,
        loop_ctx.prev_stats,
        loop_ctx.campaign_sentiment,
        loop_ctx.airport_runtime,
    )


def store_frame_locals_to_context(
    *,
    loop_ctx: MainLoopContext,
    mission: object,
    helicopter: object,
    accumulator: float,
    prev_stats: object,
    campaign_sentiment: float,
    airport_runtime: object,
) -> None:
    """Persist frame-local loop values back to the shared main-loop context."""
    loop_ctx.mission = mission
    loop_ctx.helicopter = helicopter
    loop_ctx.accumulator = accumulator
    loop_ctx.prev_stats = prev_stats
    loop_ctx.campaign_sentiment = campaign_sentiment
    loop_ctx.airport_runtime = airport_runtime
