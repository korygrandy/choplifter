"""Airport mission hostage boarding/deboarding logic."""

from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass
class AirportHostageState:
	total_hostages: int = 16
	boarded_hostages: int = 0
	rescued_hostages: int = 0
	pickup_x: float = 1232.0
	pickup_radius_px: float = 72.0
	helicopter_bus_radius_px: float = 150.0
	state: str = "waiting"  # waiting -> boarded -> rescued
	boarding_started_s: float = 0.0
	rescue_completed_s: float = 0.0


def create_airport_hostage_state(*, total_hostages: int = 16, pickup_x: float = 1232.0) -> AirportHostageState:
	return AirportHostageState(total_hostages=max(1, int(total_hostages)), pickup_x=float(pickup_x))


def update_airport_hostage_logic(hostage_state, dt: float, *, bus_state=None, helicopter=None, mission=None, audio=None):
	if hostage_state is None:
		hostage_state = create_airport_hostage_state()

	if bus_state is None or helicopter is None:
		return hostage_state

	# Board when the bus reaches the pickup zone and player is assisting on the ground.
	if hostage_state.state == "waiting":
		bus_at_pickup = abs(float(bus_state.x) - float(hostage_state.pickup_x)) <= float(hostage_state.pickup_radius_px)
		player_supporting = bool(getattr(helicopter, "grounded", False) and getattr(helicopter, "doors_open", False))
		near_bus = abs(float(getattr(helicopter.pos, "x", 0.0)) - float(bus_state.x)) <= float(hostage_state.helicopter_bus_radius_px)

		if bus_at_pickup and player_supporting and near_bus:
			hostage_state.boarded_hostages = int(hostage_state.total_hostages)
			hostage_state.state = "boarded"
			hostage_state.boarding_started_s = float(getattr(mission, "elapsed_seconds", 0.0))
			if audio is not None and hasattr(audio, "play_bus_door"):
				audio.play_bus_door()

	# Deboard when bus has completed its run and player opens doors nearby.
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

	if hostage_state.state == "rescued":
		# Draw a tiny offload cluster near the bus stop point.
		base_x = bus_x - 10
		base_y = int(float(ground_y) - 10)
		for i in range(min(4, max(1, int(hostage_state.rescued_hostages // 4) + 1))):
			pygame.draw.circle(target, (245, 235, 210), (base_x + i * 7, base_y), 4)
			pygame.draw.circle(target, (25, 25, 25), (base_x + i * 7, base_y), 4, 1)
