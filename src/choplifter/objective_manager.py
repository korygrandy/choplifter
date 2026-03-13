"""Airport mission objective tracking and lightweight HUD helpers."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from .hostage_logic import get_active_airport_terminal_label


CITY_MISSION_IDS = ("city", "city_center", "citycenter", "mission1", "m1")
AIRPORT_MISSION_IDS = ("airport", "airport_special_ops", "airportspecialops", "mission2", "m2")

ELEVATED_FIRST_SENTIMENT_BONUS = 3.0
LOWER_FIRST_SENTIMENT_BONUS = 2.0


# Top-center objective strip typewriter state.
_TYPEWRITER_TEXT: str = ""
_TYPEWRITER_TYPED_LEN: int = 0
_TYPEWRITER_LAST_TICK_MS: int = 0
_TYPEWRITER_CHARS_PER_SEC: float = 26.0


@dataclass
class AirportObjectiveState:
	hostage_deadline_s: float = 120.0
	deadline_failed: bool = False
	mission_phase: str = "waiting_for_tech_deploy"
	status_text: str = "Deploy mission tech to meal truck"
	route_tip_shown: bool = False


def create_airport_objective_state(*, hostage_deadline_s: float = 120.0) -> AirportObjectiveState:
	return AirportObjectiveState(hostage_deadline_s=max(15.0, float(hostage_deadline_s)))


def _airport_terminal_display_name(label: str) -> str:
	label_norm = str(label or "").strip().lower()
	if label_norm == "fuselage":
		return "Fuselage Terminal"
	if label_norm == "jetway":
		return "Jetway Terminal"
	if label_norm == "lower":
		return "Lower Terminal"
	return "Elevated Terminal"


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
	remaining_elevated = sum(max(0, int(v)) for v in (getattr(hostage_state, "terminal_remaining", []) or [])) if hostage_state is not None else 0
	terminal_label = get_active_airport_terminal_label(hostage_state) if hostage_state is not None else "elevated"
	terminal_display_name = _airport_terminal_display_name(terminal_label)
    
	tech_operating = bool(tech_state is not None and getattr(tech_state, "is_deployed", False))
	tech_on_bus = bool(tech_state is not None and getattr(tech_state, "on_bus", False))
	tech_state_name = str(getattr(tech_state, "state", "")) if tech_state is not None else ""
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

	total_target = 16
	lower_rescued = int(getattr(getattr(mission, "stats", None), "saved", 0)) if mission is not None else 0
	elevated_rescued = int(getattr(hostage_state, "rescued_hostages", 0)) if hostage_state is not None else 0
	combined_rescued = lower_rescued + elevated_rescued

	mission_id = str(getattr(mission, "mission_id", "")).strip().lower() if mission is not None else ""
	is_airport = mission_id in AIRPORT_MISSION_IDS
	if is_airport and mission is not None:
		first_route = str(getattr(mission, "airport_first_rescue_route", "")).strip().lower()
		if first_route not in ("lower", "elevated"):
			if elevated_rescued > 0 and lower_rescued <= 0:
				first_route = "elevated"
			elif lower_rescued > 0 and elevated_rescued <= 0:
				first_route = "lower"
			if first_route:
				setattr(mission, "airport_first_rescue_route", first_route)

		if elevated_rescued > 0 and lower_rescued > 0 and not bool(getattr(mission, "airport_route_bonus_awarded", False)):
			first_route = str(getattr(mission, "airport_first_rescue_route", "")).strip().lower()
			bonus = LOWER_FIRST_SENTIMENT_BONUS
			if first_route == "elevated":
				bonus = ELEVATED_FIRST_SENTIMENT_BONUS
			mission.sentiment = min(100.0, float(getattr(mission, "sentiment", 50.0)) + float(bonus))
			setattr(mission, "airport_route_bonus_awarded", True)
			setattr(mission, "airport_route_bonus_value", float(bonus))

	if rescued and combined_rescued >= total_target:
		objective_state.mission_phase = "mission_complete"
		objective_state.status_text = "All civilians rescued"
	elif rescued and tech_state_name == "waiting_at_lz":
		objective_state.mission_phase = "awaiting_tech_reboard"
		objective_state.status_text = "Land at tower LZ and pick up mission tech"
	elif rescued and not tech_on_bus:
		# Elevated rescue flow is complete; continue lower-level rescues after tech rejoins chopper.
		objective_state.mission_phase = "resume_lower_rescue"
		objective_state.status_text = "Resume Lower Terminal rescues"
	elif waiting and interrupted_transfers > 0 and not tech_operating and not tech_on_bus:
		objective_state.mission_phase = "auto_reset"
		objective_state.status_text = "Bus resetting to standby"
	elif waiting and remaining_elevated > 0 and lower_rescued <= 0 and not bool(getattr(objective_state, "route_tip_shown", False)):
		objective_state.mission_phase = "waiting_for_tech_deploy"
		objective_state.status_text = "Tip: any order works; elevated-first is riskiest (+bonus)"
		objective_state.route_tip_shown = True
	elif boarded:
		objective_state.mission_phase = "escort_to_lz"
		objective_state.status_text = "Escort bus to tower LZ"
	elif hostage_state is not None and str(getattr(hostage_state, "state", "")) == "transferring_to_bus":
		objective_state.mission_phase = "transferring_to_bus"
		objective_state.status_text = "Transfer civilians to bus"
	elif truck_loaded:
		if remaining_elevated > 0:
			objective_state.mission_phase = "truck_driving_to_bunker"
			objective_state.status_text = f"Drive meal truck to {terminal_display_name}"
		else:
			objective_state.mission_phase = "truck_driving_to_bus"
			objective_state.status_text = "Drive meal truck to bus transfer lane"
	elif truck_loading:
		objective_state.mission_phase = "extracting_hostages"
		objective_state.status_text = f"Load civilians onto meal truck at {terminal_display_name}"
	elif truck_active and tech_operating:
		objective_state.mission_phase = "truck_driving_to_bunker"
		if truck_at_plane_lz and not truck_extended:
			objective_state.status_text = f"Extend meal-truck lift at {terminal_display_name}"
		else:
			objective_state.status_text = f"Drive meal truck to {terminal_display_name}"
	elif waiting:
		objective_state.mission_phase = "waiting_for_tech_deploy"
		objective_state.status_text = "Deploy mission tech to meal truck"
	else:
		objective_state.mission_phase = "waiting_for_tech_deploy"
		objective_state.status_text = "Deploy mission tech to meal truck"

	return objective_state


def _is_city_siege_mission(mission) -> bool:
	mission_id = str(getattr(mission, "mission_id", "")).strip().lower()
	return mission_id in CITY_MISSION_IDS


def _city_status_text(mission) -> str:
	stats = getattr(mission, "stats", None)
	saved = int(getattr(stats, "saved", 0)) if stats is not None else 0
	total_target = max(1, int(getattr(mission, "hostages_to_save", 21)))

	vip_hostage = next((h for h in getattr(mission, "hostages", []) if bool(getattr(h, "is_vip", False))), None)
	vip_state = str(getattr(getattr(vip_hostage, "state", None), "name", "")) if vip_hostage is not None else ""

	if bool(getattr(mission, "ended", False)):
		if bool(getattr(mission, "mission_success", False)):
			return "Mission complete"
		if vip_state == "KIA":
			return "Mission failed: VIP lost"
		return "Mission failed"

	if vip_state == "KIA":
		return "VIP down - extraction failed"

	if vip_hostage is None:
		return f"Rescue civilians ({saved}/{total_target})"

	vip_secured = vip_state in ("BOARDED", "SAVED")
	if vip_secured:
		return f"VIP secured - rescue civilians ({saved}/{total_target})"

	return f"Rescue VIP + civilians ({saved}/{total_target})"


def draw_city_objectives(target: pygame.Surface, mission) -> None:
	"""Draw City Siege top-center command strip using airport objective panel styling."""
	if mission is None or not _is_city_siege_mission(mission):
		return

	status_text = _city_status_text(mission)
	objective_state = type(
		"CityObjectiveState",
		(),
		{
			"status_text": status_text,
			"deadline_failed": False,
			"mission_phase": "city_siege",
		},
	)()
	draw_airport_objectives(target, objective_state, camera_x=0.0, ground_y=0.0, bus_state=None)


def draw_airport_objectives(target: pygame.Surface, objective_state, *, camera_x: float, ground_y: float, bus_state=None) -> None:
	global _TYPEWRITER_TEXT, _TYPEWRITER_TYPED_LEN, _TYPEWRITER_LAST_TICK_MS

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

	# Compact top-center status panel (1980s green-screen terminal style).
	status = str(getattr(objective_state, "status_text", "Objective")).upper().strip()
	if not status:
		status = "OBJECTIVE"

	panel_w = 380
	try:
		font_probe = pygame.font.SysFont("consolas", 18, bold=True)
		prompt_w = font_probe.size(">")[0]
		status_w = font_probe.size(status)[0]
		required_w = 34 + prompt_w + status_w
		panel_w = min(max(380, required_w), max(380, target.get_width() - 16))
	except Exception:
		# Keep fixed baseline width if font probing is unavailable.
		panel_w = min(380, max(180, target.get_width() - 16))

	panel_h = 28
	panel_x = max(8, (target.get_width() - panel_w) // 2)
	panel = pygame.Rect(panel_x, 10, panel_w, panel_h)

	t = pygame.time.get_ticks() / 1000.0
	flicker = 0.80 + 0.20 * (0.5 + 0.5 * math.sin(t * 18.0))

	# Panel background + old CRT green frame.
	pygame.draw.rect(target, (8, 16, 8), panel, border_radius=4)
	border_green = int(90 + 70 * flicker)
	pygame.draw.rect(target, (24, border_green, 24), panel, 1, border_radius=4)

	# Subtle scan lines for old display feel.
	for y in range(panel.y + 2, panel.bottom - 1, 3):
		pygame.draw.line(target, (6, 24, 6), (panel.x + 2, y), (panel.right - 2, y), 1)

	# Clip text rendering inside panel interior.
	old_clip = target.get_clip()
	inner = panel.inflate(-8, -8)
	target.set_clip(inner)
	try:
		font = pygame.font.SysFont("consolas", 18, bold=True)

		now_ms = pygame.time.get_ticks()
		if _TYPEWRITER_LAST_TICK_MS <= 0:
			_TYPEWRITER_LAST_TICK_MS = now_ms

		# Event-driven update: clear previous line and retype only when objective text changes.
		if status != _TYPEWRITER_TEXT:
			_TYPEWRITER_TEXT = status
			_TYPEWRITER_TYPED_LEN = 0
			_TYPEWRITER_LAST_TICK_MS = now_ms

		dt_s = max(0.0, (now_ms - _TYPEWRITER_LAST_TICK_MS) / 1000.0)
		if _TYPEWRITER_TYPED_LEN < len(_TYPEWRITER_TEXT):
			advance = int(dt_s * _TYPEWRITER_CHARS_PER_SEC)
			if advance > 0:
				_TYPEWRITER_TYPED_LEN = min(len(_TYPEWRITER_TEXT), _TYPEWRITER_TYPED_LEN + advance)
				_TYPEWRITER_LAST_TICK_MS = now_ms

		typed_text = _TYPEWRITER_TEXT[:_TYPEWRITER_TYPED_LEN]

		prompt_color = (72, int(208 * flicker), 72)
		text_color = (92, int(236 * flicker), 92)
		glow_color = (24, 82, 24)

		# Left DOS prompt anchor.
		cursor_on = int(t * 2.2) % 2 == 0
		prompt = font.render(">", True, prompt_color)
		prompt_x = inner.x + 4
		prompt_y = inner.centery - prompt.get_height() // 2
		target.blit(prompt, (prompt_x, prompt_y))

		surf = font.render(typed_text, True, text_color)
		text_x = prompt_x + prompt.get_width() + 8
		text_y = inner.centery - surf.get_height() // 2

		# Soft glow pass then bright text pass.
		glow = font.render(typed_text, True, glow_color)
		target.blit(glow, (text_x + 1, text_y + 1))
		target.blit(surf, (text_x, text_y))

		# Blinking cursor follows the typed text like a classic terminal.
		if cursor_on:
			cursor_x = text_x + surf.get_width() + 1
			cursor = font.render("_", True, text_color)
			target.blit(cursor, (cursor_x, text_y))
	except Exception:
		# Keep draw path resilient when font init is unavailable.
		pass
	finally:
		target.set_clip(old_clip)
