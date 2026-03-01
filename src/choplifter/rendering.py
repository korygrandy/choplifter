from __future__ import annotations

import math
import pygame

from .helicopter import Facing, Helicopter
from .mission import HostageState, MissionState, ProjectileKind


_HUD_FONT: pygame.font.Font | None = None


def draw_ground(screen: pygame.Surface, ground_y: float) -> None:
    pygame.draw.rect(screen, (40, 40, 40), pygame.Rect(0, int(ground_y), screen.get_width(), screen.get_height() - int(ground_y)))
    pygame.draw.line(screen, (90, 90, 90), (0, int(ground_y)), (screen.get_width(), int(ground_y)), 2)


def draw_helicopter(screen: pygame.Surface, helicopter: Helicopter) -> None:
    # Minimal placeholder: a rotated body + rotor line.
    body_w, body_h = 70, 22
    x = int(helicopter.pos.x)
    y = int(helicopter.pos.y)

    body = pygame.Surface((body_w, body_h), pygame.SRCALPHA)
    body.fill((0, 0, 0, 0))
    pygame.draw.rect(body, (60, 190, 80), pygame.Rect(0, 0, body_w, body_h), border_radius=6)

    # Nose marker depending on facing.
    if helicopter.facing is Facing.LEFT:
        pygame.draw.circle(body, (220, 220, 220), (8, body_h // 2), 4)
    elif helicopter.facing is Facing.RIGHT:
        pygame.draw.circle(body, (220, 220, 220), (body_w - 8, body_h // 2), 4)
    else:
        pygame.draw.circle(body, (220, 220, 220), (body_w // 2, body_h // 2), 4)

    rotated = pygame.transform.rotate(body, -helicopter.tilt_deg)
    rect = rotated.get_rect(center=(x, y))
    screen.blit(rotated, rect)

    # Rotor: draw a line above the body, rotated to match.
    rotor_len = 90
    rotor_offset = 18
    angle_rad = math.radians(-helicopter.tilt_deg)
    cx, cy = rect.centerx, rect.centery - rotor_offset
    dx = math.cos(angle_rad) * (rotor_len / 2)
    dy = math.sin(angle_rad) * (rotor_len / 2)
    pygame.draw.line(screen, (30, 30, 30), (cx - dx, cy - dy), (cx + dx, cy + dy), 4)


def draw_mission(screen: pygame.Surface, mission: MissionState) -> None:
    _draw_base(screen, mission)
    _draw_compounds(screen, mission)
    _draw_hostages(screen, mission)
    _draw_projectiles(screen, mission)

    if mission.ended and mission.end_text:
        boarded = sum(1 for h in mission.hostages if h.state is HostageState.BOARDED)
        _draw_end(screen, mission.end_text, mission.stats.saved, boarded, mission.stats.kia_by_player)


def draw_hud(screen: pygame.Surface, mission: MissionState, helicopter: Helicopter) -> None:
    global _HUD_FONT
    if _HUD_FONT is None:
        pygame.font.init()
        _HUD_FONT = pygame.font.SysFont("consolas", 18)

    font = _HUD_FONT

    boarded = sum(1 for h in mission.hostages if h.state is HostageState.BOARDED)
    saved = mission.stats.saved

    # Minimal always-on guidance so the rescue loop is discoverable.
    lines = [
        f"Objective: save 20 (saved {saved}/20)",
        f"Rescue: shoot compound (Space) → land near hostages → press E to open doors → load {boarded}/16",
        "Unload: land in base zone (flag) → press E to open doors",
    ]

    x = 12
    y = screen.get_height() - 12 - len(lines) * 20
    for i, line in enumerate(lines):
        surf = font.render(line, True, (10, 10, 10))
        # Shadow for readability.
        shadow = font.render(line, True, (255, 255, 255))
        screen.blit(shadow, (x + 1, y + i * 20 + 1))
        screen.blit(surf, (x, y + i * 20))


def _draw_base(screen: pygame.Surface, mission: MissionState) -> None:
    r = pygame.Rect(int(mission.base.pos.x), int(mission.base.pos.y), int(mission.base.width), int(mission.base.height))
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


def _draw_compounds(screen: pygame.Surface, mission: MissionState) -> None:
    for c in mission.compounds:
        r = pygame.Rect(int(c.pos.x), int(c.pos.y), int(c.width), int(c.height))
        color = (160, 120, 70) if not c.is_open else (120, 95, 60)
        pygame.draw.rect(screen, color, r)
        pygame.draw.rect(screen, (30, 30, 30), r, 2)
        if c.is_open:
            gap = pygame.Rect(r.centerx - 10, r.bottom - 14, 20, 14)
            pygame.draw.rect(screen, (35, 35, 35), gap)


def _draw_hostages(screen: pygame.Surface, mission: MissionState) -> None:
    for h in mission.hostages:
        if h.state in (HostageState.IDLE, HostageState.BOARDED, HostageState.SAVED):
            continue

        if h.state is HostageState.KIA:
            pygame.draw.circle(screen, (120, 10, 10), (int(h.pos.x), int(h.pos.y)), 4)
            continue

        pygame.draw.circle(screen, (245, 235, 210), (int(h.pos.x), int(h.pos.y)), 5)
        pygame.draw.circle(screen, (25, 25, 25), (int(h.pos.x), int(h.pos.y)), 5, 1)


def _draw_projectiles(screen: pygame.Surface, mission: MissionState) -> None:
    for p in mission.projectiles:
        if p.kind is ProjectileKind.BULLET:
            pygame.draw.circle(screen, (240, 240, 240), (int(p.pos.x), int(p.pos.y)), 2)
        else:
            pygame.draw.circle(screen, (35, 35, 35), (int(p.pos.x), int(p.pos.y)), 4)


def _draw_end(screen: pygame.Surface, text: str, saved: int, boarded: int, kia_player: int) -> None:
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
        f"Saved: {saved}",
        f"Boarded (not yet unloaded): {boarded}",
        f"KIA (player): {kia_player}",
    ]
    y = rect.bottom + 18
    for line in lines:
        s = small.render(line, True, (235, 235, 235))
        r = s.get_rect(center=(screen.get_width() // 2, y))
        screen.blit(s, r)
        y += 28
