"""
bus_ai.py

Handles bus movement, obstacle logic, health, and repair triggers for the Airport Special Ops mission.

TODO:
- Implement AI pathing and obstacle avoidance
- Integrate bus health and damage system
- Add repair trigger logic (Mission Tech interaction)
"""

import math

import pygame
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import haptics
from .game_types import ProjectileKind
from .math2d import Vec2
from .vehicle_damage import apply_vehicle_damage, is_airport_bus_vulnerable


# Cache for loaded bus sprite
_bus_sprite_cache: Optional[pygame.Surface] = None
_bus_sprite_doors_open_cache: Optional[pygame.Surface] = None
BUS_SPEED_PX_PER_SEC: float = 80.0
BUS_ACCEL_TIME_S: float = 1.4
BUS_DECEL_DISTANCE_PX: float = 240.0
BUS_STOP_X: float = 500.0
BUS_CREEP_SPEED_PX_PER_SEC: float = 20.0
BUS_DOOR_ANIMATION_DURATION: float = 0.3  # Duration for opening/closing animation
BUS_SHIFT_JERK_DURATION_S: float = 0.18
BUS_SHIFT_SMOKE_DURATION_S: float = 0.32
_AIRPORT_ENEMY_BULLET_DAMAGE: float = 11.0
_AIRPORT_ENEMY_BOMB_DAMAGE: float = 36.0


def _clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _smoothstep01(value: float) -> float:
    """Smooth 0..1 curve used for easing in/out."""
    t = _clamp01(value)
    return t * t * (3.0 - 2.0 * t)


def _load_bus_sprite() -> Optional[pygame.Surface]:
    """Load the bus sprite from assets. Returns None if loading fails."""
    global _bus_sprite_cache
    
    if _bus_sprite_cache is not None:
        return _bus_sprite_cache
    
    try:
        module_dir = Path(__file__).resolve().parent
        bus_asset_path = module_dir / "assets" / "city-bus.png"
        _bus_sprite_cache = pygame.image.load(str(bus_asset_path)).convert_alpha()
        return _bus_sprite_cache
    except Exception:
        return None


def _load_bus_sprite_doors_open() -> Optional[pygame.Surface]:
    """Load the bus (doors open) sprite from assets. Returns None if loading fails."""
    global _bus_sprite_doors_open_cache
	
    if _bus_sprite_doors_open_cache is not None:
        return _bus_sprite_doors_open_cache
	
    try:
        module_dir = Path(__file__).resolve().parent
        bus_asset_path = module_dir / "assets" / "city-bus-doors-open.png"
        _bus_sprite_doors_open_cache = pygame.image.load(str(bus_asset_path)).convert_alpha()
        return _bus_sprite_doors_open_cache
    except Exception:
        return None


@dataclass
class BusDriverInput:
    """Player input for manually driving the bus (left/right only)."""
    move_left: bool = False
    move_right: bool = False


@dataclass
class BusState:
    """Represents the state of the bus in the Airport mission."""
    x: float              # World position x
    y: float              # World position y (typically ground_y)
    width: int = 64       # Pixel width
    height: int = 24      # Pixel height
    velocity_x: float = 0 # Speed moving left across screen (negative = moving left)
    is_moving: bool = False  # Whether bus is actively moving
    elapsed_s: float = 0.0
    start_x: float = 0.0
    stop_x: float = BUS_STOP_X
    phase: str = "stopped"       # "accelerating", "cruising", "decelerating", "stopped"
    max_health: float = 100.0
    health: float = 100.0
    
    drive_mode: str = "parked"   # "parked" / "forward" / "reset"
    driver_mode_active: bool = False  # True when player is manually driving
    # Bus door animation state machine
    door_state: str = "closed"  # closed/opening/open/closing
    door_animation_progress: float = 0.0  # 0.0 to 1.0 over 0.3 seconds
    door_animation_duration: float = 0.3  # Animation duration in seconds
    door_auto_close_timer_s: float = 0.0  # Optional hold-open timer (used for deboarding)
    door_auto_close_armed: bool = False
    shift_jerk_timer_s: float = 0.0
    shift_jerk_duration_s: float = BUS_SHIFT_JERK_DURATION_S
    shift_jerk_px: float = 0.0
    shift_smoke_timer_s: float = 0.0
    shift_smoke_duration_s: float = BUS_SHIFT_SMOKE_DURATION_S


