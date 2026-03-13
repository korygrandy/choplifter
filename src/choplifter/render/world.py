from __future__ import annotations
import os
# Image cache for enemy sprites
_enemy_image_cache = {}
_airport_backdrop_image_cache: pygame.Surface | None | bool = False

def get_enemy_image(name):
    if name not in _enemy_image_cache:
        # Use absolute path to ensure asset is found
        asset_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))
        path = os.path.join(asset_dir, name)
        _enemy_image_cache[name] = pygame.image.load(path).convert_alpha()
    return _enemy_image_cache[name]


def _load_airplane_backdrop_sprite() -> pygame.Surface | None:
    """Load airport fuselage backdrop sprite once; return None when unavailable."""
    global _airport_backdrop_image_cache
    if _airport_backdrop_image_cache is not False:
        return _airport_backdrop_image_cache if isinstance(_airport_backdrop_image_cache, pygame.Surface) else None
    try:
        asset_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))
        path = os.path.join(asset_dir, "airplane-backdrop.png")
        _airport_backdrop_image_cache = pygame.image.load(path).convert_alpha()
    except Exception:
        _airport_backdrop_image_cache = None
    return _airport_backdrop_image_cache if isinstance(_airport_backdrop_image_cache, pygame.Surface) else None

# Volatile surface cache: surfaces are reused across frames and redrawn each time.
# Keys are (width, height, flags) tuples. Surfaces are created once and resized as needed.
_volatile_surface_cache = {}

# Font and text caches for world rendering
_WORLD_FONT_CACHE: dict[tuple[str, int, bool], pygame.font.Font] = {}
_WORLD_TEXT_CACHE: dict[tuple[str, tuple[int, int, int], str], pygame.Surface] = {}

def get_world_font(name: str, size: int, bold: bool = False) -> pygame.font.Font:
    """Get a cached font for world rendering."""
    key = (name, size, bold)
    if key not in _WORLD_FONT_CACHE:
        _WORLD_FONT_CACHE[key] = pygame.font.SysFont(name, size, bold=bold)
    return _WORLD_FONT_CACHE[key]

def get_world_text(text: str, font_size: int, color: tuple[int, int, int]) -> pygame.Surface:
    """Get a cached rendered text surface."""
    key = (text, color, str(font_size))
    if key not in _WORLD_TEXT_CACHE:
        font = get_world_font("consolas", font_size, bold=True)
        _WORLD_TEXT_CACHE[key] = font.render(text, True, color)
    return _WORLD_TEXT_CACHE[key]

def get_volatile_surface(width: int, height: int, flags: int = 0) -> pygame.Surface:
    """Get a cached volatile surface, creating or resizing as needed.
    
    Volatile surfaces are transient: they are redrawn each frame and safe to reuse
    across multiple callers. The content is NOT preserved between frames.
    
    Args:
        width, height: Required dimensions
        flags: pygame surface flags (e.g., pygame.SRCALPHA). Default 0 = opaque surface.
    
    Returns:
        A pygame.Surface with the requested dimensions, cleared to transparent/black.
    """
    key = (width, height, flags)
    if key not in _volatile_surface_cache:
        _volatile_surface_cache[key] = pygame.Surface((width, height), flags)
    else:
        surf = _volatile_surface_cache[key]
        if surf.get_size() != (width, height):
            # Resize if dimensions changed
            _volatile_surface_cache[key] = pygame.Surface((width, height), flags)
    
    # Clear the surface before returning (critical for safe reuse across callers)
    surf = _volatile_surface_cache[key]
    if flags & pygame.SRCALPHA:
        surf.fill((0, 0, 0, 0))  # Transparent for alpha surfaces
    else:
        surf.fill((0, 0, 0))  # Black for opaque surfaces
    
    return surf

import math
from typing import TYPE_CHECKING
import pygame

# Thermal overlay toggle state (runtime mutable via toggle_thermal_mode).
thermal_mode = False

from ..game_types import EnemyKind, HostageState, ProjectileKind
from ..barak_mrad import BARAK_LAUNCHER_VISIBLE_STATES
from ..airport_fuselage import (
    FUSELAGE_DAMAGE_STAGE_TOTAL,
    get_airport_fuselage_damage_stage,
)
from ..hostage_logic import _draw_stick_figure_passenger, _draw_stick_figure_passenger_rotated
from ..mission_helpers import sentiment_band_label, sentiment_contributions
_airport_fuselage_half_image_cache: pygame.Surface | None | bool = False
_airport_fuselage_total_image_cache: pygame.Surface | None | bool = False

FUSELAGE_BACKDROP_OFFSET_X = -245
FUSELAGE_BACKDROP_OFFSET_Y = -175


def _load_fuselage_damage_sprite(*, total: bool) -> pygame.Surface | None:
    """Load fuselage damage overlay sprite; supports legacy and corrected names."""
    global _airport_fuselage_half_image_cache
    global _airport_fuselage_total_image_cache

    cache = _airport_fuselage_total_image_cache if total else _airport_fuselage_half_image_cache
    if cache is not False:
        return cache if isinstance(cache, pygame.Surface) else None

    candidates = [
        "plane-fuselage-totally-amaged.png",
        "plane-fuselage-totally-damaged.png",
    ] if total else [
        "plan-fuselage-half-damaged.png",
        "plane-fuselage-half-damaged.png",
    ]

    loaded: pygame.Surface | None = None
    asset_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))
    for name in candidates:
        try:
            loaded = pygame.image.load(os.path.join(asset_dir, name)).convert_alpha()
            break
        except Exception:
            loaded = None

    if total:
        _airport_fuselage_total_image_cache = loaded
        cached = _airport_fuselage_total_image_cache
    else:
        _airport_fuselage_half_image_cache = loaded
        cached = _airport_fuselage_half_image_cache
    return cached if isinstance(cached, pygame.Surface) else None


