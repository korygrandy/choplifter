from __future__ import annotations

import math
from typing import TYPE_CHECKING
import pygame

from ..game_types import EnemyKind, HostageState, ProjectileKind

if TYPE_CHECKING:
    from ..mission import MissionState


def draw_mission(screen: pygame.Surface, mission: MissionState, *, camera_x: float = 0.0, enable_particles: bool = True) -> None:
    _draw_base(screen, mission, camera_x=camera_x)
    _draw_compounds(screen, mission, camera_x=camera_x)
    _draw_hostages(screen, mission, camera_x=camera_x)
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

    if mission.ended and mission.end_text:
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
        )


def _draw_base(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    r = pygame.Rect(
        int(mission.base.pos.x - camera_x),
        int(mission.base.pos.y),
        int(mission.base.width),
        int(mission.base.height),
    )
    pygame.draw.rect(screen, (60, 60, 75), r, border_radius=8)
    pygame.draw.rect(screen, (210, 210, 210), r, 2, border_radius=8)

    # Simple flag pole marker.
    pole_x = r.right - 26
    pygame.draw.line(screen, (230, 230, 230), (pole_x, r.top + 10), (pole_x, r.bottom - 10), 3)
    pygame.draw.polygon(
        screen,
        (200, 40, 40),
        [(pole_x, r.top + 14), (pole_x + 22, r.top + 22), (pole_x, r.top + 30)],
    )


def _draw_compounds(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    for c in mission.compounds:
        r = pygame.Rect(int(c.pos.x - camera_x), int(c.pos.y), int(c.width), int(c.height))
        color = (160, 120, 70) if not c.is_open else (120, 95, 60)
        pygame.draw.rect(screen, color, r)
        pygame.draw.rect(screen, (30, 30, 30), r, 2)
        if c.is_open:
            gap = pygame.Rect(r.centerx - 10, r.bottom - 14, 20, 14)
            pygame.draw.rect(screen, (35, 35, 35), gap)


def _draw_hostages(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    for h in mission.hostages:
        if h.state in (HostageState.IDLE, HostageState.BOARDED):
            continue

        x = int(h.pos.x - camera_x)
        y = int(h.pos.y)

        if h.state is HostageState.KIA:
            # KIA: dark red
            color = (80, 0, 0)
            pygame.draw.circle(screen, color, (x, y), 4)
            continue

        # Old style: simple person dot (beige with dark outline), or purple for VIP
        if getattr(h, "is_vip", False):
            body_color = (160, 60, 200)  # Purple
        else:
            body_color = (245, 235, 210)  # Beige
        pygame.draw.circle(screen, body_color, (x, y), 5)
        pygame.draw.circle(screen, (25, 25, 25), (x, y), 5, 1)

        # Tiny accent for EXITING so it's visually distinct.
        if h.state is HostageState.EXITING:
            pygame.draw.circle(screen, (255, 255, 255), (x, y - 1), 1)
        # Falling: draw with a blue trail
        if h.state is HostageState.FALLING:
            pygame.draw.line(screen, (80, 180, 255), (x, y-8), (x, y), 2)

        # --- VIP marker (drawn last, always on top) ---
        if getattr(h, "is_vip", False):
            # Draw a gold ring above the VIP's head
            pygame.draw.circle(screen, (255, 215, 0), (x, y - 10), 6, 2)  # gold ring
            # Optionally, add a small white dot in the center for extra highlight
            pygame.draw.circle(screen, (255, 255, 255), (x, y - 10), 2)
def toggle_thermal_mode():
    global thermal_mode
    thermal_mode = not thermal_mode
    setattr(_draw_hostages, "thermal_mode", thermal_mode)


def _draw_projectiles(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    for p in mission.projectiles:
        x = int(p.pos.x - camera_x)
        y = int(p.pos.y)
        if p.kind is ProjectileKind.BULLET:
            pygame.draw.circle(screen, (240, 240, 240), (x, y), 2)
        elif p.kind in (ProjectileKind.ENEMY_BULLET, ProjectileKind.ENEMY_ARTILLERY):
            pygame.draw.circle(screen, (200, 40, 40), (x, y), 2)
        else:
            pygame.draw.circle(screen, (35, 35, 35), (x, y), 4)


def _draw_enemies(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    ground_y = mission.base.pos.y + mission.base.height
    t = float(getattr(mission, "elapsed_seconds", 0.0))

    for e in mission.enemies:
        if e.kind is EnemyKind.TANK:
            # Simple tank block near ground.
            w, h = 44, 18
            r = pygame.Rect(int(e.pos.x - camera_x - w / 2), int(ground_y - h), w, h)
            pygame.draw.rect(screen, (70, 70, 70), r)
            pygame.draw.rect(screen, (25, 25, 25), r, 2)
            # Turret marker.
            pygame.draw.line(screen, (25, 25, 25), (r.centerx, r.top + 3), (r.centerx + 10, r.top - 6), 3)

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

    ring = pygame.Surface((ring_size, ring_size), pygame.SRCALPHA)
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
    if int(t * 5.0) % 2 == 0:
        pygame.draw.circle(screen, (240, 240, 240), (x, y), 2)
    else:
        pygame.draw.circle(screen, (35, 35, 35), (x, y), 2)


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
) -> None:
    panel = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 120))
    screen.blit(panel, (0, 0))

    pygame.font.init()
    font = pygame.font.SysFont("consolas", 72, bold=True)
    surf = font.render(text, True, (255, 255, 255))
    rect = surf.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
    screen.blit(surf, rect)

    small = pygame.font.SysFont("consolas", 22)
    lines = [
        f"Result: {reason}",
        f"Saved: {saved}",
        f"Boarded (not yet unloaded): {boarded}",
        f"KIA (player): {kia_player}",
        f"KIA (by enemy): {kia_enemy}",
        f"Lost in transit: {lost_in_transit}",
        f"Enemies destroyed: {enemies_destroyed}",
        f"Crashes: {crashes}",
        f"Sentiment: {int(sentiment)}",
        "Press Enter (or Start) to restart",
    ]
    y = rect.bottom + 18
    for line in lines:
        s = small.render(line, True, (235, 235, 235))
        r = s.get_rect(center=(screen.get_width() // 2, y))
        screen.blit(s, r)
        y += 28
