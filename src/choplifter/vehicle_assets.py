"""Airport mission vehicle assets and the meal-truck gameplay state."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pygame


@dataclass
class AirportMealTruckState:
	x: float
	y: float
	width: int = 78
	height: int = 28
	speed_px_per_s: float = 66.0
	plane_lz_x: float = 1232.0
	is_active: bool = True  # Always visible, controls whether truck is operational
	at_plane_lz: bool = False
	extension_progress: float = 0.0
	tech_has_deployed: bool = False  # Controls whether truck starts driving
	
	# Driver mode state (player can control truck when in driver mode)
	driver_mode_active: bool = False
	driver_mode_exit_timer: float = 0.0  # Prevents rapid mode switching
	heli_proximity: float = 999999.0  # Distance to helicopter in pixels
	use_extended_visual: bool = False  # Hysteresis latch to avoid render flicker at threshold
	facing_right: bool = True  # Sprite orientation based on driving direction


@dataclass
class TruckDriverInput:
	"""Input for controlling the meal truck instead of helicopter."""
	move_left: bool = False
	move_right: bool = False
	extend_lift: bool = False


_meal_cart_sprite: Optional[pygame.Surface] = None
_meal_cart_box_sprite: Optional[pygame.Surface] = None
_meal_cart_extended_sprite: Optional[pygame.Surface] = None


def _load_sprite(name: str) -> Optional[pygame.Surface]:
	try:
		asset_dir = Path(__file__).resolve().parent / "assets"
		return pygame.image.load(str(asset_dir / name)).convert_alpha()
	except Exception:
		return None


def _ensure_meal_truck_sprites() -> None:
	global _meal_cart_sprite, _meal_cart_box_sprite, _meal_cart_extended_sprite
	if _meal_cart_sprite is None:
		_meal_cart_sprite = _load_sprite("airport-meal-cart.png")
	if _meal_cart_box_sprite is None:
		_meal_cart_box_sprite = _load_sprite("airport-meal-cart-box.png")
	if _meal_cart_extended_sprite is None:
		_meal_cart_extended_sprite = _load_sprite("airport-meal-cart-extended.png")


def create_airport_meal_truck_state(*, start_x: float, ground_y: float, plane_lz_x: float = 1232.0) -> AirportMealTruckState:
	_ensure_meal_truck_sprites()
	width = _meal_cart_sprite.get_width() if _meal_cart_sprite is not None else 78
	height = _meal_cart_sprite.get_height() if _meal_cart_sprite is not None else 28
	return AirportMealTruckState(
		x=float(start_x),
		y=float(ground_y),
		width=int(width),
		height=int(height),
		plane_lz_x=float(plane_lz_x),
	)


def update_airport_meal_truck(
	meal_truck_state: AirportMealTruckState | None,
	dt: float,
	*,
	helicopter=None,
	tech_state=None,
	bus_state=None,
	driver_input: TruckDriverInput | None = None,
) -> AirportMealTruckState:
	if meal_truck_state is None:
		start_x = float(getattr(bus_state, "x", 1180.0)) - 90.0
		ground_y = float(getattr(bus_state, "y", 400.0))
		meal_truck_state = create_airport_meal_truck_state(start_x=start_x, ground_y=ground_y)

	dt = max(0.0, float(dt))
	if bus_state is not None:
		meal_truck_state.y = float(getattr(bus_state, "y", meal_truck_state.y))

	# Update helicopter proximity for driver mode detection
	if helicopter is not None:
		heli_x = float(getattr(helicopter, "x", 0.0) if hasattr(helicopter, "x") else getattr(helicopter, "pos", {}).x if hasattr(getattr(helicopter, "pos", None), "x") else 0.0)
		heli_y = float(getattr(helicopter, "y", 0.0) if hasattr(helicopter, "y") else getattr(helicopter, "pos", {}).y if hasattr(getattr(helicopter, "pos", None), "y") else 0.0)
		truck_x = meal_truck_state.x
		truck_y = meal_truck_state.y
		dx = heli_x - truck_x
		dy = heli_y - truck_y
		proximity = (dx * dx + dy * dy) ** 0.5
		meal_truck_state.heli_proximity = proximity
	
	# Driver mode exit timer countdown
	if meal_truck_state.driver_mode_active:
		meal_truck_state.driver_mode_exit_timer = max(0.0, meal_truck_state.driver_mode_exit_timer - dt)

	# Check if tech has been deployed to truck (activates truck driving)
	if tech_state is not None:
		tech_state_name = str(getattr(tech_state, "state", "on_chopper"))
		# Tech is deployed if state is anything except "on_chopper"
		if tech_state_name != "on_chopper":
			meal_truck_state.tech_has_deployed = True

	# In driver mode, use driver input to control truck movement and lift
	if meal_truck_state.driver_mode_active and driver_input is not None:
		# Driver mode movement (left/right arrows move truck)
		driver_speed = meal_truck_state.speed_px_per_s * 0.8  # Slower than auto-drive
		if driver_input.move_left:
			meal_truck_state.x -= driver_speed * dt
			meal_truck_state.facing_right = False
		elif driver_input.move_right:
			meal_truck_state.x += driver_speed * dt
			meal_truck_state.facing_right = True
		
		# Driver control of lift extension (using doors/open trigger)
		lift_extend_rate = 2.0  # Slightly faster than auto-extend
		if driver_input.extend_lift:
			meal_truck_state.extension_progress = min(1.0, meal_truck_state.extension_progress + lift_extend_rate * dt)
		else:
			meal_truck_state.extension_progress = max(0.0, meal_truck_state.extension_progress - lift_extend_rate * dt)
	else:
		# Normal (non-driver) mode: truck auto-drives and extends automatically
		# Truck only drives after tech has deployed
		if meal_truck_state.tech_has_deployed and not meal_truck_state.at_plane_lz:
			dx = meal_truck_state.plane_lz_x - meal_truck_state.x
			step = meal_truck_state.speed_px_per_s * dt
			if abs(dx) <= step:
				meal_truck_state.x = meal_truck_state.plane_lz_x
				meal_truck_state.at_plane_lz = True
			else:
				meal_truck_state.x += step if dx > 0.0 else -step
				meal_truck_state.facing_right = dx > 0.0

		# Box extension is manual-only in driver mode.
		# In non-driver mode, keep retracting toward closed so boarding the truck does not auto-extend.
		target_extension = 0.0
		extend_rate = 1.7
		if target_extension > meal_truck_state.extension_progress:
			meal_truck_state.extension_progress = min(target_extension, meal_truck_state.extension_progress + extend_rate * dt)
		else:
			meal_truck_state.extension_progress = max(target_extension, meal_truck_state.extension_progress - extend_rate * dt)

	# Visual hysteresis: once extended sprite is shown, keep it until mostly retracted.
	# This prevents rapid flicker when progress hovers around the switch threshold.
	progress = float(meal_truck_state.extension_progress)
	if bool(getattr(meal_truck_state, "use_extended_visual", False)):
		if progress <= 0.90:
			meal_truck_state.use_extended_visual = False
	else:
		if progress >= 0.985:
			meal_truck_state.use_extended_visual = True

	return meal_truck_state


def get_airport_priority_target_x(*, bus_state=None, meal_truck_state=None, tech_state=None) -> float:
	# Enemy retargeting: prioritize meal truck when tech has deployed to it
	tech_has_deployed = False
	if tech_state is not None:
		tech_state_name = str(getattr(tech_state, "state", "on_chopper"))
		tech_has_deployed = tech_state_name != "on_chopper"
	
	if (
		meal_truck_state is not None
		and bool(getattr(meal_truck_state, "tech_has_deployed", False))
		and tech_has_deployed
	):
		return float(getattr(meal_truck_state, "x", 0.0))
	return float(getattr(bus_state, "x", 0.0)) if bus_state is not None else 0.0


def should_activate_truck_driver_mode(
	*,
	meal_truck_state: AirportMealTruckState | None = None,
	doors_button_pressed: bool = False,
) -> bool:
	"""Check if player should enter truck driver mode.
	
	Conditions:
	- Doors button is being pressed (doors trigger as entry point)
	- Helicopter is within ~150px of truck
	- Tech has already deployed to truck
	- Not already in driver mode
	"""
	if meal_truck_state is None or not doors_button_pressed:
		return False
	
	# Need tech deployed and within reasonable proximity
	if not bool(getattr(meal_truck_state, "tech_has_deployed", False)):
		return False
	
	# Must be close enough to interact (within 150px)
	proximity = float(getattr(meal_truck_state, "heli_proximity", 999999.0))
	if proximity > 150.0:
		return False
	
	# Not already in driver mode
	if bool(getattr(meal_truck_state, "driver_mode_active", False)):
		return False
	
	# Don't activate if exit timer is active (prevents rapid switching)
	if float(getattr(meal_truck_state, "driver_mode_exit_timer", 0.0)) > 0.0:
		return False
	
	return True


def should_deactivate_truck_driver_mode(
	*,
	meal_truck_state: AirportMealTruckState | None = None,
	doors_button_pressed: bool = False,
) -> bool:
	"""Check if player should exit truck driver mode.
	
	Exit when doors button is pressed again while already in driver mode.
	"""
	if meal_truck_state is None:
		return False
	
	if not bool(getattr(meal_truck_state, "driver_mode_active", False)):
		return False
	
	# Exit on doors button press (press again to exit)
	return doors_button_pressed


def draw_airport_meal_truck(target: pygame.Surface, meal_truck_state, *, camera_x: float) -> None:
	if meal_truck_state is None or not bool(getattr(meal_truck_state, "is_active", False)):
		return

	_ensure_meal_truck_sprites()
	x = int(float(getattr(meal_truck_state, "x", 0.0)) - float(camera_x))
	y = int(float(getattr(meal_truck_state, "y", 0.0)) - int(getattr(meal_truck_state, "height", 28)))
	progress = max(0.0, min(1.0, float(getattr(meal_truck_state, "extension_progress", 0.0))))
	facing_right = bool(getattr(meal_truck_state, "facing_right", True))

	# Two-state rendering: retracted vs extended with fade transition
	if progress <= 0.0:
		# Retracted state: draw base truck sprite
		if _meal_cart_sprite is not None:
			sprite = pygame.transform.flip(_meal_cart_sprite, True, False) if facing_right else _meal_cart_sprite
			target.blit(sprite, (x, y))
		else:
			pygame.draw.rect(target, (220, 220, 230), pygame.Rect(x, y, 72, 24), border_radius=3)
			pygame.draw.rect(target, (20, 20, 25), pygame.Rect(x, y, 72, 24), 1, border_radius=3)
	else:
		# Extended state: draw extended sprite with fade based on progress
		if _meal_cart_extended_sprite is not None:
			sprite = pygame.transform.flip(_meal_cart_extended_sprite, True, False) if facing_right else _meal_cart_extended_sprite
			alpha = max(0, min(255, int(255 * progress)))
			sprite_with_alpha = sprite.copy()
			sprite_with_alpha.set_alpha(alpha)
			target.blit(sprite_with_alpha, (x, y))
		else:
			# Fallback: draw base sprite if extended sprite missing
			pygame.draw.rect(target, (220, 220, 230), pygame.Rect(x, y, 72, 24), border_radius=3)
			pygame.draw.rect(target, (20, 20, 25), pygame.Rect(x, y, 72, 24), 1, border_radius=3)