def _draw_fuselage_damage_fallback(screen: pygame.Surface, fuselage_rect: pygame.Rect, stage: int, t: float) -> None:
    if stage <= 0:
        return
    crack = (86, 86, 86) if stage == 1 else (122, 70, 66)
    for i in range(3 + stage):
        cx = fuselage_rect.x + 8 + i * max(10, fuselage_rect.width // 6)
        cy = fuselage_rect.y + 10 + (i % 2) * 8
        jitter = int(math.sin(t * 4.8 + i * 0.9) * 2)
        pygame.draw.line(screen, crack, (cx, cy + jitter), (cx + 8, cy + 6 + jitter), 2)


def _draw_fuselage_damage_particles(screen: pygame.Surface, fuselage_rect: pygame.Rect, stage: int, t: float) -> None:
    if stage <= 0:
        return
    count = 10 if stage == 1 else 18
    for i in range(count):
        phase = t * (1.4 + i * 0.03) + i * 0.5
        sx = int(fuselage_rect.centerx + math.sin(phase * 2.2) * (10 + stage * 4) + (i % 5) * 3 - 6)
        sy = int(fuselage_rect.y - (phase * 14 + i * 4) % (36 + stage * 10))
        radius = 2 if stage == 1 else 3
        alpha = 90 if stage == 1 else 130
        color = (132, 132, 132, alpha) if stage == 1 else (186, 112, 64, alpha)
        puff_layer = get_volatile_surface(screen.get_width(), screen.get_height(), pygame.SRCALPHA)
        pygame.draw.circle(puff_layer, color, (sx, sy), radius)
        screen.blit(puff_layer, (0, 0))


def _draw_fuselage_damage_overlay(screen: pygame.Surface, fuselage_rect: pygame.Rect, stage: int, t: float) -> None:
    if stage <= 0:
        return

    sprite = _load_fuselage_damage_sprite(total=stage >= FUSELAGE_DAMAGE_STAGE_TOTAL)
    if sprite is not None:
        sprite_w = max(1, int(fuselage_rect.width * 1.34))
        sprite_h = max(1, int(fuselage_rect.height * 1.24))
        scaled = pygame.transform.smoothscale(sprite, (sprite_w, sprite_h))
        rect = scaled.get_rect(center=fuselage_rect.center)
        rect.y -= 8
        screen.blit(scaled, rect)
    else:
        _draw_fuselage_damage_fallback(screen, fuselage_rect, stage, t)

    _draw_fuselage_damage_particles(screen, fuselage_rect, stage, t)

if TYPE_CHECKING:
    from ..mission_state import MissionState


def draw_mission(screen: pygame.Surface, mission: MissionState, *, camera_x: float = 0.0, enable_particles: bool = True) -> None:
    _draw_base(screen, mission, camera_x=camera_x)
    _draw_compounds(screen, mission, camera_x=camera_x)
    _draw_airport_lz_tower(screen, mission, camera_x=camera_x)
    _draw_hostages(screen, mission, camera_x=camera_x)
    _draw_engineer_boarding(screen, mission, camera_x=camera_x)
    _draw_engineer_wrench_indicator(screen, mission, camera_x=camera_x)
    if enable_particles:
        from .particles import draw_jet_trail_particles

        draw_jet_trail_particles(screen, mission, camera_x=camera_x)
    _draw_enemies(screen, mission, camera_x=camera_x)
    if enable_particles:
        from .particles import draw_burning_particles, draw_dust_storm_particles, draw_explosion_particles

        draw_burning_particles(screen, mission, camera_x=camera_x)
        draw_explosion_particles(screen, mission, camera_x=camera_x)
        draw_dust_storm_particles(screen, mission, camera_x=camera_x)
    _draw_projectiles(screen, mission, camera_x=camera_x)
    _draw_supply_drops(screen, mission, camera_x=camera_x)


def _is_on_screen(world_x: float, camera_x: float, screen_width: int, margin: int = 200) -> bool:
    """Quick culling check: is a world position visible within camera view + margin?
    
    Args:
        world_x: Entity's world x coordinate
        camera_x: Camera's world x position
        screen_width: Screen width in pixels
        margin: Buffer around screen edges (pixels) for partially visible objects
        
    Returns:
        True if entity is within visible range (camera view + margin buffer)
    """
    screen_x = world_x - camera_x
    return -margin <= screen_x <= screen_width + margin

def _compound_has_awaiting_passengers(mission: MissionState, compound: object) -> bool:
    start = max(0, int(getattr(compound, "hostage_start", 0)))
    count = max(0, int(getattr(compound, "hostage_count", 0)))
    if count <= 0:
        return False
    hostages = list(getattr(mission, "hostages", []) or [])
    end = min(len(hostages), start + count)
    awaiting_states = {
        HostageState.IDLE,
        HostageState.PANIC,
        HostageState.MOVING_TO_LZ,
        HostageState.WAITING,
    }
    for h in hostages[start:end]:
        state = getattr(h, "state", None)
        if state in awaiting_states:
            return True
    return False

    # Draw wind-blown dust clouds if present
    from .particles import draw_wind_dust_clouds
    draw_wind_dust_clouds(screen, mission, camera_x=camera_x)

def draw_mission_end_overlay(
    screen: pygame.Surface,
    mission: MissionState,
    *,
    mission_end_return_seconds: float = 0.0,
) -> None:
    """Draw THE END/debrief overlay as a top-most layer above world entities and weather."""
    if not (getattr(mission, "ended", False) and getattr(mission, "end_text", "")):
        return

    boarded = sum(1 for h in mission.hostages if h.state is HostageState.BOARDED)
    _draw_end(
        screen,
        mission.end_text,
        mission.end_reason,
        mission.stats.saved,
        boarded,
        mission.stats.kia_by_player,
        mission.stats.kia_by_enemy,
        mission.stats.lost_in_transit,
        mission.stats.enemies_destroyed,
        mission.crashes,
        mission.sentiment,
        mission_id=str(getattr(mission, "mission_id", "")),
        route_bonus_awarded=bool(getattr(mission, "airport_route_bonus_awarded", False)),
        route_bonus_value=float(getattr(mission, "airport_route_bonus_value", 0.0)),
        first_route=str(getattr(mission, "airport_first_rescue_route", "")),
        mission_end_return_seconds=float(mission_end_return_seconds),
    )


def _countdown_seconds_label(remaining_seconds: float) -> str:
    seconds = max(0.0, float(remaining_seconds))
    if seconds <= 0.0:
        return ""
    display = max(1, int(math.ceil(seconds)))
    return f"Returning to Mission Select in {display}s"


def _draw_base(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    r = pygame.Rect(
        int(mission.base.pos.x - camera_x),
        int(mission.base.pos.y),
        int(mission.base.width),
        int(mission.base.height),
    )

    def _is_unload_active() -> bool:
        if float(getattr(mission, "unload_release_seconds", 0.0)) > 0.0:
            return True
        for h in getattr(mission, "hostages", []):
            if getattr(h, "state", None) is HostageState.EXITING:
                return True
        return False

    unload_active = _is_unload_active()
    t = float(getattr(mission, "elapsed_seconds", 0.0))
    unload_pulse = (math.sin(t * 6.2) + 1.0) * 0.5 if unload_active else 0.0

    # Post Office body (retro utilitarian palette).
    main_color = (164, 172, 186)
    shadow_color = (112, 118, 132)
    frame_color = (44, 50, 64)
    trim_color = (208, 214, 224)

    pygame.draw.rect(screen, main_color, r, border_radius=6)
    pygame.draw.rect(screen, frame_color, r, 2, border_radius=6)

    # Lower facade block texture for depth.
    brick_band_h = max(10, int(r.height * 0.20))
    brick_band = pygame.Rect(r.x + 2, r.bottom - brick_band_h - 2, r.width - 4, brick_band_h)
    pygame.draw.rect(screen, (194, 202, 214), brick_band, border_radius=3)
    brick_h = 4
    brick_w = 10
    mortar = (146, 152, 164)
    for row_y in range(brick_band.y + brick_h, brick_band.bottom, brick_h):
        pygame.draw.line(screen, mortar, (brick_band.x, row_y), (brick_band.right, row_y), 1)
    for row_i, y0 in enumerate(range(brick_band.y, brick_band.bottom, brick_h)):
        x_off = 0 if row_i % 2 == 0 else brick_w // 2
        for x0 in range(brick_band.x + x_off + brick_w, brick_band.right, brick_w):
            y1 = min(brick_band.bottom, y0 + brick_h)
            pygame.draw.line(screen, mortar, (x0, y0), (x0, y1), 1)
    pygame.draw.line(screen, shadow_color, (brick_band.x, brick_band.y), (brick_band.right, brick_band.y), 1)

    # Roof and central pediment.
    roof_h = max(8, int(r.height * 0.16))
    roof = pygame.Rect(r.x - 3, r.y - roof_h + 2, r.width + 6, roof_h)
    pygame.draw.rect(screen, trim_color, roof, border_radius=4)
    pygame.draw.rect(screen, frame_color, roof, 1, border_radius=4)

    pediment_h = max(10, int(r.height * 0.22))
    pediment = [
        (r.centerx - 26, roof.bottom + 2),
        (r.centerx + 26, roof.bottom + 2),
        (r.centerx, roof.bottom - pediment_h),
    ]
    pygame.draw.polygon(screen, (198, 204, 214), pediment)

    # Subtle tile texture for the triangular pediment roof.
    apex_x, apex_y = pediment[2]
    base_y = pediment[0][1]
    row_spacing = 3
    seam_spacing = 8
    tile_row_color = (170, 176, 188)
    tile_seam_color = (152, 158, 172)
    for row_i, y in enumerate(range(apex_y + 2, base_y - 1, row_spacing)):
        depth_t = (y - apex_y) / max(1, (base_y - apex_y))
        half_span = max(1, int((pediment[1][0] - apex_x) * depth_t))
        x_left = apex_x - half_span + 1
        x_right = apex_x + half_span - 1
        if x_right <= x_left:
            continue
        pygame.draw.line(screen, tile_row_color, (x_left, y), (x_right, y), 1)
        seam_offset = 0 if row_i % 2 == 0 else seam_spacing // 2
        for sx in range(x_left + seam_offset, x_right, seam_spacing):
            pygame.draw.line(screen, tile_seam_color, (sx, y), (sx, min(base_y - 1, y + 2)), 1)

    pygame.draw.polygon(screen, frame_color, pediment, 1)

    # Entry doors and stairs.
    entry_w = max(20, int(r.width * 0.22))
    entry_h = max(22, int(r.height * 0.44))
    entry = pygame.Rect(r.centerx - entry_w // 2, r.bottom - entry_h - 4, entry_w, entry_h)

    # Post Office placard label.
    placard_w = max(44, int(r.width * 0.42))
    placard_h = max(10, int(r.height * 0.12))
    placard_y = roof.bottom + 4
    placard = pygame.Rect(r.centerx - placard_w // 2, placard_y, placard_w, placard_h)
    pygame.draw.rect(screen, (34, 44, 72), placard, border_radius=2)
    placard_border_boost = int(26 * unload_pulse)
    placard_border = (
        min(255, 184 + placard_border_boost),
        min(255, 190 + placard_border_boost),
        min(255, 204 + placard_border_boost),
    )
    pygame.draw.rect(screen, placard_border, placard, 1, border_radius=2)
    font_size = max(8, min(13, int(placard_h * 0.8)))
    placard_font = get_world_font("consolas", font_size, bold=True)
    placard_text = placard_font.render("US POST OFFICE", True, (232, 236, 244))
    text_x = placard.centerx - placard_text.get_width() // 2
    text_y = placard.centery - placard_text.get_height() // 2
    screen.blit(placard_text, (text_x, text_y))

    # Tiny pixel eagle/mail emblem to reinforce the postal identity.
    emblem = pygame.Rect(placard.x + 6, placard.y + 2, 12, max(6, placard.height - 4))
    pygame.draw.rect(screen, (228, 232, 240), emblem, border_radius=1)
    pygame.draw.rect(screen, (28, 34, 46), emblem, 1, border_radius=1)
    # Stylized eagle wings (blue chevrons) + mail bar (red stripe).
    wing_y = emblem.y + 2
    pygame.draw.line(screen, (54, 94, 176), (emblem.x + 1, wing_y + 1), (emblem.centerx, wing_y + 3), 1)
    pygame.draw.line(screen, (54, 94, 176), (emblem.right - 2, wing_y + 1), (emblem.centerx, wing_y + 3), 1)
    pygame.draw.line(screen, (188, 48, 58), (emblem.x + 2, emblem.bottom - 3), (emblem.right - 3, emblem.bottom - 3), 1)

    # Red/blue postal accent stripes.
    stripe_y = placard.bottom + 4
    pygame.draw.rect(screen, (184, 36, 42), pygame.Rect(r.x + 8, stripe_y, r.width - 16, 3), border_radius=1)
    pygame.draw.rect(screen, (52, 86, 164), pygame.Rect(r.x + 8, stripe_y + 4, r.width - 16, 3), border_radius=1)

    pygame.draw.rect(screen, (58, 68, 84), entry, border_radius=3)
    pygame.draw.rect(screen, (22, 26, 34), entry, 1, border_radius=3)
    pygame.draw.line(screen, (86, 98, 118), (entry.centerx, entry.y + 2), (entry.centerx, entry.bottom - 2), 1)
    if unload_active:
        glow = int(32 * unload_pulse)
        pulse_outline = (min(255, 188 + glow), min(255, 196 + glow), min(255, 214 + glow))
        pygame.draw.rect(screen, pulse_outline, entry.inflate(4, 4), 1, border_radius=4)

    step_h = max(4, int(r.height * 0.08))
    step = pygame.Rect(entry.x - 8, entry.bottom, entry.width + 16, step_h)
    pygame.draw.rect(screen, (132, 138, 150), step, border_radius=2)
    pygame.draw.rect(screen, frame_color, step, 1, border_radius=2)

    # Painted postal LZ apron marking in front of the post office entry.
    apron_mark = pygame.Rect(entry.centerx - 38, r.bottom + 2, 76, 10)
    pygame.draw.rect(screen, (176, 168, 132), apron_mark, border_radius=2)
    pygame.draw.rect(screen, (56, 62, 72), apron_mark, 1, border_radius=2)
    inner = apron_mark.inflate(-10, -4)
    pygame.draw.rect(screen, (40, 66, 118), inner, border_radius=1)
    lz_font = get_world_font("consolas", 9, bold=True)
    lz_text = lz_font.render("LZ", True, (238, 220, 132))
    screen.blit(lz_text, (inner.centerx - lz_text.get_width() // 2, inner.centery - lz_text.get_height() // 2))

    # Windows.
    win_w = max(9, int(r.width * 0.11))
    win_h = max(10, int(r.height * 0.16))
    win_y = r.y + roof_h + 8
    window_glow = 0
    if unload_active:
        window_glow = int((math.sin(t * 7.0) + 1.0) * 30)
    window_color = (82 + window_glow, 104 + window_glow, 132 + window_glow)
    window_color = tuple(max(0, min(255, c)) for c in window_color)
    for i in range(2):
        lx = r.x + 10 + i * (win_w + 8)
        rx = r.right - 10 - win_w - i * (win_w + 8)
        left = pygame.Rect(lx, win_y, win_w, win_h)
        right = pygame.Rect(rx, win_y, win_w, win_h)
        pygame.draw.rect(screen, window_color, left, border_radius=2)
        pygame.draw.rect(screen, window_color, right, border_radius=2)
        pygame.draw.rect(screen, frame_color, left, 1, border_radius=2)
        pygame.draw.rect(screen, frame_color, right, 1, border_radius=2)

    # Loading-bay roller door and stencil to match the smuggled manifest lore.
    bay_w = max(24, int(r.width * 0.26))
    bay_h = max(14, int(r.height * 0.24))
    bay = pygame.Rect(r.right - bay_w - 8, r.bottom - bay_h - 4, bay_w, bay_h)
    pygame.draw.rect(screen, (126, 132, 146), bay, border_radius=2)
    pygame.draw.rect(screen, (34, 38, 48), bay, 1, border_radius=2)
    for y in range(bay.y + 3, bay.bottom, 3):
        pygame.draw.line(screen, (104, 110, 124), (bay.x + 2, y), (bay.right - 2, y), 1)

    tiny_font = get_world_font("consolas", max(8, int(font_size * 0.75)), bold=True)
    lore_text = tiny_font.render("MAIL SORTING EQUIP", True, (196, 146, 92))
    lore_x = entry.centerx - lore_text.get_width() // 2
    lore_y = max(r.y + 4, entry.y - lore_text.get_height() - 5)
    screen.blit(lore_text, (lore_x, lore_y))

    # Two small mail crates near the entry.
    crate_a = pygame.Rect(entry.x - 18, entry.bottom - 8, 10, 8)
    crate_b = pygame.Rect(entry.right + 8, entry.bottom - 8, 10, 8)
    for crate in (crate_a, crate_b):
        pygame.draw.rect(screen, (142, 112, 74), crate, border_radius=1)
        pygame.draw.rect(screen, (58, 42, 28), crate, 1, border_radius=1)
        pygame.draw.line(screen, (98, 74, 48), (crate.x + 2, crate.y + 2), (crate.right - 2, crate.bottom - 2), 1)

    # Animated red/white/blue flag.
    pole_x = r.right - 20
    pole_top = r.y - 18
    pole_bottom = r.bottom - 8
    pygame.draw.line(screen, (228, 228, 236), (pole_x, pole_top), (pole_x, pole_bottom), 3)

    wave_speed = 6.4 if unload_active else 3.5
    wave_amp = (3.2 + unload_pulse * 0.9) if unload_active else 2.0
    base_y = pole_top + 8
    flag_len = max(20, int(r.width * 0.26))
    stripe_h = 3
    stripe_colors = ((190, 32, 32), (236, 236, 236), (36, 72, 190))

    for si, color in enumerate(stripe_colors):
        pts: list[tuple[int, int]] = []
        for dx in range(flag_len + 1):
            phase = (dx / max(1.0, flag_len)) * math.pi * 1.7
            y_off = int(math.sin(t * wave_speed + phase) * wave_amp)
            y = base_y + si * stripe_h + y_off
            pts.append((pole_x + 1 + dx, y))
        pts.append((pole_x + 1 + flag_len, base_y + (si + 1) * stripe_h + 2))
        pts.append((pole_x + 1, base_y + (si + 1) * stripe_h + 2))
        pygame.draw.polygon(screen, color, pts)

    # Flag border for readability.
    pygame.draw.line(screen, frame_color, (pole_x + 1, base_y), (pole_x + 1 + flag_len, base_y + 1), 1)


def _draw_fuselage_wreck(screen: pygame.Surface, r: pygame.Rect, t: float) -> None:
    """Wrecked plane fuselage visual beneath the left (fuselage) elevated airport terminal."""
    bx = r.x - 38
    by = r.bottom + 2
    bw = r.width + 74
    bh = 22
    body = pygame.Rect(bx, by, bw, bh)
    pygame.draw.rect(screen, (84, 78, 70), body, border_radius=5)
    pygame.draw.line(screen, (104, 96, 88), (bx + 14, by + 4), (bx + bw - 22, by + 4), 2)
    pygame.draw.rect(screen, (38, 34, 30), body, 2, border_radius=5)
    # Tail fin (vertical stabiliser at left end).
    tf = ((bx + 8, by), (bx + 4, by - 28), (bx + 26, by))
    pygame.draw.polygon(screen, (72, 66, 58), tf)
    pygame.draw.polygon(screen, (36, 32, 28), tf, 1)
    # Nose cone (tapered right end).
    nc_mid_y = by + bh // 2
    nc = ((bx + bw - 4, by + 3), (bx + bw + 28, nc_mid_y), (bx + bw - 4, by + bh - 3))
    pygame.draw.polygon(screen, (78, 72, 64), nc)
    pygame.draw.polygon(screen, (38, 34, 30), nc, 1)
    # Broken lower wing stub angling down-left from body.
    wx = bx + bw // 3
    wy = by + bh - 5
    wing = ((wx, wy), (wx - 32, wy + 12), (wx - 20, wy + 12), (wx + 6, wy))
    pygame.draw.polygon(screen, (78, 70, 62), wing)
    pygame.draw.polygon(screen, (38, 34, 30), wing, 1)
    # Engine fire (animated).
    fx = bx + int(bw * 0.58)
    fy = by - 1
    flicker = (math.sin(t * 11.5 + 1.3) + 1.0) * 0.5
    fh = int(13 + flicker * 9)
    fw = int(8 + flicker * 5)
    pygame.draw.polygon(screen, (228, 76, 18), [(fx, fy), (fx + fw, fy - fh // 2), (fx, fy - fh), (fx - 4, fy - fh // 2)])
    pygame.draw.polygon(screen, (255, 190, 42), [(fx + 1, fy - 2), (fx + fw // 2 + 1, fy - fh // 2), (fx + 1, fy - fh + 4)])


def _airport_terminal_sign_label(*, is_elevated_terminal: bool, is_fuselage_terminal: bool) -> str:
    if is_elevated_terminal:
        return "" if is_fuselage_terminal else "D5"
    return "D6"


def _draw_compounds(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    mission_id = str(getattr(mission, "mission_id", "")).lower()
    is_airport_special = mission_id in ("airport", "airport_special_ops")
    airport_hostage_state = getattr(mission, "airport_hostage_state", None)
    airport_meal_truck_state = getattr(mission, "airport_meal_truck_state", None)
    airport_hostage_state_name = str(getattr(airport_hostage_state, "state", "")) if airport_hostage_state is not None else ""
    pickup_x = float(getattr(airport_hostage_state, "pickup_x", 1500.0)) if airport_hostage_state is not None else 1500.0
    terminal_pickup_xs = list(getattr(airport_hostage_state, "terminal_pickup_xs", ()) or ()) if airport_hostage_state is not None else []
    terminal_remaining = list(getattr(airport_hostage_state, "terminal_remaining", []) or []) if airport_hostage_state is not None else []
    loading_terminal_index = int(getattr(airport_hostage_state, "loading_terminal_index", -1)) if airport_hostage_state is not None else -1
    truck_load_base = int(getattr(airport_hostage_state, "truck_load_base", 0)) if airport_hostage_state is not None else 0
    loaded_now = int(getattr(airport_hostage_state, "meal_truck_loaded_hostages", 0)) if airport_hostage_state is not None else 0
    loading_total = int(getattr(airport_hostage_state, "loading_terminal_initial_count", 0)) if airport_hostage_state is not None else 0
    loading_left = max(0, loading_total - max(0, loaded_now - truck_load_base))
    t = float(getattr(mission, "elapsed_seconds", 0.0))
    elevated_y = min((float(c.pos.y) for c in mission.compounds), default=99999.0)

    def _terminal_index_for_compound(compound_center_x: float, compound_width: float) -> int:
        if terminal_pickup_xs:
            best_i = -1
            best_d = 1e9
            for i, tx in enumerate(terminal_pickup_xs):
                d = abs(float(tx) - compound_center_x)
                if d < best_d:
                    best_d = d
                    best_i = i
            if best_i >= 0 and best_d <= max(90.0, compound_width * 0.9):
                return best_i
        if abs(compound_center_x - pickup_x) <= max(80.0, compound_width * 0.65):
            return 0
        return -1

    for c in mission.compounds:
        r = pygame.Rect(int(c.pos.x - camera_x), int(c.pos.y), int(c.width), int(c.height))

        # Cull compounds far outside visible range (they're large, use larger margin)
        if not _is_on_screen(float(c.pos.x), camera_x, screen.get_width(), margin=200):
            continue

        if is_airport_special:
            compound_center_x = float(c.pos.x) + float(c.width) * 0.5
            terminal_index = _terminal_index_for_compound(compound_center_x, float(c.width))
            terminal_remaining_count = 0
            if 0 <= terminal_index < len(terminal_remaining):
                terminal_remaining_count = max(0, int(terminal_remaining[terminal_index]))
            if airport_hostage_state_name == "truck_loading" and terminal_index == loading_terminal_index:
                terminal_remaining_count = max(terminal_remaining_count, loading_left)
            is_loading_terminal = terminal_index >= 0 and terminal_index == loading_terminal_index
            boarding_active = is_loading_terminal and airport_hostage_state_name == "truck_loading"
            is_elevated_terminal = abs(float(c.pos.y) - elevated_y) <= 1.0
            if is_elevated_terminal:
                passengers_inside = terminal_remaining_count > 0
            else:
                # Lower compounds illuminate while any assigned passengers still await rescue.
                passengers_inside = _compound_has_awaiting_passengers(mission, c)
            # Fuselage terminal: leftmost elevated compound (wrecked-plane visual).
            is_fuselage_terminal = (
                is_elevated_terminal
                and len(terminal_pickup_xs) >= 2
                and compound_center_x <= min(float(tx) for tx in terminal_pickup_xs) + 55.0
            )
            fuselage_damage_stage = (
                int(get_airport_fuselage_damage_stage(mission)) if is_fuselage_terminal else 0
            )
            fuselage_backdrop_drawn = False
            if is_fuselage_terminal:
                backdrop = _load_airplane_backdrop_sprite()
                if backdrop is not None:
                    backdrop_x = r.x + FUSELAGE_BACKDROP_OFFSET_X
                    backdrop_y = r.y + FUSELAGE_BACKDROP_OFFSET_Y
                    screen.blit(backdrop, (backdrop_x, backdrop_y))
                    fuselage_backdrop_drawn = True

            # Elevated jetway set piece: smoke plume behind roof + intense side flames.
            if is_elevated_terminal:
                smoke_layer = get_volatile_surface(screen.get_width(), screen.get_height(), pygame.SRCALPHA)
                plume_x = r.x + int(r.width * 0.72)
                plume_base_y = r.y + 4
                for i in range(7):
                    phase = t * (0.85 + i * 0.06) + i * 0.55
                    drift_x = int(math.sin(phase) * (4 + i))
                    rise = int((t * 26 + i * 18) % 96)
                    puff_y = plume_base_y - rise
                    puff_r = 8 + i * 2
                    alpha = max(26, 120 - i * 12)
                    shade = 96 + i * 8
                    pygame.draw.circle(
                        smoke_layer,
                        (shade, shade, shade + 6, alpha),
                        (plume_x + drift_x, puff_y),
                        puff_r,
                    )
                screen.blit(smoke_layer, (0, 0))

                flame_core = 0.5 + 0.5 * math.sin(t * 13.0)
                flame_h = 20 + int(flame_core * 12)
                flame_w = 14 + int(flame_core * 6)
                flame_origin_x = r.right - 4
                flame_origin_y = r.bottom - 9

                outer = [
                    (flame_origin_x, flame_origin_y),
                    (flame_origin_x + flame_w, flame_origin_y - flame_h // 2),
                    (flame_origin_x, flame_origin_y - flame_h),
                    (flame_origin_x - 3, flame_origin_y - flame_h // 2),
                ]
                inner = [
                    (flame_origin_x + 1, flame_origin_y - 2),
                    (flame_origin_x + flame_w // 2, flame_origin_y - flame_h // 2),
                    (flame_origin_x + 1, flame_origin_y - flame_h + 4),
                    (flame_origin_x - 1, flame_origin_y - flame_h // 2),
                ]
                ember = [
                    (flame_origin_x + 1, flame_origin_y - 4),
                    (flame_origin_x + max(2, flame_w // 3), flame_origin_y - flame_h // 2),
                    (flame_origin_x + 1, flame_origin_y - flame_h + 8),
                ]
                pygame.draw.polygon(screen, (255, 132, 28), outer)
                pygame.draw.polygon(screen, (255, 202, 62), inner)
                pygame.draw.polygon(screen, (255, 238, 140), ember)

                # Fuselage wreck underlay drawn behind the elevated platform.
                if is_fuselage_terminal and not fuselage_backdrop_drawn:
                    _draw_fuselage_wreck(screen, r, t)

            # Light tan jetway body (fuselage terminal stays transparent).
            body_color = (212, 198, 172) if not c.is_open else (170, 156, 132)
            edge_color = (78, 72, 60)
            roof_color = (194, 184, 164)
            draw_rect = r
            if is_fuselage_terminal:
                square_side = max(42, min(r.width, r.height))
                draw_rect = pygame.Rect(0, 0, square_side, square_side)
                draw_rect.center = r.center
                draw_rect.y = r.bottom - square_side
            if not is_fuselage_terminal:
                pygame.draw.rect(screen, body_color, draw_rect, border_radius=2)
                pygame.draw.rect(screen, edge_color, draw_rect, 2, border_radius=2)

            if is_fuselage_terminal:
                _draw_fuselage_damage_overlay(screen, draw_rect, fuselage_damage_stage, t)

            # Jetway roof cap.
            roof_h = max(6, int(c.height * 0.16))
            roof = pygame.Rect(draw_rect.x - 3, draw_rect.y - roof_h + 2, draw_rect.width + 6, roof_h)
            if not is_fuselage_terminal:
                pygame.draw.rect(screen, roof_color, roof, border_radius=3)
                pygame.draw.rect(screen, (96, 88, 72), roof, 1, border_radius=3)

            # Side panel seams.
            seam_color = (172, 158, 132)
            if not is_fuselage_terminal:
                for i in range(1, 4):
                    sx = draw_rect.x + int((draw_rect.width / 4.0) * i)
                    pygame.draw.line(screen, seam_color, (sx, draw_rect.y + 4), (sx, draw_rect.bottom - 4), 1)

            # Upper porthole row: warm amber flicker when occupied, dark when empty.
            if is_elevated_terminal and not is_fuselage_terminal:
                port_y = draw_rect.y + max(8, int(draw_rect.height * 0.26))
                port_r = max(3, int(draw_rect.width * 0.055))
                n_ports = max(2, min(4, draw_rect.width // 22))
                for pi in range(n_ports):
                    px = draw_rect.centerx if n_ports == 1 else draw_rect.x + 12 + pi * ((draw_rect.width - 24) // max(1, n_ports - 1))
                    if passengers_inside:
                        pf = (math.sin(t * 14.0 + pi * 1.7 + compound_center_x * 0.04) + 1.0) * 0.5
                        port_color = (
                            min(255, int(186 + pf * 64)),
                            min(255, int(140 + pf * 55)),
                            int(32 + pf * 30),
                        )
                    else:
                        port_color = (44, 52, 66)
                    pygame.draw.circle(screen, port_color, (px, port_y), port_r)
                    pygame.draw.circle(screen, (18, 22, 28), (px, port_y), port_r, 1)

            # French door pair near lower center with long vertical windows.
            door_h = max(18, int(draw_rect.height * 0.38))
            door_w_total = max(26, int(draw_rect.width * 0.32))
            door_y = draw_rect.bottom - door_h - 3
            door_x = draw_rect.centerx - door_w_total // 2
            door_area = pygame.Rect(door_x, door_y, door_w_total, door_h)
            leaf_w = max(10, door_w_total // 2 - 1)

            terminal_label = _airport_terminal_sign_label(
                is_elevated_terminal=is_elevated_terminal,
                is_fuselage_terminal=is_fuselage_terminal,
            )
            if terminal_label:
                sign_font = get_world_font("consolas", 11, bold=True)
                sign_text = sign_font.render(terminal_label, True, (236, 240, 248))
                sign_pad_x = 6
                sign_pad_y = 3
                sign_rect = pygame.Rect(
                    0,
                    0,
                    sign_text.get_width() + sign_pad_x * 2,
                    sign_text.get_height() + sign_pad_y * 2,
                )
                sign_rect.midbottom = (door_area.centerx, door_area.y - 4)
                min_x = draw_rect.x + 2
                max_x = draw_rect.right - sign_rect.width - 2
                sign_rect.x = int(max(min_x, min(max_x, sign_rect.x)))
                if sign_rect.y < draw_rect.y + 2:
                    sign_rect.y = draw_rect.y + 2
                pygame.draw.rect(screen, (46, 58, 74), sign_rect, border_radius=2)
                pygame.draw.rect(screen, (132, 152, 178), sign_rect, 1, border_radius=2)
                screen.blit(sign_text, (sign_rect.x + sign_pad_x, sign_rect.y + sign_pad_y))

            # Doors animate in explicit cycles: open -> release small group -> close.
            if boarding_active and airport_hostage_state is not None:
                rate = max(0.2, float(getattr(airport_hostage_state, "transfer_rate_s", 0.5)))
                started = float(getattr(airport_hostage_state, "boarding_started_s", t))
                elapsed = max(0.0, t - started)
                door_cycle_s = max(0.55, rate * 2.4)
                cycle_phase = (elapsed % door_cycle_s) / door_cycle_s
                if cycle_phase < 0.20:
                    door_open_t = cycle_phase / 0.20
                elif cycle_phase < 0.62:
                    door_open_t = 1.0
                elif cycle_phase < 0.82:
                    door_open_t = 1.0 - ((cycle_phase - 0.62) / 0.20)
                else:
                    door_open_t = 0.0
            else:
                door_open_t = 0.0
            slide_px = int(door_open_t * 6.0)

            left_door = pygame.Rect(door_area.x - slide_px, door_area.y, leaf_w, door_h)
            right_door = pygame.Rect(door_area.centerx + slide_px, door_area.y, leaf_w, door_h)
            door_color = (164, 154, 132)
            if not is_fuselage_terminal:
                pygame.draw.rect(screen, door_color, left_door, border_radius=1)
                pygame.draw.rect(screen, door_color, right_door, border_radius=1)
                pygame.draw.rect(screen, edge_color, left_door, 1, border_radius=1)
                pygame.draw.rect(screen, edge_color, right_door, 1, border_radius=1)

            # Window glow: warm amber double-flicker when occupied, dim off-state when empty.
            if passengers_inside:
                breath = (math.sin(t * 6.5) + 1.0) * 0.5
                stutter = (math.sin(t * 21.0 + compound_center_x * 0.08) + 1.0) * 0.5
                mix = breath * 0.6 + stutter * 0.4
                win_fill = (
                    min(255, int(192 + mix * 60)),
                    min(255, int(148 + mix * 52)),
                    int(38 + mix * 28),
                )
            else:
                win_fill = (52, 62, 76)

            # Long windows on each french door leaf.
            left_glass = left_door.inflate(-6, -4)
            right_glass = right_door.inflate(-6, -4)
            if not is_fuselage_terminal:
                pygame.draw.rect(screen, win_fill, left_glass, border_radius=1)
                pygame.draw.rect(screen, win_fill, right_glass, border_radius=1)
                pygame.draw.rect(screen, (34, 42, 52), left_glass, 1, border_radius=1)
                pygame.draw.rect(screen, (34, 42, 52), right_glass, 1, border_radius=1)

            # Additional right-side window beside the french doors.
            side_window = pygame.Rect(door_area.right + 4, door_area.y + 1, max(8, int(r.width * 0.11)), door_h - 2)
            side_window = pygame.Rect(door_area.right + 4, door_area.y + 1, max(8, int(draw_rect.width * 0.11)), door_h - 2)
            side_window.clamp_ip(pygame.Rect(draw_rect.x + 2, draw_rect.y + 2, draw_rect.width - 4, draw_rect.height - 4))
            if not is_fuselage_terminal:
                pygame.draw.rect(screen, win_fill, side_window, border_radius=1)
                pygame.draw.rect(screen, (34, 42, 52), side_window, 1, border_radius=1)

            # Render waiting civilians on top of elevated terminal roofs.
            # For each passenger currently mid-burst through the jetway door, remove one
            # roof silhouette simultaneously — selling the illusion they walked inside.
            if is_elevated_terminal and terminal_remaining_count > 0:
                # Count passengers actively walking through the door right now.
                active_in_burst = 0
                if boarding_active and door_open_t > 0.05 and airport_hostage_state is not None:
                    _rb = max(0.2, float(getattr(airport_hostage_state, "transfer_rate_s", 0.5)))
                    _sb = float(getattr(airport_hostage_state, "boarding_started_s", t))
                    _eb = max(0.0, t - _sb)
                    _dcb = max(0.55, _rb * 2.4)
                    _cib = int(_eb / _dcb)
                    _cpb = (_eb % _dcb) / _dcb
                    _gsb = min(max(1, terminal_remaining_count), 1 + ((_cib + int(compound_center_x)) % 3))
                    for _ib in range(_gsb):
                        _lpb = (_cpb - 0.22 - _ib * 0.14) / 0.36
                        if 0.0 <= _lpb <= 1.0:
                            active_in_burst += 1
                roof_count = max(0, terminal_remaining_count - active_in_burst)
                max_roof_slots = max(2, min(6, int(r.width // 14)))
                visible_on_roof = min(roof_count, max_roof_slots)
                if visible_on_roof > 0:
                    span_left = roof.x + 8
                    span_right = roof.right - 8
                    if visible_on_roof <= 1:
                        roof_positions = [r.centerx]
                    else:
                        spacing = (span_right - span_left) / float(max(1, visible_on_roof - 1))
                        roof_positions = [int(span_left + i * spacing) for i in range(visible_on_roof)]
                    roof_feet_y = roof.bottom - 1
                    for i, px in enumerate(roof_positions):
                        _draw_stick_figure_passenger(
                            screen,
                            px,
                            roof_feet_y,
                            i + terminal_index * 17,
                            t,
                        )

            # During elevated boarding, release passengers only through open jetway doors.
            if boarding_active and airport_hostage_state is not None:
                rate = max(0.2, float(getattr(airport_hostage_state, "transfer_rate_s", 0.5)))
                started = float(getattr(airport_hostage_state, "boarding_started_s", t))
                elapsed = max(0.0, t - started)
                door_cycle_s = max(0.55, rate * 2.4)
                cycle_idx = int(elapsed / door_cycle_s)
                cycle_phase = (elapsed % door_cycle_s) / door_cycle_s

                facing_right = bool(getattr(airport_meal_truck_state, "facing_right", True))
                move_dir = 1 if facing_right else -1
                start_x = door_area.centerx
                front_x = start_x + move_dir * 22
                group_size = min(max(1, terminal_remaining_count), 1 + ((cycle_idx + int(compound_center_x)) % 3))

                if door_open_t > 0.05:
                    for i in range(group_size):
                        local_phase = (cycle_phase - 0.22 - i * 0.14) / 0.36
                        if local_phase < 0.0 or local_phase > 1.0:
                            continue

                        px = int(start_x + move_dir * (front_x - start_x) * local_phase)
                        py = door_area.bottom - 1 - (i % 2)

                        # Tiny passenger silhouette (head + torso + legs).
                        pygame.draw.circle(screen, (255, 255, 255), (px, py - 10), 2)
                        pygame.draw.line(screen, (250, 250, 250), (px, py - 8), (px, py - 3), 2)
                        leg_swing = -1 if math.sin(t * 10.0 + i * 0.8) > 0 else 1
                        pygame.draw.line(screen, (250, 250, 250), (px, py - 3), (px - leg_swing, py), 1)
                        pygame.draw.line(screen, (250, 250, 250), (px, py - 3), (px + leg_swing, py), 1)
                        pygame.draw.circle(screen, (30, 34, 40), (px, py - 10), 2, 1)

                # After the burst exits, keep a tiny group visible in front of the compound.
                if cycle_phase >= 0.60 and cycle_phase <= 0.96:
                    settled = min(2, group_size)
                    for i in range(settled):
                        px = int(front_x + move_dir * i * 7)
                        py = door_area.bottom - 1 - (i % 2)
                        pygame.draw.circle(screen, (255, 255, 255), (px, py - 10), 2)
                        pygame.draw.line(screen, (250, 250, 250), (px, py - 8), (px, py - 3), 2)
                        pygame.draw.line(screen, (250, 250, 250), (px, py - 3), (px - 1, py), 1)
                        pygame.draw.line(screen, (250, 250, 250), (px, py - 3), (px + 1, py), 1)
                        pygame.draw.circle(screen, (30, 34, 40), (px, py - 10), 2, 1)

            # Preserve destroyed/open gameplay readability.
            if c.is_open:
                breach = pygame.Rect(r.centerx - 14, r.bottom - 16, 28, 16)
                pygame.draw.rect(screen, (52, 48, 42), breach)
                pygame.draw.rect(screen, (92, 84, 70), breach, 1)
            continue

        color = (150, 112, 68) if not c.is_open else (118, 92, 58)

        # Main bunker body.
        pygame.draw.rect(screen, color, r, border_radius=2)
        pygame.draw.rect(screen, (26, 26, 26), r, 2, border_radius=2)

        # Roof cap to make compounds read as fortified bunkers.
        roof_h = max(6, int(c.height * 0.14))
        roof = pygame.Rect(r.x - 4, r.y - roof_h + 1, r.width + 8, roof_h)
        pygame.draw.rect(screen, (98, 84, 58), roof, border_radius=3)
        pygame.draw.rect(screen, (36, 36, 36), roof, 1, border_radius=3)

        # Vent slits / panel lines.
        slit_y = r.y + max(4, r.height // 4)
        for i in range(3):
            sx = r.x + 8 + i * max(12, r.width // 4)
            pygame.draw.line(screen, (78, 62, 40), (sx, slit_y), (sx + 10, slit_y), 2)

        # Corner turret domes.
        turret_r = max(3, min(6, r.height // 5))
        turret_y = roof.y + roof_h // 2
        left_turret_x = r.x + 8
        right_turret_x = r.right - 8
        pygame.draw.circle(screen, (92, 102, 96), (left_turret_x, turret_y), turret_r)
        pygame.draw.circle(screen, (92, 102, 96), (right_turret_x, turret_y), turret_r)
        pygame.draw.circle(screen, (32, 32, 32), (left_turret_x, turret_y), turret_r, 1)
        pygame.draw.circle(screen, (32, 32, 32), (right_turret_x, turret_y), turret_r, 1)

        if c.is_open:
            gap = pygame.Rect(r.centerx - 12, r.bottom - 15, 24, 15)
            pygame.draw.rect(screen, (35, 35, 35), gap)
            pygame.draw.rect(screen, (70, 70, 70), gap, 1)


def _draw_airport_lz_tower(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    bg_asset = str(getattr(mission, "bg_asset", "")).lower()
    if "airport" not in bg_asset and "mission2" not in bg_asset:
        return

    # Keep the tower in the bus unload LZ neighborhood (bus stop_x is ~500).
    tower_world_x = 620
    compounds = list(getattr(mission, "compounds", []))
    if compounds:
        ground_y = int(max(float(c.pos.y) + float(c.height) for c in compounds))
    else:
        ground_y = int(float(getattr(mission.base.pos, "y", 400.0)) + float(getattr(mission.base, "height", 44.0)))

    t = float(getattr(mission, "elapsed_seconds", 0.0))
    x = int(tower_world_x - camera_x)
    # Cull tower if far outside visible range
    if not _is_on_screen(float(tower_world_x), camera_x, screen.get_width(), margin=250):
        return
    

    # Tower footing and apron pad.
    apron = pygame.Rect(x - 56, ground_y - 7, 112, 7)
    pygame.draw.rect(screen, (108, 112, 122), apron, border_radius=2)
    pygame.draw.rect(screen, (36, 40, 48), apron, 1, border_radius=2)

    footing = pygame.Rect(x - 24, ground_y - 18, 48, 18)
    pygame.draw.rect(screen, (130, 136, 148), footing, border_radius=3)
    pygame.draw.rect(screen, (38, 42, 50), footing, 1, border_radius=3)

    # Adjacent low terminal block aligned so the bus stops in front of its facade.
    terminal = pygame.Rect(x - 182, ground_y - 27, 132, 28)
    pygame.draw.rect(screen, (142, 148, 160), terminal, border_radius=3)
    pygame.draw.rect(screen, (36, 40, 48), terminal, 1, border_radius=3)

    terminal_roof = pygame.Rect(terminal.x - 4, terminal.y - 7, terminal.width + 8, 7)
    pygame.draw.rect(screen, (124, 130, 142), terminal_roof, border_radius=2)
    pygame.draw.rect(screen, (34, 38, 46), terminal_roof, 1, border_radius=2)

    for i in range(6):
        win = pygame.Rect(terminal.x + 8 + i * 14, terminal.y + 8, 10, 10)
        pygame.draw.rect(screen, (108, 146, 184), win, border_radius=1)
        pygame.draw.rect(screen, (24, 28, 34), win, 1, border_radius=1)

    # Main tapered shaft.
    shaft_bottom_y = ground_y - 18
    shaft_top_y = shaft_bottom_y - 128
    shaft_points = [
        (x - 14, shaft_bottom_y),
        (x + 14, shaft_bottom_y),
        (x + 7, shaft_top_y),
        (x - 7, shaft_top_y),
    ]
    pygame.draw.polygon(screen, (166, 172, 186), shaft_points)
    pygame.draw.polygon(screen, (42, 46, 54), shaft_points, 2)

    # Vertical panel seams to avoid a flat silhouette.
    pygame.draw.line(screen, (144, 150, 164), (x - 5, shaft_bottom_y - 2), (x - 2, shaft_top_y + 4), 1)
    pygame.draw.line(screen, (144, 150, 164), (x + 5, shaft_bottom_y - 2), (x + 2, shaft_top_y + 4), 1)

    # Mid-ring platform and neck (Mehrabad-like broad cabin support).
    ring = pygame.Rect(x - 26, shaft_top_y - 8, 52, 9)
    pygame.draw.rect(screen, (106, 114, 126), ring, border_radius=2)
    pygame.draw.rect(screen, (36, 40, 48), ring, 1, border_radius=2)

    neck = pygame.Rect(x - 12, shaft_top_y - 24, 24, 16)
    pygame.draw.rect(screen, (148, 156, 170), neck, border_radius=2)
    pygame.draw.rect(screen, (36, 40, 48), neck, 1, border_radius=2)

    # Glazed control cab in an upside-down trapezoid to match Tehran tower profile.
    cab_top_y = shaft_top_y - 46
    cab_bottom_y = shaft_top_y - 16
    cab_points = [
        (x - 44, cab_top_y),
        (x + 44, cab_top_y),
        (x + 30, cab_bottom_y),
        (x - 30, cab_bottom_y),
    ]
    pygame.draw.polygon(screen, (158, 168, 184), cab_points)
    pygame.draw.polygon(screen, (30, 34, 42), cab_points, 2)

    # Cabin glazing band.
    # Cabin glazing band.
    # Flicker the centre window amber when mission tech is waiting at the LZ for pickup.
    tech_state_obj = getattr(mission, "mission_tech", None)
    tech_waiting_at_lz = (
        tech_state_obj is not None
        and str(getattr(tech_state_obj, "state", "")) == "waiting_at_lz"
    )
    flicker_intensity = (math.sin(t * 8.0) + 1.0) * 0.5  # 0..1 at 4 Hz
    window_color = (102, 146, 186)
    win_y = cab_top_y + 10
    for i in range(7):
        wx = x - 32 + i * 10
        win = pygame.Rect(wx, win_y, 8, 9)
        if tech_waiting_at_lz and i == 3:
            r_c = int(200 + 55 * flicker_intensity)
            g_c = int(140 + 60 * flicker_intensity)
            win_fill = (r_c, g_c, 40)
        else:
            win_fill = window_color
        pygame.draw.rect(screen, win_fill, win, border_radius=1)
        pygame.draw.rect(screen, (26, 30, 36), win, 1, border_radius=1)

    # Roof cap plus a small radar deck.
    roof = pygame.Rect(x - 26, cab_top_y - 8, 52, 8)
    pygame.draw.rect(screen, (132, 138, 152), roof, border_radius=2)
    pygame.draw.rect(screen, (36, 40, 48), roof, 1, border_radius=2)

    radar_deck = pygame.Rect(x - 16, roof.y - 5, 32, 5)
    pygame.draw.rect(screen, (118, 124, 138), radar_deck, border_radius=2)
    pygame.draw.rect(screen, (34, 38, 46), radar_deck, 1, border_radius=2)

    # Beacon mast and blink light.
    mast_top_y = roof.y - 26
    pygame.draw.line(screen, (214, 216, 224), (x, roof.y), (x, mast_top_y), 2)
    blink = (math.sin(t * 6.0) + 1.0) * 0.5
    beacon_color = (255, int(70 + 150 * blink), int(70 + 120 * blink))
    pygame.draw.circle(screen, beacon_color, (x, mast_top_y), 3)
    pygame.draw.circle(screen, (40, 20, 20), (x, mast_top_y), 3, 1)

    # Ground shadow helps anchor the tall object in side-view.
    shadow = pygame.Rect(x - 22, ground_y - 3, 44, 3)
    pygame.draw.ellipse(screen, (28, 30, 36), shadow)


def _draw_hostages(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    vip_positions: list[tuple[int, int]] = []
    mission_time = float(getattr(mission, "elapsed_seconds", 0.0))
    screen_width = screen.get_width()
    
    for i, h in enumerate(mission.hostages):
        if h.state in (HostageState.IDLE, HostageState.BOARDED):
            continue

        # Cull hostages far outside visible range (keep reasonable margin for context)
        if not _is_on_screen(h.pos.x, camera_x, screen_width, margin=300):
            continue

        x = int(h.pos.x - camera_x)
        y = int(h.pos.y)

        if h.state is HostageState.KIA:
            # KIA: dark red
            color = (80, 0, 0)
            pygame.draw.circle(screen, color, (x, y), 4)
            continue

        # All active passengers use the same animated stick-figure language.
        if h.state is HostageState.FALLING:
            # Tumble animation: rotate the figure around its centre via accumulated fall_angle.
            _draw_stick_figure_passenger_rotated(
                screen, x, y + 4,
                passenger_index=i,
                mission_time=mission_time,
                angle_degrees=float(getattr(h, "fall_angle", 0.0)),
            )
        else:
            _draw_stick_figure_passenger(screen, x, y + 4, passenger_index=i, mission_time=mission_time)

        # Tiny accent for EXITING so it's visually distinct.
        if h.state is HostageState.EXITING:
            pygame.draw.circle(screen, (255, 255, 255), (x, y - 1), 1)

        if getattr(h, "is_vip", False):
            vip_positions.append((x, y))

    # Draw VIP markers at the end so they remain top-most over all hostage indicators.
    for x, y in vip_positions:
        _draw_vip_crown(screen, x, y, mission_time=float(getattr(mission, "elapsed_seconds", 0.0)))


def _draw_vip_crown(screen: pygame.Surface, x: int, y: int, *, mission_time: float) -> None:
    # Position crown directly above the VIP circle marker.
    crown_y = y - 12
    alpha = int(127.5 * (math.sin(mission_time * 5.2) + 1.0))
    alpha = max(36, min(255, alpha))

    crown = get_volatile_surface(20, 14, pygame.SRCALPHA)
    points = [(2, 12), (5, 5), (9, 9), (12, 3), (15, 9), (18, 5), (18, 12)]
    pygame.draw.polygon(crown, (255, 220, 70, alpha), points)
    pygame.draw.polygon(crown, (255, 245, 185, min(255, alpha + 20)), points, 1)
    crown.set_alpha(alpha)
    screen.blit(crown, (x - crown.get_width() // 2, crown_y - crown.get_height() // 2))


def toggle_thermal_mode():
    global thermal_mode
    thermal_mode = not thermal_mode
    setattr(_draw_hostages, "thermal_mode", thermal_mode)


def _draw_engineer_boarding(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
	"""Draw engineer walking between chopper and truck during boarding/unboarding animations."""
	tech_state = getattr(mission, "mission_tech", None)
	if tech_state is None:
		return
	
	# Only draw during active boarding animations
	if tech_state.boarding_animation_state == "idle":
		return
	
	# Calculate animation progress (0.0 to 1.0)
	animation_progress = tech_state.boarding_animation_timer / 0.4  # 0.4s total duration
	animation_progress = min(1.0, max(0.0, animation_progress))
	
	# Interpolate X position only - engineer walks on the ground like hostages
	start_x = tech_state.boarding_start_x
	end_x = tech_state.boarding_end_x
	ground_y = tech_state.boarding_start_y  # Y is constant at ground level
	
	current_x = start_x + (end_x - start_x) * animation_progress
	
	x = int(current_x - camera_x)
	y = int(ground_y)
	
	# Green color for camo representation
	green_color = (34, 177, 76)  # Bright green
	white_color = (255, 255, 255)
	
	# Calculate walking animation cycle (legs alternate)
	walk_cycle = math.sin(animation_progress * math.pi * 8.0)  # 4 complete steps during animation
	leg_frame = 1 if walk_cycle > 0 else 0  # Binary leg position for pixelated look
	
	# Determine facing direction
	dx = end_x - start_x
	facing_right = dx > 0 if abs(dx) > 0 else True
	direction = 1 if facing_right else -1
	
	# Pixel size for retro look
	pixel = 2
	
	# Draw pixelated stick figure from feet up (so feet are at ground level)
	# Feet position is at y (ground level)
	feet_y = y
	
	# Legs (pixelated walking poses) - start from feet
	if leg_frame == 1:
		# Left leg forward
		pygame.draw.rect(screen, white_color, (x - pixel * 2 * direction, feet_y - pixel * 2, pixel, pixel))
		pygame.draw.rect(screen, white_color, (x - pixel * 2 * direction, feet_y - pixel, pixel, pixel))
		pygame.draw.rect(screen, white_color, (x - pixel * direction, feet_y, pixel, pixel))
		# Right leg back
		pygame.draw.rect(screen, white_color, (x + pixel * direction, feet_y, pixel, pixel))
		pygame.draw.rect(screen, white_color, (x + pixel * direction, feet_y - pixel, pixel, pixel))
		pygame.draw.rect(screen, white_color, (x + pixel * direction, feet_y - pixel * 2, pixel, pixel))
	else:
		# Right leg forward
		pygame.draw.rect(screen, white_color, (x + pixel * 2 * direction, feet_y - pixel * 2, pixel, pixel))
		pygame.draw.rect(screen, white_color, (x + pixel * 2 * direction, feet_y - pixel, pixel, pixel))
		pygame.draw.rect(screen, white_color, (x + pixel * direction, feet_y, pixel, pixel))
		# Left leg back
		pygame.draw.rect(screen, white_color, (x - pixel * direction, feet_y, pixel, pixel))
		pygame.draw.rect(screen, white_color, (x - pixel * direction, feet_y - pixel, pixel, pixel))
		pygame.draw.rect(screen, white_color, (x - pixel * direction, feet_y - pixel * 2, pixel, pixel))
	
	# Body (vertical pixels) - from hips up
	hip_y = feet_y - pixel * 3
	for i in range(4):
		body_y = hip_y - i * pixel
		pygame.draw.rect(screen, white_color, (x - 1, body_y, pixel, pixel))
	
	# Head (2x2 pixel block) at top
	head_y = hip_y - pixel * 4
	pygame.draw.rect(screen, green_color, (x - pixel, head_y - pixel, pixel * 2, pixel * 2))
	pygame.draw.rect(screen, white_color, (x - pixel, head_y - pixel, pixel * 2, pixel * 2), 1)
	
	# Arms (2 pixels each, animated) - positioned at shoulder level
	arm_y = hip_y - pixel * 2
	if leg_frame == 1:
		# Left arm forward, right arm back
		pygame.draw.rect(screen, white_color, (x - pixel * 2 * direction, arm_y, pixel, pixel))
		pygame.draw.rect(screen, white_color, (x - pixel * 3 * direction, arm_y + pixel, pixel, pixel))
		pygame.draw.rect(screen, white_color, (x + pixel * direction, arm_y, pixel, pixel))
		pygame.draw.rect(screen, white_color, (x + pixel * 2 * direction, arm_y - pixel, pixel, pixel))
	else:
		# Right arm forward, left arm back
		pygame.draw.rect(screen, white_color, (x + pixel * 2 * direction, arm_y, pixel, pixel))
		pygame.draw.rect(screen, white_color, (x + pixel * 3 * direction, arm_y + pixel, pixel, pixel))
		pygame.draw.rect(screen, white_color, (x - pixel * direction, arm_y, pixel, pixel))
		pygame.draw.rect(screen, white_color, (x - pixel * 2 * direction, arm_y - pixel, pixel, pixel))


def _draw_engineer_wrench_indicator(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
	"""Draw wrench indicator when engineer is deployed in the meal truck.
	
	Positioned above the engineer's location (above the green boarding circle),
	similar to how VIP crown is positioned above VIP hostage.
	"""
	tech_state = getattr(mission, "mission_tech", None)
	meal_truck_state = getattr(mission, "meal_truck", None)
	
	if tech_state is None or meal_truck_state is None:
		return
	
	# Only show wrench when engineer is in truck (not on chopper)
	if tech_state.state == "on_chopper":
		return
	
	# Position wrench directly above the engineer's location (12px above, like VIP crown)
	engineer_x = int(meal_truck_state.x - camera_x)
	engineer_y = int(meal_truck_state.y)
	wrench_y = engineer_y - 14
	
	# Draw wrench on a surface for proper centering (similar to VIP crown)
	wrench_surf = get_volatile_surface(16, 14, pygame.SRCALPHA)
	wx, wy = 8, 7  # Center of surface
	
	# Draw wrench symbol using simple shapes centered on surface
	# Wrench handle (diagonal line)
	pygame.draw.line(wrench_surf, (200, 100, 50), (wx - 6, wy + 4), (wx + 6, wy - 4), 2)
	# Wrench head (circle)
	pygame.draw.circle(wrench_surf, (200, 100, 50), (wx - 7, wy + 5), 3)
	# Wrench mouth (small arc)
	pygame.draw.arc(wrench_surf, (200, 100, 50), pygame.Rect(wx + 2, wy - 3, 7, 7), 0, math.pi/2, 2)
	
	# Blit centered above engineer position (like VIP crown)
	screen.blit(wrench_surf, (engineer_x - wrench_surf.get_width() // 2, wrench_y - wrench_surf.get_height() // 2))


def _draw_projectiles(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    screen_width = screen.get_width()
    
    for p in mission.projectiles:
        if not bool(getattr(p, "alive", False)):
            continue
        
        # Cull projectiles outside visible range
        if not _is_on_screen(p.pos.x, camera_x, screen_width, margin=100):
            continue
            
        x = int(p.pos.x - camera_x)
        y = int(p.pos.y)
        # Barak MRAD missile: draw as a large missile with flame and smoke, rotated by current_angle
        if getattr(p, "is_barak_missile", False):
            missile_len = 34
            missile_w = 6
            surf_w = 32
            surf_h = 48
            missile_surf = get_volatile_surface(surf_w, surf_h, pygame.SRCALPHA)
            cx, cy = surf_w // 2, surf_h // 2
            # Draw missile body (white)
            body_rect = pygame.Rect(cx - missile_w // 2, cy - missile_len, missile_w, missile_len)
            pygame.draw.rect(missile_surf, (230, 230, 230), body_rect)
            # Draw missile tip (red)
            pygame.draw.polygon(missile_surf, (200, 40, 40), [
                (cx, cy - missile_len - 6),
                (cx - missile_w // 2, cy - missile_len),
                (cx + missile_w // 2, cy - missile_len),
            ])
            # Draw fins (gray)
            pygame.draw.polygon(missile_surf, (120, 120, 120), [
                (cx - missile_w // 2, cy - missile_len + 8),
                (cx - missile_w, cy - missile_len + 16),
                (cx - missile_w // 2, cy - missile_len + 16),
            ])
            pygame.draw.polygon(missile_surf, (120, 120, 120), [
                (cx + missile_w // 2, cy - missile_len + 8),
                (cx + missile_w, cy - missile_len + 16),
                (cx + missile_w // 2, cy - missile_len + 16),
            ])
            # Draw propulsion flame (orange/yellow)
            flame_colors = [(255, 200, 40), (255, 120, 0)]
            for i, color in enumerate(flame_colors):
                flame_len = 10 + i * 4
                flame_w = missile_w - i * 2
                pygame.draw.ellipse(
                    missile_surf, color,
                    (cx - flame_w // 2, cy + 2 + i * 2, flame_w, flame_len)
                )
            # Always rotate sprite by (current_angle - 90deg) so it appears horizontal in all phases
            angle_rad = getattr(p, "current_angle", math.pi/2) - math.pi/2
            angle_deg = -math.degrees(angle_rad)
            rotated = pygame.transform.rotate(missile_surf, angle_deg)
            rot_rect = rotated.get_rect(center=(x, y))
            screen.blit(rotated, rot_rect)
            # Optionally: draw smoke (handled as particles for realism)
            continue
        if p.kind is ProjectileKind.BULLET:
            pygame.draw.circle(screen, (240, 240, 240), (x, y), 2)
        elif p.kind in (ProjectileKind.ENEMY_BULLET, ProjectileKind.ENEMY_ARTILLERY):
            pygame.draw.circle(screen, (200, 40, 40), (x, y), 2)
        else:
            pygame.draw.circle(screen, (35, 35, 35), (x, y), 4)


def _draw_enemies(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    ground_y = mission.base.pos.y + mission.base.height
    t = float(getattr(mission, "elapsed_seconds", 0.0))
    screen_width = screen.get_width()

    for e in mission.enemies:
        # Cull enemies outside visible range + margin
        if not _is_on_screen(e.pos.x, camera_x, screen_width, margin=150):
            continue
            
        if e.kind is EnemyKind.TANK:
            # Load and draw karrar.png sprite
            img = get_enemy_image('karrar.png')
            img_rect = img.get_rect()
            
            # Position tank at ground level, centered on e.pos.x
            x = int(e.pos.x - camera_x)
            y = int(ground_y - img_rect.height)
            screen.blit(img, (x - img_rect.width // 2, y))
            
            # Turret overlay using e.turret_angle (draw over the sprite)
            # Airport mission gets tan turret with 2x length
            is_airport = getattr(mission, "mission_id", "").lower() in ("airport", "airport_special_ops")
            turret_length = 48 if is_airport else 24
            turret_color = (180, 150, 110) if is_airport else (28, 30, 28)  # Darker tan for airport, dark for others
            turret_base = (x, y + img_rect.height // 3)  # Position turret at top third of sprite
            
            # Turret barrel indicator
            angle = getattr(e, 'turret_angle', 0.0)
            turret_tip = (
                int(turret_base[0] + turret_length * math.cos(angle)),
                int(turret_base[1] + turret_length * math.sin(angle))
            )
            pygame.draw.line(screen, turret_color, turret_base, turret_tip, 3)

            # Pre-fire tell: subtle amber pulse at the muzzle before a tank shot.
            if getattr(e, "fire_tell_seconds", 0.0) > 0.0:
                tell_r = 4 + int((math.sin(t * 24.0) + 1.0) * 1.5)
                pygame.draw.circle(screen, (255, 200, 80), turret_tip, tell_r)

            # Shot confirmation: brief bright muzzle flash.
            if getattr(e, "muzzle_flash_seconds", 0.0) > 0.0:
                pygame.draw.circle(screen, (255, 240, 170), turret_tip, 6)
                pygame.draw.circle(screen, (255, 120, 80), turret_tip, 3)

        elif e.kind is EnemyKind.BARAK_MRAD:
            # Draw the MRAP vehicle sprite
            img = get_enemy_image('mrap-vehicle.png')
            img_rect = img.get_rect()
            x = int(e.pos.x - camera_x)
            y = int(ground_y - img_rect.height)
            screen.blit(img, (x - img_rect.width // 2, y))

            max_health = float(getattr(e, "max_health", 0.0))
            if max_health <= 0.0:
                max_health = max(1.0, float(getattr(mission.tuning, "barak_health", 143.0)))
            health = max(0.0, float(getattr(e, "health", max_health)))
            damage_ratio = max(0.0, min(1.0, 1.0 - (health / max_health)))

            if damage_ratio > 0.0:
                smoke_count = 1 + int(damage_ratio * 4.0)
                smoke_origin_x = x - 10
                smoke_origin_y = y + 7
                smoke_surf = get_volatile_surface(screen.get_width(), screen.get_height(), pygame.SRCALPHA)
                for si in range(smoke_count):
                    wobble = math.sin(t * (3.2 + si * 0.45) + si * 1.73)
                    puff_x = int(smoke_origin_x + wobble * (5.0 + 2.0 * damage_ratio))
                    puff_y = int(smoke_origin_y - (si * 5 + 4 + damage_ratio * 5.0))
                    puff_r = int(4 + damage_ratio * 6.0 + (si % 2))
                    puff_a = int(80 + damage_ratio * 90.0)
                    pygame.draw.circle(smoke_surf, (46, 46, 46, puff_a), (puff_x, puff_y), puff_r)
                screen.blit(smoke_surf, (0, 0))

            # Engine-front fire breakout once BARAK health drops to 70% or lower.
            if health <= max_health * 0.70:
                flame_phase = 0.55 + 0.45 * math.sin(t * 11.0)
                flame_x = x + 18
                flame_y = y + img_rect.height - 12
                outer_r = max(3, int(4 + flame_phase * 2))
                inner_r = max(1, outer_r - 2)
                pygame.draw.circle(screen, (255, int(130 + 70 * flame_phase), 62), (flame_x, flame_y), outer_r)
                pygame.draw.circle(screen, (255, 218, 120), (flame_x, flame_y), inner_r)

            # Draw the launcher (rectangle) if deploying or later
            if getattr(e, "mrad_state", None) in BARAK_LAUNCHER_VISIBLE_STATES:
                # Launcher base position: on top of vehicle, offset 40px left and 8px up
                base_x = x - 40
                base_y = y + 18 - 8 - 10  # raise by 10 pixels
                launcher_len = 70  # twice as long as before (152*2)
                launcher_w = 18      # half as long as before (8/2)
                angle = getattr(e, "launcher_angle", 0.0)
                ext_progress = getattr(e, "launcher_ext_progress", 0.0)
                # Main launcher rectangle (rotates)
                rect = pygame.Rect(0, 0, launcher_len, launcher_w)
                rect.center = (base_x + (launcher_len/2) * math.cos(-angle)/2, base_y - (launcher_len/2) * math.sin(-angle)/2)
                launcher_surf = get_volatile_surface(launcher_len, launcher_w, pygame.SRCALPHA)
                army_green = (80, 81, 63)        # #50513f html color code
                dark_green = (60, 90, 30)        # outline
                pygame.draw.rect(launcher_surf, army_green, (0, 0, launcher_len, launcher_w))
                pygame.draw.rect(launcher_surf, dark_green, (0, 0, launcher_len, launcher_w), 2)
                # Add simple texture: horizontal lines and a vertical band
                texture_color = (106, 113, 81)  # #6a7151 html color code
                for i in range(2, launcher_w-2, 4):
                    pygame.draw.line(launcher_surf, texture_color, (2, i), (launcher_len-2, i), 1)
                # Vertical band near the base
                band_color = (100, 120, 60)
                band_w = max(2, launcher_len // 16)
                pygame.draw.rect(launcher_surf, band_color, (4, 2, band_w, launcher_w-4))
                # Barrel extension (thinner, animates out)
                ext_max_len = 176  # twice as long as before (88*2)
                ext_len = int(ext_max_len * ext_progress)
                ext_w = 2  # half as long as before (4/2)
                if ext_len > 0:
                    pygame.draw.rect(launcher_surf, (180, 180, 180), (launcher_len-2, (launcher_w-ext_w)//2, ext_len, ext_w))
                    pygame.draw.rect(launcher_surf, (60, 60, 60), (launcher_len-2, (launcher_w-ext_w)//2, ext_len, ext_w), 1)
                # Rotate the surface
                rotated = pygame.transform.rotate(launcher_surf, math.degrees(angle))
                rot_rect = rotated.get_rect(center=rect.center)
                screen.blit(rotated, rot_rect)

        elif e.kind is EnemyKind.JET:
            x = int(e.pos.x - camera_x)
            y = int(e.pos.y)
            direction = 1 if e.vel.x >= 0 else -1
            pygame.draw.polygon(
                screen,
                (35, 35, 35),
                [(x, y), (x - 20 * direction, y - 8), (x - 20 * direction, y + 8)],
            )

        elif e.kind is EnemyKind.AIR_MINE:
            x = int(e.pos.x - camera_x)
            y = int(e.pos.y)
            _draw_air_mine(screen, x, y, t)


def _draw_air_mine(screen: pygame.Surface, x: int, y: int, t: float) -> None:
    # Telegraph ring: pulsing outline.
    pulse = 0.5 + 0.5 * math.sin(t * 6.0)
    ring_radius = int(16 + pulse * 7)
    ring_alpha = int(70 + pulse * 120)
    ring_size = ring_radius * 2 + 8

    ring = get_volatile_surface(ring_size, ring_size, pygame.SRCALPHA)
    cx = ring_size // 2
    cy = ring_size // 2
    pygame.draw.circle(ring, (240, 240, 240, ring_alpha), (cx, cy), ring_radius, 2)
    screen.blit(ring, (x - cx, y - cy))

    # "Sputnik" core: red orb with spikes.
    core_r = 9
    pygame.draw.circle(screen, (200, 40, 40), (x, y), core_r)
    pygame.draw.circle(screen, (25, 25, 25), (x, y), core_r, 2)

    spikes = 8
    spin = t * 1.4
    for i in range(spikes):
        a = (i / float(spikes)) * (math.tau) + spin
        sx = int(x + math.cos(a) * (core_r + 1))
        sy = int(y + math.sin(a) * (core_r + 1))
        ex = int(x + math.cos(a) * (core_r + 8))
        ey = int(y + math.sin(a) * (core_r + 8))
        pygame.draw.line(screen, (25, 25, 25), (sx, sy), (ex, ey), 2)

    # Blinking inner dot.


def _draw_supply_drops(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    manager = getattr(mission, "supply_drops", None)
    drops = getattr(manager, "drops", None)
    if not drops:
        return

    t = float(getattr(mission, "elapsed_seconds", 0.0))
    for d in drops:
        x = int(float(getattr(d, "pos").x) - camera_x)
        y = int(float(getattr(d, "pos").y))

        # Small parachute canopy.
        canopy = pygame.Rect(x - 9, y - 18, 18, 8)
        pygame.draw.ellipse(screen, (230, 230, 236), canopy)
        pygame.draw.ellipse(screen, (40, 40, 45), canopy, 1)
        pygame.draw.line(screen, (210, 210, 220), (x - 6, y - 10), (x - 4, y - 2), 1)
        pygame.draw.line(screen, (210, 210, 220), (x + 6, y - 10), (x + 4, y - 2), 1)

        # Crate body with kind accent color.
        kind = str(getattr(d, "kind", "bullets"))
        ring_phase_offset = 0.0
        ring_alpha = 90
        if kind == "health":
            pulse_t = 0.5 + 0.5 * math.sin((t * 5.8) + float(getattr(d, "age_s", 0.0)) * 3.0)
            dark_red = (110, 20, 20)
            fire_engine_red = (206, 32, 41)
            accent = (
                int(dark_red[0] + (fire_engine_red[0] - dark_red[0]) * pulse_t),
                int(dark_red[1] + (fire_engine_red[1] - dark_red[1]) * pulse_t),
                int(dark_red[2] + (fire_engine_red[2] - dark_red[2]) * pulse_t),
            )
            # Keep ring pulse intentionally out of phase vs. the plus pulse.
            ring_phase_offset = math.pi * 0.5
            ring_alpha = 132
        elif kind == "bullets":
            accent = (95, 175, 255)
        else:
            accent = (255, 168, 78)
        crate = pygame.Rect(x - 6, y - 2, 12, 10)
        pygame.draw.rect(screen, (84, 70, 48), crate, border_radius=2)
        pygame.draw.rect(screen, (30, 24, 18), crate, 1, border_radius=2)
        pygame.draw.rect(screen, accent, pygame.Rect(crate.x + 2, crate.y + 2, crate.width - 4, 2), border_radius=1)

        if kind == "health":
            # Match the HUD fallback health icon language: a simple red plus.
            pygame.draw.rect(screen, accent, pygame.Rect(crate.centerx - 1, crate.y + 2, 2, 6), border_radius=1)
            pygame.draw.rect(screen, accent, pygame.Rect(crate.x + 2, crate.centery - 1, 8, 2), border_radius=1)

        pulse = 0.55 + 0.45 * math.sin((t * 6.0) + float(getattr(d, "age_s", 0.0)) * 4.0 + ring_phase_offset)
        ring_r = int(10 + pulse * 3)
        ring = get_volatile_surface(ring_r * 2 + 4, ring_r * 2 + 4, pygame.SRCALPHA)
        pygame.draw.circle(ring, (accent[0], accent[1], accent[2], ring_alpha), (ring.get_width() // 2, ring.get_height() // 2), ring_r, 1)
        screen.blit(ring, (x - ring.get_width() // 2, y - ring.get_height() // 2))

        if int(t * 5.0) % 2 == 0:
            pygame.draw.circle(screen, (240, 240, 240), (x, y), 2)
        else:
            pygame.draw.circle(screen, (35, 35, 35), (x, y), 2)


def _sentiment_reason_lines(
    *,
    saved: int,
    kia_player: int,
    kia_enemy: int,
    lost_in_transit: int,
    mission_id: str = "",
    route_bonus_awarded: bool = False,
    route_bonus_value: float = 0.0,
    first_route: str = "",
) -> list[str]:
    factors = sentiment_contributions(
        saved=saved,
        kia_player=kia_player,
        kia_enemy=kia_enemy,
        lost_in_transit=lost_in_transit,
    )
    add_saved = factors["saved"]
    sub_kia_player = abs(factors["kia_player"])
    sub_kia_enemy = abs(factors["kia_enemy"])
    sub_lost = abs(factors["lost_in_transit"])

    lines = [
        f"Sentiment factors: +{add_saved:0.1f} rescued civilians",
        f"Sentiment factors: -{sub_kia_player:0.1f} player-caused casualties",
        f"Sentiment factors: -{sub_kia_enemy:0.1f} enemy-caused casualties",
        f"Sentiment factors: -{sub_lost:0.1f} lost in transit",
    ]

    mission_id_norm = str(mission_id or "").strip().lower()
    is_airport = mission_id_norm in ("airport", "airport_special_ops", "airportspecialops", "mission2", "m2")
    route_norm = str(first_route or "").strip().lower()
    bonus_value = max(0.0, float(route_bonus_value or 0.0))
    bonus_awarded = bool(route_bonus_awarded and bonus_value > 0.0)

    if is_airport:
        if bonus_awarded:
            bonus_label = "Riskier Path Bonus" if route_norm == "elevated" else "Route Bonus"
            lines.append(f"Sentiment factors: +{bonus_value:0.1f} {bonus_label}")

        riskier_earned = bonus_awarded and route_norm == "elevated"
        if riskier_earned:
            lines.append("Riskier Path Bonus: EARNED (upper compounds rescued first)")
        else:
            lines.append("Riskier Path Bonus: NOT EARNED (rescue upper compounds first)")

    return lines


def _draw_end(
    screen: pygame.Surface,
    text: str,
    reason: str,
    saved: int,
    boarded: int,
    kia_player: int,
    kia_enemy: int,
    lost_in_transit: int,
    enemies_destroyed: int,
    crashes: int,
    sentiment: float,
    mission_id: str = "",
    route_bonus_awarded: bool = False,
    route_bonus_value: float = 0.0,
    first_route: str = "",
    mission_end_return_seconds: float = 0.0,
) -> None:
    panel = get_volatile_surface(screen.get_width(), screen.get_height(), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 120))
    screen.blit(panel, (0, 0))

    font = get_world_font("consolas", 72, bold=True)
    surf = font.render(text, True, (255, 255, 255))
    rect = surf.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
    screen.blit(surf, rect)

    small = get_world_font("consolas", 22)
    band = sentiment_band_label(sentiment)
    lines = [
        f"Result: {reason}",
        f"Saved: {saved}",
        f"Boarded (not yet unloaded): {boarded}",
        f"KIA (player): {kia_player}",
        f"KIA (by enemy): {kia_enemy}",
        f"Lost in transit: {lost_in_transit}",
        f"Enemies destroyed: {enemies_destroyed}",
        f"Crashes: {crashes}",
        f"Sentiment: {int(sentiment)} ({band})",
    ]
    lines.extend(
        _sentiment_reason_lines(
            saved=saved,
            kia_player=kia_player,
            kia_enemy=kia_enemy,
            lost_in_transit=lost_in_transit,
            mission_id=mission_id,
            route_bonus_awarded=route_bonus_awarded,
            route_bonus_value=route_bonus_value,
            first_route=first_route,
        )
    )

    countdown_line = _countdown_seconds_label(mission_end_return_seconds)
    if countdown_line:
        lines.append(countdown_line)

    # Keep restart prompt anchored to the bottom so it stays visible while stats scroll.
    prompt = small.render("Press Enter (or Start) to restart", True, (235, 235, 235))
    prompt_rect = prompt.get_rect(center=(screen.get_width() // 2, screen.get_height() - 10))
    screen.blit(prompt, prompt_rect)

    # Render debrief stats in a clipped viewport; auto-scroll if content exceeds available height.
    viewport_top = rect.bottom + 21
    bottom_inner_padding = 10
    viewport_bottom = max(viewport_top + 40, prompt_rect.top - bottom_inner_padding)
    viewport_rect = pygame.Rect(20, viewport_top, max(1, screen.get_width() - 40), max(1, viewport_bottom - viewport_top))

    line_step = 28
    top_inner_padding = 10
    content_height = top_inner_padding + len(lines) * line_step + bottom_inner_padding
    max_scroll = max(0.0, float(content_height - viewport_rect.height))

    scroll_offset = 0.0
    if max_scroll > 0.0:
        scroll_speed_px_s = 34.0
        edge_pause_s = 1.1
        one_way_s = max_scroll / scroll_speed_px_s
        cycle_s = (edge_pause_s * 2.0) + (one_way_s * 2.0)
        t = pygame.time.get_ticks() / 1000.0
        phase = t % max(0.001, cycle_s)

        if phase < edge_pause_s:
            scroll_offset = 0.0
        elif phase < edge_pause_s + one_way_s:
            scroll_offset = (phase - edge_pause_s) * scroll_speed_px_s
        elif phase < edge_pause_s + one_way_s + edge_pause_s:
            scroll_offset = max_scroll
        else:
            scroll_offset = max_scroll - (phase - edge_pause_s - one_way_s - edge_pause_s) * scroll_speed_px_s

    previous_clip = screen.get_clip()
    screen.set_clip(viewport_rect)
    y = viewport_rect.top + top_inner_padding + (line_step // 2) - int(scroll_offset)
    for line in lines:
        s = small.render(line, True, (235, 235, 235))
        r = s.get_rect(center=(screen.get_width() // 2, y))
        screen.blit(s, r)
        y += line_step
    screen.set_clip(previous_clip)