def _trigger_shift_feedback(bus_state: BusState, *, severity: float, logger=None) -> None:
    s = _clamp01(float(severity))
    bus_state.shift_jerk_duration_s = BUS_SHIFT_JERK_DURATION_S
    bus_state.shift_smoke_duration_s = BUS_SHIFT_SMOKE_DURATION_S
    bus_state.shift_jerk_timer_s = max(float(getattr(bus_state, "shift_jerk_timer_s", 0.0)), BUS_SHIFT_JERK_DURATION_S)
    bus_state.shift_smoke_timer_s = max(float(getattr(bus_state, "shift_smoke_timer_s", 0.0)), BUS_SHIFT_SMOKE_DURATION_S)
    bus_state.shift_jerk_px = max(float(getattr(bus_state, "shift_jerk_px", 0.0)), 1.0 + 2.0 * s)
    haptics.rumble_bus_shift(severity=0.5 + 0.5 * s, logger=logger)


def _bus_door_open_blend(bus_state: BusState) -> float:
    """Return 0..1 blend weight for the doors-open sprite."""
    state = str(getattr(bus_state, "door_state", "closed"))
    progress = _clamp01(float(getattr(bus_state, "door_animation_progress", 0.0)))
    if state == "open":
        return 1.0
    if state == "opening":
        return progress
    if state == "closing":
        return 1.0 - progress
    return 0.0


def create_bus_state(start_x: float = 1200, ground_y: float = 400) -> BusState:
    """Create initial bus state at the given position."""
    # Try to get actual sprite dimensions
    sprite = _load_bus_sprite()
    if sprite:
        width = sprite.get_width()
        height = sprite.get_height()
        return BusState(x=start_x, y=ground_y, width=width, height=height, start_x=start_x)
    return BusState(x=start_x, y=ground_y, start_x=start_x)


def _run_bus_door_animation(bus_state: BusState, dt: float) -> None:
    """Advance the door open/close animation one tick."""
    door_state = getattr(bus_state, "door_state", "closed")
    was_open_at_tick_start = door_state == "open"
    door_progress = getattr(bus_state, "door_animation_progress", 0.0)
    door_duration = getattr(bus_state, "door_animation_duration", BUS_DOOR_ANIMATION_DURATION)
    if door_state == "opening":
        door_progress += dt / door_duration
        if door_progress >= 1.0:
            door_progress = 1.0
            bus_state.door_state = "open"
        bus_state.door_animation_progress = door_progress
    elif door_state == "closing":
        door_progress += dt / door_duration
        if door_progress >= 1.0:
            door_progress = 1.0
            bus_state.door_state = "closed"
        bus_state.door_animation_progress = door_progress

    if bool(getattr(bus_state, "door_auto_close_armed", False)) and was_open_at_tick_start and str(getattr(bus_state, "door_state", "closed")) == "open":
        hold = max(0.0, float(getattr(bus_state, "door_auto_close_timer_s", 0.0)) - float(dt))
        bus_state.door_auto_close_timer_s = hold
        if hold <= 0.0:
            bus_state.door_auto_close_armed = False
            close_bus_doors(bus_state)


