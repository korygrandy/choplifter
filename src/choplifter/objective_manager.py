"""Airport mission objective tracking and lightweight HUD helpers."""

from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass
class AirportObjectiveState:
	hostage_deadline_s: float = 120.0
	deadline_failed: bool = False
	mission_phase: str = "reach_hostages"  # reach_hostages -> escort_return -> complete
	status_text: str = "Reach hostages"


def create_airport_objective_state(*, hostage_deadline_s: float = 120.0) -> AirportObjectiveState:
	return AirportObjectiveState(hostage_deadline_s=max(15.0, float(hostage_deadline_s)))


def update_airport_objectives(objective_state, dt: float, *, mission=None, hostage_state=None, bus_state=None):
	if objective_state is None:
		objective_state = create_airport_objective_state()

	elapsed = float(getattr(mission, "elapsed_seconds", 0.0)) if mission is not None else 0.0

	waiting = hostage_state is not None and str(getattr(hostage_state, "state", "waiting")) == "waiting"
	boarded = hostage_state is not None and str(getattr(hostage_state, "state", "waiting")) == "boarded"
	rescued = hostage_state is not None and str(getattr(hostage_state, "state", "waiting")) == "rescued"

	if waiting and elapsed >= float(objective_state.hostage_deadline_s):
		objective_state.deadline_failed = True

	if rescued:
		objective_state.mission_phase = "complete"
		objective_state.status_text = "Hostages rescued"
	elif boarded:
		objective_state.mission_phase = "escort_return"
		objective_state.status_text = "Escort bus to LZ"
	else:
		objective_state.mission_phase = "reach_hostages"
		remaining = max(0, int(objective_state.hostage_deadline_s - elapsed))
		objective_state.status_text = f"Reach hostages ({remaining}s)"

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
	elif str(getattr(objective_state, "mission_phase", "")) == "complete":
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
