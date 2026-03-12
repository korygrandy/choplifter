from __future__ import annotations

import math
from typing import TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from ..mission_state import MissionState


_BURN_SPRITE_CACHE: dict[tuple[str, int], pygame.Surface] = {}
_RAIN_STREAK_CACHE: dict[int, pygame.Surface] = {}
_FOG_PUFF_CACHE: dict[int, pygame.Surface] = {}
_WIND_DUST_CACHE: dict[tuple[int, tuple[int, int, int]], pygame.Surface] = {}
_FIRE_PLUME_CACHE: dict[tuple[int, int], pygame.Surface] = {}


def _draw_fx_particles(screen: pygame.Surface, particles: list[object], *, camera_x: float) -> None:
    # Particles are in world-space; apply camera offset.
    for p in particles:
        pos = getattr(p, "pos", None)
        if pos is None:
            continue

        x = int(float(pos.x) - camera_x)
        y = int(float(pos.y))

        age = float(getattr(p, "age", 0.0))
        ttl = float(getattr(p, "ttl", 0.0))
        t = age / max(0.001, ttl)

        kind = str(getattr(p, "kind", "smoke"))
        radius_f = float(getattr(p, "radius", 4.0))
        radius = int(max(1.0, radius_f))

        intensity = float(getattr(p, "intensity", 1.0))
        if not math.isfinite(intensity):
            intensity = 1.0
        intensity = max(0.0, intensity)

        if kind == "ember":
            alpha = int(240 * (1.0 - t) * intensity)
            sprite = _get_burn_sprite("ember", radius)
            sprite.set_alpha(alpha)
            screen.blit(sprite, (x - sprite.get_width() // 2, y - sprite.get_height() // 2))
        elif kind == "smoke":
            alpha = int(120 * (1.0 - t) * (1.0 - t) * intensity)
            radius = int(max(1.0, radius_f * (1.0 + 0.45 * t)))
            color = getattr(p, "color", None)
            def clamp255(v):
                try:
                    return max(0, min(255, int(round(v))))
                except Exception:
                    return 0

            if (
                isinstance(color, tuple)
                and len(color) == 3
                and all(isinstance(c, (int, float)) for c in color)
            ):
                draw_color = tuple(clamp255(c) for c in color) + (clamp255(alpha),)
            else:
                draw_color = (120, 120, 120, clamp255(alpha))
            s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, draw_color, (radius, radius), radius)
            s.set_alpha(clamp255(alpha))
            screen.blit(s, (x - radius, y - radius))
        elif kind == "fire_plume":
            alpha = int(230 * (1.0 - t) * intensity)
            plume_h = int(max(6.0, radius_f * (1.9 + 0.7 * t)))
            plume_w = int(max(4.0, radius_f * (1.0 + 0.35 * t)))

            plume = _get_fire_plume_sprite(plume_w=plume_w, plume_h=plume_h)
            plume.set_alpha(max(0, min(255, alpha)))
            screen.blit(plume, (x - plume.get_width() // 2, y - plume.get_height() // 2))
        else:
            # Fallback for any other kind (future-proofing)
            alpha = int(120 * (1.0 - t) * (1.0 - t) * intensity)
            radius = int(max(1.0, radius_f * (1.0 + 0.45 * t)))
            sprite = _get_burn_sprite(kind, radius)
            sprite.set_alpha(alpha)
            screen.blit(sprite, (x - sprite.get_width() // 2, y - sprite.get_height() // 2))


def draw_jet_trail_particles(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    jet_trails = getattr(mission, "jet_trails", None)
    if jet_trails is None:
        return
    _draw_fx_particles(screen, list(getattr(jet_trails, "particles", [])), camera_x=camera_x)


def draw_dust_storm_particles(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    dust = getattr(mission, "dust_storm", None)
    if dust is None:
        return
    _draw_fx_particles(screen, list(getattr(dust, "particles", [])), camera_x=camera_x)


def draw_explosion_particles(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    explosions = getattr(mission, "explosions", None)
    if explosions is None:
        return
    _draw_fx_particles(screen, list(getattr(explosions, "particles", [])), camera_x=camera_x)


def draw_burning_particles(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    # Particles are in world-space; apply camera offset.
    for p in getattr(mission, "burning").particles:
        x = int(p.pos.x - camera_x)
        y = int(p.pos.y)

        t = p.age / max(0.001, p.ttl)
        if p.kind == "ember":
            alpha = int(220 * (1.0 - t))
            radius = int(max(1.0, p.radius))
            sprite = _get_burn_sprite("ember", radius)
        else:
            # Smoke: fades slower and expands a little.
            alpha = int(160 * (1.0 - t) * (1.0 - t))
            radius = int(max(1.0, p.radius * (1.0 + 0.35 * t)))
            sprite = _get_burn_sprite("smoke", radius)

        if alpha <= 0:
            continue

        sprite.set_alpha(alpha)
        screen.blit(sprite, (x - sprite.get_width() // 2, y - sprite.get_height() // 2))


def draw_flares(screen: pygame.Surface, mission: MissionState, *, camera_x: float = 0.0, enable_particles: bool = True) -> None:
    if not enable_particles:
        return
    flares = getattr(mission, "flares", None)
    if flares is None:
        return
    _draw_fx_particles(screen, list(getattr(flares, "particles", [])), camera_x=camera_x)


def draw_helicopter_damage_fx(
    screen: pygame.Surface,
    mission: MissionState,
    *,
    camera_x: float = 0.0,
    enable_particles: bool = True,
) -> None:
    if not enable_particles:
        return
    fx = getattr(mission, "heli_damage_fx", None)
    if fx is None:
        return
    _draw_fx_particles(screen, list(getattr(fx, "particles", [])), camera_x=camera_x)


def draw_enemy_damage_fx(
    screen: pygame.Surface,
    mission: MissionState,
    *,
    camera_x: float = 0.0,
    enable_particles: bool = True,
) -> None:
    if not enable_particles:
        return
    fx = getattr(mission, "enemy_damage_fx", None)
    if fx is None:
        return
    _draw_fx_particles(screen, list(getattr(fx, "particles", [])), camera_x=camera_x)


def draw_impact_sparks(screen: pygame.Surface, mission: MissionState, *, camera_x: float = 0.0, enable_particles: bool = True) -> None:
    if not enable_particles:
        return
    sparks = getattr(mission, "impact_sparks", None)
    if sparks is None:
        return
    _draw_fx_particles(screen, list(getattr(sparks, "particles", [])), camera_x=camera_x)


def draw_rain_particles(screen: pygame.Surface, rain_system, *, camera_x: float = 0.0) -> None:
    # Draw blue streaks for rain
    for p in getattr(rain_system, "particles", []):
        x = int(p.pos.x - camera_x)
        y = int(p.pos.y)
        t = p.age / max(0.001, p.ttl)
        alpha = int(180 * (1.0 - t))
        if alpha <= 0:
            continue
        color = (120, 180, 255, alpha)
        length = int(12 + 16 * (1.0 - t))
        end_y = y + length
        s = _get_rain_streak_sprite(length=max(1, length), color_rgb=(120, 180, 255))
        s.set_alpha(alpha)
        screen.blit(s, (x - 1, y))


def draw_fog_particles(screen: pygame.Surface, fog_system, *, camera_x: float = 0.0) -> None:
    # Draw large, soft white fog puffs
    for p in getattr(fog_system, "particles", []):
        x = int(p.pos.x - camera_x)
        y = int(p.pos.y)
        t = p.age / max(0.001, p.ttl)
        alpha = int(60 * (1.0 - t) * (1.0 - t))
        if alpha <= 0:
            continue
        radius = int(max(8, p.radius * (1.0 + 0.2 * t)))
        s = _get_fog_puff_sprite(radius=radius)
        s.set_alpha(alpha)
        screen.blit(s, (x - radius, y - radius))


def draw_wind_dust_clouds(screen, mission, *, camera_x=0.0):
    clouds = getattr(mission, "wind_dust_clouds", None)
    if not clouds:
        return
    for c in getattr(clouds, "clouds", []):
        if c.alpha <= 0:
            continue
        x = int(c.pos.x - camera_x)
        y = int(c.pos.y)
        radius = int(c.radius)
        rgb = tuple(int(max(0, min(255, v))) for v in c.color)
        s = _get_wind_dust_sprite(radius=radius, color_rgb=rgb)
        s.set_alpha(c.alpha)
        screen.blit(s, (x - radius, y - radius))


def _get_rain_streak_sprite(*, length: int, color_rgb: tuple[int, int, int]) -> pygame.Surface:
    length = max(1, int(length))
    cached = _RAIN_STREAK_CACHE.get(length)
    if cached is not None:
        return cached

    s = pygame.Surface((3, length), pygame.SRCALPHA)
    pygame.draw.line(s, (color_rgb[0], color_rgb[1], color_rgb[2], 255), (1, 0), (1, length), 2)
    _RAIN_STREAK_CACHE[length] = s
    if len(_RAIN_STREAK_CACHE) > 64:
        _RAIN_STREAK_CACHE.clear()
        _RAIN_STREAK_CACHE[length] = s
    return s


def _get_fog_puff_sprite(*, radius: int) -> pygame.Surface:
    radius = max(1, int(radius))
    cached = _FOG_PUFF_CACHE.get(radius)
    if cached is not None:
        return cached

    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    pygame.draw.circle(s, (220, 220, 220, 255), (radius, radius), radius)
    _FOG_PUFF_CACHE[radius] = s
    if len(_FOG_PUFF_CACHE) > 64:
        _FOG_PUFF_CACHE.clear()
        _FOG_PUFF_CACHE[radius] = s
    return s


def _get_wind_dust_sprite(*, radius: int, color_rgb: tuple[int, int, int]) -> pygame.Surface:
    radius = max(1, int(radius))
    key = (radius, color_rgb)
    cached = _WIND_DUST_CACHE.get(key)
    if cached is not None:
        return cached

    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    pygame.draw.circle(s, (color_rgb[0], color_rgb[1], color_rgb[2], 255), (radius, radius), radius)
    _WIND_DUST_CACHE[key] = s
    if len(_WIND_DUST_CACHE) > 64:
        _WIND_DUST_CACHE.clear()
        _WIND_DUST_CACHE[key] = s
    return s


def _get_fire_plume_sprite(*, plume_w: int, plume_h: int) -> pygame.Surface:
    plume_w = max(1, int(plume_w))
    plume_h = max(1, int(plume_h))
    key = (plume_w, plume_h)
    cached = _FIRE_PLUME_CACHE.get(key)
    if cached is not None:
        return cached

    plume = pygame.Surface((plume_w * 2, plume_h * 2), pygame.SRCALPHA)
    cx = plume.get_width() // 2
    base_y = plume.get_height() - 4

    outer = [
        (cx - plume_w, base_y),
        (cx + plume_w, base_y),
        (cx + max(2, plume_w // 3), base_y - plume_h),
        (cx - max(2, plume_w // 3), base_y - plume_h),
    ]
    inner = [
        (cx - max(2, plume_w // 2), base_y - 1),
        (cx + max(2, plume_w // 2), base_y - 1),
        (cx + max(1, plume_w // 5), base_y - int(plume_h * 0.62)),
        (cx - max(1, plume_w // 5), base_y - int(plume_h * 0.62)),
    ]
    pygame.draw.polygon(plume, (255, 110, 20, 255), outer)
    pygame.draw.polygon(plume, (255, 210, 80, 255), inner)

    _FIRE_PLUME_CACHE[key] = plume
    if len(_FIRE_PLUME_CACHE) > 64:
        _FIRE_PLUME_CACHE.clear()
        _FIRE_PLUME_CACHE[key] = plume
    return plume


def _get_burn_sprite(kind: str, radius: int) -> pygame.Surface:
    radius = max(1, int(radius))
    key = (kind, radius)
    cached = _BURN_SPRITE_CACHE.get(key)
    if cached is not None:
        return cached

    size = radius * 2 + 6
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = size // 2
    cy = size // 2

    if kind == "ember":
        # Small hot spark with bright core.
        pygame.draw.circle(s, (255, 210, 80, 220), (cx, cy), radius)
        pygame.draw.circle(s, (255, 245, 220, 235), (cx, cy), max(1, radius // 2))
    else:
        # Soft smoke puff.
        pygame.draw.circle(s, (55, 55, 55, 46), (cx, cy), radius)
        pygame.draw.circle(s, (75, 75, 75, 62), (cx - max(1, radius // 5), cy), max(1, int(radius * 0.75)))
        pygame.draw.circle(
            s,
            (35, 35, 35, 40),
            (cx + max(1, radius // 6), cy + max(1, radius // 8)),
            max(1, int(radius * 0.60)),
        )

    _BURN_SPRITE_CACHE[key] = s
    return s
