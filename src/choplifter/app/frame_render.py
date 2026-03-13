from __future__ import annotations

import math
import random
import pygame

from ..objective_manager import draw_city_objectives
from .objective_overlay import get_mission_objective_overlay, overlay_alpha, tick_overlay_timer


def _draw_vip_crown_icon(target: pygame.Surface, *, x: int, y: int, mission_time: float, alpha: int) -> None:
    pulse = int(127.5 * (math.sin(float(mission_time) * 5.2) + 1.0))
    pulse = max(36, min(255, pulse))
    crown_alpha = max(0, min(255, int(alpha * (pulse / 255.0))))

    crown = pygame.Surface((20, 14), pygame.SRCALPHA)
    points = [(2, 12), (5, 5), (9, 9), (12, 3), (15, 9), (18, 5), (18, 12)]
    pygame.draw.polygon(crown, (255, 220, 70, crown_alpha), points)
    pygame.draw.polygon(crown, (255, 245, 185, min(255, crown_alpha + 20)), points, 1)
    crown.set_alpha(crown_alpha)
    target.blit(crown, (x, y - 15))

    halo = pygame.Surface((18, 18), pygame.SRCALPHA)
    # Match the in-world VIP marker language: solid purple fill under the crown.
    pygame.draw.circle(halo, (170, 65, 220, max(0, min(255, alpha))), (9, 9), 7)
    pygame.draw.circle(halo, (255, 235, 140, max(26, crown_alpha // 3)), (9, 9), 7, 2)
    target.blit(halo, (x + 1, y - 3))


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
    tech_kia_overlay_timer: float,
    city_objective_overlay_timer: float,
    frame_dt: float,
    draw_hud_fn: object,
    driver_mode_active: bool = False,
    debug_mode: bool = False,
) -> tuple[float, float, float]:
    """Draw playing HUD effects and return updated (vip_timer, tech_timer, objective_timer)."""
    if hud_disabled_timer > 0.0:
        # Draw a static overlay to indicate HUD/targeting is disabled.
        overlay_surf = pygame.Surface(target.get_size(), pygame.SRCALPHA)
        overlay_surf.fill((40, 40, 40, 180))
        target.blit(overlay_surf, (0, 0))
    else:
        draw_hud_fn(target, mission, helicopter, driver_mode_active=driver_mode_active, debug_mode=debug_mode)

    next_vip_timer = float(vip_kia_overlay_timer)
    next_tech_kia_timer = float(tech_kia_overlay_timer)
    next_city_objective_timer = float(city_objective_overlay_timer)

    if next_city_objective_timer > 0.0:
        next_city_objective_timer = tick_overlay_timer(timer_s=next_city_objective_timer, frame_dt=frame_dt)
        alpha = overlay_alpha(remaining_s=next_city_objective_timer)
        mission_time = float(getattr(mission, "elapsed_seconds", 0.0))
        objective_text, show_vip_icon = get_mission_objective_overlay(
            mission_id=str(getattr(mission, "mission_id", ""))
        )
        if not objective_text:
            objective_text = "Rescue hostages and return them to base"

        font = pygame.font.SysFont("consolas", 28, bold=True)
        text = font.render(objective_text, True, (255, 226, 148))
        text.set_alpha(alpha)

        icon_gap = 8 if show_vip_icon else 0
        icon_w = 20 if show_vip_icon else 0
        row_w = text.get_width() + icon_gap + icon_w
        row_x = (screen.get_width() - row_w) // 2
        text_x = row_x
        icon_x = row_x + text.get_width() + icon_gap
        panel_y = 52
        panel = pygame.Surface((screen.get_width(), 50), pygame.SRCALPHA)
        panel.fill((0, 0, 0, max(0, min(180, int(alpha * 0.6)))))
        panel.blit(text, (text_x, 10))
        if show_vip_icon:
            _draw_vip_crown_icon(panel, x=icon_x, y=14, mission_time=mission_time, alpha=alpha)
        target.blit(panel, (0, panel_y))

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

    if next_tech_kia_timer > 0.0:
        next_tech_kia_timer -= float(frame_dt)
        font = pygame.font.SysFont("consolas", 36)
        text = font.render("MISSION FAILED. Mission Technician KIA.", True, (255, 32, 32))
        if next_tech_kia_timer < 0.5:
            alpha = int(255 * (next_tech_kia_timer / 0.5))
        elif next_tech_kia_timer > 2.5:
            alpha = int(255 * (3.0 - next_tech_kia_timer) / 0.5)
        else:
            alpha = 255
        overlay = pygame.Surface((screen.get_width(), 60), pygame.SRCALPHA)
        bg_alpha = max(0, min(255, int(alpha * 0.5)))
        overlay.fill((0, 0, 0, bg_alpha))
        text.set_alpha(alpha)
        overlay.blit(text, ((screen.get_width() - text.get_width()) // 2, 10))
        target.blit(overlay, (0, screen.get_height() // 2 - 30))

    return next_vip_timer, next_tech_kia_timer, next_city_objective_timer


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


def render_world_branch(
    *,
    mode: str,
    target: pygame.Surface,
    screen: pygame.Surface,
    mission: object,
    helicopter: object,
    camera_x: float,
    frame_dt: float,
    selected_mission_id: str,
    particles_enabled: bool,
    weather_mode: str,
    ground_y: float,
    sky_smoke: object,
    rain: object,
    fog: object,
    dust: object,
    storm_clouds: object,
    lightning: object,
    airport_runtime: object,
    hud_disabled_timer: float,
    vip_kia_overlay_timer: float,
    tech_kia_overlay_timer: float,
    city_objective_overlay_timer: float,
    meal_truck_driver_mode: bool,
    debug_mode: bool,
    mission_choices: object,
    selected_mission_index: int,
    chopper_choices: object,
    selected_chopper_index: int,
    pause_focus: str,
    muted: bool,
    quit_confirm: bool,
    paused_hint: str,
    draw_sky_fn: object,
    draw_ground_fn: object,
    draw_mission_fn: object,
    draw_airport_world_overlays_fn: object,
    draw_flares_fn: object,
    draw_explosion_particles_fn: object,
    draw_enemy_damage_fx_fn: object,
    draw_helicopter_damage_fx_fn: object,
    draw_helicopter_fn: object,
    draw_impact_sparks_fn: object,
    boarded_count_fn: object,
    draw_hud_fn: object,
    draw_mission_select_overlay_fn: object,
    draw_chopper_select_overlay_fn: object,
    draw_mission_end_overlay_fn: object,
) -> tuple[float, float, float]:
    """Render the shared world branch and return updated overlay timers."""
    draw_sky_fn(
        target,
        ground_y,
        bg_asset=getattr(mission, "bg_asset", "mission1-bg.jpg"),
        dt=frame_dt,
        enable_fade=(mode == "select_mission"),
    )
    draw_weather_particles(
        target=target,
        particles_enabled=particles_enabled,
        weather_mode=weather_mode,
        sky_smoke=sky_smoke,
        rain=rain,
        fog=fog,
        dust=dust,
        storm_clouds=storm_clouds,
        lightning=lightning,
        ground_y=float(ground_y),
    )
    draw_ground_fn(target, ground_y)
    draw_mission_fn(target, mission, camera_x=camera_x, enable_particles=particles_enabled)

    if selected_mission_id == "airport":
        draw_airport_world_overlays_fn(
            target=target,
            camera_x=camera_x,
            helicopter=helicopter,
            mission=mission,
            heli_ground_y=ground_y,
            airport_bus_state=airport_runtime.bus_state,
            airport_hostage_state=airport_runtime.hostage_state,
            airport_enemy_state=airport_runtime.enemy_state,
            airport_tech_state=airport_runtime.tech_state,
            airport_objective_state=airport_runtime.objective_state,
            airport_meal_truck_state=airport_runtime.meal_truck_state,
            airport_cutscene_state=airport_runtime.cutscene_state,
        )

    if mode == "playing":
        draw_city_objectives(target, mission)

    draw_flares_fn(target, mission, camera_x=camera_x, enable_particles=particles_enabled)
    draw_explosion_particles_fn(target, mission, camera_x=camera_x)
    draw_enemy_damage_fx_fn(target, mission, camera_x=camera_x, enable_particles=particles_enabled)
    draw_helicopter_damage_fx_fn(target, mission, camera_x=camera_x, enable_particles=particles_enabled)
    draw_helicopter_fn(target, helicopter, camera_x=camera_x, boarded=boarded_count_fn(mission))
    draw_impact_sparks_fn(target, mission, camera_x=camera_x, enable_particles=particles_enabled)

    if weather_mode == "storm":
        storm_clouds.draw(target, layer="black")

    next_vip_timer = float(vip_kia_overlay_timer)
    next_tech_kia_timer = float(tech_kia_overlay_timer)
    next_city_objective_timer = float(city_objective_overlay_timer)
    if mode == "playing":
        next_vip_timer, next_tech_kia_timer, next_city_objective_timer = draw_playing_hud_and_overlays(
            target=target,
            screen=screen,
            mission=mission,
            helicopter=helicopter,
            hud_disabled_timer=hud_disabled_timer,
            vip_kia_overlay_timer=next_vip_timer,
            tech_kia_overlay_timer=next_tech_kia_timer,
            city_objective_overlay_timer=next_city_objective_timer,
            frame_dt=frame_dt,
            draw_hud_fn=draw_hud_fn,
            driver_mode_active=meal_truck_driver_mode,
            debug_mode=debug_mode,
        )
    else:
        draw_mode_overlays(
            mode=mode,
            target=target,
            mission_choices=mission_choices,
            selected_mission_index=selected_mission_index,
            chopper_choices=chopper_choices,
            selected_chopper_index=selected_chopper_index,
            pause_focus=pause_focus,
            muted=muted,
            quit_confirm=quit_confirm,
            paused_hint=paused_hint,
            draw_mission_select_overlay_fn=draw_mission_select_overlay_fn,
            draw_chopper_select_overlay_fn=draw_chopper_select_overlay_fn,
        )

    draw_mission_end_overlay_fn(target, mission)
    return next_vip_timer, next_tech_kia_timer, next_city_objective_timer


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
    perf_counters: object,
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
        overlay.draw(
            target,
            helicopter,
            mission,
            fps,
            perf_counters=perf_counters,
        )

    if target is not screen:
        screen.fill((0, 0, 0))
        screen.blit(target, (int(shake_x), int(shake_y)))


def render_mode_frame(
    *,
    mode: str,
    target: pygame.Surface,
    screen: pygame.Surface,
    skip_hint: str,
    cutscenes: object,
    mission: object,
    helicopter: object,
    camera_x: float,
    frame_dt: float,
    selected_mission_id: str,
    particles_enabled: bool,
    weather_mode: str,
    ground_y: float,
    sky_smoke: object,
    rain: object,
    fog: object,
    dust: object,
    storm_clouds: object,
    lightning: object,
    airport_runtime: object,
    hud_disabled_timer: float,
    vip_kia_overlay_timer: float,
    tech_kia_overlay_timer: float,
    city_objective_overlay_timer: float,
    meal_truck_driver_mode: bool,
    debug_mode: bool,
    mission_choices: object,
    selected_mission_index: int,
    chopper_choices: object,
    selected_chopper_index: int,
    pause_focus: str,
    muted: bool,
    quit_confirm: bool,
    paused_hint: str,
    draw_intro_fn: object,
    draw_mission_cutscene_fn: object,
    draw_sky_fn: object,
    draw_ground_fn: object,
    draw_mission_fn: object,
    draw_airport_world_overlays_fn: object,
    draw_flares_fn: object,
    draw_explosion_particles_fn: object,
    draw_enemy_damage_fx_fn: object,
    draw_helicopter_damage_fx_fn: object,
    draw_helicopter_fn: object,
    draw_impact_sparks_fn: object,
    boarded_count_fn: object,
    draw_hud_fn: object,
    draw_mission_select_overlay_fn: object,
    draw_chopper_select_overlay_fn: object,
    draw_mission_end_overlay_fn: object,
    shake_x: int,
    shake_y: int,
    debug_show_overlay: bool,
    toast_message: str,
    flashes_enabled: bool,
    overlay: object,
    fps: float,
    perf_counters: object,
    draw_debug_overlay_fn: object,
    draw_toast_fn: object,
    draw_damage_flash_fn: object,
) -> tuple[float, float, float]:
    """Render the frame by mode and return updated overlay timers."""
    next_vip_timer = float(vip_kia_overlay_timer)
    next_tech_kia_timer = float(tech_kia_overlay_timer)
    next_city_objective_timer = float(city_objective_overlay_timer)

    if mode == "intro":
        draw_intro_fn(cutscenes.intro, target, skip_hint=skip_hint)
        return next_vip_timer, next_tech_kia_timer, next_city_objective_timer

    if mode == "cutscene":
        draw_mission_cutscene_fn(cutscenes.mission, target, skip_hint=skip_hint)
        return next_vip_timer, next_tech_kia_timer, next_city_objective_timer

    next_vip_timer, next_tech_kia_timer, next_city_objective_timer = render_world_branch(
        mode=mode,
        target=target,
        screen=screen,
        mission=mission,
        helicopter=helicopter,
        camera_x=camera_x,
        frame_dt=frame_dt,
        selected_mission_id=selected_mission_id,
        particles_enabled=particles_enabled,
        weather_mode=weather_mode,
        ground_y=ground_y,
        sky_smoke=sky_smoke,
        rain=rain,
        fog=fog,
        dust=dust,
        storm_clouds=storm_clouds,
        lightning=lightning,
        airport_runtime=airport_runtime,
        hud_disabled_timer=hud_disabled_timer,
        vip_kia_overlay_timer=next_vip_timer,
        tech_kia_overlay_timer=next_tech_kia_timer,
        city_objective_overlay_timer=next_city_objective_timer,
        meal_truck_driver_mode=meal_truck_driver_mode,
        debug_mode=debug_mode,
        mission_choices=mission_choices,
        selected_mission_index=selected_mission_index,
        chopper_choices=chopper_choices,
        selected_chopper_index=selected_chopper_index,
        pause_focus=pause_focus,
        muted=muted,
        quit_confirm=quit_confirm,
        paused_hint=paused_hint,
        draw_sky_fn=draw_sky_fn,
        draw_ground_fn=draw_ground_fn,
        draw_mission_fn=draw_mission_fn,
        draw_airport_world_overlays_fn=draw_airport_world_overlays_fn,
        draw_flares_fn=draw_flares_fn,
        draw_explosion_particles_fn=draw_explosion_particles_fn,
        draw_enemy_damage_fx_fn=draw_enemy_damage_fx_fn,
        draw_helicopter_damage_fx_fn=draw_helicopter_damage_fx_fn,
        draw_helicopter_fn=draw_helicopter_fn,
        draw_impact_sparks_fn=draw_impact_sparks_fn,
        boarded_count_fn=boarded_count_fn,
        draw_hud_fn=draw_hud_fn,
        draw_mission_select_overlay_fn=draw_mission_select_overlay_fn,
        draw_chopper_select_overlay_fn=draw_chopper_select_overlay_fn,
        draw_mission_end_overlay_fn=draw_mission_end_overlay_fn,
    )

    render_frame_post_fx(
        mode=mode,
        target=target,
        screen=screen,
        shake_x=shake_x,
        shake_y=shake_y,
        debug_mode=debug_mode,
        debug_show_overlay=debug_show_overlay,
        toast_message=toast_message,
        flashes_enabled=flashes_enabled,
        helicopter=helicopter,
        mission=mission,
        overlay=overlay,
        fps=fps,
        perf_counters=perf_counters,
        draw_debug_overlay_fn=draw_debug_overlay_fn,
        draw_toast_fn=draw_toast_fn,
        draw_damage_flash_fn=draw_damage_flash_fn,
    )

    return next_vip_timer, next_tech_kia_timer, next_city_objective_timer


def render_mode_frame_from_runtime(
    *,
    mode: str,
    target: pygame.Surface,
    screen: pygame.Surface,
    skip_hint: str,
    cutscenes: object,
    mission: object,
    helicopter: object,
    camera_x: float,
    frame_dt: float,
    selected_mission_id: str,
    particles_enabled: bool,
    sky_smoke: object,
    rain: object,
    fog: object,
    dust: object,
    storm_clouds: object,
    lightning: object,
    runtime: object,
    heli_settings: object,
    airport_runtime: object,
    mission_choices: object,
    selected_mission_index: int,
    chopper_choices: object,
    selected_chopper_index: int,
    paused_hint: str,
    debug_show_overlay: bool,
    toast_message: str,
    flashes_enabled: bool,
    overlay: object,
    fps: float,
    draw_intro_fn: object,
    draw_mission_cutscene_fn: object,
    draw_sky_fn: object,
    draw_ground_fn: object,
    draw_mission_fn: object,
    draw_airport_world_overlays_fn: object,
    draw_flares_fn: object,
    draw_explosion_particles_fn: object,
    draw_enemy_damage_fx_fn: object,
    draw_helicopter_damage_fx_fn: object,
    draw_helicopter_fn: object,
    draw_impact_sparks_fn: object,
    boarded_count_fn: object,
    draw_hud_fn: object,
    draw_mission_select_overlay_fn: object,
    draw_chopper_select_overlay_fn: object,
    draw_mission_end_overlay_fn: object,
    shake_x: int,
    shake_y: int,
    draw_debug_overlay_fn: object,
    draw_toast_fn: object,
    draw_damage_flash_fn: object,
) -> tuple[float, float, float]:
    """Render a frame by adapting grouped runtime settings into render_mode_frame."""
    return render_mode_frame(
        mode=mode,
        target=target,
        screen=screen,
        skip_hint=skip_hint,
        cutscenes=cutscenes,
        mission=mission,
        helicopter=helicopter,
        camera_x=camera_x,
        frame_dt=frame_dt,
        selected_mission_id=selected_mission_id,
        particles_enabled=particles_enabled,
        weather_mode=str(getattr(runtime, "weather_mode", "clear")),
        ground_y=float(getattr(heli_settings, "ground_y", 0.0)),
        sky_smoke=sky_smoke,
        rain=rain,
        fog=fog,
        dust=dust,
        storm_clouds=storm_clouds,
        lightning=lightning,
        airport_runtime=airport_runtime,
        hud_disabled_timer=float(getattr(runtime, "hud_disabled_timer", 0.0)),
        vip_kia_overlay_timer=float(getattr(runtime, "vip_kia_overlay_timer", 0.0)),
        tech_kia_overlay_timer=float(getattr(runtime, "tech_kia_overlay_timer", 0.0)),
        city_objective_overlay_timer=float(getattr(runtime, "city_objective_overlay_timer", 0.0)),
        meal_truck_driver_mode=bool(getattr(runtime, "meal_truck_driver_mode", False)),
        debug_mode=bool(getattr(runtime, "debug_mode", False)),
        mission_choices=mission_choices,
        selected_mission_index=selected_mission_index,
        chopper_choices=chopper_choices,
        selected_chopper_index=selected_chopper_index,
        pause_focus=str(getattr(runtime, "pause_focus", "choppers")),
        muted=bool(getattr(runtime, "muted", False)),
        quit_confirm=bool(getattr(runtime, "quit_confirm", False)),
        paused_hint=paused_hint,
        draw_intro_fn=draw_intro_fn,
        draw_mission_cutscene_fn=draw_mission_cutscene_fn,
        draw_sky_fn=draw_sky_fn,
        draw_ground_fn=draw_ground_fn,
        draw_mission_fn=draw_mission_fn,
        draw_airport_world_overlays_fn=draw_airport_world_overlays_fn,
        draw_flares_fn=draw_flares_fn,
        draw_explosion_particles_fn=draw_explosion_particles_fn,
        draw_enemy_damage_fx_fn=draw_enemy_damage_fx_fn,
        draw_helicopter_damage_fx_fn=draw_helicopter_damage_fx_fn,
        draw_helicopter_fn=draw_helicopter_fn,
        draw_impact_sparks_fn=draw_impact_sparks_fn,
        boarded_count_fn=boarded_count_fn,
        draw_hud_fn=draw_hud_fn,
        draw_mission_select_overlay_fn=draw_mission_select_overlay_fn,
        draw_chopper_select_overlay_fn=draw_chopper_select_overlay_fn,
        draw_mission_end_overlay_fn=draw_mission_end_overlay_fn,
        shake_x=shake_x,
        shake_y=shake_y,
        debug_show_overlay=debug_show_overlay,
        toast_message=toast_message,
        flashes_enabled=flashes_enabled,
        overlay=overlay,
        fps=fps,
        perf_counters=getattr(runtime, "perf_overlay", None),
        draw_debug_overlay_fn=draw_debug_overlay_fn,
        draw_toast_fn=draw_toast_fn,
        draw_damage_flash_fn=draw_damage_flash_fn,
    )
