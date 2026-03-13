"""Airport mission Mission Tech deployment and state machine."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random

import pygame


@dataclass
class MissionTechState:
	"""Mission Tech lifecycle state for Airport Special Ops mission.
	
	Lifecycle states:
	- on_chopper: Tech is aboard helicopter (mission start)
	- deployed_to_truck: Tech has deployed from chopper to meal truck
	- driving_to_extraction: Meal truck driving to elevated jetway
	- extracting: Box extended, hostages boarding
	- transferring: Box retracted, driving to bus for passenger transfer
	- transfer_complete: Passengers on bus, mission tech objective complete
	"""
	state: str = "on_chopper"  # Lifecycle state
	tech_x: float = 0.0  # Current tech position (for rendering)
	tech_y: float = 0.0
	deploy_timer_s: float = 0.0  # Time since deployment started
	
	# Boarding animation state (for visual representation)
	boarding_animation_state: str = "idle"  # "idle", "deploying" (from chopper to truck), "returning" (truck to chopper)
	boarding_animation_timer: float = 0.0  # Time elapsed in current boarding animation
	boarding_start_x: float = 0.0  # Start X position for boarding animation
	boarding_start_y: float = 0.0  # Start Y position for boarding animation
	boarding_end_x: float = 0.0  # End X position for boarding animation
	boarding_end_y: float = 0.0  # End Y position for boarding animation
	
	# Legacy fields (kept for compatibility, may be deprecated later)
	is_deployed: bool = False  # True when state != "on_chopper"
	on_bus: bool = False  # True after tech transfers onto the bus
	is_repairing: bool = False  # Currently unused in new design
	repairs_completed: int = 0  # Currently unused in new design
	lz_wait_x: float = 0.0
	lz_wait_y: float = 0.0
	disembark_started_s: float = 0.0

	# Fall physics (when tech falls from chopper with doors open while airborne)
	fall_vel_x: float = 0.0
	fall_vel_y: float = 0.0
	fall_angle: float = 0.0        # degrees; accumulates for tumble animation
	fall_airborne_timer: float = 0.0  # seconds: doors open while airborne on chopper
	fall_delay_s: float = 2.5  # sampled per airborne window; 2-3s before ejection


def create_mission_tech_state() -> MissionTechState:
	"""Create initial mission tech state (tech starts on chopper)."""
	return MissionTechState(state="on_chopper")


def _bus_door_boarding_x(bus_state) -> float:
	"""Estimate a stable world-X boarding point near the bus door."""
	bus_x = float(getattr(bus_state, "x", 0.0))
	bus_w = float(getattr(bus_state, "width", 64.0))
	# Door sits around the front-right side in the current sprite set.
	return bus_x + bus_w * 0.68


def _tech_boarding_jitter_x(tech_state) -> float:
	"""Deterministic tiny jitter to avoid robotic repeat paths."""
	seed_x = float(getattr(tech_state, "boarding_start_x", getattr(tech_state, "tech_x", 0.0)))
	# Stable [-2, +2] px offset derived from start position.
	return float((int(seed_x) % 5) - 2)


def update_mission_tech(
	tech_state: MissionTechState | None,
	dt: float,
	*,
	helicopter=None,
	meal_truck_state=None,
	bus_state=None,
	hostage_state=None,
	audio=None,
	ground_y: float = 530.0,
	tuning=None,
) -> MissionTechState:
	"""Update mission tech state machine.
	
	Args:
		tech_state: Current tech state
		dt: Delta time in seconds
		helicopter: Helicopter object (needed for deployment trigger)
		meal_truck_state: Meal truck state (needed for tracking tech on truck)
		bus_state: Bus state (needed for transfer completion check)
		hostage_state: Hostage state (used to detect transfer completion)
	
	Returns:
		Updated tech state
	"""
	if tech_state is None:
		tech_state = create_mission_tech_state()

	dt_s = max(0.0, float(dt))

	# Update boarding animation timer
	BOARDING_ANIMATION_DURATION = 0.4  # seconds
	if tech_state.boarding_animation_state != "idle":
		boarding_state = str(getattr(tech_state, "boarding_animation_state", "idle"))
		tech_state.boarding_animation_timer += dt_s
		if boarding_state == "boarding_bus":
			anim_limit = None
		elif boarding_state == "disembarking":
			anim_limit = 0.9
		else:
			anim_limit = BOARDING_ANIMATION_DURATION
		if anim_limit is not None and tech_state.boarding_animation_timer >= anim_limit:
			tech_state.boarding_animation_state = "idle"
			tech_state.boarding_animation_timer = 0.0

	# Re-board behavior: engineer can return to helicopter when linked up near truck.
	if (
		tech_state.state not in ("on_chopper", "falling", "kia")
		and helicopter is not None
		and meal_truck_state is not None
		and not bool(getattr(meal_truck_state, "driver_mode_active", False))
	):
		heli_x = float(getattr(helicopter.pos, "x", 0.0))
		truck_x = float(getattr(meal_truck_state, "x", 0.0))
		can_reboard = bool(
			getattr(helicopter, "grounded", False)
			and getattr(helicopter, "doors_open", False)
			and abs(heli_x - truck_x) <= 120.0
		)
		if can_reboard:
			# Trigger returning animation before re-boarding
			tech_state.boarding_animation_state = "returning"
			tech_state.boarding_animation_timer = 0.0
			tech_state.state = "on_chopper"
			tech_state.is_deployed = False
			tech_state.tech_x = heli_x
			tech_state.tech_y = float(getattr(helicopter.pos, "y", tech_state.tech_y))
			return tech_state

	# LZ re-board behavior: after bus disembark, engineer waits near tower until picked up.
	if tech_state.state == "waiting_at_lz" and helicopter is not None:
		heli_x = float(getattr(helicopter.pos, "x", 0.0))
		tech_x = float(getattr(tech_state, "tech_x", 0.0))
		can_reboard_lz = bool(
			getattr(helicopter, "grounded", False)
			and getattr(helicopter, "doors_open", False)
			and abs(heli_x - tech_x) <= 120.0
		)
		if can_reboard_lz:
			tech_state.boarding_animation_state = "returning"
			tech_state.boarding_animation_timer = 0.0
			tech_state.state = "on_chopper"
			tech_state.is_deployed = False
			tech_state.on_bus = False
			tech_state.tech_x = heli_x
			tech_state.tech_y = float(getattr(helicopter.pos, "y", tech_state.tech_y))
			if bus_state is not None and str(getattr(bus_state, "door_state", "closed")) == "open":
				bus_state.door_state = "closing"
				bus_state.door_animation_progress = 0.0
			return tech_state
	
	# --- State: on_chopper ---
	# Tech is aboard helicopter, waiting for deployment
	if tech_state.state == "on_chopper":
		tech_state.on_bus = False
		# Deployment trigger: grounded + doors open + near meal truck
		if helicopter is not None and meal_truck_state is not None:
			heli_x = float(getattr(helicopter.pos, "x", 0.0))
			truck_x = float(getattr(meal_truck_state, "x", 0.0))
			near_truck = abs(heli_x - truck_x) <= 120.0
			supports_deploy = bool(
				getattr(helicopter, "grounded", False)
				and getattr(helicopter, "doors_open", False)
				and near_truck
			)
			
			if supports_deploy:
				# Transition: deploy tech to meal truck
				tech_state.boarding_animation_state = "deploying"
				tech_state.boarding_animation_timer = 0.0
				tech_state.state = "deployed_to_truck"
				tech_state.is_deployed = True
				tech_state.deploy_timer_s = 0.0
				tech_state.tech_x = truck_x
				tech_state.tech_y = float(getattr(meal_truck_state, "y", 0.0))

		# Fall trigger: airborne + doors open for longer than 1s → tech falls out
		is_airborne_doors_open = (
			helicopter is not None
			and bool(getattr(helicopter, "doors_open", False))
			and not bool(getattr(helicopter, "grounded", True))
		)
		if is_airborne_doors_open:
			if tech_state.fall_airborne_timer <= 0.0:
				fall_delay_min_s = float(getattr(tuning, "airborne_fall_delay_min_s", 2.0))
				fall_delay_max_s = float(getattr(tuning, "airborne_fall_delay_max_s", 3.0))
				if fall_delay_max_s < fall_delay_min_s:
					fall_delay_min_s, fall_delay_max_s = fall_delay_max_s, fall_delay_min_s
				tech_state.fall_delay_s = random.uniform(fall_delay_min_s, fall_delay_max_s)
			tech_state.fall_airborne_timer += dt_s
			if tech_state.fall_airborne_timer > float(getattr(tech_state, "fall_delay_s", 2.5)):
				# Tech tumbles out of the chopper
				tech_state.state = "falling"
				tech_state.tech_x = float(getattr(helicopter.pos, "x", tech_state.tech_x))
				tech_state.tech_y = float(getattr(helicopter.pos, "y", tech_state.tech_y))
				tech_state.fall_vel_x = random.uniform(-60.0, 60.0)
				tech_state.fall_vel_y = random.uniform(-80.0, -120.0)
				tech_state.fall_angle = 0.0
				if audio is not None and hasattr(audio, "play_female_scream"):
					audio.play_female_scream()
				return tech_state
		else:
			tech_state.fall_airborne_timer = 0.0

		# Tech follows helicopter position while on board
		if helicopter is not None:
			tech_state.tech_x = float(getattr(helicopter.pos, "x", tech_state.tech_x))
			tech_state.tech_y = float(getattr(helicopter.pos, "y", tech_state.tech_y))
	
	# --- State: deployed_to_truck ---
	# Tech has entered meal truck, truck is about to drive to extraction point
	elif tech_state.state == "deployed_to_truck":
		tech_state.on_bus = False
		tech_state.deploy_timer_s += dt_s
		
		# Tech follows meal truck position
		if meal_truck_state is not None:
			tech_state.tech_x = float(getattr(meal_truck_state, "x", tech_state.tech_x))
			tech_state.tech_y = float(getattr(meal_truck_state, "y", tech_state.tech_y))
			
			# Transition: truck starts driving to extraction point
			if bool(getattr(meal_truck_state, "is_active", False)):
				tech_state.state = "driving_to_extraction"
	
	# --- State: driving_to_extraction ---
	# Meal truck is en route to elevated jetway at hostage location
	elif tech_state.state == "driving_to_extraction":
		tech_state.on_bus = False
		tech_state.deploy_timer_s += dt_s
		
		# Tech follows meal truck position
		if meal_truck_state is not None:
			tech_state.tech_x = float(getattr(meal_truck_state, "x", tech_state.tech_x))
			tech_state.tech_y = float(getattr(meal_truck_state, "y", tech_state.tech_y))
			
			# Transition: truck reached extraction point, box extending
			if bool(getattr(meal_truck_state, "at_plane_lz", False)):
				extension_progress = float(getattr(meal_truck_state, "extension_progress", 0.0))
				if extension_progress > 0.01:  # Box extension has started
					tech_state.state = "extracting"
	
	# --- State: extracting ---
	# Box is extended, hostages are boarding meal truck
	elif tech_state.state == "extracting":
		tech_state.on_bus = False
		tech_state.deploy_timer_s += dt_s
		
		# Tech follows meal truck position
		if meal_truck_state is not None:
			tech_state.tech_x = float(getattr(meal_truck_state, "x", tech_state.tech_x))
			tech_state.tech_y = float(getattr(meal_truck_state, "y", tech_state.tech_y))
			
			# Transition: box retracting (hostages loaded, ready for transfer)
			extension_progress = float(getattr(meal_truck_state, "extension_progress", 0.0))
			at_plane_lz = bool(getattr(meal_truck_state, "at_plane_lz", False))
			if at_plane_lz and extension_progress < 0.99:  # Box is retracting
				tech_state.state = "transferring"
	
	# --- State: transferring ---
	# Box retracted, meal truck driving to bus for passenger transfer
	elif tech_state.state == "transferring":
		tech_state.on_bus = False
		tech_state.deploy_timer_s += dt_s
		
		# Tech follows meal truck position
		if meal_truck_state is not None:
			tech_state.tech_x = float(getattr(meal_truck_state, "x", tech_state.tech_x))
			tech_state.tech_y = float(getattr(meal_truck_state, "y", tech_state.tech_y))
		
		# Transition: passengers transferred to bus
		if hostage_state is not None:
			hostage_state_name = str(getattr(hostage_state, "state", ""))
			boarded = int(getattr(hostage_state, "boarded_hostages", 0))
			rescued = int(getattr(hostage_state, "rescued_hostages", 0))
			total_hostages = int(getattr(hostage_state, "total_hostages", 16))
			if hostage_state_name in ("boarded", "rescued") or boarded >= total_hostages or rescued >= total_hostages:
				# Trigger a short visible tech boarding pass from truck to bus.
				tech_state.state = "boarding_bus"
				tech_state.on_bus = False
				tech_state.boarding_animation_state = "boarding_bus"
				tech_state.boarding_animation_timer = 0.0
				tech_state.boarding_start_x = float(getattr(meal_truck_state, "x", tech_state.tech_x)) if meal_truck_state is not None else float(tech_state.tech_x)
				tech_state.boarding_start_y = float(getattr(meal_truck_state, "y", tech_state.tech_y)) if meal_truck_state is not None else float(tech_state.tech_y)
				if bus_state is not None:
					tech_state.boarding_end_x = _bus_door_boarding_x(bus_state) + _tech_boarding_jitter_x(tech_state)
					tech_state.boarding_end_y = float(getattr(bus_state, "y", tech_state.tech_y))
					if str(getattr(bus_state, "door_state", "closed")) in ("closed", "closing"):
						bus_state.door_state = "opening"
						bus_state.door_animation_progress = 0.0
						if audio is not None and hasattr(audio, "play_bus_door"):
							audio.play_bus_door()
					if audio is not None and hasattr(audio, "play_hang_on_yall"):
						audio.play_hang_on_yall()

	# --- State: boarding_bus ---
	# Tech visibly moves from meal truck to bus before becoming on_bus.
	elif tech_state.state == "boarding_bus":
		tech_state.on_bus = False
		tech_state.deploy_timer_s += dt_s
		if bus_state is not None:
			tech_state.boarding_end_x = _bus_door_boarding_x(bus_state) + _tech_boarding_jitter_x(tech_state)
			tech_state.boarding_end_y = float(getattr(bus_state, "y", tech_state.boarding_end_y))
		walk_duration = 0.8
		p = min(1.0, float(getattr(tech_state, "boarding_animation_timer", 0.0)) / walk_duration)
		tech_state.tech_x = float(getattr(tech_state, "boarding_start_x", tech_state.tech_x)) + (float(getattr(tech_state, "boarding_end_x", tech_state.tech_x)) - float(getattr(tech_state, "boarding_start_x", tech_state.tech_x))) * p
		tech_state.tech_y = float(getattr(tech_state, "boarding_start_y", tech_state.tech_y)) + (float(getattr(tech_state, "boarding_end_y", tech_state.tech_y)) - float(getattr(tech_state, "boarding_start_y", tech_state.tech_y))) * p
		if p >= 1.0:
			tech_state.state = "transfer_complete"
			tech_state.on_bus = True
			tech_state.boarding_animation_state = "idle"
			if bus_state is not None and str(getattr(bus_state, "door_state", "closed")) in ("open", "opening"):
				bus_state.door_state = "closing"
				bus_state.door_animation_progress = 0.0
				if audio is not None and hasattr(audio, "play_bus_door"):
					audio.play_bus_door()
	
	# --- State: transfer_complete ---
	# Passengers on bus, tech mission objective complete
	elif tech_state.state == "transfer_complete":
		tech_state.on_bus = True
		tech_state.deploy_timer_s += dt_s
		if bus_state is not None:
			tech_state.tech_x = float(getattr(bus_state, "x", tech_state.tech_x))
			tech_state.tech_y = float(getattr(bus_state, "y", tech_state.tech_y))
		if bus_state is not None:
			# Keep mission-tech deboard timing aligned with passenger deboard timing at tower LZ.
			bus_x = float(getattr(bus_state, "x", tech_state.tech_x))
			bus_y = float(getattr(bus_state, "y", tech_state.tech_y))
			stop_x = float(getattr(bus_state, "stop_x", 500.0))
			bus_at_lz = bus_x <= stop_x + 140.0
			if bus_at_lz:
				tech_state.state = "waiting_at_lz"
				tech_state.on_bus = False
				tech_state.is_deployed = True
				tech_state.disembark_started_s = tech_state.deploy_timer_s
				tech_state.boarding_animation_state = "disembarking"
				tech_state.boarding_animation_timer = 0.0
				tech_state.boarding_start_x = bus_x
				tech_state.boarding_start_y = bus_y
				tech_state.lz_wait_x = stop_x - 80.0
				tech_state.lz_wait_y = bus_y
				tech_state.boarding_end_x = tech_state.lz_wait_x
				tech_state.boarding_end_y = tech_state.lz_wait_y
				if str(getattr(bus_state, "door_state", "closed")) == "closed":
					bus_state.door_state = "opening"
					bus_state.door_animation_progress = 0.0

	# --- State: waiting_at_lz ---
	elif tech_state.state == "waiting_at_lz":
		tech_state.on_bus = False
		tech_state.deploy_timer_s += dt_s
		# Walk out from bus then wait at a fixed pickup point just outside tower rescue zone.
		if tech_state.boarding_animation_state == "disembarking":
			walk_duration = 0.9
			p = min(1.0, tech_state.boarding_animation_timer / walk_duration)
			tech_state.tech_x = float(tech_state.boarding_start_x) + (float(tech_state.lz_wait_x) - float(tech_state.boarding_start_x)) * p
			tech_state.tech_y = float(tech_state.lz_wait_y)
			if p >= 1.0:
				tech_state.boarding_animation_state = "idle"
		else:
			tech_state.tech_x = float(getattr(tech_state, "lz_wait_x", tech_state.tech_x))
			tech_state.tech_y = float(getattr(tech_state, "lz_wait_y", tech_state.tech_y))

	# --- State: falling ---
	# Tech has fallen from chopper; gravity + tumble until ground impact.
	elif tech_state.state == "falling":
		gravity = 900.0  # px/s^2
		tech_state.fall_vel_y += gravity * dt_s
		tech_state.tech_x += tech_state.fall_vel_x * dt_s
		tech_state.tech_y += tech_state.fall_vel_y * dt_s
		tech_state.fall_angle += 720.0 * dt_s  # 2 full spins per second
		if tech_state.tech_y >= ground_y - 6.0:
			tech_state.tech_y = ground_y - 6.0
			tech_state.state = "kia"
			tech_state.fall_angle = 0.0

	# --- State: kia ---
	# Terminal state; tech is dead on the ground.
	elif tech_state.state == "kia":
		pass

	return tech_state


def _draw_tech_stick_figure_rotated(target: pygame.Surface, cx: int, cy: int, *, t: float, angle_degrees: float) -> None:
	"""Draw the green engineer stick-figure rotated for tumble animation.

	Args:
		target: Surface to draw on
		cx, cy: Screen-space centre of the figure
		t: Timer used for the walk-cycle (keeps limbs dynamic during tumble)
		angle_degrees: Cumulative rotation in degrees
	"""
	surf_size = 40
	temp = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
	half = surf_size // 2
	# Feet sit ~5 px below figure centre; offset so figure centre aligns with surf centre.
	_draw_tech_stick_figure(temp, half, half + 5, t=t, walking=True)
	rotated = pygame.transform.rotate(temp, -angle_degrees)  # negative → visually clockwise
	rect = rotated.get_rect(center=(cx, cy))
	target.blit(rotated, rect)


def _draw_tech_stick_figure(target: pygame.Surface, x: int, y: int, *, t: float, walking: bool) -> None:
	"""Draw a small green stick-figure engineer with optional walk cycle."""
	pixel = 2
	body = (96, 212, 112)
	head = (72, 172, 92)
	outline = (22, 52, 24)
	cycle = math.sin(t * 9.0)
	leg = 1 if (walking and cycle > 0.0) else -1

	# Legs
	pygame.draw.line(target, body, (x, y - 3), (x - leg * 2, y), 2)
	pygame.draw.line(target, body, (x, y - 3), (x + leg * 2, y), 2)
	# Torso
	pygame.draw.line(target, body, (x, y - 8), (x, y - 3), 2)
	# Arms
	arm = -leg
	pygame.draw.line(target, body, (x, y - 7), (x - arm * 2, y - 5), 2)
	pygame.draw.line(target, body, (x, y - 7), (x + arm * 2, y - 5), 2)
	# Head
	pygame.draw.rect(target, head, pygame.Rect(x - pixel, y - 11, pixel * 2, pixel * 2))
	pygame.draw.rect(target, outline, pygame.Rect(x - pixel, y - 11, pixel * 2, pixel * 2), 1)


def draw_airport_mission_tech(
	target: pygame.Surface,
	tech_state: MissionTechState | None,
	*,
	camera_x: float,
	helicopter=None,
) -> None:
	"""Draw mission tech indicator and tech sprite.
	
	Args:
		target: Surface to draw on
		tech_state: Current tech state
		camera_x: Camera x position for world-to-screen conversion
		helicopter: Helicopter object (for indicator above chopper when tech on board)
	"""
	if tech_state is None:
		return

	# --- Draw falling tech (tumbling out of chopper) ---
	if tech_state.state == "falling":
		cx = int(tech_state.tech_x - camera_x)
		cy = int(tech_state.tech_y) - 7  # Figure centre is 7 px above feet
		_draw_tech_stick_figure_rotated(target, cx, cy, t=tech_state.deploy_timer_s, angle_degrees=tech_state.fall_angle)
		return

	# --- Draw KIA tech (impact mark on the ground) ---
	if tech_state.state == "kia":
		cx = int(tech_state.tech_x - camera_x)
		cy = int(tech_state.tech_y)
		pygame.draw.circle(target, (60, 20, 0), (cx, cy), 5)
		return

	# --- Draw tech indicator above chopper when tech is on board ---
	if tech_state.state == "on_chopper" and helicopter is not None:
		heli_x = float(getattr(helicopter.pos, "x", 0.0))
		heli_y = float(getattr(helicopter.pos, "y", 0.0))
		screen_x = int(heli_x - camera_x)
		screen_y = int(heli_y - 60)
		pulse = 0.75 + 0.25 * (0.5 + 0.5 * pygame.math.Vector2(1.0, 0.0).rotate(tech_state.deploy_timer_s * 300.0).x)
		
		# Draw wrench icon (simple L-shape)
		wrench_color = (
			int(160 + 55 * pulse),
			int(160 + 55 * pulse),
			80,
		)
		# Wrench handle (vertical)
		pygame.draw.rect(target, wrench_color, pygame.Rect(screen_x - 2, screen_y, 4, 12))
		# Wrench head (horizontal)
		pygame.draw.rect(target, wrench_color, pygame.Rect(screen_x - 6, screen_y, 10, 4))
		# Add outline for visibility
		pygame.draw.rect(target, (60, 60, 20), pygame.Rect(screen_x - 2, screen_y, 4, 12), 1)
		pygame.draw.rect(target, (60, 60, 20), pygame.Rect(screen_x - 6, screen_y, 10, 4), 1)
		return
	
	# --- Draw tech sprite when deployed (on truck, bus, or waiting at LZ) ---
	if tech_state.state != "on_chopper":
		x = int(tech_state.tech_x - camera_x)
		y = int(tech_state.tech_y)
		walking = str(getattr(tech_state, "boarding_animation_state", "")) in ("deploying", "returning", "disembarking", "boarding_bus")
		_draw_tech_stick_figure(target, x, y - 2, t=float(getattr(tech_state, "deploy_timer_s", 0.0)), walking=walking)
		
		# Draw wrench indicator above truck/tech at y-60 while deployed.
		if tech_state.state in ("deployed_to_truck", "driving_to_extraction", "extracting", "transferring", "boarding_bus", "transfer_complete", "waiting_at_lz"):
			indicator_x = int(tech_state.tech_x - camera_x)
			indicator_y = int(tech_state.tech_y - 60)
			pulse = 0.75 + 0.25 * (0.5 + 0.5 * pygame.math.Vector2(1.0, 0.0).rotate(tech_state.deploy_timer_s * 300.0).x)
			wrench_color = (
				int(160 + 55 * pulse),
				int(160 + 55 * pulse),
				80,
			)
			pygame.draw.rect(target, wrench_color, pygame.Rect(indicator_x - 2, indicator_y, 4, 12))
			pygame.draw.rect(target, wrench_color, pygame.Rect(indicator_x - 6, indicator_y, 10, 4))
			pygame.draw.rect(target, (60, 60, 20), pygame.Rect(indicator_x - 2, indicator_y, 4, 12), 1)
			pygame.draw.rect(target, (60, 60, 20), pygame.Rect(indicator_x - 6, indicator_y, 10, 4), 1)
