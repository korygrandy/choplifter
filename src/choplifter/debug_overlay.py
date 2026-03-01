from __future__ import annotations

import pygame

from .helicopter import Helicopter


class DebugOverlay:
    def __init__(self) -> None:
        pygame.font.init()
        self._font = pygame.font.SysFont("consolas", 18)

    def draw(self, screen: pygame.Surface, helicopter: Helicopter, fps: float) -> None:
        lines = [
            f"FPS: {fps:0.1f}",
            f"pos: ({helicopter.pos.x:0.1f}, {helicopter.pos.y:0.1f})",
            f"vel: ({helicopter.vel.x:0.2f}, {helicopter.vel.y:0.2f})",
            f"tilt: {helicopter.tilt_deg:0.1f} deg",
            f"facing: {helicopter.facing.name}",
            f"grounded: {helicopter.grounded}",
            f"doors: {'OPEN' if helicopter.doors_open else 'closed'}",
            f"damage: {helicopter.damage:0.1f}",
            f"fuel: {helicopter.fuel:0.1f}",
        ]

        x, y = 12, 10
        padding = 4
        rendered = [self._font.render(line, True, (240, 240, 240)) for line in lines]
        w = max(s.get_width() for s in rendered) + padding * 2
        h = sum(s.get_height() for s in rendered) + padding * 2 + (len(rendered) - 1) * 2

        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 140))

        cy = padding
        for surf in rendered:
            panel.blit(surf, (padding, cy))
            cy += surf.get_height() + 2

        screen.blit(panel, (x, y))