def update_bus_ai(bus_state: BusState, dt: float, audio=None, *, mission_phase: str = "waiting_for_tech_deploy", tech_on_bus: bool = False, driver_input=None) -> BusState:
    """
    Update bus position and behavior.
    
    Args:
        bus_state: Current bus state
        dt: Delta time in seconds
        audio: Optional AudioBank instance for playing sound effects
        
    Returns:
        Updated bus state
    """
    dt_s = max(0.0, float(dt))
    bus_state.shift_jerk_timer_s = max(0.0, float(getattr(bus_state, "shift_jerk_timer_s", 0.0)) - dt_s)
    bus_state.shift_smoke_timer_s = max(0.0, float(getattr(bus_state, "shift_smoke_timer_s", 0.0)) - dt_s)

    # --- Manual driver override: player is in the bus cab ---
    if bus_state.driver_mode_active and driver_input is not None:
        if driver_input.move_left:
            bus_state.velocity_x = -BUS_SPEED_PX_PER_SEC
            bus_state.is_moving = True
            bus_state.phase = "cruising"
        elif driver_input.move_right:
            bus_state.velocity_x = BUS_SPEED_PX_PER_SEC
            bus_state.is_moving = True
            bus_state.phase = "cruising"
        else:
            bus_state.velocity_x = 0.0
            bus_state.is_moving = False
            bus_state.phase = "stopped"
        bus_state.x += bus_state.velocity_x * dt
        if bus_state.x > bus_state.start_x:
            bus_state.x = bus_state.start_x
        if bus_state.x <= bus_state.stop_x:
            bus_state.x = bus_state.stop_x
            bus_state.velocity_x = 0.0
            bus_state.is_moving = False
            bus_state.phase = "stopped"
            bus_state.drive_mode = "parked"
        _run_bus_door_animation(bus_state, dt)
        return bus_state

    # --- Phase-gated auto-drive (player is in the chopper) ---
    # ------------------------------------------------------------------
    # Phase-gated drive modes.
    # - truck_driving_to_bus: slow creep left so transfer lane is reachable
    # - escort_to_lz (+ tech_on_bus): full drive to mission stop_x
    # - auto_reset: drive right back to start_x
    # - everything else: parked
    # ------------------------------------------------------------------
    if mission_phase == "auto_reset":
        target_drive_mode = "reset"
    elif mission_phase == "truck_driving_to_bus":
        target_drive_mode = "forward"
    elif mission_phase == "escort_to_lz" and bool(tech_on_bus):
        target_drive_mode = "forward"
    else:
        target_drive_mode = "parked"

    prev_is_moving = bool(getattr(bus_state, "is_moving", False))
    if target_drive_mode != bus_state.drive_mode:
        if target_drive_mode == "forward":
            # Tech just boarded — start escort drive from rest.
            bus_state.drive_mode = "forward"
            bus_state.is_moving = True
            bus_state.elapsed_s = 0.0   # reset accel ramp
            bus_state.phase = "accelerating"
            _trigger_shift_feedback(bus_state, severity=0.45, logger=None)
            if audio is not None and hasattr(audio, "play_bus_accelerate"):
                audio.play_bus_accelerate()
        elif target_drive_mode == "reset":
            bus_state.drive_mode = "reset"
            bus_state.is_moving = True
            bus_state.phase = "cruising"
            _trigger_shift_feedback(bus_state, severity=0.50, logger=None)
            if audio is not None and hasattr(audio, "play_bus_accelerate"):
                audio.play_bus_accelerate()
        else:
            # Escort cancelled or mission over — stop the bus.
            bus_state.drive_mode = "parked"
            bus_state.is_moving = False
            bus_state.velocity_x = 0.0
            bus_state.phase = "stopped"
            if prev_is_moving and audio is not None and hasattr(audio, "play_bus_brakes"):
                audio.play_bus_brakes()

    if bus_state.is_moving and bus_state.drive_mode == "reset":
        bus_state.phase = "cruising"
        bus_state.velocity_x = BUS_SPEED_PX_PER_SEC
        bus_state.x += bus_state.velocity_x * dt

        if bus_state.x >= bus_state.start_x - 1.0:
            bus_state.x = bus_state.start_x
            bus_state.velocity_x = 0.0
            bus_state.is_moving = False
            bus_state.phase = "stopped"
            bus_state.drive_mode = "parked"

    elif bus_state.is_moving:
        prev_phase = bus_state.phase
        if mission_phase == "truck_driving_to_bus":
            # Gentle pre-transfer movement to keep the bus in the active lane.
            bus_state.phase = "cruising"
            bus_state.velocity_x = -BUS_CREEP_SPEED_PX_PER_SEC
        else:
            bus_state.elapsed_s += dt

            # Ease in from rest based on elapsed time.
            accel_factor = _smoothstep01(bus_state.elapsed_s / BUS_ACCEL_TIME_S)

            # Ease out as we approach the final stop x.
            distance_to_stop = max(0.0, bus_state.x - bus_state.stop_x)
            decel_factor = _smoothstep01(distance_to_stop / BUS_DECEL_DISTANCE_PX)

            # Determine which factor is limiting (acceleration vs deceleration)
            if accel_factor < 1.0:
                bus_state.phase = "accelerating"
            elif decel_factor < accel_factor:
                bus_state.phase = "decelerating"
            else:
                bus_state.phase = "cruising"

            # Play sounds on phase transitions
            if audio is not None:
                if prev_phase == "accelerating" and bus_state.phase == "accelerating" and bus_state.elapsed_s < dt * 1.5:
                    # Play acceleration sound once at start
                    audio.play_bus_accelerate()
                elif prev_phase != "decelerating" and bus_state.phase == "decelerating":
                    # Play brake sound when entering deceleration
                    audio.play_bus_brakes()
                    _trigger_shift_feedback(bus_state, severity=0.35, logger=None)

            speed_factor = min(accel_factor, decel_factor)
            bus_state.velocity_x = -BUS_SPEED_PX_PER_SEC * speed_factor

        bus_state.x += bus_state.velocity_x * dt

        # Snap to the final stop point when nearly there.
        if bus_state.x <= bus_state.stop_x + 1.0:
            bus_state.x = bus_state.stop_x
            bus_state.velocity_x = 0.0
            bus_state.is_moving = False
            bus_state.phase = "stopped"
            bus_state.drive_mode = "parked"  # arrived at LZ

    _run_bus_door_animation(bus_state, dt)
    if prev_is_moving and not bool(getattr(bus_state, "is_moving", False)):
        if audio is not None and hasattr(audio, "play_bus_brakes"):
            audio.play_bus_brakes()
    return bus_state


