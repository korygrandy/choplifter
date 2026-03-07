from __future__ import annotations

import random
import pygame


def draw_weather_particles(
    *,
    target: pygame.Surface,
    particles_enabled: bool,
    weather_mode: str,
    sky_smoke: object,
    rain: object,
    fog: object,
    dust: object,
    storm_clouds: object,
    lightning: object,
    ground_y: float,
) -> None:
    """Draw sky particles and weather layers behind world entities."""
    if not particles_enabled:
        return

    sky_smoke.draw(target, horizon_y=int(ground_y))

    if weather_mode == "rain":
        for p in getattr(rain, "particles", []):
            pygame.draw.circle(target, (120, 120, 255), (int(p.pos.x), int(p.pos.y)), 2)

    if weather_mode == "fog":
        for p in getattr(fog, "particles", []):
            # Draw fog as long, semi-transparent ovals.
            oval_width = int(p.radius * 2.5)
            oval_height = int(p.radius * 0.7)
            alpha = 32  # ~12.5% opacity
            fog_color = (220, 220, 220, alpha)
            oval_surf = pygame.Surface((oval_width, oval_height), pygame.SRCALPHA)
            pygame.draw.ellipse(oval_surf, fog_color, (0, 0, oval_width, oval_height))
            target.blit(oval_surf, (int(p.pos.x - oval_width // 2), int(p.pos.y - oval_height // 2)))

        # Add long horizontal fog streaks with variance.
        streak_count = 4
        for _ in range(streak_count):
            area_width = target.get_width()
            area_height = int(target.get_height() * 0.7)
            streak_x = random.randint(0, area_width - 1)
            streak_y = random.randint(int(area_height * 0.2), int(area_height * 0.8))
            streak_width = random.randint(int(area_width * 0.25), int(area_width * 0.5))
            streak_height = random.randint(10, 18)
            streak_alpha = random.randint(22, 38)  # 9-15% opacity
            streak_color = (210, 210, 210, streak_alpha)
            streak_surf = pygame.Surface((streak_width, streak_height), pygame.SRCALPHA)
            pygame.draw.ellipse(streak_surf, streak_color, (0, 0, streak_width, streak_height))
            target.blit(streak_surf, (streak_x, streak_y))

    if weather_mode == "dust":
        for p in getattr(dust, "particles", []):
            pygame.draw.circle(target, (180, 160, 120, 80), (int(p.pos.x), int(p.pos.y)), int(p.radius))

    if weather_mode == "storm":
        # Draw storm clouds in layers around world entities.
        storm_clouds.draw(target, layer="back")
        for p in getattr(rain, "particles", []):
            pygame.draw.circle(target, (120, 120, 255), (int(p.pos.x), int(p.pos.y)), 2)
        lightning.draw(target)
        storm_clouds.draw(target, layer="front")


def draw_playing_hud_and_overlays(
    *,
    target: pygame.Surface,
    screen: pygame.Surface,
    mission: object,
    helicopter: object,
    hud_disabled_timer: float,
    vip_kia_overlay_timer: float,
    frame_dt: float,
    draw_hud_fn: object,
) -> float:
    """Draw playing HUD effects and return updated VIP KIA overlay timer."""
    if hud_disabled_timer > 0.0:
        # Draw a static overlay to indicate HUD/targeting is disabled.
        overlay_surf = pygame.Surface(target.get_size(), pygame.SRCALPHA)
        overlay_surf.fill((40, 40, 40, 180))
        target.blit(overlay_surf, (0, 0))
    else:
        draw_hud_fn(target, mission, helicopter)

    next_vip_timer = float(vip_kia_overlay_timer)
    if next_vip_timer > 0.0:
        next_vip_timer -= float(frame_dt)
        font = pygame.font.SysFont("consolas", 36)
        text = font.render("MISSION FAILED. VIP target KIA.", True, (255, 32, 32))
        # Fade in/out: full alpha for most of duration, fade last 0.5s and first 0.5s.
        if next_vip_timer < 0.5:
            alpha = int(255 * (next_vip_timer / 0.5))
        elif next_vip_timer > 2.5:
            alpha = int(255 * (3.0 - next_vip_timer) / 0.5)
        else:
            alpha = 255
        overlay = pygame.Surface((screen.get_width(), 60), pygame.SRCALPHA)
        bg_alpha = max(0, min(255, int(alpha * 0.5)))
        overlay.fill((0, 0, 0, bg_alpha))
        text.set_alpha(alpha)
        overlay.blit(text, ((screen.get_width() - text.get_width()) // 2, 10))
        target.blit(overlay, (0, screen.get_height() // 2 - 30))

    return next_vip_timer


def draw_mode_overlays(
    *,
    mode: str,
    target: pygame.Surface,
    mission_choices: object,
    selected_mission_index: int,
    chopper_choices: object,
    selected_chopper_index: int,
    pause_focus: str,
    muted: bool,
    quit_confirm: bool,
    paused_hint: str,
    draw_mission_select_overlay_fn: object,
    draw_chopper_select_overlay_fn: object,
) -> None:
    """Draw non-playing mode overlays on top of the world background."""
    if mode == "select_mission":
        draw_mission_select_overlay_fn(target, mission_choices, selected_mission_index)
        return

    if mode == "select_chopper":
        draw_chopper_select_overlay_fn(target, chopper_choices, selected_chopper_index)
        return

    if mode == "paused":
        draw_chopper_select_overlay_fn(
            target,
            chopper_choices,
            selected_chopper_index,
            title="Paused",
            hint=paused_hint,
            show_mute=True,
            mute_selected=(pause_focus == "mute"),
            muted=muted,
            show_restart=True,
            restart_selected=(pause_focus == "restart_mission"),
            show_restart_game=True,
            restart_game_selected=(pause_focus == "restart_game"),
            show_quit=True,
            quit_selected=(pause_focus == "quit"),
            quit_confirm=quit_confirm,
        )


def render_frame_post_fx(
    *,
    mode: str,
    target: pygame.Surface,
    screen: pygame.Surface,
    shake_x: int,
    shake_y: int,
    debug_mode: bool,
    debug_show_overlay: bool,
    toast_message: str,
    flashes_enabled: bool,
    helicopter: object,
    mission: object,
    overlay: object,
    fps: float,
    draw_debug_overlay_fn: object,
    draw_toast_fn: object,
    draw_damage_flash_fn: object,
) -> None:
    """Render post-world overlays and present the final frame to the screen."""
    if debug_mode:
        draw_debug_overlay_fn(target)
    if toast_message:
        draw_toast_fn(target, toast_message)
    if mode == "playing" and flashes_enabled:
        draw_damage_flash_fn(target, helicopter)

    if debug_show_overlay and mode == "playing":
        overlay.draw(target, helicopter, mission, fps)

    if target is not screen:
        screen.fill((0, 0, 0))
        screen.blit(target, (int(shake_x), int(shake_y)))
