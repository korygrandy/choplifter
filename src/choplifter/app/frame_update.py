from __future__ import annotations


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
    """Advance visual-only sky/weather systems for the current frame."""
    if not particles_enabled or mode in ("intro", "cutscene"):
        return

    sky_smoke.update(frame_dt, width=screen.get_width(), horizon_y=int(getattr(heli_settings, "ground_y", 0.0)))
    if weather_mode == "rain":
        rain.update(frame_dt, area_width=getattr(window, "width", 0), area_height=getattr(window, "height", 0))
    if weather_mode == "fog":
        fog.update(frame_dt, area_width=getattr(window, "width", 0), area_height=getattr(window, "height", 0))
    if weather_mode == "dust":
        dust.update(
            frame_dt,
            heli_pos=getattr(helicopter, "pos", None),
            heli_vel=getattr(helicopter, "vel", None),
            ground_y=getattr(heli_settings, "ground_y", 0.0),
        )
    if weather_mode == "storm":
        storm_clouds.update(frame_dt)
        rain.update(frame_dt, area_width=getattr(window, "width", 0), area_height=getattr(window, "height", 0))
        fog.update(frame_dt, area_width=getattr(window, "width", 0), area_height=getattr(window, "height", 0))
        dust.update(
            frame_dt,
            heli_pos=getattr(helicopter, "pos", None),
            heli_vel=getattr(helicopter, "vel", None),
            ground_y=getattr(heli_settings, "ground_y", 0.0),
        )
        heli_pos = getattr(helicopter, "pos", None)
        lightning.update(
            frame_dt,
            helicopter_x=float(getattr(heli_pos, "x", 0.0)),
            helicopter_y=float(getattr(heli_pos, "y", 0.0)),
        )


def compute_camera_x(*, world_width: float, view_width: float, helicopter_x: float) -> float:
    """Compute side-scrolling camera X with world bounds clamping."""
    max_cam_x = max(0.0, float(world_width) - float(view_width))
    camera_x = float(helicopter_x) - float(view_width) * 0.5
    if camera_x < 0.0:
        return 0.0
    if camera_x > max_cam_x:
        return max_cam_x
    return camera_x
