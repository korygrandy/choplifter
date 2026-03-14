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
	max_health: float = 120.0
	health: float = 120.0
	damage_state: str = "nominal"
	damage_flash_s: float = 0.0
	destroyed: bool = False
	speed_px_per_s: float = 66.0
	plane_lz_x: float = 1500.0  # Elevated bunker (compound index 1)
	is_active: bool = True  # Always visible, controls whether truck is operational
	at_plane_lz: bool = False
	extension_progress: float = 0.0
	tech_has_deployed: bool = False  # Controls whether truck starts driving
	
	# Box animation state machine (three-layer rendering system)
	box_state: str = "idle"  # idle/extending/extended/retracting
	box_animation_progress: float = 0.0  # 0.0 to 1.0 over 1.8 seconds
	box_animation_duration: float = 1.8  # Animation duration in seconds
	
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
_flipped_surface_cache: dict[int, pygame.Surface] = {}


def _load_sprite(name: str) -> Optional[pygame.Surface]:
	try:
		asset_dir = Path(__file__).resolve().parent / "assets"
		return pygame.image.load(str(asset_dir / name)).convert_alpha()
	except Exception:
		return None


def _ensure_meal_truck_sprites() -> None:
	global _meal_cart_sprite, _meal_cart_box_sprite, _meal_cart_extended_sprite
	reloaded = False
	if _meal_cart_sprite is None:
		_meal_cart_sprite = _load_sprite("airport-meal-cart.png")
		reloaded = True
	if _meal_cart_box_sprite is None:
		_meal_cart_box_sprite = _load_sprite("airport-meal-cart-box.png")
		reloaded = True
	if _meal_cart_extended_sprite is None:
		_meal_cart_extended_sprite = _load_sprite("airport-meal-cart-extended.png")
		reloaded = True
	if reloaded:
		_flipped_surface_cache.clear()


def _get_facing_surface(base: Optional[pygame.Surface], *, facing_right: bool) -> Optional[pygame.Surface]:
	if base is None:
		return None
	if not facing_right:
		return base

	key = id(base)
	cached = _flipped_surface_cache.get(key)
	if cached is not None:
		return cached

	flipped = pygame.transform.flip(base, True, False)
	_flipped_surface_cache[key] = flipped
	if len(_flipped_surface_cache) > 16:
		_flipped_surface_cache.clear()
		_flipped_surface_cache[key] = flipped
	return flipped


