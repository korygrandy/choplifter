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
from ..barak_mrad import BARAK_LAUNCHER_VISIBLE_STATES
from ..mission_helpers import sentiment_band_label, sentiment_contributions

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
    _draw_supply_drops(screen, mission, camera_x=camera_x)

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

    # Embassy body.
    main_color = (176, 182, 194)
    shadow_color = (120, 126, 140)
    frame_color = (54, 60, 74)
    trim_color = (214, 218, 226)

    pygame.draw.rect(screen, main_color, r, border_radius=6)
    pygame.draw.rect(screen, frame_color, r, 2, border_radius=6)

    # Lower facade brick texture (light gray) for depth.
    brick_band_h = max(10, int(r.height * 0.20))
    brick_band = pygame.Rect(r.x + 2, r.bottom - brick_band_h - 2, r.width - 4, brick_band_h)
    pygame.draw.rect(screen, (202, 207, 216), brick_band, border_radius=3)
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

    # Embassy placard label.
    placard_w = max(44, int(r.width * 0.42))
    placard_h = max(10, int(r.height * 0.12))
    placard_y = roof.bottom + 4
    placard = pygame.Rect(r.centerx - placard_w // 2, placard_y, placard_w, placard_h)
    pygame.draw.rect(screen, (36, 42, 56), placard, border_radius=2)
    placard_border_boost = int(26 * unload_pulse)
    placard_border = (
        min(255, 184 + placard_border_boost),
        min(255, 190 + placard_border_boost),
        min(255, 204 + placard_border_boost),
    )
    pygame.draw.rect(screen, placard_border, placard, 1, border_radius=2)
    font_size = max(8, min(13, int(placard_h * 0.8)))
    placard_font = pygame.font.SysFont("consolas", font_size, bold=True)
    placard_text = placard_font.render("US EMBASSY", True, (232, 236, 244))
    text_x = placard.centerx - placard_text.get_width() // 2
    text_y = placard.centery - placard_text.get_height() // 2
    screen.blit(placard_text, (text_x, text_y))

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

        # Keep VIP marker a clearly filled purple dot that stays readable under effects.
        if getattr(h, "is_vip", False):
            body_color = (170, 65, 220)
            pygame.draw.circle(screen, body_color, (x, y), 6)
            pygame.draw.circle(screen, (25, 25, 25), (x, y), 6, 1)
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
    # Position crown directly above the VIP circle marker.
    crown_y = y - 12
    alpha = int(127.5 * (math.sin(mission_time * 5.2) + 1.0))
    alpha = max(36, min(255, alpha))

    crown = pygame.Surface((20, 14), pygame.SRCALPHA)
    points = [(2, 12), (5, 5), (9, 9), (12, 3), (15, 9), (18, 5), (18, 12)]
    pygame.draw.polygon(crown, (255, 220, 70, alpha), points)
    pygame.draw.polygon(crown, (255, 245, 185, min(255, alpha + 20)), points, 1)
    crown.set_alpha(alpha)
    screen.blit(crown, (x - crown.get_width() // 2, crown_y - crown.get_height() // 2))


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
        ring = pygame.Surface((ring_r * 2 + 4, ring_r * 2 + 4), pygame.SRCALPHA)
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

    return [
        f"Sentiment factors: +{add_saved:0.1f} rescued civilians",
        f"Sentiment factors: -{sub_kia_player:0.1f} player-caused casualties",
        f"Sentiment factors: -{sub_kia_enemy:0.1f} enemy-caused casualties",
        f"Sentiment factors: -{sub_lost:0.1f} lost in transit",
    ]


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
        )
    )

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
