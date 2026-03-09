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
) -> AirportMealTruckState:
	if meal_truck_state is None:
		start_x = float(getattr(bus_state, "x", 1180.0)) - 90.0
		ground_y = float(getattr(bus_state, "y", 400.0))
		meal_truck_state = create_airport_meal_truck_state(start_x=start_x, ground_y=ground_y)

	dt = max(0.0, float(dt))
	if bus_state is not None:
		meal_truck_state.y = float(getattr(bus_state, "y", meal_truck_state.y))

	# Check if tech has been deployed to truck (activates truck driving)
	if tech_state is not None:
		tech_state_name = str(getattr(tech_state, "state", "on_chopper"))
		# Tech is deployed if state is anything except "on_chopper"
		if tech_state_name != "on_chopper":
			meal_truck_state.tech_has_deployed = True

	# Truck only drives after tech has deployed
	if meal_truck_state.tech_has_deployed and not meal_truck_state.at_plane_lz:
		dx = meal_truck_state.plane_lz_x - meal_truck_state.x
		step = meal_truck_state.speed_px_per_s * dt
		if abs(dx) <= step:
			meal_truck_state.x = meal_truck_state.plane_lz_x
			meal_truck_state.at_plane_lz = True
		else:
			meal_truck_state.x += step if dx > 0.0 else -step

	# Box extension: extends when at plane LZ and tech is still operating (not yet transfer_complete)
	tech_still_operating = False
	if tech_state is not None:
		tech_state_name = str(getattr(tech_state, "state", "on_chopper"))
		tech_still_operating = tech_state_name not in ("on_chopper", "transfer_complete")
	
	target_extension = 1.0 if meal_truck_state.at_plane_lz and tech_still_operating else 0.0
	extend_rate = 1.7
	if target_extension > meal_truck_state.extension_progress:
		meal_truck_state.extension_progress = min(target_extension, meal_truck_state.extension_progress + extend_rate * dt)
	else:
		meal_truck_state.extension_progress = max(target_extension, meal_truck_state.extension_progress - extend_rate * dt)

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


def draw_airport_meal_truck(target: pygame.Surface, meal_truck_state, *, camera_x: float) -> None:
	if meal_truck_state is None or not bool(getattr(meal_truck_state, "is_active", False)):
		return

	_ensure_meal_truck_sprites()
	x = int(float(getattr(meal_truck_state, "x", 0.0)) - float(camera_x))
	y = int(float(getattr(meal_truck_state, "y", 0.0)) - int(getattr(meal_truck_state, "height", 28)))
	progress = max(0.0, min(1.0, float(getattr(meal_truck_state, "extension_progress", 0.0))))

	if _meal_cart_extended_sprite is not None and progress >= 0.98:
		target.blit(_meal_cart_extended_sprite, (x, y))
		return

	if _meal_cart_sprite is not None:
		target.blit(_meal_cart_sprite, (x, y))
	else:
		pygame.draw.rect(target, (220, 220, 230), pygame.Rect(x, y, 72, 24), border_radius=3)
		pygame.draw.rect(target, (20, 20, 25), pygame.Rect(x, y, 72, 24), 1, border_radius=3)

	# Animate the lift section when approaching/operating at the plane LZ.
	lift_px = int(100.0 * progress)
	if lift_px > 0:
		if _meal_cart_box_sprite is not None:
			target.blit(_meal_cart_box_sprite, (x + 8, y - lift_px))
		else:
			pygame.draw.rect(target, (240, 245, 250), pygame.Rect(x + 10, y - lift_px, 40, 28), border_radius=2)
			pygame.draw.rect(target, (35, 35, 40), pygame.Rect(x + 10, y - lift_px, 40, 28), 1, border_radius=2)
