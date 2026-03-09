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


# Cache for loaded bus sprite
_bus_sprite_cache: Optional[pygame.Surface] = None
BUS_SPEED_PX_PER_SEC: float = 80.0
BUS_ACCEL_TIME_S: float = 1.4
BUS_DECEL_DISTANCE_PX: float = 240.0
BUS_STOP_X: float = -100.0


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
    
    return bus_state


def draw_airport_bus(target: pygame.Surface, bus_state: BusState, camera_x: float) -> None:
    """
    Draw the bus on screen.
    
    Args:
        target: Pygame surface to draw on
        bus_state: Current bus state
        camera_x: Camera x position for world-to-screen conversion
    """
    screen_x = int(bus_state.x - camera_x)
    screen_y = int(bus_state.y - bus_state.height)
    
    # Try to load and render the bus sprite
    sprite = _load_bus_sprite()
    if sprite:
        # Render the actual bus sprite (front already points left)
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