def open_bus_doors(bus_state: BusState, *, audio=None, auto_close_delay_s: float | None = None) -> None:
    """Trigger bus door opening animation."""
    current_state = getattr(bus_state, "door_state", "closed")
    if auto_close_delay_s is not None:
        bus_state.door_auto_close_timer_s = max(0.0, float(auto_close_delay_s))
        bus_state.door_auto_close_armed = True
    else:
        bus_state.door_auto_close_timer_s = 0.0
        bus_state.door_auto_close_armed = False
    if current_state in ("closed", "closing"):
        bus_state.door_state = "opening"
        bus_state.door_animation_progress = 0.0
        if audio is not None and hasattr(audio, "play_bus_door"):
            audio.play_bus_door()


def close_bus_doors(bus_state: BusState, *, audio=None) -> None:
    """Trigger bus door closing animation."""
    current_state = getattr(bus_state, "door_state", "closed")
    bus_state.door_auto_close_timer_s = 0.0
    bus_state.door_auto_close_armed = False
    if current_state in ("open", "opening"):
        bus_state.door_state = "closing"
        bus_state.door_animation_progress = 0.0
        if audio is not None and hasattr(audio, "play_bus_door"):
            audio.play_bus_door()


def are_bus_doors_open(bus_state: BusState) -> bool:
    """Check if bus doors are fully open (transfer can occur)."""
    return getattr(bus_state, "door_state", "closed") == "open"


