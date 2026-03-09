"""Airport mission cutscene trigger helpers."""

from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass
class AirportCutsceneState:
	meal_truck_extend_triggered: bool = False
	cue_timer_s: float = 0.0
	cue_text: str = ""


def create_airport_cutscene_state() -> AirportCutsceneState:
	return AirportCutsceneState()


def update_airport_cutscene_state(cutscene_state, dt: float, *, meal_truck_state=None, hostage_state=None, tech_state=None):
	if cutscene_state is None:
		cutscene_state = create_airport_cutscene_state()

	cutscene_state.cue_timer_s = max(0.0, float(cutscene_state.cue_timer_s) - max(0.0, float(dt)))

	truck_extended = bool(meal_truck_state is not None and float(getattr(meal_truck_state, "extension_progress", 0.0)) >= 0.98)
	tech_operating = bool(tech_state is not None and getattr(tech_state, "is_deployed", False))
	hostage_state_name = str(getattr(hostage_state, "state", "waiting")) if hostage_state is not None else "waiting"

	if (
		not cutscene_state.meal_truck_extend_triggered
		and truck_extended
		and tech_operating
		and hostage_state_name in ("waiting", "truck_loading")
	):
		cutscene_state.meal_truck_extend_triggered = True
		cutscene_state.cue_timer_s = 4.0
		cutscene_state.cue_text = "Plane breach reached: extraction window open"

	return cutscene_state


def draw_airport_cutscene_markers(target: pygame.Surface, cutscene_state, *, camera_x: float, ground_y: float, pickup_x: float = 1232.0) -> None:
	if cutscene_state is None:
		return

	x = int(float(pickup_x) - float(camera_x))
	y = int(float(ground_y) - 60)
	pygame.draw.polygon(target, (255, 215, 90), [(x, y), (x + 5, y + 10), (x + 12, y + 10), (x + 7, y + 16), (x + 9, y + 26), (x, y + 20), (x - 9, y + 26), (x - 7, y + 16), (x - 12, y + 10), (x - 5, y + 10)])

	if float(getattr(cutscene_state, "cue_timer_s", 0.0)) <= 0.0:
		return

	panel = pygame.Rect(220, 46, 360, 24)
	pygame.draw.rect(target, (22, 28, 34), panel, border_radius=5)
	pygame.draw.rect(target, (88, 96, 110), panel, 1, border_radius=5)
	try:
		font = pygame.font.Font(None, 20)
		surf = font.render(str(getattr(cutscene_state, "cue_text", "")), True, (242, 236, 220))
		target.blit(surf, (panel.x + 8, panel.y + 5))
	except Exception:
		pass
