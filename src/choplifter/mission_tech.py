"""Airport mission Mission Tech deployment and state machine."""

from __future__ import annotations

from dataclasses import dataclass

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
	is_repairing: bool = False  # Currently unused in new design
	repairs_completed: int = 0  # Currently unused in new design


def create_mission_tech_state() -> MissionTechState:
	"""Create initial mission tech state (tech starts on chopper)."""
	return MissionTechState(state="on_chopper")


def update_mission_tech(
	tech_state: MissionTechState | None,
	dt: float,
	*,
	helicopter=None,
	meal_truck_state=None,
	bus_state=None,
) -> MissionTechState:
	"""Update mission tech state machine.
	
	Args:
		tech_state: Current tech state
		dt: Delta time in seconds
		helicopter: Helicopter object (needed for deployment trigger)
		meal_truck_state: Meal truck state (needed for tracking tech on truck)
		bus_state: Bus state (needed for transfer completion check)
	
	Returns:
		Updated tech state
	"""
	if tech_state is None:
		tech_state = create_mission_tech_state()

	dt_s = max(0.0, float(dt))

	# Update boarding animation timer
	BOARDING_ANIMATION_DURATION = 0.4  # seconds
	if tech_state.boarding_animation_state != "idle":
		tech_state.boarding_animation_timer += dt_s
		if tech_state.boarding_animation_timer >= BOARDING_ANIMATION_DURATION:
			tech_state.boarding_animation_state = "idle"
			tech_state.boarding_animation_timer = 0.0

	# Re-board behavior: engineer can return to helicopter when linked up near truck.
	if (
		tech_state.state != "on_chopper"
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
	
	# --- State: on_chopper ---
	# Tech is aboard helicopter, waiting for deployment
	if tech_state.state == "on_chopper":
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
		
		# Tech follows helicopter position while on board
		if helicopter is not None:
			tech_state.tech_x = float(getattr(helicopter.pos, "x", tech_state.tech_x))
			tech_state.tech_y = float(getattr(helicopter.pos, "y", tech_state.tech_y))
	
	# --- State: deployed_to_truck ---
	# Tech has entered meal truck, truck is about to drive to extraction point
	elif tech_state.state == "deployed_to_truck":
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
		tech_state.deploy_timer_s += dt_s
		
		# Tech follows meal truck position
		if meal_truck_state is not None:
			tech_state.tech_x = float(getattr(meal_truck_state, "x", tech_state.tech_x))
			tech_state.tech_y = float(getattr(meal_truck_state, "y", tech_state.tech_y))
		
		# Transition: passengers transferred to bus (handled externally by hostage logic)
		# For now, tech stays in this state until mission ends
		# Future: add explicit transfer_complete transition when bus has passengers
	
	# --- State: transfer_complete ---
	# Passengers on bus, tech mission objective complete
	elif tech_state.state == "transfer_complete":
		tech_state.deploy_timer_s += dt_s
		# Tech position frozen at last known location
		# (Can return to chopper in future enhancement)
	
	return tech_state


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
	
	# --- Draw tech indicator above chopper when tech is on board ---
	if tech_state.state == "on_chopper" and helicopter is not None:
		heli_x = float(getattr(helicopter.pos, "x", 0.0))
		heli_y = float(getattr(helicopter.pos, "y", 0.0))
		screen_x = int(heli_x - camera_x)
		screen_y = int(heli_y - 60)
		
		# Draw wrench icon (simple L-shape)
		wrench_color = (200, 200, 80)  # Yellow-ish
		# Wrench handle (vertical)
		pygame.draw.rect(target, wrench_color, pygame.Rect(screen_x - 2, screen_y, 4, 12))
		# Wrench head (horizontal)
		pygame.draw.rect(target, wrench_color, pygame.Rect(screen_x - 6, screen_y, 10, 4))
		# Add outline for visibility
		pygame.draw.rect(target, (60, 60, 20), pygame.Rect(screen_x - 2, screen_y, 4, 12), 1)
		pygame.draw.rect(target, (60, 60, 20), pygame.Rect(screen_x - 6, screen_y, 10, 4), 1)
		return
	
	# --- Draw tech sprite when deployed (on truck or in field) ---
	if tech_state.state != "on_chopper":
		x = int(tech_state.tech_x - camera_x)
		y = int(tech_state.tech_y - 16)
		
		# Tech sprite (small green rectangle representing engineer)
		body = pygame.Rect(x - 6, y, 12, 14)
		pygame.draw.rect(target, (120, 200, 120), body, border_radius=3)
		pygame.draw.rect(target, (20, 60, 20), body, 1, border_radius=3)
		
		# Draw wrench icon above tech when deployed to truck
		if tech_state.state in ("deployed_to_truck", "driving_to_extraction", "extracting", "transferring"):
			wrench_color = (200, 200, 80)
			pygame.draw.rect(target, wrench_color, pygame.Rect(x - 2, y - 18, 4, 12))
			pygame.draw.rect(target, wrench_color, pygame.Rect(x - 6, y - 18, 10, 4))
			pygame.draw.rect(target, (60, 60, 20), pygame.Rect(x - 2, y - 18, 4, 12), 1)
			pygame.draw.rect(target, (60, 60, 20), pygame.Rect(x - 6, y - 18, 10, 4), 1)
