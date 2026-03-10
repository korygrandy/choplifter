"""Airport mission hostage boarding/deboarding logic."""

from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass
class AirportHostageState:
	total_hostages: int = 16
	boarded_hostages: int = 0
	rescued_hostages: int = 0
	meal_truck_loaded_hostages: int = 0
	interrupted_transfers: int = 0
	pickup_x: float = 1232.0
	pickup_radius_px: float = 72.0
	helicopter_bus_radius_px: float = 150.0
	state: str = "waiting"  # waiting -> truck_loading -> truck_loaded -> boarded -> rescued
	boarding_started_s: float = 0.0
	rescue_completed_s: float = 0.0


def create_airport_hostage_state(*, total_hostages: int = 16, pickup_x: float = 1232.0) -> AirportHostageState:
	return AirportHostageState(total_hostages=max(1, int(total_hostages)), pickup_x=float(pickup_x))


def update_airport_hostage_logic(hostage_state, dt: float, *, bus_state=None, helicopter=None, mission=None, audio=None, meal_truck_state=None, tech_state=None):
	if hostage_state is None:
		hostage_state = create_airport_hostage_state()

	if bus_state is None or helicopter is None:
		return hostage_state

	# Meal-truck LZ is dynamic: the pickup marker follows truck position.
	if meal_truck_state is not None:
		hostage_state.pickup_x = float(getattr(meal_truck_state, "x", hostage_state.pickup_x))

	tech_operating = bool(tech_state is not None and getattr(tech_state, "is_deployed", False))
	truck_at_plane = bool(meal_truck_state is not None and getattr(meal_truck_state, "at_plane_lz", False))
	truck_extended = bool(meal_truck_state is not None and float(getattr(meal_truck_state, "extension_progress", 0.0)) >= 0.98)
	truck_retracted = bool(meal_truck_state is not None and float(getattr(meal_truck_state, "extension_progress", 0.0)) <= 0.05)

	# Recalling mission tech during truck extraction interrupts the transfer flow.
	if not tech_operating and hostage_state.state in ("truck_loading", "truck_loaded"):
		hostage_state.interrupted_transfers = int(hostage_state.interrupted_transfers) + 1
		hostage_state.meal_truck_loaded_hostages = 0
		hostage_state.state = "waiting"
		return hostage_state

	# Phase 1: player deploys tech and gets meal truck in place at the damaged plane.
	if hostage_state.state == "waiting":
		# Boarding is allowed only while the meal-truck box is extended.
		if tech_operating and truck_extended:
			hostage_state.state = "truck_loading"
			hostage_state.boarding_started_s = float(getattr(mission, "elapsed_seconds", 0.0))
			if audio is not None and hasattr(audio, "play_bus_door"):
				audio.play_bus_door()

	elif hostage_state.state == "truck_loading":
		# Simulate short extraction/loading window at the plane breach.
		elapsed_since_start = float(getattr(mission, "elapsed_seconds", 0.0)) - float(hostage_state.boarding_started_s)
		if elapsed_since_start >= 1.8:
			hostage_state.meal_truck_loaded_hostages = int(hostage_state.total_hostages)
			hostage_state.state = "truck_loaded"

	# Phase 2: transfer from meal truck to bus near the bus lane while tech is still active.
	elif hostage_state.state == "truck_loaded":
		if meal_truck_state is not None:
			# Unboard requires retracted box and being inside rescue LZ (bus transfer zone).
			near_bus = abs(float(getattr(meal_truck_state, "x", 0.0)) - float(bus_state.x)) <= float(hostage_state.helicopter_bus_radius_px)
			if near_bus and tech_operating and truck_retracted:
				hostage_state.boarded_hostages = int(hostage_state.meal_truck_loaded_hostages)
				hostage_state.meal_truck_loaded_hostages = 0
				hostage_state.state = "boarded"
				if audio is not None and hasattr(audio, "play_bus_door"):
					audio.play_bus_door()

	# Phase 3: deboard at LZ when bus route is done.
	elif hostage_state.state == "boarded":
		bus_stopped = not bool(getattr(bus_state, "is_moving", True))
		player_supporting = bool(getattr(helicopter, "grounded", False) and getattr(helicopter, "doors_open", False))
		near_bus = abs(float(getattr(helicopter.pos, "x", 0.0)) - float(bus_state.x)) <= float(hostage_state.helicopter_bus_radius_px)

		if bus_stopped and player_supporting and near_bus:
			hostage_state.rescued_hostages = int(hostage_state.boarded_hostages)
			hostage_state.boarded_hostages = 0
			hostage_state.state = "rescued"
			hostage_state.rescue_completed_s = float(getattr(mission, "elapsed_seconds", 0.0))
			if audio is not None and hasattr(audio, "play_bus_door"):
				audio.play_bus_door()

	return hostage_state


def draw_airport_hostages(target: pygame.Surface, hostage_state, *, camera_x: float, ground_y: float, bus_state=None) -> None:
	if hostage_state is None:
		return

	if hostage_state.state == "waiting":
		x = int(float(hostage_state.pickup_x) - float(camera_x))
		y = int(float(ground_y) - 28)
		pygame.draw.circle(target, (245, 235, 210), (x, y), 8)
		pygame.draw.circle(target, (25, 25, 25), (x, y), 8, 1)
		return

	if hostage_state.state == "truck_loading":
		x = int(float(hostage_state.pickup_x) - float(camera_x))
		y = int(float(ground_y) - 28)
		pygame.draw.circle(target, (255, 215, 100), (x, y), 8)
		pygame.draw.circle(target, (25, 25, 25), (x, y), 8, 1)
		return

	if bus_state is None:
		return

	bus_x = int(float(getattr(bus_state, "x", 0.0)) - float(camera_x))
	bus_y = int(float(getattr(bus_state, "y", ground_y)) - float(getattr(bus_state, "height", 24)))

	if hostage_state.state == "boarded":
		# Draw a small passenger indicator over the bus.
		marker_rect = pygame.Rect(bus_x + 8, bus_y - 14, 20, 12)
		pygame.draw.rect(target, (245, 235, 210), marker_rect, border_radius=3)
		pygame.draw.rect(target, (25, 25, 25), marker_rect, 1, border_radius=3)
		return

	if hostage_state.state == "truck_loaded":
		marker_rect = pygame.Rect(bus_x - 14, bus_y - 14, 20, 12)
		pygame.draw.rect(target, (255, 215, 100), marker_rect, border_radius=3)
		pygame.draw.rect(target, (25, 25, 25), marker_rect, 1, border_radius=3)
		return

	if hostage_state.state == "rescued":
		# Draw a tiny offload cluster near the bus stop point.
		base_x = bus_x - 10
		base_y = int(float(ground_y) - 10)
		for i in range(min(4, max(1, int(hostage_state.rescued_hostages // 4) + 1))):
			pygame.draw.circle(target, (245, 235, 210), (base_x + i * 7, base_y), 4)
			pygame.draw.circle(target, (25, 25, 25), (base_x + i * 7, base_y), 4, 1)
