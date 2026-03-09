"""Airport mission Mission Tech deployment and repair helpers."""

from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass
class MissionTechState:
	is_deployed: bool = False
	is_repairing: bool = False
	tech_x: float = 0.0
	tech_y: float = 0.0
	deploy_timer_s: float = 0.0
	repairs_completed: int = 0


def create_mission_tech_state() -> MissionTechState:
	return MissionTechState()


def update_mission_tech(tech_state, dt: float, *, helicopter=None, bus_state=None):
	if tech_state is None:
		tech_state = create_mission_tech_state()

	if helicopter is None or bus_state is None:
		return tech_state

	near_bus = abs(float(getattr(helicopter.pos, "x", 0.0)) - float(getattr(bus_state, "x", 0.0))) <= 120.0
	supports_deploy = bool(getattr(helicopter, "grounded", False) and getattr(helicopter, "doors_open", False) and near_bus)

	if supports_deploy and not tech_state.is_deployed:
		tech_state.is_deployed = True
		tech_state.deploy_timer_s = 0.0
		tech_state.tech_x = float(getattr(bus_state, "x", 0.0)) - 18.0
		tech_state.tech_y = float(getattr(bus_state, "y", 0.0))
	elif not supports_deploy and tech_state.is_deployed:
		tech_state.is_deployed = False
		tech_state.is_repairing = False

	if not tech_state.is_deployed:
		return tech_state

	tech_state.deploy_timer_s += max(0.0, float(dt))
	tech_state.tech_x = float(getattr(bus_state, "x", tech_state.tech_x)) - 18.0
	tech_state.tech_y = float(getattr(bus_state, "y", tech_state.tech_y))

	# Delay a beat before repairs start, so deployment is visible.
	repair_window_open = tech_state.deploy_timer_s >= 0.65
	bus_health = float(getattr(bus_state, "health", 100.0))
	bus_max_health = float(getattr(bus_state, "max_health", 100.0))

	tech_state.is_repairing = repair_window_open and bus_health < bus_max_health
	if tech_state.is_repairing:
		new_health = min(bus_max_health, bus_health + 22.0 * max(0.0, float(dt)))
		setattr(bus_state, "health", new_health)
		if int(new_health) != int(bus_health) and int(new_health) >= int(bus_max_health):
			tech_state.repairs_completed += 1

	return tech_state


def draw_airport_mission_tech(target: pygame.Surface, tech_state, *, camera_x: float, bus_state=None) -> None:
	if tech_state is None or not bool(getattr(tech_state, "is_deployed", False)):
		return

	x = int(float(getattr(tech_state, "tech_x", 0.0)) - float(camera_x))
	y = int(float(getattr(tech_state, "tech_y", 0.0)) - 16)
	body = pygame.Rect(x, y, 12, 14)
	pygame.draw.rect(target, (120, 200, 120), body, border_radius=3)
	pygame.draw.rect(target, (20, 60, 20), body, 1, border_radius=3)

	if bool(getattr(tech_state, "is_repairing", False)):
		# Tiny wrench spark indicator.
		pygame.draw.line(target, (255, 240, 120), (x + 8, y - 2), (x + 13, y - 6), 2)

	if bus_state is not None:
		health = float(getattr(bus_state, "health", 100.0))
		max_health = max(1.0, float(getattr(bus_state, "max_health", 100.0)))
		frac = max(0.0, min(1.0, health / max_health))
		bx = int(float(getattr(bus_state, "x", 0.0)) - float(camera_x))
		by = int(float(getattr(bus_state, "y", 0.0)) - float(getattr(bus_state, "height", 24)) - 10)
		pygame.draw.rect(target, (30, 30, 30), pygame.Rect(bx, by, 44, 6), border_radius=2)
		pygame.draw.rect(target, (90, 220, 110), pygame.Rect(bx + 1, by + 1, int(42 * frac), 4), border_radius=2)
