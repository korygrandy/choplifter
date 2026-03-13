"""Airport mission cutscene trigger helpers."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from .hostage_logic import get_active_airport_terminal_label


@dataclass
class AirportCutsceneState:
	last_cued_terminal_index: int = -1
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

	current_terminal = int(getattr(hostage_state, "active_terminal_index", 0)) if hostage_state is not None else 0
	if (
		cutscene_state.last_cued_terminal_index != current_terminal
		and truck_extended
		and tech_operating
		and hostage_state_name in ("waiting", "truck_loading")
	):
		terminal_label = get_active_airport_terminal_label(hostage_state) if hostage_state is not None else "elevated"
		cutscene_state.last_cued_terminal_index = current_terminal
		cutscene_state.cue_timer_s = 4.0
		cutscene_state.cue_text = f"{terminal_label.title()} terminal reached. Extraction window open."

	return cutscene_state


def draw_airport_cutscene_markers(target: pygame.Surface, cutscene_state, *, camera_x: float, ground_y: float, pickup_x: float = 1500.0) -> None:
	if cutscene_state is None:
		return

	x = int(float(pickup_x) - float(camera_x))
	y = int(float(ground_y) - 60)
	pygame.draw.polygon(target, (255, 215, 90), [(x, y), (x + 5, y + 10), (x + 12, y + 10), (x + 7, y + 16), (x + 9, y + 26), (x, y + 20), (x - 9, y + 26), (x - 7, y + 16), (x - 12, y + 10), (x - 5, y + 10)])
	# Text cues are intentionally handled by the centered objective strip to avoid duplicate HUD messaging.
