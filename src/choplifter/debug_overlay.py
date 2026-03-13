from __future__ import annotations

import pygame

from .helicopter import Helicopter
from .game_types import EnemyKind
from .mission_helpers import boarded_count
from .mission_state import MissionState
from .threat_tells import THREAT_TELL_MATRIX


class DebugOverlay:
    def __init__(self) -> None:
        pygame.font.init()
        self._font = pygame.font.SysFont("consolas", 18)
        self._panel_cache: dict[tuple[int, int], pygame.Surface] = {}

    def _get_panel_surface(self, *, width: int, height: int) -> pygame.Surface:
        key = (int(width), int(height))
        panel = self._panel_cache.get(key)
        if panel is not None:
            return panel

        panel = pygame.Surface((key[0], key[1]), pygame.SRCALPHA)
        self._panel_cache[key] = panel
        if len(self._panel_cache) > 8:
            self._panel_cache.clear()
            self._panel_cache[key] = panel
        return panel

    def draw(
        self,
        screen: pygame.Surface,
        helicopter: Helicopter,
        mission: MissionState,
        fps: float,
        perf_counters: object | None = None,
    ) -> None:
        boarded = boarded_count(mission)
        compound_states = " ".join(
            f"{max(0, int(c.health))}{'O' if c.is_open else 'S'}" for c in mission.compounds
        )
        tank_tell_active = sum(
            1
            for e in mission.enemies
            if e.kind is EnemyKind.TANK and float(getattr(e, "fire_tell_seconds", 0.0)) > 0.0
        )
        tank_flash_active = sum(
            1
            for e in mission.enemies
            if e.kind is EnemyKind.TANK and float(getattr(e, "muzzle_flash_seconds", 0.0)) > 0.0
        )
        tank_tell = THREAT_TELL_MATRIX[EnemyKind.TANK]
        jet_tell = THREAT_TELL_MATRIX[EnemyKind.JET]
        mine_tell = THREAT_TELL_MATRIX[EnemyKind.AIR_MINE]
        barak = next((e for e in mission.enemies if e.kind is EnemyKind.BARAK_MRAD and e.alive), None)
        if barak is None:
            barak_state_line = "barak: none"
            barak_pose_line = "barak_pose: --"
        else:
            barak_state_line = (
                f"barak: {getattr(barak, 'mrad_state', '?')} "
                f"t={float(getattr(barak, 'mrad_state_seconds', 0.0)):0.1f}s "
                f"reload={float(getattr(barak, 'mrad_reload_seconds', 0.0)):0.1f}s"
            )
            barak_pose_line = (
                f"barak_pose: ang={float(getattr(barak, 'launcher_angle', 0.0)):0.2f} "
                f"ext={float(getattr(barak, 'launcher_ext_progress', 0.0)):0.2f}"
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
            f"threat_tells: tank={tank_tell_active} flash={tank_flash_active}",
            f"threat_warn: jet={mission.jet_warning_seconds:0.1f}s mine={mission.mine_warning_seconds:0.1f}s",
            f"matrix[tank]: lead={tank_tell.lead_time_s:0.2f}s range={int(tank_tell.effective_range_px)}px",
            f"matrix[jet ]: lead={jet_tell.lead_time_s:0.2f}s range={int(jet_tell.effective_range_px)}px",
            f"matrix[mine]: lead={mine_tell.lead_time_s:0.2f}s range={int(mine_tell.effective_range_px)}px",
            barak_state_line,
            barak_pose_line,
            f"compounds: {compound_states}",
        ]

        if isinstance(perf_counters, dict) and perf_counters:
            lines.extend(
                [
                    "perf(ms):",
                    (
                        "  frame="
                        f"{float(perf_counters.get('frame_total_ms', 0.0)):0.2f} "
                        "preamble="
                        f"{float(perf_counters.get('frame_preamble_ms', 0.0)):0.2f} "
                        "event="
                        f"{float(perf_counters.get('event_dispatch_ms', 0.0)):0.2f}"
                    ),
                    (
                        "  input="
                        f"{float(perf_counters.get('input_phase_ms', 0.0)):0.2f} "
                        "fixed="
                        f"{float(perf_counters.get('fixed_step_ms', 0.0)):0.2f} "
                        "post="
                        f"{float(perf_counters.get('post_phase_ms', 0.0)):0.2f}"
                    ),
                    (
                        "  prep="
                        f"{float(perf_counters.get('frame_prep_ms', 0.0)):0.2f} "
                        "render="
                        f"{float(perf_counters.get('render_present_ms', 0.0)):0.2f}"
                    ),
                ]
            )

        x, y = 12, 10
        padding = 4
        rendered = [self._font.render(line, True, (240, 240, 240)) for line in lines]
        w = max(s.get_width() for s in rendered) + padding * 2
        h = sum(s.get_height() for s in rendered) + padding * 2 + (len(rendered) - 1) * 2

        panel = self._get_panel_surface(width=w, height=h)
        panel.fill((0, 0, 0, 140))

        cy = padding
        for surf in rendered:
            panel.blit(surf, (padding, cy))
            cy += surf.get_height() + 2

        screen.blit(panel, (x, y))