def create_airport_meal_truck_state(*, start_x: float, ground_y: float, plane_lz_x: float = 1500.0) -> AirportMealTruckState:
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
		meal_truck_state.tech_has_deployed = tech_state_name in (
			"deployed_to_truck",
			"driving_to_extraction",
			"extracting",
			"transferring",
			"boarding_bus",
		)

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
		
		# Driver control of lift extension (using doors/open trigger) - triggers box state machine
		current_box_state = getattr(meal_truck_state, "box_state", "idle")
		if driver_input.extend_lift:
			# Request extension if not already extending/extended
			if current_box_state in ("idle", "retracting"):
				meal_truck_state.box_state = "extending"
				meal_truck_state.box_animation_progress = 0.0
		else:
			# Request retraction if currently extended/extending
			if current_box_state in ("extended", "extending"):
				meal_truck_state.box_state = "retracting"
				meal_truck_state.box_animation_progress = 0.0
	else:
		# Normal (non-driver) mode: truck auto-drives and extends automatically
		# Truck only drives after tech has deployed
		auto_target_x = float(meal_truck_state.plane_lz_x)
		tech_state_name = str(getattr(tech_state, "state", "")) if tech_state is not None else ""
		if tech_state_name in ("transferring", "boarding_bus") and bus_state is not None:
			# After elevated loading is complete, return to bus transfer lane autonomously.
			auto_target_x = float(getattr(bus_state, "x", meal_truck_state.x)) + 20.0

		if meal_truck_state.tech_has_deployed and abs(float(meal_truck_state.x) - auto_target_x) > 2.0:
			dx = auto_target_x - meal_truck_state.x
			step = meal_truck_state.speed_px_per_s * dt
			if abs(dx) <= step:
				meal_truck_state.x = auto_target_x
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
	
	# Box animation state machine (1.8 second animation for 53 pixel vertical movement)
	# This runs regardless of driver mode - handles the actual animation timing
	# Keep plane-LZ detection position-based so manual driver mode can still trigger LZ systems.
	plane_lz_snap_radius = 34.0
	meal_truck_state.at_plane_lz = abs(float(meal_truck_state.x) - float(meal_truck_state.plane_lz_x)) <= plane_lz_snap_radius

	box_state = getattr(meal_truck_state, "box_state", "idle")
	box_progress = getattr(meal_truck_state, "box_animation_progress", 0.0)
	box_duration = getattr(meal_truck_state, "box_animation_duration", 1.8)
	
	if box_state == "extending":
		box_progress += dt / box_duration
		if box_progress >= 1.0:
			box_progress = 1.0
			meal_truck_state.box_state = "extended"
		meal_truck_state.box_animation_progress = box_progress
		meal_truck_state.extension_progress = box_progress  # Legacy field sync
	elif box_state == "retracting":
		box_progress += dt / box_duration
		if box_progress >= 1.0:
			box_progress = 1.0
			meal_truck_state.box_state = "idle"
		meal_truck_state.box_animation_progress = box_progress
		meal_truck_state.extension_progress = 1.0 - box_progress  # Legacy field sync
	elif box_state == "extended":
		meal_truck_state.extension_progress = 1.0  # Legacy field sync
	else:  # idle
		meal_truck_state.extension_progress = 0.0  # Legacy field sync

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
	facing_right = bool(getattr(meal_truck_state, "facing_right", True))
	
	# Get box animation state for three-layer rendering
	box_state = getattr(meal_truck_state, "box_state", "idle")
	box_progress = max(0.0, min(1.0, float(getattr(meal_truck_state, "box_animation_progress", 0.0))))
	
	# Calculate box position while the box is actively moving.
	if box_state == "extending":
		box_y_offset = int(-53.0 * box_progress)
	elif box_state == "retracting":
		box_y_offset = int(-53.0 * (1.0 - box_progress))
	elif box_state == "extended":
		box_y_offset = -53
	else:  # idle
		box_y_offset = 0
	
	# Body sprite swap behavior:
	# - `extended`: use airport-meal-cart-extended.png
	# - all other states: use airport-meal-cart.png
	if box_state == "extended" and _meal_cart_extended_sprite is not None:
		body_sprite = _get_facing_surface(_meal_cart_extended_sprite, facing_right=facing_right)
		target.blit(body_sprite, (x, y))
	elif _meal_cart_sprite is not None:
		body_sprite = _get_facing_surface(_meal_cart_sprite, facing_right=facing_right)
		target.blit(body_sprite, (x, y))
	else:
		# Fallback body rectangle
		pygame.draw.rect(target, (220, 220, 230), pygame.Rect(x, y, 72, 24), border_radius=3)
		pygame.draw.rect(target, (20, 20, 25), pygame.Rect(x, y, 72, 24), 1, border_radius=3)
	
	# Moving box overlay must stay top-most during slide up/down animation.
	if _meal_cart_box_sprite is not None and box_state in ("extending", "retracting"):
		box_sprite = _get_facing_surface(_meal_cart_box_sprite, facing_right=facing_right)
		target.blit(box_sprite, (x, y + box_y_offset))

	max_health = float(getattr(meal_truck_state, "max_health", 120.0) or 120.0)
	health = max(0.0, float(getattr(meal_truck_state, "health", max_health)))
	ratio = health / max_health if max_health > 0.0 else 0.0
	if ratio <= 0.70:
		smoke = pygame.Surface((18, 10), pygame.SRCALPHA)
		smoke_alpha = 90 if ratio > 0.35 else 150
		pygame.draw.circle(smoke, (58, 58, 58, smoke_alpha), (8, 5), 4)
		engine_x = x + (8 if facing_right else int(getattr(meal_truck_state, "width", 78)) - 12)
		target.blit(smoke, (engine_x - 6, y - 9))
	if ratio <= 0.35:
		engine_x = x + (8 if facing_right else int(getattr(meal_truck_state, "width", 78)) - 12)
		engine_y = y + 7
		pygame.draw.circle(target, (255, 145, 70), (engine_x, engine_y), 3)
		pygame.draw.circle(target, (255, 220, 130), (engine_x, engine_y), 1)
