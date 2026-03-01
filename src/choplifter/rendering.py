from __future__ import annotations

import math
import pygame

from .helicopter import Facing, Helicopter


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
