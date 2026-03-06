from __future__ import annotations
import os
# Image cache for enemy sprites
_enemy_image_cache = {}

def get_enemy_image(name):
    if name not in _enemy_image_cache:
        # Use absolute path to ensure asset is found
        asset_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))
        path = os.path.join(asset_dir, name)
        _enemy_image_cache[name] = pygame.image.load(path).convert_alpha()
    return _enemy_image_cache[name]

import math
from typing import TYPE_CHECKING
import pygame

from ..game_types import EnemyKind, HostageState, ProjectileKind

if TYPE_CHECKING:
    from ..mission_state import MissionState


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

    # Draw wind-blown dust clouds if present
    from .particles import draw_wind_dust_clouds
    draw_wind_dust_clouds(screen, mission, camera_x=camera_x)

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


def _draw_hostages(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    vip_positions: list[tuple[int, int]] = []
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

        if getattr(h, "is_vip", False):
            vip_positions.append((x, y))

    # Draw VIP markers at the end so they remain top-most over all hostage indicators.
    for x, y in vip_positions:
        _draw_vip_crown(screen, x, y, mission_time=float(getattr(mission, "elapsed_seconds", 0.0)))


def _draw_vip_crown(screen: pygame.Surface, x: int, y: int, *, mission_time: float) -> None:
    crown_y = y - 12
    alpha = int(127.5 * (math.sin(mission_time * 5.2) + 1.0))
    alpha = max(36, min(255, alpha))

    crown = pygame.Surface((20, 14), pygame.SRCALPHA)
    points = [(2, 12), (5, 5), (9, 9), (12, 3), (15, 9), (18, 5), (18, 12)]
    pygame.draw.polygon(crown, (255, 220, 70, alpha), points)
    pygame.draw.polygon(crown, (255, 245, 185, min(255, alpha + 20)), points, 1)
    crown.set_alpha(alpha)
    screen.blit(crown, (x - crown.get_width() // 2, crown_y - crown.get_height() // 2))

    # Small halo ring to improve readability over bright backgrounds.
    halo = pygame.Surface((18, 18), pygame.SRCALPHA)
    pygame.draw.circle(halo, (255, 235, 140, max(26, alpha // 3)), (9, 9), 7, 2)
    screen.blit(halo, (x - 9, crown_y - 9))
def toggle_thermal_mode():
    global thermal_mode
    thermal_mode = not thermal_mode
    setattr(_draw_hostages, "thermal_mode", thermal_mode)


def _draw_projectiles(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    for p in mission.projectiles:
        x = int(p.pos.x - camera_x)
        y = int(p.pos.y)
        # Barak MRAD missile: draw as a large missile with flame and smoke, rotated by current_angle
        if getattr(p, "is_barak_missile", False):
            missile_len = 34
            missile_w = 6
            surf_w = 32
            surf_h = 48
            missile_surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
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

    for e in mission.enemies:
        if e.kind is EnemyKind.TANK:
            # Reskinned tank with richer hull + turret silhouette.
            w, h = 46, 18
            r = pygame.Rect(int(e.pos.x - camera_x - w / 2), int(ground_y - h), w, h)
            pygame.draw.rect(screen, (68, 74, 68), r, border_radius=2)
            pygame.draw.rect(screen, (24, 24, 24), r, 2, border_radius=2)

            tread_h = 5
            tread = pygame.Rect(r.x + 2, r.bottom - tread_h, r.width - 4, tread_h)
            pygame.draw.rect(screen, (42, 42, 42), tread)

            hull = [
                (r.x + 5, r.y + 3),
                (r.right - 8, r.y + 3),
                (r.right - 3, r.y + 8),
                (r.right - 7, r.y + 12),
                (r.x + 7, r.y + 12),
                (r.x + 3, r.y + 8),
            ]
            pygame.draw.polygon(screen, (86, 96, 82), hull)
            pygame.draw.polygon(screen, (25, 25, 25), hull, 1)

            # Turret marker using e.turret_angle
            turret_length = 24
            turret_base = (r.centerx - 1, r.top + 6)
            pygame.draw.circle(screen, (76, 82, 76), turret_base, 5)
            pygame.draw.circle(screen, (30, 30, 30), turret_base, 5, 1)
            angle = getattr(e, 'turret_angle', 0.0)
            turret_tip = (
                int(turret_base[0] + turret_length * math.cos(angle)),
                int(turret_base[1] + turret_length * math.sin(angle))
            )
            pygame.draw.line(screen, (28, 30, 28), turret_base, turret_tip, 4)

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

            # Draw the launcher (rectangle) if deploying or later
            if getattr(e, "mrad_state", None) in ("deploying", "aiming", "launching", "done"):
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
                launcher_surf = pygame.Surface((launcher_len, launcher_w), pygame.SRCALPHA)
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
    y = rect.bottom + 19
    for line in lines:
        s = small.render(line, True, (235, 235, 235))
        r = s.get_rect(center=(screen.get_width() // 2, y))
        screen.blit(s, r)
        y += 28
