from __future__ import annotations

from dataclasses import dataclass
import random


@dataclass
class WeatherRuntimeUpdateResult:
    weather_mode: str
    weather_timer: float
    weather_duration: float
    hud_disabled_timer: float
    lightning_disabled_hud: bool


@dataclass
class VipOverlayStateResult:
    vip_kia_overlay_timer: float
    vip_kia_overlay_shown: bool
    tech_kia_overlay_timer: float
    tech_kia_overlay_shown: bool


@dataclass
class FramePreambleResult:
    skip_hint: str


def advance_weather_runtime(
    *,
    debug_mode: bool,
    debug_weather_modes: list[str],
    frame_dt: float,
    weather_mode: str,
    weather_timer: float,
    weather_duration: float,
    hud_disabled_timer: float,
    rain: object,
    fog: object,
    dust: object,
    lightning: object,
    helicopter: object,
    heli_settings: object,
    window: object,
) -> WeatherRuntimeUpdateResult:
    if not debug_mode:
        weather_timer += frame_dt
        if weather_timer > weather_duration:
            weather_mode = random.choice(debug_weather_modes)
            weather_timer = 0.0
            weather_duration = random.uniform(18, 40)

    lightning_disabled_hud = False
    if weather_mode == "rain":
        rain.update(frame_dt, area_width=window.width, area_height=window.height)
    if weather_mode == "fog":
        fog.update(frame_dt, area_width=window.width, area_height=window.height)
    if weather_mode == "dust":
        dust.update(frame_dt, heli_pos=helicopter.pos, heli_vel=helicopter.vel, ground_y=heli_settings.ground_y)
    if weather_mode == "storm":
        rain.update(frame_dt, area_width=window.width, area_height=window.height)
        fog.update(frame_dt, area_width=window.width, area_height=window.height)
        hit_player, _strike_x = lightning.update(
            frame_dt,
            helicopter_x=helicopter.pos.x,
            helicopter_y=helicopter.pos.y,
        )
        if hit_player:
            hud_disabled_timer = 3.0
            lightning_disabled_hud = True
    if hud_disabled_timer > 0.0:
        hud_disabled_timer -= frame_dt

    return WeatherRuntimeUpdateResult(
        weather_mode=weather_mode,
        weather_timer=weather_timer,
        weather_duration=weather_duration,
        hud_disabled_timer=hud_disabled_timer,
        lightning_disabled_hud=lightning_disabled_hud,
    )


def update_vip_overlay_state(
    *,
    mission: object,
    vip_kia_overlay_timer: float,
    vip_kia_overlay_shown: bool,
    tech_kia_overlay_timer: float,
    tech_kia_overlay_shown: bool,
) -> VipOverlayStateResult:
    if hasattr(mission, "hostages"):
        vip_hostage = next((h for h in mission.hostages if getattr(h, "is_vip", False)), None)
        if vip_hostage:
            if vip_hostage.state.name != "KIA":
                vip_kia_overlay_shown = False
            elif vip_kia_overlay_timer <= 0.0 and not vip_kia_overlay_shown:
                vip_kia_overlay_timer = 3.0
                vip_kia_overlay_shown = True

    mission_id = str(getattr(mission, "mission_id", "")).strip().lower()
    if mission_id in ("airport", "airport_special_ops", "airportspecialops", "mission2", "m2"):
        tech_state_name = str(getattr(getattr(mission, "mission_tech", None), "state", "")).strip().lower()
        tech_kia_failure = tech_state_name == "kia"
        if not tech_kia_failure:
            tech_kia_overlay_shown = False
        elif tech_kia_overlay_timer <= 0.0 and not tech_kia_overlay_shown:
            tech_kia_overlay_timer = 3.0
            tech_kia_overlay_shown = True

    return VipOverlayStateResult(
        vip_kia_overlay_timer=vip_kia_overlay_timer,
        vip_kia_overlay_shown=vip_kia_overlay_shown,
        tech_kia_overlay_timer=tech_kia_overlay_timer,
        tech_kia_overlay_shown=tech_kia_overlay_shown,
    )


