"""Airport mission hostage boarding/deboarding logic."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame


@dataclass
class AirportHostageState:
	total_hostages: int = 16
	boarded_hostages: int = 0
	rescued_hostages: int = 0
	meal_truck_loaded_hostages: int = 0
	transferring_hostages: int = 0
	interrupted_transfers: int = 0
	pickup_x: float = 1232.0
	pickup_radius_px: float = 28.0
	pickup_passed_offset_px: float = 66.0
	helicopter_bus_radius_px: float = 150.0
	state: str = "waiting"  # waiting -> truck_loading -> truck_loaded -> transferring_to_bus -> boarded -> rescued
	boarding_started_s: float = 0.0
	transfer_started_s: float = 0.0
	transfer_duration_s: float = 1.2
	rescue_completed_s: float = 0.0


def create_airport_hostage_state(*, total_hostages: int = 16, pickup_x: float = 1500.0) -> AirportHostageState:
	return AirportHostageState(total_hostages=max(1, int(total_hostages)), pickup_x=float(pickup_x))


def update_airport_hostage_logic(hostage_state, dt: float, *, bus_state=None, helicopter=None, mission=None, audio=None, meal_truck_state=None, tech_state=None):
	if hostage_state is None:
		hostage_state = create_airport_hostage_state()

	if bus_state is None or helicopter is None:
		return hostage_state

	# Keep hostage pickup anchor synced to the truck's configured terminal LZ center.
	if meal_truck_state is not None:
		hostage_state.pickup_x = float(getattr(meal_truck_state, "plane_lz_x", hostage_state.pickup_x))

	tech_operating = bool(tech_state is not None and getattr(tech_state, "is_deployed", False))
	tech_on_truck = bool(meal_truck_state is not None and getattr(meal_truck_state, "tech_has_deployed", False))
	tech_available_for_boarding = tech_operating or tech_on_truck
	truck_extended = bool(
		meal_truck_state is not None
		and (
			float(getattr(meal_truck_state, "extension_progress", 0.0)) >= 0.92
			or str(getattr(meal_truck_state, "box_state", "idle")) == "extended"
		)
	)
	truck_retracted = bool(meal_truck_state is not None and float(getattr(meal_truck_state, "extension_progress", 0.0)) <= 0.05)
	truck_x = float(getattr(meal_truck_state, "x", 0.0)) if meal_truck_state is not None else 0.0
	pickup_x = float(getattr(hostage_state, "pickup_x", 1500.0))
	pickup_radius = float(getattr(hostage_state, "pickup_radius_px", 28.0))
	passed_offset = float(getattr(hostage_state, "pickup_passed_offset_px", 66.0))
	# Center the sensitive boarding zone slightly "past" the terminal midpoint.
	boarding_center_x = pickup_x + passed_offset
	near_pickup_center = abs(truck_x - boarding_center_x) <= pickup_radius

	# Recalling mission tech during truck extraction interrupts the transfer flow.
	if not tech_operating and hostage_state.state in ("truck_loading", "truck_loaded"):
		hostage_state.interrupted_transfers = int(hostage_state.interrupted_transfers) + 1
		hostage_state.meal_truck_loaded_hostages = 0
		hostage_state.state = "waiting"
		return hostage_state

	# Phase 1: player deploys tech and gets meal truck in place at the damaged plane.
	if hostage_state.state == "waiting":
		# Boarding starts only in a tight center LZ when the lift is extended.
		if tech_available_for_boarding and truck_extended and near_pickup_center:
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
				hostage_state.transferring_hostages = int(hostage_state.meal_truck_loaded_hostages)
				hostage_state.transfer_started_s = float(getattr(mission, "elapsed_seconds", 0.0))
				hostage_state.state = "transferring_to_bus"
				if audio is not None and hasattr(audio, "play_bus_door"):
					audio.play_bus_door()

	elif hostage_state.state == "transferring_to_bus":
		elapsed_since_transfer_start = float(getattr(mission, "elapsed_seconds", 0.0)) - float(getattr(hostage_state, "transfer_started_s", 0.0))
		transfer_duration = max(0.4, float(getattr(hostage_state, "transfer_duration_s", 1.2)))
		if elapsed_since_transfer_start >= transfer_duration:
			hostage_state.boarded_hostages = int(hostage_state.transferring_hostages)
			hostage_state.meal_truck_loaded_hostages = 0
			hostage_state.transferring_hostages = 0
			hostage_state.state = "boarded"

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


def _draw_stick_figure_passenger(target: pygame.Surface, x: int, y: int, passenger_index: int, mission_time: float) -> None:
	"""Draw a pixelated stick figure passenger with walking and waving animations.
	
	Args:
		target: Surface to draw on
		x, y: Screen position (x is center, y is feet position)
		passenger_index: Unique index for this passenger (determines waving behavior)
		mission_time: Current mission elapsed time for animation
	"""
	# Pixel size for retro look
	pixel = 2
	
	# Beige/tan color for civilians
	body_color = (245, 235, 210)  # Beige
	head_color = (210, 180, 140)  # Tan
	outline_color = (25, 25, 25)  # Dark outline
	
	# Determine if this passenger waves (based on index - about 30% wave)
	is_waving = (passenger_index % 7) in (0, 2, 5)  # Pseudo-random selection
	
	# Calculate animation cycle
	if is_waving:
		# Waving animation - slower arm movement
		wave_cycle = math.sin(mission_time * 3.0 + passenger_index)  # Offset by index for variety
		arm_state = 0 if wave_cycle > 0.3 else (1 if wave_cycle > -0.3 else 0)  # 0=wave up, 1=wave mid
	else:
		# Walking animation - legs alternate
		walk_cycle = math.sin(mission_time * 4.0 + passenger_index * 0.5)
		arm_state = 1 if walk_cycle > 0 else 0  # Binary arm/leg position
	
	# Draw from feet up (feet at y position)
	feet_y = y
	
	# Legs (2 pixels each)
	if arm_state == 1:
		# Left leg forward
		pygame.draw.rect(target, body_color, (x - pixel * 2, feet_y - pixel * 2, pixel, pixel))
		pygame.draw.rect(target, body_color, (x - pixel * 2, feet_y - pixel, pixel, pixel))
		pygame.draw.rect(target, body_color, (x - pixel, feet_y, pixel, pixel))
		# Right leg back
		pygame.draw.rect(target, body_color, (x + pixel, feet_y, pixel, pixel))
		pygame.draw.rect(target, body_color, (x + pixel, feet_y - pixel, pixel, pixel))
	else:
		# Right leg forward
		pygame.draw.rect(target, body_color, (x + pixel * 2, feet_y - pixel * 2, pixel, pixel))
		pygame.draw.rect(target, body_color, (x + pixel * 2, feet_y - pixel, pixel, pixel))
		pygame.draw.rect(target, body_color, (x + pixel, feet_y, pixel, pixel))
		# Left leg back
		pygame.draw.rect(target, body_color, (x - pixel, feet_y, pixel, pixel))
		pygame.draw.rect(target, body_color, (x - pixel, feet_y - pixel, pixel, pixel))
	
	# Body (vertical line from hips to shoulders)
	hip_y = feet_y - pixel * 3
	for i in range(3):
		body_y = hip_y - i * pixel
		pygame.draw.rect(target, body_color, (x - 1, body_y, pixel, pixel))
	
	# Arms - different poses for waving vs walking
	shoulder_y = hip_y - pixel * 2
	if is_waving:
		# Waving gesture - one arm up
		if arm_state == 0:
			# Arm raised high (waving)
			pygame.draw.rect(target, body_color, (x + pixel * 2, shoulder_y - pixel * 3, pixel, pixel))
			pygame.draw.rect(target, body_color, (x + pixel, shoulder_y - pixel * 2, pixel, pixel))
			pygame.draw.rect(target, body_color, (x + pixel, shoulder_y - pixel, pixel, pixel))
			# Other arm down
			pygame.draw.rect(target, body_color, (x - pixel, shoulder_y, pixel, pixel))
		else:
			# Arm mid-wave
			pygame.draw.rect(target, body_color, (x + pixel * 2, shoulder_y - pixel, pixel, pixel))
			pygame.draw.rect(target, body_color, (x + pixel, shoulder_y, pixel, pixel))
			# Other arm down
			pygame.draw.rect(target, body_color, (x - pixel, shoulder_y, pixel, pixel))
	else:
		# Walking arms (alternate with legs)
		if arm_state == 1:
			# Left arm forward, right arm back
			pygame.draw.rect(target, body_color, (x - pixel * 2, shoulder_y, pixel, pixel))
			pygame.draw.rect(target, body_color, (x + pixel, shoulder_y, pixel, pixel))
		else:
			# Right arm forward, left arm back
			pygame.draw.rect(target, body_color, (x + pixel * 2, shoulder_y, pixel, pixel))
			pygame.draw.rect(target, body_color, (x - pixel, shoulder_y, pixel, pixel))
	
	# Head (2x2 pixel block)
	head_y = hip_y - pixel * 3
	pygame.draw.rect(target, head_color, (x - pixel, head_y - pixel, pixel * 2, pixel * 2))
	pygame.draw.rect(target, outline_color, (x - pixel, head_y - pixel, pixel * 2, pixel * 2), 1)


def _draw_meal_truck_passengers(target: pygame.Surface, hostage_state, meal_truck_state, *, camera_x: float, mission_time: float = 0.0) -> None:
	"""Draw passenger count as pixelated text above the meal truck when passengers are boarded.
	
	This replaces individual passenger indicators with a simple count display.
	"""
	if meal_truck_state is None:
		return
	
	passenger_count = int(getattr(hostage_state, "meal_truck_loaded_hostages", 0))
	if passenger_count <= 0:
		return
	
	# Get truck position
	truck_x = int(float(getattr(meal_truck_state, "x", 0.0)) - float(camera_x))
	truck_y = int(float(getattr(meal_truck_state, "y", 0.0)) - int(getattr(meal_truck_state, "height", 28)))
	
	# Draw passenger count text above truck (below the diamond indicator)
	text_y = truck_y - 35  # Position text 35px above truck (below diamond at -50)
	
	# Use pixelated/retro font consistent with game style
	try:
		pygame.font.init()
		font = pygame.font.SysFont("consolas", 16, bold=True)
		text = f"x{passenger_count}"
		surf = font.render(text, True, (255, 235, 205))  # Light beige/cream color
		
		# Center the text horizontally on the truck
		text_rect = surf.get_rect(center=(truck_x, text_y))
		
		# Draw dark background for readability
		bg_rect = text_rect.inflate(6, 4)
		pygame.draw.rect(target, (20, 20, 30, 180), bg_rect, border_radius=3)
		pygame.draw.rect(target, (245, 235, 210), bg_rect, 1, border_radius=3)
		
		# Draw the text
		target.blit(surf, text_rect)
	except Exception:
		# Fallback: simple circle indicator if font fails
		pygame.draw.circle(target, (255, 235, 205), (truck_x, text_y), 6)
		pygame.draw.circle(target, (25, 25, 25), (truck_x, text_y), 6, 1)


def _draw_awaiting_passengers(target: pygame.Surface, hostage_state, *, camera_x: float, ground_y: float, mission_time: float) -> None:
	"""Draw animated stick figures at the pickup location, awaiting boarding onto the meal truck."""
	if hostage_state is None:
		return
	
	# Only draw during the loading phase before passengers board
	if hostage_state.state != "truck_loading":
		return
	
	total_hostages = int(getattr(hostage_state, "total_hostages", 16))
	pickup_x_world = float(getattr(hostage_state, "pickup_x", 1500.0))
	
	# Convert to screen coordinates
	pickup_x = int(pickup_x_world - float(camera_x))
	pickup_y = int(float(ground_y))
	
	# Draw stick figures in a cluster at the jetway (4 per row, 12px spacing)
	row_size = 4
	spacing = 12
	
	for i in range(total_hostages):
		row = i // row_size
		col = i % row_size
		
		# Center the cluster around the pickup point
		offset_x = (col - (row_size - 1) / 2.0) * spacing
		offset_y = row * spacing
		
		x = int(pickup_x + offset_x)
		y = int(pickup_y - offset_y)
		
		# Draw animated stick figure passenger
		_draw_stick_figure_passenger(target, x, y, i, mission_time)


def draw_airport_hostages(target: pygame.Surface, hostage_state, *, camera_x: float, ground_y: float, bus_state=None, meal_truck_state=None, mission_time: float = 0.0) -> None:
	"""Draw hostage status indicators for Airport mission.
	
	Handles different states including waiting, loading, truck_loaded (with animated position), boarded, and rescued.
	"""
	if hostage_state is None:
		return
	
	# State: truck_loading - Draw animated stick figures at pickup location
	if hostage_state.state == "truck_loading":
		_draw_awaiting_passengers(target, hostage_state, camera_x=camera_x, ground_y=ground_y, mission_time=mission_time)
		
		# Draw pulsing indicator at pickup location
		x = int(float(hostage_state.pickup_x) - float(camera_x))
		y = int(float(ground_y) - 28)
		pulse = 0.8 + 0.2 * math.sin(mission_time * 5.0)
		radius = int(8 * pulse)
		pygame.draw.circle(target, (255, 215, 100), (x, y), radius)
		pygame.draw.circle(target, (25, 25, 25), (x, y), radius, 2)
		return
	
	# State: truck_loaded - Draw passenger count above truck
	if hostage_state.state == "truck_loaded":
		_draw_meal_truck_passengers(target, hostage_state, meal_truck_state, camera_x=camera_x, mission_time=mission_time)
		
		# Draw diamond indicator above meal truck when it has passengers
		if meal_truck_state is not None:
			truck_x = int(float(getattr(meal_truck_state, "x", 0.0)) - float(camera_x))
			truck_y = int(float(getattr(meal_truck_state, "y", 0.0)) - int(getattr(meal_truck_state, "height", 28)))
			diamond_y = truck_y - 50  # Position diamond 50px above truck
			
			# Draw yellow diamond (4-point polygon)
			diamond_size = 8
			diamond_points = [
				(truck_x, diamond_y - diamond_size),  # Top
				(truck_x + diamond_size, diamond_y),   # Right
				(truck_x, diamond_y + diamond_size),   # Bottom
				(truck_x - diamond_size, diamond_y)    # Left
			]
			pygame.draw.polygon(target, (255, 215, 0), diamond_points)
			pygame.draw.polygon(target, (25, 25, 25), diamond_points, 2)
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
		return

	if hostage_state.state == "transferring_to_bus" and meal_truck_state is not None:
		truck_x = int(float(getattr(meal_truck_state, "x", 0.0)) - float(camera_x))
		truck_y = int(float(getattr(meal_truck_state, "y", ground_y)))
		transfer_started_s = float(getattr(hostage_state, "transfer_started_s", mission_time))
		transfer_duration = max(0.4, float(getattr(hostage_state, "transfer_duration_s", 1.2)))
		progress = (mission_time - transfer_started_s) / transfer_duration
		progress = max(0.0, min(1.0, progress))

		# Render a subset of walkers marching from truck to bus while transfer is active.
		walker_count = min(6, max(2, int(getattr(hostage_state, "transferring_hostages", 0)) // 3 + 1))
		for i in range(walker_count):
			phase = ((i * 0.17) % 0.7)
			walker_t = max(0.0, min(1.0, progress - phase))
			x = int(truck_x + (bus_x - truck_x) * walker_t)
			y = int(truck_y - 2 - (i % 2) * 2)
			_draw_stick_figure_passenger(target, x, y, i, mission_time)

		# Keep count indicators visible at both endpoints during movement.
		_draw_meal_truck_passengers(target, hostage_state, meal_truck_state, camera_x=camera_x, mission_time=mission_time)
		if int(getattr(hostage_state, "transferring_hostages", 0)) > 0:
			panel = pygame.Rect(bus_x - 16, bus_y - 16, 32, 12)
			pygame.draw.rect(target, (25, 30, 35), panel, border_radius=3)
			pygame.draw.rect(target, (220, 220, 190), panel, 1, border_radius=3)
