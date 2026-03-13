"""Eager sprite/image preloader.

Called once when the player confirms their mission + chopper selection so that
no disk I/O (or pygame.image.load + scale) occurs during the first gameplay
frame.  Every function called here is already backed by a module-level cache;
calling them now just warms that cache before the game loop starts.
"""
from __future__ import annotations


_HUD_ICON_NAMES = ("hud_fuel", "hud_health", "hud_sentiment", "hud_saved", "hud_vip")
_HUD_ICON_SIZE = 18
_LIFE_ICON_W = 60
_CHOPPER_RENDER_W = 120  # matches the width_px used in render/helicopter.py


def preload_mission_sprites(mission_id: str, chopper_asset: str) -> None:
    """Warm all sprite caches for the given mission / chopper combination.

    Safe to call multiple times (all loaders are idempotent after first load).
    Must be called after pygame.display.set_mode() so convert_alpha() works.
    """
    from .render.world import get_enemy_image
    from .render.helicopter import _get_chopper_scaled
    from .render.hud import _load_hud_icon, _load_life_icon

    # --- Common to all missions ---

    # Tank sprite used by every mission.
    get_enemy_image("karrar.png")

    # Chopper sprite at the render width the game uses.
    _get_chopper_scaled(chopper_asset, width_px=_CHOPPER_RENDER_W)

    # HUD icon PNGs (gracefully returns None when asset files don't exist yet,
    # but the None result is cached so the filesystem is never probed again).
    for name in _HUD_ICON_NAMES:
        _load_hud_icon(name, _HUD_ICON_SIZE)

    # Life-strip icons for both active and spent states.
    _load_life_icon(chopper_asset, _LIFE_ICON_W, lost=False)
    _load_life_icon(chopper_asset, _LIFE_ICON_W, lost=True)

    # --- Airport mission extras ---
    if str(mission_id).lower() == "airport":
        # MRAP vehicle sprite (airport compound guard)
        get_enemy_image("mrap-vehicle.png")

        from .bus_ai import _load_bus_sprite, _load_bus_sprite_doors_open
        _load_bus_sprite()
        _load_bus_sprite_doors_open()

        from .vehicle_assets import _ensure_meal_truck_sprites
        _ensure_meal_truck_sprites()

        from .enemy_spawns import _get_raider_sprite
        _get_raider_sprite()