def apply_vip_overlay_update(*, runtime: object, vip_overlay_state: VipOverlayStateResult) -> None:
    """Apply VIP overlay state update results to runtime."""
    runtime.vip_kia_overlay_timer = vip_overlay_state.vip_kia_overlay_timer
    runtime.vip_kia_overlay_shown = vip_overlay_state.vip_kia_overlay_shown
    runtime.tech_kia_overlay_timer = vip_overlay_state.tech_kia_overlay_timer
    runtime.tech_kia_overlay_shown = vip_overlay_state.tech_kia_overlay_shown


def apply_weather_runtime_update(
    *,
    runtime: object,
    weather_runtime: WeatherRuntimeUpdateResult,
    set_toast: object,
) -> None:
    """Apply weather runtime outputs to mutable runtime state and optional toast."""
    runtime.weather_mode = weather_runtime.weather_mode
    runtime.weather_timer = weather_runtime.weather_timer
    runtime.weather_duration = weather_runtime.weather_duration
    runtime.hud_disabled_timer = weather_runtime.hud_disabled_timer
    if weather_runtime.lightning_disabled_hud:
        set_toast("⚡ ELECTRONIC WARFARE: HUD/Targeting disabled!")


def run_frame_preamble(
    *,
    mission: object,
    runtime: object,
    frame_dt: float,
    debug_weather_modes: list[str],
    rain: object,
    fog: object,
    dust: object,
    lightning: object,
    helicopter: object,
    heli_settings: object,
    window: object,
    joysticks: object,
    set_toast: object,
    build_skip_hint_fn: object,
) -> FramePreambleResult:
    """Apply per-frame overlay and weather bookkeeping before input/event handling."""
    vip_overlay_state = update_vip_overlay_state(
        mission=mission,
        vip_kia_overlay_timer=runtime.vip_kia_overlay_timer,
        vip_kia_overlay_shown=runtime.vip_kia_overlay_shown,
        tech_kia_overlay_timer=runtime.tech_kia_overlay_timer,
        tech_kia_overlay_shown=runtime.tech_kia_overlay_shown,
    )
    apply_vip_overlay_update(runtime=runtime, vip_overlay_state=vip_overlay_state)

    weather_runtime = advance_weather_runtime(
        debug_mode=runtime.debug_mode,
        debug_weather_modes=debug_weather_modes,
        frame_dt=frame_dt,
        weather_mode=runtime.weather_mode,
        weather_timer=runtime.weather_timer,
        weather_duration=runtime.weather_duration,
        hud_disabled_timer=runtime.hud_disabled_timer,
        rain=rain,
        fog=fog,
        dust=dust,
        lightning=lightning,
        helicopter=helicopter,
        heli_settings=heli_settings,
        window=window,
    )
    apply_weather_runtime_update(
        runtime=runtime,
        weather_runtime=weather_runtime,
        set_toast=set_toast,
    )

    return FramePreambleResult(skip_hint=build_skip_hint_fn(joysticks))


def update_weather_effects(
    *,
    particles_enabled: bool,
    mode: str,
    frame_dt: float,
    weather_mode: str,
    sky_smoke: object,
    rain: object,
    fog: object,
    dust: object,
    storm_clouds: object,
    lightning: object,
    helicopter: object,
    heli_settings: object,
    screen: object,
    window: object,
) -> None:
    """Advance visual-only weather layers that are not simulated in frame preamble."""
    if not particles_enabled or mode in ("intro", "cutscene"):
        return

    sky_smoke.update(frame_dt, width=screen.get_width(), horizon_y=int(getattr(heli_settings, "ground_y", 0.0)))

    if weather_mode == "storm":
        storm_clouds.update(frame_dt)


def compute_camera_x(*, world_width: float, view_width: float, helicopter_x: float) -> float:
    """Compute side-scrolling camera X with world bounds clamping."""
    max_cam_x = max(0.0, float(world_width) - float(view_width))
    camera_x = float(helicopter_x) - float(view_width) * 0.5
    if camera_x < 0.0:
        return 0.0
    if camera_x > max_cam_x:
        return max_cam_x
    return camera_x


@dataclass
class CameraUpdateResult:
    camera_x: float
    camera_x_smoothed: float | None


@dataclass
class FrameRenderPreparationResult:
    camera_x: float
    target: object
    shake_x: int
    shake_y: int


