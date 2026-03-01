from __future__ import annotations

import pygame

from .helicopter import Helicopter
from .mission import MissionState, boarded_count


class DebugOverlay:
    def __init__(self) -> None:
        pygame.font.init()
        self._font = pygame.font.SysFont("consolas", 18)

    def draw(self, screen: pygame.Surface, helicopter: Helicopter, mission: MissionState, fps: float) -> None:
        boarded = boarded_count(mission)
        compound_states = " ".join(
            f"{max(0, int(c.health))}{'O' if c.is_open else 'S'}" for c in mission.compounds
        )

        lines = [
            f"FPS: {fps:0.1f}",
            f"t: {mission.elapsed_seconds:0.1f}s",
            f"pos: ({helicopter.pos.x:0.1f}, {helicopter.pos.y:0.1f})",
            f"vel: ({helicopter.vel.x:0.2f}, {helicopter.vel.y:0.2f})",
            f"tilt: {helicopter.tilt_deg:0.1f} deg",
            f"facing: {helicopter.facing.name}",
            f"grounded: {helicopter.grounded}",
            f"doors: {'OPEN' if helicopter.doors_open else 'closed'}",
            f"damage: {helicopter.damage:0.1f}",
            f"fuel: {helicopter.fuel:0.1f}",
            f"invuln: {mission.invuln_seconds:0.1f}s",
            f"boarded: {boarded}/16",
            f"saved: {mission.stats.saved}",
            f"KIA(player): {mission.stats.kia_by_player}",
            f"KIA(enemy): {mission.stats.kia_by_enemy}",
            f"lost_in_transit: {mission.stats.lost_in_transit}",
            f"sentiment: {mission.sentiment:0.1f}",
            f"compounds: {compound_states}",
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
