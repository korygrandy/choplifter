"""Airport mission objective tracking and lightweight HUD helpers."""

from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass
class AirportObjectiveState:
	hostage_deadline_s: float = 120.0
	deadline_failed: bool = False
	mission_phase: str = "waiting_for_tech_deploy"
	status_text: str = "Deploy tech to meal truck"


def create_airport_objective_state(*, hostage_deadline_s: float = 120.0) -> AirportObjectiveState:
	return AirportObjectiveState(hostage_deadline_s=max(15.0, float(hostage_deadline_s)))


def update_airport_objectives(objective_state, dt: float, *, mission=None, hostage_state=None, bus_state=None, meal_truck_state=None, tech_state=None):
	if objective_state is None:
		objective_state = create_airport_objective_state()

	elapsed = float(getattr(mission, "elapsed_seconds", 0.0)) if mission is not None else 0.0

	waiting = hostage_state is not None and str(getattr(hostage_state, "state", "waiting")) == "waiting"
	truck_loading = hostage_state is not None and str(getattr(hostage_state, "state", "waiting")) == "truck_loading"
	truck_loaded = hostage_state is not None and str(getattr(hostage_state, "state", "waiting")) == "truck_loaded"
	boarded = hostage_state is not None and str(getattr(hostage_state, "state", "waiting")) == "boarded"
	rescued = hostage_state is not None and str(getattr(hostage_state, "state", "waiting")) == "rescued"
    
	interrupted_transfers = int(getattr(hostage_state, "interrupted_transfers", 0)) if hostage_state is not None else 0
    
	tech_operating = bool(tech_state is not None and getattr(tech_state, "is_deployed", False))
	tech_on_bus = bool(tech_state is not None and getattr(tech_state, "on_bus", False))
	truck_active = bool(meal_truck_state is not None and getattr(meal_truck_state, "is_active", False))
	truck_at_plane_lz = bool(meal_truck_state is not None and getattr(meal_truck_state, "at_plane_lz", False))
	truck_extended = bool(
		meal_truck_state is not None
		and (
			float(getattr(meal_truck_state, "extension_progress", 0.0)) >= 0.92
			or str(getattr(meal_truck_state, "box_state", "idle")) == "extended"
		)
	)

	if waiting and elapsed >= float(objective_state.hostage_deadline_s):
		objective_state.deadline_failed = True

	if rescued:
		objective_state.mission_phase = "mission_complete"
		objective_state.status_text = "Hostages rescued"
	elif waiting and interrupted_transfers > 0 and not tech_operating and not tech_on_bus:
		objective_state.mission_phase = "auto_reset"
		objective_state.status_text = "Bus resetting to standby"
	elif boarded:
		objective_state.mission_phase = "escort_to_lz"
		objective_state.status_text = "Escort bus to LZ"
	elif hostage_state is not None and str(getattr(hostage_state, "state", "")) == "transferring_to_bus":
		objective_state.mission_phase = "transferring_to_bus"
		objective_state.status_text = "Transferring civilians to bus"
	elif truck_loaded:
		objective_state.mission_phase = "truck_driving_to_bus"
		objective_state.status_text = "Drive truck to bus transfer lane"
	elif truck_loading:
		objective_state.mission_phase = "extracting_hostages"
		objective_state.status_text = "Meal truck extracting civilians"
	elif truck_active and tech_operating:
		objective_state.mission_phase = "truck_driving_to_bunker"
		if truck_at_plane_lz and not truck_extended:
			objective_state.status_text = "Extend lift at damaged plane"
		else:
			objective_state.status_text = "Drive meal truck to damaged plane"
	elif waiting:
		objective_state.mission_phase = "waiting_for_tech_deploy"
		objective_state.status_text = "Deploy tech to meal truck"
	else:
		objective_state.mission_phase = "waiting_for_tech_deploy"
		objective_state.status_text = "Deploy tech to meal truck"

	return objective_state


def draw_airport_objectives(target: pygame.Surface, objective_state, *, camera_x: float, ground_y: float, bus_state=None) -> None:
	if objective_state is None:
		return

	# World marker at bus position so objective context stays in-world.
	marker_x_world = float(getattr(bus_state, "x", 1300.0)) if bus_state is not None else 1300.0
	marker_x = int(marker_x_world - float(camera_x))
	marker_y = int(float(ground_y) - 50)

	color = (255, 215, 0)
	if bool(getattr(objective_state, "deadline_failed", False)):
		color = (225, 70, 70)
	elif str(getattr(objective_state, "mission_phase", "")) == "mission_complete":
		color = (95, 215, 120)

	pygame.draw.circle(target, color, (marker_x, marker_y), 6)
	pygame.draw.circle(target, (20, 20, 20), (marker_x, marker_y), 6, 1)

	# Compact top-left status panel.
	panel = pygame.Rect(12, 46, 248, 24)
	pygame.draw.rect(target, (20, 24, 30), panel, border_radius=5)
	pygame.draw.rect(target, (70, 80, 95), panel, 1, border_radius=5)
	try:
		font = pygame.font.Font(None, 20)
		text = str(getattr(objective_state, "status_text", "Objective"))
		surf = font.render(text, True, (236, 236, 236))
		target.blit(surf, (panel.x + 8, panel.y + 5))
	except Exception:
		# Keep draw path resilient when font init is unavailable.
		pass