def update_camera_tracking(
    *,
    selected_mission_id: str,
    helicopter_x: float,
    meal_truck_driver_mode: bool,
    bus_driver_mode: bool,
    airport_meal_truck_state,
    airport_bus_state,
    camera_x_smoothed: float | None,
    frame_dt: float,
    world_width: float,
    view_width: float,
) -> CameraUpdateResult:
    """Select camera follow target and apply airport driver-mode smoothing."""
    camera_track_x = float(helicopter_x)
    airport_truck_active = bool(
        airport_meal_truck_state is not None and bool(getattr(airport_meal_truck_state, "is_active", False))
    )

    if selected_mission_id == "airport" and bool(meal_truck_driver_mode) and airport_truck_active:
        camera_track_x = float(getattr(airport_meal_truck_state, "x", camera_track_x))
    elif selected_mission_id == "airport" and bool(bus_driver_mode) and airport_bus_state is not None:
        camera_track_x = float(getattr(airport_bus_state, "x", camera_track_x))

    camera_x_target = compute_camera_x(
        world_width=world_width,
        view_width=view_width,
        helicopter_x=camera_track_x,
    )

    if (
        selected_mission_id == "airport"
        and (bool(meal_truck_driver_mode) or bool(bus_driver_mode))
        and (airport_meal_truck_state is not None or airport_bus_state is not None)
    ):
        if camera_x_smoothed is None:
            camera_x_smoothed = camera_x_target
        else:
            follow_alpha = min(1.0, frame_dt * 7.0)
            camera_x_smoothed = camera_x_smoothed + (camera_x_target - camera_x_smoothed) * follow_alpha
        camera_x = float(camera_x_smoothed)
    else:
        camera_x_smoothed = None
        camera_x = camera_x_target

    return CameraUpdateResult(
        camera_x=camera_x,
        camera_x_smoothed=camera_x_smoothed,
    )


def apply_camera_update(*, runtime: object, camera_update: CameraUpdateResult) -> float:
    """Persist camera smoothing state and return current camera x for rendering."""
    runtime.camera_x_smoothed = camera_update.camera_x_smoothed
    return float(camera_update.camera_x)


def prepare_frame_render_state(
    *,
    particles_enabled: bool,
    mode: str,
    frame_dt: float,
    runtime: object,
    selected_mission_id: str,
    mission: object,
    helicopter: object,
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
    screen: object,
    window: object,
    update_screenshake_target_fn: object,
) -> FrameRenderPreparationResult:
    """Prepare camera/audio/screenshake state used by frame rendering."""
    update_weather_effects(
        particles_enabled=particles_enabled,
        mode=mode,
        frame_dt=frame_dt,
        weather_mode=runtime.weather_mode,
        sky_smoke=sky_smoke,
        rain=rain,
        fog=fog,
        dust=dust,
        storm_clouds=storm_clouds,
        lightning=lightning,
        helicopter=helicopter,
        heli_settings=heli_settings,
        screen=screen,
        window=window,
    )

    camera_update = update_camera_tracking(
        selected_mission_id=selected_mission_id,
        helicopter_x=float(helicopter.pos.x),
        meal_truck_driver_mode=bool(runtime.meal_truck_driver_mode),
        bus_driver_mode=bool(runtime.bus_driver_mode),
        airport_meal_truck_state=airport_runtime.meal_truck_state,
        airport_bus_state=airport_runtime.bus_state,
        camera_x_smoothed=runtime.camera_x_smoothed,
        frame_dt=frame_dt,
        world_width=float(mission.world_width),
        view_width=float(screen.get_width()),
    )
    camera_x = apply_camera_update(runtime=runtime, camera_update=camera_update)

    # Update audio (ducking is applied via bus volumes).
    audio.set_cinematic_ducked(mode == "cutscene", factor=0.5)
    audio.update(frame_dt)

    # Screenshake offsets (render-time only; affects the whole frame).
    target, shake_x, shake_y = update_screenshake_target_fn(
        state=screenshake,
        frame_dt=frame_dt,
        enabled=screenshake_enabled,
        mode=mode,
        screen=screen,
    )

    return FrameRenderPreparationResult(
        camera_x=float(camera_x),
        target=target,
        shake_x=int(shake_x),
        shake_y=int(shake_y),
    )