def draw_airport_bus(target: pygame.Surface, bus_state: BusState, camera_x: float, *, boarded_count: int = 0, tech_on_bus: bool = False) -> None:
    """
    Draw the bus on screen.
    
    Args:
        target: Pygame surface to draw on
        bus_state: Current bus state
        camera_x: Camera x position for world-to-screen conversion
        boarded_count: Number of passengers currently boarded on bus
        tech_on_bus: Whether mission tech has transferred onto bus
    """
    screen_x = int(bus_state.x - camera_x)
    screen_y = int(bus_state.y - bus_state.height)

    shift_jerk_timer = max(0.0, float(getattr(bus_state, "shift_jerk_timer_s", 0.0)))
    if shift_jerk_timer > 0.0:
        jerk_duration = max(0.001, float(getattr(bus_state, "shift_jerk_duration_s", BUS_SHIFT_JERK_DURATION_S)))
        norm = max(0.0, min(1.0, shift_jerk_timer / jerk_duration))
        phase = 1.0 - norm
        amp = float(getattr(bus_state, "shift_jerk_px", 0.0))
        screen_x += int(math.sin(phase * math.pi * 2.2) * amp * norm)
    
    closed_sprite = _load_bus_sprite()
    open_sprite = _load_bus_sprite_doors_open()
    blend_open = _bus_door_open_blend(bus_state)

    if closed_sprite is not None and open_sprite is not None:
        # Cross-fade bus door sprites during opening/closing animation.
        base = closed_sprite.copy()
        if blend_open >= 0.999:
            target.blit(open_sprite, (screen_x, screen_y))
        elif blend_open <= 0.001:
            target.blit(base, (screen_x, screen_y))
        else:
            over = open_sprite.copy()
            over.set_alpha(int(255.0 * blend_open))
            base.blit(over, (0, 0))
            target.blit(base, (screen_x, screen_y))
    elif closed_sprite is not None:
        target.blit(closed_sprite, (screen_x, screen_y))
    elif open_sprite is not None:
        target.blit(open_sprite, (screen_x, screen_y))
    else:
        # Fallback: Draw bus body (blue rectangle with darker border)
        bus_rect = pygame.Rect(screen_x, screen_y, bus_state.width, bus_state.height)
        pygame.draw.rect(target, (80, 120, 200), bus_rect, border_radius=6)
        pygame.draw.rect(target, (30, 40, 60), bus_rect, 2, border_radius=6)
        
        # Draw simple wheels (two circles)
        wheel_y = screen_y + bus_state.height
        wheel_radius = 3
        pygame.draw.circle(target, (50, 50, 50), (screen_x + 12, wheel_y), wheel_radius)
        pygame.draw.circle(target, (50, 50, 50), (screen_x + 52, wheel_y), wheel_radius)

    max_health = float(getattr(bus_state, "max_health", 100.0) or 100.0)
    health = max(0.0, float(getattr(bus_state, "health", max_health)))
    ratio = health / max_health if max_health > 0.0 else 0.0
    shift_smoke_timer = max(0.0, float(getattr(bus_state, "shift_smoke_timer_s", 0.0)))
    if shift_smoke_timer > 0.0:
        shift_smoke_duration = max(0.001, float(getattr(bus_state, "shift_smoke_duration_s", BUS_SHIFT_SMOKE_DURATION_S)))
        t_norm = max(0.0, min(1.0, shift_smoke_timer / shift_smoke_duration))
        smoke_alpha = int(30 + 35 * t_norm)
        puffs = pygame.Surface((24, 14), pygame.SRCALPHA)
        wobble = math.sin(float(getattr(bus_state, "elapsed_s", 0.0)) * 16.0) * 1.5
        pygame.draw.circle(puffs, (70, 70, 70, smoke_alpha), (7, 8), 4)
        pygame.draw.circle(puffs, (65, 65, 65, int(smoke_alpha * 0.75)), (13, int(6 + wobble)), 4)
        target.blit(puffs, (screen_x + 4, screen_y + bus_state.height - 4))
    if ratio <= 0.70:
        smoke = pygame.Surface((20, 12), pygame.SRCALPHA)
        smoke_alpha = 95 if ratio > 0.35 else 155
        pygame.draw.circle(smoke, (55, 55, 55, smoke_alpha), (8, 6), 5)
        target.blit(smoke, (screen_x + bus_state.width - 10, screen_y - 10))
    if ratio <= 0.35:
        fire_x = screen_x + bus_state.width - 3
        fire_y = screen_y + 6
        pygame.draw.circle(target, (255, 142, 64), (fire_x, fire_y), 4)
        pygame.draw.circle(target, (255, 220, 130), (fire_x, fire_y), 2)

    # Passenger count indicator above bus after transfer.
    if int(boarded_count) > 0:
        label = f"x{int(boarded_count)}"
        try:
            font = pygame.font.SysFont("Consolas", 16, bold=True)
        except Exception:
            font = pygame.font.Font(None, 20)
        text = font.render(label, True, (255, 235, 205))
        text_rect = text.get_rect(center=(screen_x + bus_state.width // 2, screen_y - 18))
        bg_rect = text_rect.inflate(8, 4)
        pygame.draw.rect(target, (20, 24, 30, 190), bg_rect, border_radius=4)
        pygame.draw.rect(target, (90, 100, 120), bg_rect, 1, border_radius=4)
        target.blit(text, text_rect)

    # Mission Tech badge above bus once engineer has boarded.
    if bool(tech_on_bus):
        badge_center = (screen_x + bus_state.width // 2 + 28, screen_y - 18)
        pygame.draw.circle(target, (24, 30, 26), badge_center, 8)
        pygame.draw.circle(target, (140, 225, 140), badge_center, 8, 2)
        # Tiny wrench-like icon.
        pygame.draw.rect(target, (170, 235, 170), pygame.Rect(badge_center[0] - 1, badge_center[1] - 4, 2, 6))
        pygame.draw.rect(target, (170, 235, 170), pygame.Rect(badge_center[0] - 4, badge_center[1] - 5, 6, 2))


def _closest_alive_raider_in_bus_lz(bus_left: float, bus_top: float, bus_right: float, bus_bottom: float, projectile, mission) -> object | None:
    """Return the alive raider overlapping the bus art that best matches the shot.

    When a raider sprite overlaps the bus silhouette, player fire should resolve
    against the raider before the bus. Preference is given to the raider nearest
    the projectile position so overlap hits feel consistent.
    """
    enemy_state = getattr(mission, "airport_enemy_state", None)
    enemies = getattr(enemy_state, "enemies", None)
    if not enemies:
        return None

    projectile_pos = getattr(projectile, "pos", None)
    shot_x = float(getattr(projectile_pos, "x", (bus_left + bus_right) * 0.5))
    shot_y = float(getattr(projectile_pos, "y", (bus_top + bus_bottom) * 0.5))

    best = None
    best_score = float("inf")
    for e in enemies:
        if str(getattr(e, "kind", "")).lower() != "raider":
            continue
        if float(getattr(e, "health", 1.0)) <= 0.0:
            continue

        ex = float(getattr(e, "x", -99999.0))
        ey = float(getattr(e, "y", -99999.0))
        raider_left = ex - 18.0
        raider_right = ex + 18.0
        raider_top = ey - 24.0
        raider_bottom = ey

        overlaps_bus = (
            raider_right >= bus_left
            and raider_left <= bus_right
            and raider_bottom >= bus_top
            and raider_top <= bus_bottom
        )
        if not overlaps_bus:
            continue

        dx = 0.0
        if shot_x < raider_left:
            dx = raider_left - shot_x
        elif shot_x > raider_right:
            dx = shot_x - raider_right

        dy = 0.0
        if shot_y < raider_top:
            dy = raider_top - shot_y
        elif shot_y > raider_bottom:
            dy = shot_y - raider_bottom

        score = dx * dx + dy * dy
        if score < best_score:
            best_score = score
            best = e
    return best


def apply_airport_bus_friendly_fire(bus_state: BusState | None, mission, *, logger=None) -> int:
    """Apply player projectile hits on the airport bus.

    When an alive raider occupies the bus LZ the hit is routed to the raider
    instead, matching player expectation that visible targets absorb damage.

    Returns the number of friendly-fire hits consumed this tick.
    """
    if bus_state is None or mission is None:
        return 0

    projectiles = getattr(mission, "projectiles", None)
    if not projectiles:
        return 0

    bus_left = float(getattr(bus_state, "x", 0.0))
    bus_top = float(getattr(bus_state, "y", 0.0)) - float(getattr(bus_state, "height", 24))
    bus_right = bus_left + float(getattr(bus_state, "width", 64))
    bus_bottom = float(getattr(bus_state, "y", 0.0))

    hits = 0
    can_damage_bus = is_airport_bus_vulnerable(mission)
    for p in projectiles:
        if not bool(getattr(p, "alive", False)):
            continue
        if getattr(p, "kind", None) not in (ProjectileKind.BULLET, ProjectileKind.BOMB):
            continue

        px = float(getattr(getattr(p, "pos", None), "x", -99999.0))
        py = float(getattr(getattr(p, "pos", None), "y", -99999.0))
        if not (bus_left <= px <= bus_right and bus_top <= py <= bus_bottom):
            continue

        # If an alive raider occupies the bus LZ, route the hit to the raider.
        raider = _closest_alive_raider_in_bus_lz(bus_left, bus_top, bus_right, bus_bottom, p, mission)
        if raider is not None:
            damage = _AIRPORT_ENEMY_BOMB_DAMAGE if getattr(p, "kind", None) is ProjectileKind.BOMB else _AIRPORT_ENEMY_BULLET_DAMAGE
            result = apply_vehicle_damage(
                raider,
                damage,
                default_max_health=float(getattr(raider, "max_health", 52.0) or 52.0),
                source="friendly_fire_redirect",
            )
            if result.destroyed_now:
                stats = getattr(mission, "stats", None)
                if stats is not None:
                    try:
                        stats.enemies_destroyed += 1
                    except Exception:
                        pass
                explosions = getattr(mission, "explosions", None)
                if explosions is not None and hasattr(explosions, "emit_explosion"):
                    try:
                        explosions.emit_explosion(
                            Vec2(float(getattr(raider, "x", 0.0)), float(getattr(raider, "y", 0.0)) - 8.0),
                            strength=0.58,
                        )
                    except Exception:
                        pass
            p.alive = False
            hits += 1
            sparks = getattr(mission, "impact_sparks", None)
            if sparks is not None and hasattr(sparks, "emit_hit"):
                try:
                    sparks.emit_hit(p.pos, p.vel, strength=0.8)
                except Exception:
                    pass
            continue

        damage = 18.0 if getattr(p, "kind", None) is ProjectileKind.BOMB else 4.0
        apply_vehicle_damage(
            bus_state,
            damage,
            default_max_health=float(getattr(bus_state, "max_health", 100.0) or 100.0),
            allow_damage=can_damage_bus,
            source="friendly_fire",
        )
        p.alive = False
        hits += 1

        sparks = getattr(mission, "impact_sparks", None)
        if sparks is not None and hasattr(sparks, "emit_hit"):
            try:
                sparks.emit_hit(p.pos, p.vel, strength=0.8)
            except Exception:
                pass

    if hits > 0 and logger is not None:
        logger.info(
            "AIRPORT_BUS_FRIENDLY_FIRE: hits=%d health=%.1f vulnerable=%s",
            hits,
            float(getattr(bus_state, "health", 0.0)),
            can_damage_bus,
        )

    return hits
