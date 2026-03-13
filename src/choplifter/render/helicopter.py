from __future__ import annotations

from pathlib import Path
import math
import pygame

from ..helicopter import Facing, Helicopter


_CHOPPER_ORIG: dict[str, pygame.Surface] = {}
_CHOPPER_LOAD_FAILED: set[str] = set()
_CHOPPER_SCALED: dict[tuple[str, int], pygame.Surface] = {}
_CHOPPER_VARIANT: dict[tuple[str, int, str, bool, bool], pygame.Surface] = {}
_CHOPPER_ROTATED: dict[tuple[str, int, str, bool, bool, int], pygame.Surface] = {}
_CHOPPER_ROTATED_MAX = 256
_DAMAGE_FLASH_SURFACE: dict[tuple[int, int], pygame.Surface] = {}
_DOOR_PANEL_CACHE: dict[tuple[int, int], pygame.Surface] = {}


def _bounded_put(cache: dict, key: object, value: pygame.Surface, *, max_size: int) -> None:
    """Insert into a small transform cache and cap memory growth."""
    cache[key] = value
    if len(cache) > max_size:
        # Keep cache maintenance cheap; these surfaces are quickly repopulated.
        cache.clear()


def _get_door_panel(width: int, height: int) -> pygame.Surface:
    """Get a cached door panel surface with US flag pattern (stripes + blue canton).
    
    Args:
        width, height: Dimensions of the door panel
        
    Returns:
        A cached pygame.Surface with the door panel pattern drawn on it.
    """
    width = max(1, int(width))
    height = max(1, int(height))
    key = (width, height)
    cached = _DOOR_PANEL_CACHE.get(key)
    if cached is not None:
        return cached
    
    door_radius = 3
    door_panel = pygame.Surface((width, height), pygame.SRCALPHA)
    
    # Red/white horizontal stripes (US flag vibe)
    stripe_h = max(1, height // 7)
    y0 = 0
    stripe_index = 0
    while y0 < height:
        h_stripe = min(stripe_h, height - y0)
        color = (200, 30, 30, 200) if (stripe_index % 2 == 0) else (245, 245, 245, 200)
        pygame.draw.rect(door_panel, color, pygame.Rect(0, y0, width, h_stripe))
        y0 += stripe_h
        stripe_index += 1
    
    # Blue canton in the upper corner + tiny white dots to suggest stars
    canton_w = max(2, int(width * 0.45))
    canton_h = max(2, int(height * 0.45))
    canton = pygame.Rect(0, 0, canton_w, canton_h)
    pygame.draw.rect(door_panel, (20, 60, 160, 220), canton)
    for sx, sy in (
        (canton.left + canton.width // 3, canton.top + canton.height // 3),
        (canton.left + (2 * canton.width) // 3, canton.top + canton.height // 3),
        (canton.left + canton.width // 2, canton.top + (2 * canton.height) // 3),
    ):
        pygame.draw.circle(door_panel, (245, 245, 245, 230), (sx, sy), 1)
    
    # Apply a rounded-rect alpha mask so the fill has rounded edges too
    mask = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=door_radius)
    door_panel.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    
    _DOOR_PANEL_CACHE[key] = door_panel
    if len(_DOOR_PANEL_CACHE) > 64:
        _DOOR_PANEL_CACHE.clear()
        _DOOR_PANEL_CACHE[key] = door_panel
    
    return door_panel


def draw_damage_flash(screen: pygame.Surface, helicopter: Helicopter) -> None:
    if helicopter.damage_flash_seconds <= 0.0:
        return

    # A short, bright flash that decays quickly.
    duration = 0.12
    t = max(0.0, min(1.0, helicopter.damage_flash_seconds / duration))
    alpha = int(160 * t)
    if alpha <= 0:
        return

    r, g, b = helicopter.damage_flash_rgb
    size_key = (int(screen.get_width()), int(screen.get_height()))
    overlay = _DAMAGE_FLASH_SURFACE.get(size_key)
    if overlay is None:
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        _DAMAGE_FLASH_SURFACE[size_key] = overlay
        if len(_DAMAGE_FLASH_SURFACE) > 8:
            _DAMAGE_FLASH_SURFACE.clear()
            _DAMAGE_FLASH_SURFACE[size_key] = overlay
    overlay.fill((int(r), int(g), int(b), alpha))
    screen.blit(overlay, (0, 0))


def draw_helicopter(screen: pygame.Surface, helicopter: Helicopter, *, camera_x: float = 0.0, boarded: int = 0) -> None:
    if getattr(helicopter, "crash_hide", False):
        return

    x = int(helicopter.pos.x - camera_x)
    y = int(helicopter.pos.y)

    roll_deg = float(getattr(helicopter, "crash_roll_deg", 0.0)) if getattr(helicopter, "crashing", False) else float(helicopter.tilt_deg)

    def _with_door_overlay(base: pygame.Surface) -> pygame.Surface:
        """Return a copy of the helicopter sprite with a simple door state indicator."""

        w = base.get_width()
        h = base.get_height()
        if w <= 0 or h <= 0:
            return base

        # Normalized door rectangle in sprite space.
        # Tuned for `chopper-one.png` authored facing LEFT; since we draw after flip, this stays correct.
        door_nx, door_ny, door_nw, door_nh = (0.46, 0.58, 0.16, 0.22)
        door_rect = pygame.Rect(
            int(w * door_nx),
            int(h * door_ny),
            max(1, int(w * door_nw)),
            max(1, int(h * door_nh)),
        )

        # Requested tweak: shift left ~10px, +4px height, -3px width.
        door_rect.x -= 10
        door_rect.width = max(1, door_rect.width - 3)
        door_rect.height = max(1, door_rect.height + 4)

        # Follow-up tweak: shift left another 5px, shrink width by 1px.
        door_rect.x -= 5
        door_rect.width = max(1, door_rect.width - 1)

        # Right-facing sprites are horizontally flipped; nudge to keep the door aligned.
        if helicopter.facing is Facing.RIGHT:
            door_rect.x += 27

        out = base.copy()
        # Ensure we can draw alpha on top even if the source is non-alpha.
        try:
            out = out.convert_alpha()
        except Exception:
            pass

        door_radius = 3

        if helicopter.doors_open:
            # Open: darker "cutout" + subtle light outline.
            pygame.draw.rect(out, (0, 0, 0, 170), door_rect, border_radius=door_radius)
            pygame.draw.rect(out, (235, 235, 235, 160), door_rect, 1, border_radius=door_radius)
        else:
            # Closed: use cached door panel with US flag pattern
            door_panel = _get_door_panel(door_rect.width, door_rect.height)
            out.blit(door_panel, door_rect.topleft)
            pygame.draw.rect(out, (20, 20, 20, 140), door_rect, 1, border_radius=door_radius)

        # Passenger indicator: a small "occupied" light that appears only when carrying someone.
        if boarded > 0:
            light_cx = door_rect.centerx
            light_cy = door_rect.top - max(3, door_rect.height // 5)
            light_cx = max(2, min(w - 3, light_cx))
            light_cy = max(2, min(h - 3, light_cy))
            pygame.draw.circle(out, (0, 0, 0, 150), (light_cx, light_cy), 4)
            pygame.draw.circle(out, (255, 220, 80, 230), (light_cx, light_cy), 3)

        return out

    skin = getattr(helicopter, "skin_asset", "chopper-one.png")
    width_px = 120
    sprite = _get_chopper_scaled(skin, width_px=width_px)
    if sprite is not None:
        facing_name = str(getattr(helicopter.facing, "name", "LEFT"))
        occupied = bool(boarded > 0)
        variant_key = (skin, width_px, facing_name, bool(helicopter.doors_open), occupied)
        variant = _CHOPPER_VARIANT.get(variant_key)
        if variant is None:
            variant = sprite
            # The base sprite is authored facing LEFT; flip for RIGHT-facing.
            if helicopter.facing is Facing.RIGHT:
                variant = pygame.transform.flip(variant, True, False)
            variant = _with_door_overlay(variant)
            _CHOPPER_VARIANT[variant_key] = variant

        # Quantize roll for cache reuse while keeping animation smooth.
        angle_bucket = int(round(float(roll_deg) * 2.0))  # 0.5 degree buckets
        rotated_key = variant_key + (angle_bucket,)
        rotated = _CHOPPER_ROTATED.get(rotated_key)
        if rotated is None:
            rotated = pygame.transform.rotate(variant, -(angle_bucket / 2.0))
            _bounded_put(_CHOPPER_ROTATED, rotated_key, rotated, max_size=_CHOPPER_ROTATED_MAX)

        rect = rotated.get_rect(center=(x, y))
        screen.blit(rotated, rect)
        return

    # Fallback: minimal placeholder (kept for robustness if asset missing).
    body_w, body_h = 70, 22
    body = pygame.Surface((body_w, body_h), pygame.SRCALPHA)
    body.fill((0, 0, 0, 0))
    pygame.draw.rect(body, (60, 190, 80), pygame.Rect(0, 0, body_w, body_h), border_radius=6)

    # Door indicator (fallback rendering).
    door_rect = pygame.Rect(int(body_w * 0.44), int(body_h * 0.45), int(body_w * 0.18), int(body_h * 0.45))
    door_rect.x -= 10
    door_rect.width = max(1, door_rect.width - 3)
    door_rect.height = max(1, door_rect.height + 4)
    door_rect.x -= 5
    door_rect.width = max(1, door_rect.width - 1)
    if helicopter.facing is Facing.RIGHT:
        door_rect.x += 27
    if helicopter.doors_open:
        pygame.draw.rect(body, (0, 0, 0, 170), door_rect, border_radius=3)
        pygame.draw.rect(body, (235, 235, 235, 160), door_rect, 1, border_radius=3)
    else:
        door_panel = pygame.Surface((door_rect.width, door_rect.height), pygame.SRCALPHA)
        stripe_h = max(1, door_rect.height // 5)
        y0 = 0
        stripe_index = 0
        while y0 < door_rect.height:
            h_stripe = min(stripe_h, door_rect.height - y0)
            color = (200, 30, 30, 255) if (stripe_index % 2 == 0) else (245, 245, 245, 255)
            pygame.draw.rect(door_panel, color, pygame.Rect(0, y0, door_rect.width, h_stripe))
            y0 += stripe_h
            stripe_index += 1

        canton_w = max(2, int(door_rect.width * 0.45))
        canton_h = max(2, int(door_rect.height * 0.45))
        canton = pygame.Rect(0, 0, canton_w, canton_h)
        pygame.draw.rect(door_panel, (20, 60, 160, 255), canton)
        for sx, sy in (
            (canton.left + canton.width // 3, canton.top + canton.height // 3),
            (canton.left + (2 * canton.width) // 3, canton.top + canton.height // 3),
            (canton.left + canton.width // 2, canton.top + (2 * canton.height) // 3),
        ):
            pygame.draw.circle(door_panel, (245, 245, 245, 255), (sx, sy), 1)

        mask = pygame.Surface((door_rect.width, door_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=3)
        door_panel.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        body.blit(door_panel, door_rect.topleft)

        pygame.draw.rect(body, (20, 20, 20, 160), door_rect, 1, border_radius=3)

    if boarded > 0:
        light_cx = door_rect.centerx
        light_cy = door_rect.top - max(2, door_rect.height // 4)
        light_cx = max(2, min(body_w - 3, light_cx))
        light_cy = max(2, min(body_h - 3, light_cy))
        pygame.draw.circle(body, (0, 0, 0, 170), (light_cx, light_cy), 4)
        pygame.draw.circle(body, (255, 220, 80, 255), (light_cx, light_cy), 3)

    if helicopter.facing is Facing.LEFT:
        pygame.draw.circle(body, (220, 220, 220), (8, body_h // 2), 4)
    elif helicopter.facing is Facing.RIGHT:
        pygame.draw.circle(body, (220, 220, 220), (body_w - 8, body_h // 2), 4)
    else:
        pygame.draw.circle(body, (220, 220, 220), (body_w // 2, body_h // 2), 4)

    rotated = pygame.transform.rotate(body, -roll_deg)
    rect = rotated.get_rect(center=(x, y))
    screen.blit(rotated, rect)

    rotor_len = 90
    rotor_offset = 18
    angle_rad = math.radians(-roll_deg)
    cx, cy = rect.centerx, rect.centery - rotor_offset
    dx = math.cos(angle_rad) * (rotor_len / 2)
    dy = math.sin(angle_rad) * (rotor_len / 2)
    pygame.draw.line(screen, (30, 30, 30), (cx - dx, cy - dy), (cx + dx, cy + dy), 4)


def _get_chopper_scaled(asset_filename: str, *, width_px: int) -> pygame.Surface | None:
    if asset_filename in _CHOPPER_LOAD_FAILED:
        return None

    width_px = max(1, int(width_px))
    cache_key = (asset_filename, width_px)
    cached = _CHOPPER_SCALED.get(cache_key)
    if cached is not None:
        return cached

    orig = _CHOPPER_ORIG.get(asset_filename)
    if orig is None:
        package_dir = Path(__file__).resolve().parents[1]
        path = package_dir / "assets" / asset_filename
        try:
            loaded = pygame.image.load(str(path))
            if pygame.display.get_surface() is not None:
                loaded = loaded.convert_alpha()

            # If the sprite has no transparency, treat top-left as background key.
            w = loaded.get_width()
            h = loaded.get_height()
            if w > 0 and h > 0:
                corners = ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))
                if all(loaded.get_at(p).a == 255 for p in corners):
                    key = loaded.get_at((0, 0))
                    loaded.set_colorkey((key.r, key.g, key.b), pygame.RLEACCEL)

            _CHOPPER_ORIG[asset_filename] = loaded
            orig = loaded
        except Exception:
            _CHOPPER_LOAD_FAILED.add(asset_filename)
            return None

    ow, oh = orig.get_width(), orig.get_height()
    if ow <= 0 or oh <= 0:
        _CHOPPER_LOAD_FAILED.add(asset_filename)
        return None

    scale = width_px / float(ow)
    out_h = max(1, int(oh * scale))
    scaled = pygame.transform.smoothscale(orig, (width_px, out_h))

    key = orig.get_colorkey()
    if key is not None:
        scaled.set_colorkey(key, pygame.RLEACCEL)

    _CHOPPER_SCALED[cache_key] = scaled
    # Asset reload can invalidate dependent transformed caches.
    _CHOPPER_VARIANT.clear()
    _CHOPPER_ROTATED.clear()
    return scaled
