"""
bus_ai.py

Handles bus movement, obstacle logic, health, and repair triggers for the Airport Special Ops mission.

TODO:
- Implement AI pathing and obstacle avoidance
- Integrate bus health and damage system
- Add repair trigger logic (Mission Tech interaction)
"""

import pygame
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .game_types import ProjectileKind


# Cache for loaded bus sprite
_bus_sprite_cache: Optional[pygame.Surface] = None
_bus_sprite_doors_open_cache: Optional[pygame.Surface] = None
BUS_SPEED_PX_PER_SEC: float = 80.0
BUS_ACCEL_TIME_S: float = 1.4
BUS_DECEL_DISTANCE_PX: float = 240.0
BUS_STOP_X: float = 500.0


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
class BusState:
    """Represents the state of the bus in the Airport mission."""
    x: float              # World position x
    y: float              # World position y (typically ground_y)
    width: int = 64       # Pixel width
    height: int = 24      # Pixel height
    velocity_x: float = 0 # Speed moving left across screen (negative = moving left)
    is_moving: bool = True  # Whether bus is actively moving
    elapsed_s: float = 0.0
    start_x: float = 0.0
    stop_x: float = BUS_STOP_X
    phase: str = "accelerating"  # "accelerating", "cruising", "decelerating", "stopped"
    max_health: float = 100.0
    health: float = 100.0
    
    # Bus door animation state machine
    door_state: str = "closed"  # closed/opening/open/closing
    door_animation_progress: float = 0.0  # 0.0 to 1.0 over 0.3 seconds
    door_animation_duration: float = 0.3  # Animation duration in seconds


def create_bus_state(start_x: float = 1200, ground_y: float = 400) -> BusState:
    """Create initial bus state at the given position."""
    # Try to get actual sprite dimensions
    sprite = _load_bus_sprite()
    if sprite:
        width = sprite.get_width()
        height = sprite.get_height()
        return BusState(x=start_x, y=ground_y, width=width, height=height, start_x=start_x)
    return BusState(x=start_x, y=ground_y, start_x=start_x)


def update_bus_ai(bus_state: BusState, dt: float, audio=None) -> BusState:
    """
    Update bus position and behavior.
    
    Args:
        bus_state: Current bus state
        dt: Delta time in seconds
        audio: Optional AudioBank instance for playing sound effects
        
    Returns:
        Updated bus state
    """
    if bus_state.is_moving:
        prev_phase = bus_state.phase
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

        speed_factor = min(accel_factor, decel_factor)
        bus_state.velocity_x = -BUS_SPEED_PX_PER_SEC * speed_factor
        bus_state.x += bus_state.velocity_x * dt

        # Snap to the final stop point when nearly there.
        if bus_state.x <= bus_state.stop_x + 1.0:
            bus_state.x = bus_state.stop_x
            bus_state.velocity_x = 0.0
            bus_state.is_moving = False
            bus_state.phase = "stopped"
    
    # Door animation state machine (0.3 second animation)
    door_state = getattr(bus_state, "door_state", "closed")
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
    
    return bus_state


def open_bus_doors(bus_state: BusState, *, audio=None) -> None:
    """Trigger bus door opening animation."""
    current_state = getattr(bus_state, "door_state", "closed")
    if current_state == "closed":
        bus_state.door_state = "opening"
        bus_state.door_animation_progress = 0.0
        if audio is not None and hasattr(audio, "play_bus_door"):
            audio.play_bus_door()


def close_bus_doors(bus_state: BusState, *, audio=None) -> None:
    """Trigger bus door closing animation."""
    current_state = getattr(bus_state, "door_state", "closed")
    if current_state == "open":
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
    
    # Select sprite based on door state (closed vs open/opening/closing)
    door_state = getattr(bus_state, "door_state", "closed")
    if door_state in ("open", "opening", "closing"):
        sprite = _load_bus_sprite_doors_open()
    else:  # closed
        sprite = _load_bus_sprite()
    
    if sprite is not None:
        # Render the selected bus sprite (front already points left)
        target.blit(sprite, (screen_x, screen_y))
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


def apply_airport_bus_friendly_fire(bus_state: BusState | None, mission, *, logger=None) -> int:
    """Apply player projectile hits on the airport bus.

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
    for p in projectiles:
        if not bool(getattr(p, "alive", False)):
            continue
        if getattr(p, "kind", None) not in (ProjectileKind.BULLET, ProjectileKind.BOMB):
            continue

        px = float(getattr(getattr(p, "pos", None), "x", -99999.0))
        py = float(getattr(getattr(p, "pos", None), "y", -99999.0))
        if not (bus_left <= px <= bus_right and bus_top <= py <= bus_bottom):
            continue

        damage = 18.0 if getattr(p, "kind", None) is ProjectileKind.BOMB else 4.0
        health = float(getattr(bus_state, "health", 100.0))
        setattr(bus_state, "health", max(0.0, health - damage))
        p.alive = False
        hits += 1

        sparks = getattr(mission, "impact_sparks", None)
        if sparks is not None and hasattr(sparks, "emit_hit"):
            try:
                sparks.emit_hit(p.pos, p.vel, strength=0.8)
            except Exception:
                pass

    if hits > 0 and logger is not None:
        logger.info("AIRPORT_BUS_FRIENDLY_FIRE: hits=%d health=%.1f", hits, float(getattr(bus_state, "health", 0.0)))

    return hits
BUS_DOOR_ANIMATION_DURATION: float = 0.3  # Duration for opening/closing animation
