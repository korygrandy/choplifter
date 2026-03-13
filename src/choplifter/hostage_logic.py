"""Airport mission hostage boarding/deboarding logic."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random

import pygame

from .airport_fuselage import is_airport_fuselage_boarding_unlocked


@dataclass
class AirportHostageState:
	total_hostages: int = 16
	boarded_hostages: int = 0
	rescued_hostages: int = 0
	meal_truck_loaded_hostages: int = 0
	transferring_hostages: int = 0
	transferred_so_far: int = 0   # live count incremented per passenger during transfer
	transfer_rate_s: float = 0.5  # seconds between each passenger boarding the bus
	interrupted_transfers: int = 0
	pickup_x: float = 1232.0
	pickup_radius_px: float = 28.0
	# Terminal pickup points are compound centers; +27 with a 28px radius makes
	# the right edge of the LZ roughly +55px from center (~10px past a 90px-wide compound).
	pickup_passed_offset_px: float = 27.0
	helicopter_bus_radius_px: float = 150.0
	state: str = "waiting"  # waiting -> truck_loading -> truck_loaded -> transferring_to_bus -> boarded -> rescued
	boarding_started_s: float = 0.0
	transfer_started_s: float = 0.0
	transfer_duration_s: float = 1.2
	rescue_completed_s: float = 0.0
	terminal_pickup_xs: tuple[float, ...] = ()
	terminal_remaining: list[int] | None = None
	terminal_kia: list[int] | None = None
	active_terminal_index: int = 0
	loading_terminal_index: int = -1
	loading_terminal_initial_count: int = 0
	truck_load_base: int = 0


def _allocate_terminal_hostages(total_hostages: int, pickup_points: list[float]) -> list[int]:
	"""Randomly distribute civilians across airport terminals for each mission start."""
	total = max(1, int(total_hostages))
	if not pickup_points:
		return [total]
	counts = [0 for _ in pickup_points]
	for _ in range(total):
		counts[random.randrange(len(counts))] += 1
	return counts


def _remaining_at_terminal(hostage_state, terminal_index: int) -> int:
	remaining = getattr(hostage_state, "terminal_remaining", None) or []
	if terminal_index < 0 or terminal_index >= len(remaining):
		return 0
	open_for_boarding = list(getattr(hostage_state, "terminal_open_for_boarding", []) or [])
	if terminal_index < len(open_for_boarding) and not bool(open_for_boarding[terminal_index]):
		return 0
	count = int(remaining[terminal_index])
	# During active loading, deduct passengers already boarded from that terminal.
	if (
		str(getattr(hostage_state, "state", "")) == "truck_loading"
		and int(getattr(hostage_state, "loading_terminal_index", -1)) == terminal_index
	):
		loaded_total = int(getattr(hostage_state, "meal_truck_loaded_hostages", 0))
		base_total = int(getattr(hostage_state, "truck_load_base", 0))
		loaded_from_terminal = max(0, loaded_total - base_total)
		count = max(0, count - loaded_from_terminal)
	return max(0, count)


def _compute_terminal_open_for_boarding(mission, pickup_xs: list[float]) -> list[bool]:
	if not pickup_xs:
		return []
	compounds = list(getattr(mission, "compounds", []) or []) if mission is not None else []
	if not compounds:
		return [True for _ in pickup_xs]

	open_states: list[bool] = []
	for px in pickup_xs:
		best_compound = None
		best_d = 1e9
		for c in compounds:
			pos = getattr(c, "pos", None)
			if pos is None:
				continue
			center_x = float(pos.x) + float(getattr(c, "width", 0.0)) * 0.5
			d = abs(center_x - float(px))
			if d < best_d:
				best_d = d
				best_compound = c

		if best_compound is None:
			open_states.append(True)
			continue

		max_match_distance = max(90.0, float(getattr(best_compound, "width", 0.0)) * 0.9)
		if best_d <= max_match_distance:
			open_states.append(bool(getattr(best_compound, "is_open", False)))
		else:
			open_states.append(True)

	return open_states


def _find_near_terminal_index(hostage_state, truck_x: float, pickup_radius: float, passed_offset: float) -> int:
	pickup_xs = list(getattr(hostage_state, "terminal_pickup_xs", ()) or ())
	if not pickup_xs:
		pickup_xs = [float(getattr(hostage_state, "pickup_x", 1500.0))]
	best_index = -1
	best_distance = 1e9
	for i, px in enumerate(pickup_xs):
		if _remaining_at_terminal(hostage_state, i) <= 0:
			continue
		center_x = float(px) + float(passed_offset)
		d = abs(float(truck_x) - center_x)
		if d <= float(pickup_radius) and d < best_distance:
			best_distance = d
			best_index = i
	return best_index


def get_airport_terminal_label(hostage_state, terminal_index: int | None = None) -> str:
	pickup_xs = list(getattr(hostage_state, "terminal_pickup_xs", ()) or ())
	if terminal_index is None:
		terminal_index = int(getattr(hostage_state, "active_terminal_index", 0))
	if not pickup_xs or terminal_index < 0 or terminal_index >= len(pickup_xs):
		return "elevated"

	sorted_indices = sorted(range(len(pickup_xs)), key=lambda i: float(pickup_xs[i]))
	if len(sorted_indices) >= 2:
		if terminal_index == sorted_indices[0]:
			return "fuselage"
		if terminal_index == sorted_indices[-1]:
			return "jetway"

	return f"terminal {terminal_index + 1}"


def get_active_airport_terminal_label(hostage_state) -> str:
	return get_airport_terminal_label(hostage_state, int(getattr(hostage_state, "active_terminal_index", 0)))


def _is_leftmost_terminal(hostage_state, terminal_index: int) -> bool:
	pickup_xs = list(getattr(hostage_state, "terminal_pickup_xs", ()) or ())
	if terminal_index < 0 or terminal_index >= len(pickup_xs):
		return False
	if not pickup_xs:
		return terminal_index == 0
	leftmost_x = min(float(px) for px in pickup_xs)
	return abs(float(pickup_xs[terminal_index]) - leftmost_x) <= 0.5


def _loading_right_boundary_x(hostage_state, terminal_x: float, terminal_index: int, pickup_radius: float, passed_offset: float) -> float:
	if _is_leftmost_terminal(hostage_state, terminal_index):
		# Match the tighter left-elevated cutoff: stop once truck passes
		# 5px beyond the compound right edge (90px wide footprint).
		return float(terminal_x) + 45.0 + 5.0
	lz_center_x = float(terminal_x) + float(passed_offset)
	return lz_center_x + float(pickup_radius) + 5.0


def create_airport_hostage_state(*, total_hostages: int = 16, pickup_x: float = 1500.0, pickup_points: list[float] | None = None) -> AirportHostageState:
	pickups = [float(x) for x in (pickup_points or []) if x is not None]
	if not pickups:
		pickups = [float(pickup_x)]
	counts = _allocate_terminal_hostages(total_hostages, pickups)
	active_index = next((i for i, c in enumerate(counts) if int(c) > 0), 0)
	return AirportHostageState(
		total_hostages=max(1, int(total_hostages)),
		pickup_x=float(pickups[active_index]),
		terminal_pickup_xs=tuple(pickups),
		terminal_remaining=counts,
		terminal_kia=[0 for _ in pickups],
		active_terminal_index=int(active_index),
	)


def update_airport_hostage_logic(hostage_state, dt: float, *, bus_state=None, helicopter=None, mission=None, audio=None, meal_truck_state=None, tech_state=None):
	if hostage_state is None:
		hostage_state = create_airport_hostage_state()

	if bus_state is None or helicopter is None:
		return hostage_state

	pickup_xs = list(getattr(hostage_state, "terminal_pickup_xs", ()) or ())
	if not pickup_xs:
		pickup_xs = [float(getattr(hostage_state, "pickup_x", 1500.0))]
		hostage_state.terminal_pickup_xs = tuple(pickup_xs)
	remaining = list(getattr(hostage_state, "terminal_remaining", []) or [])
	if len(remaining) != len(pickup_xs):
		remaining = [0 for _ in pickup_xs]
		remaining[0] = int(getattr(hostage_state, "total_hostages", 16))
	hostage_state.terminal_remaining = remaining
	terminal_kia = list(getattr(hostage_state, "terminal_kia", []) or [])
	if len(terminal_kia) != len(pickup_xs):
		terminal_kia = (terminal_kia + [0 for _ in pickup_xs])[: len(pickup_xs)]
	hostage_state.terminal_kia = terminal_kia
	hostage_state.terminal_open_for_boarding = _compute_terminal_open_for_boarding(mission, pickup_xs)

	tech_operating = bool(tech_state is not None and getattr(tech_state, "is_deployed", False))
	tech_on_truck = bool(meal_truck_state is not None and getattr(meal_truck_state, "tech_has_deployed", False))
	tech_available_for_boarding = tech_operating or tech_on_truck
	boarding_unlocked = is_airport_fuselage_boarding_unlocked(mission)
	truck_extended = bool(
		meal_truck_state is not None
		and (
			float(getattr(meal_truck_state, "extension_progress", 0.0)) >= 0.92
			or str(getattr(meal_truck_state, "box_state", "idle")) == "extended"
		)
	)
	truck_retracted = bool(meal_truck_state is not None and float(getattr(meal_truck_state, "extension_progress", 0.0)) <= 0.05)
	truck_x = float(getattr(meal_truck_state, "x", 0.0)) if meal_truck_state is not None else 0.0
	pickup_radius = float(getattr(hostage_state, "pickup_radius_px", 28.0))
	passed_offset = float(getattr(hostage_state, "pickup_passed_offset_px", 66.0))
	near_terminal_index = _find_near_terminal_index(hostage_state, truck_x, pickup_radius, passed_offset)

	# Keep the mission pickup marker pinned to the active terminal.
	active_terminal_index = int(getattr(hostage_state, "active_terminal_index", 0))
	if near_terminal_index >= 0:
		active_terminal_index = near_terminal_index
	else:
		closest_i = -1
		closest_d = 1e9
		for i, px in enumerate(pickup_xs):
			if _remaining_at_terminal(hostage_state, i) <= 0:
				continue
			d = abs(float(truck_x) - (float(px) + passed_offset))
			if d < closest_d:
				closest_d = d
				closest_i = i
		if closest_i >= 0:
			active_terminal_index = closest_i
	hostage_state.active_terminal_index = int(active_terminal_index)
	hostage_state.pickup_x = float(pickup_xs[active_terminal_index])

	# Recalling mission tech during truck extraction interrupts the transfer flow.
	if not tech_operating and hostage_state.state in ("truck_loading", "truck_loaded"):
		hostage_state.interrupted_transfers = int(hostage_state.interrupted_transfers) + 1
		hostage_state.meal_truck_loaded_hostages = 0
		hostage_state.truck_load_base = 0
		hostage_state.loading_terminal_index = -1
		hostage_state.loading_terminal_initial_count = 0
		hostage_state.state = "waiting"
		return hostage_state

	# Phase 1: player deploys tech and gets meal truck in place at the damaged plane.
	if hostage_state.state == "waiting":
		# Boarding starts only in a tight center LZ when the lift is extended.
		can_start_loading = False
		if boarding_unlocked and tech_available_for_boarding and truck_extended and near_terminal_index >= 0:
			terminal_x = float(pickup_xs[near_terminal_index]) if near_terminal_index < len(pickup_xs) else float(getattr(hostage_state, "pickup_x", 1500.0))
			right_boundary_x = _loading_right_boundary_x(
				hostage_state,
				terminal_x,
				near_terminal_index,
				pickup_radius,
				passed_offset,
			)
			can_start_loading = float(truck_x) <= float(right_boundary_x)
		if can_start_loading:
			hostage_state.loading_terminal_index = int(near_terminal_index)
			hostage_state.loading_terminal_initial_count = int(_remaining_at_terminal(hostage_state, near_terminal_index))
			hostage_state.truck_load_base = int(getattr(hostage_state, "meal_truck_loaded_hostages", 0))
			hostage_state.state = "truck_loading"
			hostage_state.boarding_started_s = float(getattr(mission, "elapsed_seconds", 0.0))
			if audio is not None and hasattr(audio, "play_bus_door"):
				audio.play_bus_door()

	elif hostage_state.state == "truck_loading":
		# Abort auto-boarding if truck drifts too far right of the terminal LZ.
		# This prevents unattended loading when the truck leaves the intended pickup zone.
		loading_index = int(getattr(hostage_state, "loading_terminal_index", -1))
		if meal_truck_state is not None:
			terminal_x = float(getattr(hostage_state, "pickup_x", 1500.0))
			if 0 <= loading_index < len(pickup_xs):
				terminal_x = float(pickup_xs[loading_index])
			right_boundary_x = _loading_right_boundary_x(
				hostage_state,
				terminal_x,
				loading_index,
				pickup_radius,
				passed_offset,
			)
			if float(getattr(meal_truck_state, "x", 0.0)) > right_boundary_x:
				hostage_state.loading_terminal_index = -1
				hostage_state.loading_terminal_initial_count = 0
				hostage_state.truck_load_base = int(getattr(hostage_state, "meal_truck_loaded_hostages", 0))
				hostage_state.state = "truck_loaded" if int(getattr(hostage_state, "meal_truck_loaded_hostages", 0)) > 0 else "waiting"
				return hostage_state

		# Board passengers one-by-one so elevated compound behavior matches ground compounds.
		elapsed_since_start = float(getattr(mission, "elapsed_seconds", 0.0)) - float(hostage_state.boarding_started_s)
		rate = max(0.2, float(getattr(hostage_state, "transfer_rate_s", 0.5)))
		if _is_leftmost_terminal(hostage_state, loading_index):
			# Left elevated terminal uses a slightly slower cadence so boarding reads clearly.
			rate *= 1.35
		loading_total = int(getattr(hostage_state, "loading_terminal_initial_count", 0))
		if loading_total <= 0:
			hostage_state.state = "truck_loaded"
			return hostage_state
		loaded_from_terminal = min(loading_total, int(elapsed_since_start / rate))
		truck_base = int(getattr(hostage_state, "truck_load_base", 0))
		hostage_state.meal_truck_loaded_hostages = truck_base + loaded_from_terminal
		if loaded_from_terminal >= loading_total:
			if 0 <= loading_index < len(hostage_state.terminal_remaining):
				hostage_state.terminal_remaining[loading_index] = max(0, int(hostage_state.terminal_remaining[loading_index]) - loading_total)
			hostage_state.loading_terminal_index = -1
			hostage_state.loading_terminal_initial_count = 0
			hostage_state.truck_load_base = int(hostage_state.meal_truck_loaded_hostages)
			hostage_state.state = "truck_loaded"

	# Phase 2: transfer from meal truck to bus.
	# Trigger: truck in bus transfer LZ, box retracted, at least 1 passenger loaded.
	# tech_operating is NOT required here — passengers stay on truck regardless of box state.
	elif hostage_state.state == "truck_loaded":
		hostages_remaining = sum(max(0, int(v)) for v in (getattr(hostage_state, "terminal_remaining", []) or []))
		can_restart_loading = False
		if boarding_unlocked and tech_available_for_boarding and truck_extended and near_terminal_index >= 0:
			terminal_x = float(pickup_xs[near_terminal_index]) if near_terminal_index < len(pickup_xs) else float(getattr(hostage_state, "pickup_x", 1500.0))
			right_boundary_x = _loading_right_boundary_x(
				hostage_state,
				terminal_x,
				near_terminal_index,
				pickup_radius,
				passed_offset,
			)
			can_restart_loading = float(truck_x) <= float(right_boundary_x)
		if can_restart_loading:
			hostage_state.loading_terminal_index = int(near_terminal_index)
			hostage_state.loading_terminal_initial_count = int(_remaining_at_terminal(hostage_state, near_terminal_index))
			hostage_state.truck_load_base = int(getattr(hostage_state, "meal_truck_loaded_hostages", 0))
			hostage_state.state = "truck_loading"
			hostage_state.boarding_started_s = float(getattr(mission, "elapsed_seconds", 0.0))
			if audio is not None and hasattr(audio, "play_bus_door"):
				audio.play_bus_door()
			return hostage_state
		if meal_truck_state is not None:
			near_bus = abs(float(getattr(meal_truck_state, "x", 0.0)) - float(bus_state.x)) <= float(hostage_state.helicopter_bus_radius_px)
			has_passengers = int(hostage_state.meal_truck_loaded_hostages) >= 1
			if near_bus and has_passengers and truck_retracted and hostages_remaining <= 0:
				hostage_state.transferring_hostages = int(hostage_state.meal_truck_loaded_hostages)
				hostage_state.transferred_so_far = 0
				hostage_state.transfer_started_s = float(getattr(mission, "elapsed_seconds", 0.0))
				hostage_state.truck_load_base = int(getattr(hostage_state, "boarded_hostages", 0))
				hostage_state.state = "transferring_to_bus"
				if audio is not None and hasattr(audio, "play_bus_door"):
					audio.play_bus_door()

	elif hostage_state.state == "transferring_to_bus":
		# Tick one passenger onto the bus every transfer_rate_s seconds.
		elapsed_since_transfer_start = float(getattr(mission, "elapsed_seconds", 0.0)) - float(getattr(hostage_state, "transfer_started_s", 0.0))
		rate = max(0.2, float(getattr(hostage_state, "transfer_rate_s", 0.5)))
		total = int(hostage_state.transferring_hostages)
		new_count = min(total, int(elapsed_since_transfer_start / rate))
		if new_count > int(hostage_state.transferred_so_far):
			hostage_state.transferred_so_far = new_count
			hostage_state.boarded_hostages = int(getattr(hostage_state, "truck_load_base", 0)) + new_count  # live count drives bus display
		if int(hostage_state.transferred_so_far) >= total:
			hostage_state.boarded_hostages = int(getattr(hostage_state, "truck_load_base", 0)) + total
			hostage_state.meal_truck_loaded_hostages = 0
			hostage_state.transferring_hostages = 0
			hostage_state.state = "boarded"

	# Phase 3: auto-rescued when bus reaches the LZ stop point.
	elif hostage_state.state == "boarded":
		# Allow deboarding as soon as the bus reaches the visible tower LZ band.
		bus_x = float(getattr(bus_state, "x", 9999.0))
		stop_x = float(getattr(bus_state, "stop_x", 500.0))
		bus_at_lz = bus_x <= stop_x + 140.0
		if bus_at_lz:
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
	
	# Bright white passenger palette for better readability.
	body_color = (250, 250, 250)
	head_color = (255, 255, 255)
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

def _draw_stick_figure_passenger_rotated(
	target: pygame.Surface,
	cx: int,
	feet_y: int,
	passenger_index: int,
	mission_time: float,
	angle_degrees: float,
) -> None:
	"""Draw stick-figure passenger rotated for tumble effect during FALLING state.

	Args:
		target: Surface to draw on
		cx: Horizontal centre of the figure (screen-space)
		feet_y: Y position of the figure's feet (screen-space)
		passenger_index: Unique index for animation variety
		mission_time: Current mission elapsed time
		angle_degrees: Cumulative fall rotation in degrees
	"""
	surf_size = 48  # Enough headroom for the ~14 px figure after arbitrary rotation
	temp = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
	half = surf_size // 2
	# Figure centre is ~7 px above feet; place feet at (half + 7) so centre → half.
	_draw_stick_figure_passenger(temp, half, half + 7, passenger_index=passenger_index, mission_time=mission_time)
	rotated = pygame.transform.rotate(temp, -angle_degrees)  # negative → visually clockwise
	# Blit centred at the figure’s visual centre (7 px above feet).
	rect = rotated.get_rect(center=(cx, feet_y - 7))
	target.blit(rotated, rect)


def _draw_meal_truck_passengers(target: pygame.Surface, hostage_state, meal_truck_state, *, camera_x: float, mission_time: float = 0.0) -> None:
	"""Draw animated stick-figure passenger markers above meal truck with count label."""
	if meal_truck_state is None:
		return
	
	passenger_count = int(getattr(hostage_state, "meal_truck_loaded_hostages", 0))
	if passenger_count <= 0:
		return
	
	# Get truck position
	truck_x = int(float(getattr(meal_truck_state, "x", 0.0)) - float(camera_x))
	truck_y = int(float(getattr(meal_truck_state, "y", 0.0)) - int(getattr(meal_truck_state, "height", 28)))
	
	# Draw a few animated stick figures above truck plus the full count label.
	text_y = truck_y - 35
	shown = min(3, passenger_count)
	for i in range(shown):
		_draw_stick_figure_passenger(target, truck_x - 12 + i * 12, text_y - 2, i, mission_time)
	
	# Use pixelated/retro font consistent with game style
	try:
		pygame.font.init()
		font = pygame.font.SysFont("consolas", 16, bold=True)
		text = f"x{passenger_count}"
		surf = font.render(text, True, (255, 255, 255))
		
		# Center the text horizontally on the truck
		text_rect = surf.get_rect(center=(truck_x, text_y))
		
		# Draw dark background for readability
		bg_rect = text_rect.inflate(6, 4)
		pygame.draw.rect(target, (20, 20, 30, 180), bg_rect, border_radius=3)
		pygame.draw.rect(target, (255, 255, 255), bg_rect, 1, border_radius=3)
		
		# Draw the text
		target.blit(surf, text_rect)
	except Exception:
		# Fallback: simple circle indicator if font fails
		pygame.draw.circle(target, (255, 255, 255), (truck_x, text_y), 6)
		pygame.draw.circle(target, (25, 25, 25), (truck_x, text_y), 6, 1)


def _draw_awaiting_passengers(target: pygame.Surface, hostage_state, *, camera_x: float, ground_y: float, meal_truck_state=None, mission_time: float) -> None:
	"""Draw single-file passenger queue and active walker during elevated-truck boarding."""
	if hostage_state is None:
		return
	
	# Only draw during the loading phase before passengers board
	if hostage_state.state != "truck_loading":
		return
	
	loading_total = int(getattr(hostage_state, "loading_terminal_initial_count", 0))
	loaded_hostages = max(0, int(getattr(hostage_state, "meal_truck_loaded_hostages", 0)) - int(getattr(hostage_state, "truck_load_base", 0)))
	waiting_hostages = max(0, loading_total - loaded_hostages)
	if waiting_hostages <= 0:
		return

	rate = max(0.2, float(getattr(hostage_state, "transfer_rate_s", 0.5)))
	boarding_started_s = float(getattr(hostage_state, "boarding_started_s", mission_time))
	elapsed_since_start = max(0.0, mission_time - boarding_started_s)
	current_step = elapsed_since_start / rate
	step_phase = max(0.0, min(1.0, current_step - math.floor(current_step)))
	pickup_x_world = float(getattr(hostage_state, "pickup_x", 1500.0))
	
	# Convert to screen coordinates.
	pickup_x = int(pickup_x_world - float(camera_x))
	# Anchor boarding to the raised service platform when truck state is available.
	if meal_truck_state is not None:
		truck_top_y = float(getattr(meal_truck_state, "y", ground_y)) - float(getattr(meal_truck_state, "height", 28))
		pickup_y = int(truck_top_y - 53.0 + 20.0)
		truck_entry_x = int(float(getattr(meal_truck_state, "x", pickup_x_world)) - float(camera_x) + 18.0)
	else:
		pickup_y = int(float(ground_y))
		truck_entry_x = pickup_x + 48

	# Draw waiting passengers queued in single-file behind the active walker.
	queue_spacing = 12
	for i in range(max(0, waiting_hostages - 1)):
		x = int(pickup_x - (i + 1) * queue_spacing)
		y = int(pickup_y)
		_draw_stick_figure_passenger(target, x, y, loaded_hostages + i + 1, mission_time)

	# Draw one active passenger moving from queue to truck.
	active_x = int(pickup_x + (truck_entry_x - pickup_x) * step_phase)
	_draw_stick_figure_passenger(target, active_x, int(pickup_y), loaded_hostages, mission_time)


def draw_airport_hostages(target: pygame.Surface, hostage_state, *, camera_x: float, ground_y: float, bus_state=None, meal_truck_state=None, tech_state=None, mission_time: float = 0.0) -> None:
	"""Draw hostage status indicators for Airport mission.
	
	Handles different states including waiting, loading, truck_loaded (with animated position), boarded, and rescued.
	"""
	if hostage_state is None:
		return
	
	# State: truck_loading - Draw animated stick figures at pickup location
	if hostage_state.state == "truck_loading":
		# Elevated airport civilians are rendered by the world layer (roof silhouettes + door bursts).
		# Keep this layer focused on the pickup marker.
		
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
		y = int(float(ground_y) - 26)
		_draw_stick_figure_passenger(target, x, y, 0, mission_time)
		return

	if bus_state is None:
		return

	bus_x = int(float(getattr(bus_state, "x", 0.0)) - float(camera_x))
	bus_y = int(float(getattr(bus_state, "y", ground_y)) - float(getattr(bus_state, "height", 24)))

	if hostage_state.state == "boarded":
		# Draw tiny animated passengers inside the bus window band.
		for i in range(2):
			_draw_stick_figure_passenger(target, bus_x + 12 + i * 10, bus_y - 2, i, mission_time)
		return

	if hostage_state.state == "rescued":
		# Stage rescued civilians around the tower-side terminal like the original game:
		# some gather at the frontage while others stand on the low roof.
		visible_count = min(4, max(1, int(hostage_state.rescued_hostages // 4) + 1))
		roof_count = min(2, max(0, visible_count - 2))
		if visible_count >= 2:
			roof_count = max(1, roof_count)
		frontage_count = max(1, visible_count - roof_count)

		stop_x = float(getattr(bus_state, "stop_x", 500.0))
		frontage_world_x = stop_x - 78.0
		tech_state_name = str(getattr(tech_state, "state", "")) if tech_state is not None else ""
		tech_animation_state = str(getattr(tech_state, "boarding_animation_state", "")) if tech_state is not None else ""
		if tech_animation_state == "returning":
			# Avoid overlap with engineer return-boarding walk animation near the pickup ring.
			frontage_count = 0
		tech_reboarding_lz = tech_state_name == "waiting_at_lz"
		if tech_reboarding_lz:
			reserved_pickup_x = float(getattr(tech_state, "lz_wait_x", stop_x - 80.0))
			frontage_world_x = reserved_pickup_x - 18.0 - max(0, frontage_count - 1) * 10.0
		frontage_base_x = int(frontage_world_x - float(camera_x))
		frontage_base_y = int(float(ground_y) - 8)
		for i in range(frontage_count):
			_draw_stick_figure_passenger(target, frontage_base_x + i * 10, frontage_base_y, i, mission_time)

		if roof_count > 0:
			# Mirror the tower-LZ side building footprint from render/world.py.
			terminal_world_x = stop_x - 62.0
			roof_left = int((terminal_world_x - 4.0) - float(camera_x))
			roof_right = roof_left + 140
			if roof_count == 1:
				roof_positions = [roof_left + 70]
			else:
				roof_positions = [roof_left + 34, roof_right - 34]
			roof_feet_y = int(float(ground_y) - 28)
			for i, roof_x in enumerate(roof_positions):
				_draw_stick_figure_passenger(target, roof_x, roof_feet_y, frontage_count + i, mission_time)
		return

	if hostage_state.state == "transferring_to_bus" and meal_truck_state is not None:
		truck_x = int(float(getattr(meal_truck_state, "x", 0.0)) - float(camera_x))
		truck_y = int(float(getattr(meal_truck_state, "y", ground_y)))
		transfer_started_s = float(getattr(hostage_state, "transfer_started_s", mission_time))
		rate = max(0.2, float(getattr(hostage_state, "transfer_rate_s", 0.5)))
		total = int(getattr(hostage_state, "transferring_hostages", 0))
		elapsed = max(0.0, mission_time - transfer_started_s)
		current_step = elapsed / rate
		current_index = int(current_step)
		phase = max(0.0, min(1.0, current_step - current_index))

		# Render exactly one active walker for a true single-file unboarding transfer.
		if current_index < total:
			x = int(truck_x + (bus_x - truck_x) * phase)
			y = int(truck_y - 2)
			_draw_stick_figure_passenger(target, x, y, current_index, mission_time)

		# Keep count indicators visible at both endpoints during movement.
		_draw_meal_truck_passengers(target, hostage_state, meal_truck_state, camera_x=camera_x, mission_time=mission_time)
		if int(getattr(hostage_state, "transferring_hostages", 0)) > 0:
			panel = pygame.Rect(bus_x - 16, bus_y - 16, 32, 12)
			pygame.draw.rect(target, (25, 30, 35), panel, border_radius=3)
			pygame.draw.rect(target, (220, 220, 190), panel, 1, border_radius=3)
