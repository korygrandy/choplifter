from __future__ import annotations

"""Compatibility facade.

`rendering.py` historically contained all rendering logic.

For maintainability, the implementation now lives in `choplifter.render.*`,
but we keep this module as the stable import surface.
"""

from .render.backgrounds import bg_asset_exists, draw_ground, draw_sky
from .render.helicopter import draw_damage_flash, draw_helicopter
from .render.hud import draw_hud, draw_toast
from .render.overlays import (
    draw_chopper_select_overlay,
    draw_intro_cutscene,
    draw_mission_select_overlay,
    draw_skip_overlay,
)
from .render.particles import draw_flares, draw_helicopter_damage_fx, draw_impact_sparks
from .render.world import draw_mission


__all__ = [
    "bg_asset_exists",
    "draw_chopper_select_overlay",
    "draw_damage_flash",
    "draw_flares",
    "draw_ground",
    "draw_helicopter",
    "draw_helicopter_damage_fx",
    "draw_hud",
    "draw_impact_sparks",
    "draw_intro_cutscene",
    "draw_mission",
    "draw_mission_select_overlay",
    "draw_skip_overlay",
    "draw_sky",
    "draw_toast",
]
