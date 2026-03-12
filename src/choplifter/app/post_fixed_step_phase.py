from __future__ import annotations

import pygame

from .airport_render import draw_airport_world_overlays
from .cutscenes import draw_intro, draw_mission_cutscene, update_intro, update_mission_cutscene
from .frame_render import render_mode_frame_from_runtime
from .frame_update import prepare_frame_render_state
from .main_loop_context_sync import store_frame_locals_to_context
from .mode_update import apply_mode_transition_effects, resolve_post_frame_mode_transitions
from .ui_constants import PAUSED_MENU_HINT
from ..mission_helpers import boarded_count
from ..render.world import draw_mission_end_overlay
from ..rendering import (
    draw_chopper_select_overlay,
    draw_damage_flash,
    draw_enemy_damage_fx,
    draw_explosion_particles,
    draw_flares,
    draw_ground,
    draw_helicopter,
    draw_helicopter_damage_fx,
    draw_hud,
    draw_impact_sparks,
    draw_mission,
    draw_mission_select_overlay,
    draw_sky,
    draw_toast,
)


def run_post_fixed_step_phase(
    *,
    mode: str,
    frame_dt: float,
    runtime: object,
    toast: object,
    cutscenes: object,
    mission: object,
    helicopter: object,
    selected_mission_id: str,
    particles_enabled: bool,
    heli_settings: object,
    airport_runtime: object,
    screenshake: object,
    screenshake_enabled: bool,
    audio: object,
    sky_smoke: object,
    rain: object,
    fog: object,
    dust: object,
    storm_clouds: object,
    lightning: object,
    screen: pygame.Surface,
    window: object,
    update_screenshake_target_fn: object,
    skip_hint: str,
    mission_choices: object,
    selected_mission_index: int,
    chopper_choices: object,
    selected_chopper_index: int,
    debug_show_overlay: bool,
    flashes_enabled: bool,
    overlay: object,
    fps: float,
    draw_debug_overlay_fn: object,
    set_toast: object,
    logger: object,
    loop_ctx: object,
    accumulator: float,
    prev_stats: object,
    campaign_sentiment: float,
) -> str:
    """Run post-fixed-step frame phase and persist loop context. Returns next mode."""
    toast.update(frame_dt)

    intro_finished = bool(mode == "intro" and update_intro(cutscenes.intro, frame_dt))
    cutscene_finished = bool(mode == "cutscene" and update_mission_cutscene(cutscenes.mission, frame_dt))

    mode_transition = resolve_post_frame_mode_transitions(
        mode=mode,
        frame_dt=frame_dt,
        mission_end_return_seconds=runtime.mission_end_return_seconds,
        intro_finished=intro_finished,
        cutscene_finished=cutscene_finished,
    )
    mode = mode_transition.mode
    runtime.mission_end_return_seconds = mode_transition.mission_end_return_seconds
    apply_mode_transition_effects(
        mode_transition=mode_transition,
        runtime=runtime,
        helicopter=helicopter,
        logger=logger,
        audio=audio,
        set_toast=set_toast,
    )

    frame_prep = prepare_frame_render_state(
        particles_enabled=particles_enabled,
        mode=mode,
        frame_dt=frame_dt,
        runtime=runtime,
        selected_mission_id=selected_mission_id,
        mission=mission,
        helicopter=helicopter,
        heli_settings=heli_settings,
        airport_runtime=airport_runtime,
        screenshake=screenshake,
        screenshake_enabled=screenshake_enabled,
        audio=audio,
        sky_smoke=sky_smoke,
        rain=rain,
        fog=fog,
        dust=dust,
        storm_clouds=storm_clouds,
        lightning=lightning,
        screen=screen,
        window=window,
        update_screenshake_target_fn=update_screenshake_target_fn,
    )
    camera_x = frame_prep.camera_x
    target = frame_prep.target
    shake_x = frame_prep.shake_x
    shake_y = frame_prep.shake_y

    runtime.vip_kia_overlay_timer, runtime.city_objective_overlay_timer = render_mode_frame_from_runtime(
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
        sky_smoke=sky_smoke,
        rain=rain,
        fog=fog,
        dust=dust,
        storm_clouds=storm_clouds,
        lightning=lightning,
        runtime=runtime,
        heli_settings=heli_settings,
        airport_runtime=airport_runtime,
        mission_choices=mission_choices,
        selected_mission_index=selected_mission_index,
        chopper_choices=chopper_choices,
        selected_chopper_index=selected_chopper_index,
        paused_hint=PAUSED_MENU_HINT,
        debug_show_overlay=debug_show_overlay,
        toast_message=str(getattr(toast, "message", "") or ""),
        flashes_enabled=bool(flashes_enabled),
        overlay=overlay,
        fps=float(fps),
        draw_intro_fn=draw_intro,
        draw_mission_cutscene_fn=draw_mission_cutscene,
        draw_sky_fn=draw_sky,
        draw_ground_fn=draw_ground,
        draw_mission_fn=draw_mission,
        draw_airport_world_overlays_fn=draw_airport_world_overlays,
        draw_flares_fn=draw_flares,
        draw_explosion_particles_fn=draw_explosion_particles,
        draw_enemy_damage_fx_fn=draw_enemy_damage_fx,
        draw_helicopter_damage_fx_fn=draw_helicopter_damage_fx,
        draw_helicopter_fn=draw_helicopter,
        draw_impact_sparks_fn=draw_impact_sparks,
        boarded_count_fn=boarded_count,
        draw_hud_fn=draw_hud,
        draw_mission_select_overlay_fn=draw_mission_select_overlay,
        draw_chopper_select_overlay_fn=draw_chopper_select_overlay,
        draw_mission_end_overlay_fn=draw_mission_end_overlay,
        shake_x=shake_x,
        shake_y=shake_y,
        draw_debug_overlay_fn=draw_debug_overlay_fn,
        draw_toast_fn=draw_toast,
        draw_damage_flash_fn=draw_damage_flash,
    )

    pygame.display.flip()

    store_frame_locals_to_context(
        loop_ctx=loop_ctx,
        mission=mission,
        helicopter=helicopter,
        accumulator=accumulator,
        prev_stats=prev_stats,
        campaign_sentiment=campaign_sentiment,
        airport_runtime=airport_runtime,
    )

    return mode
