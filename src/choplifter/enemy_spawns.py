"""Airport mission enemy wave helpers (lightweight phase-1 implementation)."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import os
import random

import pygame
from .app.escort_risk import airport_escort_damage_multiplier
from .vehicle_damage import apply_vehicle_damage, is_airport_bus_vulnerable, vehicle_health_ratio

# Sprite cache — loaded once on first draw call, never reloaded.
_RAIDER_SPRITE: pygame.Surface | None = None
_RAIDER_SPRITE_TRIED: bool = False
_RAIDER_RENDER_W = 36
_RAIDER_RENDER_H = 24


def _get_raider_sprite() -> "pygame.Surface | None":
	global _RAIDER_SPRITE, _RAIDER_SPRITE_TRIED
	if _RAIDER_SPRITE_TRIED:
		return _RAIDER_SPRITE
	_RAIDER_SPRITE_TRIED = True
	try:
		asset_dir = os.path.join(os.path.dirname(__file__), "assets")
		path = os.path.join(asset_dir, "nazir-robot-tank.png")
		raw = pygame.image.load(path).convert_alpha()
		scaled = pygame.transform.scale(raw, (_RAIDER_RENDER_W, _RAIDER_RENDER_H))
		_RAIDER_SPRITE = scaled
	except Exception:
		_RAIDER_SPRITE = None
	return _RAIDER_SPRITE


@dataclass
class AirportSpawnEnemy:
	x: float
	y: float
	vx: float
	kind: str  # "uav", "raider" (minesweeper), or "raider_mine"
	ttl_s: float
	max_health: float = 32.0
	health: float = 32.0
	damage_state: str = "nominal"
	damage_flash_s: float = 0.0
	vy: float = 0.0
	base_y: float = 0.0
	phase: str = "approach"  # approach -> dive
	weave_phase: float = 0.0


@dataclass
class AirportEnemyState:
	enemies: list[AirportSpawnEnemy] = field(default_factory=list)
	spawn_cooldown_s: float = 4.5
	elapsed_s: float = 0.0
	total_spawned: int = 0


def create_airport_enemy_state() -> AirportEnemyState:
	return AirportEnemyState()


def _next_spawn_delay(elapsed_s: float) -> float:
	# Gradually tighten wave cadence over time.
	if elapsed_s < 45.0:
		return random.uniform(4.0, 6.0)
	if elapsed_s < 120.0:
		return random.uniform(3.2, 5.0)
	return random.uniform(2.8, 4.2)


def _is_mission_tech_bus_escort_active(*, mission: object | None, bus_state: object | None) -> bool:
	"""Threat waves are active only while mission tech is driving bus escort."""
	if mission is None or bus_state is None:
		return False

	if not bool(getattr(bus_state, "is_moving", False)):
		return False

	objective_state = getattr(mission, "airport_objective_state", None)
	mission_phase = str(getattr(objective_state, "mission_phase", "")).strip().lower()
	if mission_phase != "escort_to_lz":
		return False

	tech_state = getattr(mission, "mission_tech", None)
	return bool(tech_state is not None and bool(getattr(tech_state, "on_bus", False)))


def update_airport_enemy_spawns(enemy_state, dt: float, *, mission=None, bus_state=None, meal_truck_state=None, target_x: float | None = None):
	if enemy_state is None:
		enemy_state = create_airport_enemy_state()

	enemy_state.elapsed_s += max(0.0, float(dt))
	enemy_state.spawn_cooldown_s -= max(0.0, float(dt))

	world_width = float(getattr(mission, "world_width", 2800.0))
	ground_y = float(getattr(getattr(mission, "base", None), "pos", type("P", (), {"y": 430.0})()).y)
	if mission is not None and hasattr(mission, "base"):
		ground_y = float(mission.base.pos.y + mission.base.height)

	escort_attacks_active = _is_mission_tech_bus_escort_active(mission=mission, bus_state=bus_state)
	if not escort_attacks_active:
		# Keep airport threats dormant until mission-tech bus escort starts.
		enemy_state.enemies = []
		enemy_state.spawn_cooldown_s = max(0.2, float(enemy_state.spawn_cooldown_s))
		return enemy_state

	if enemy_state.spawn_cooldown_s <= 0.0:
		spawn_roll = random.random()
		if spawn_roll < 0.46:
			kind = "uav"
		elif spawn_roll < 0.82:
			kind = "raider"
		else:
			kind = "raider_mine"

		if kind == "raider_mine":
			bus_anchor_x = float(getattr(bus_state, "x", world_width * 0.55))
			spawn_x = bus_anchor_x + random.uniform(90.0, 240.0)
			spawn_x = max(120.0, min(world_width - 80.0, spawn_x))
		else:
			spawn_x = world_width + random.uniform(40.0, 180.0)

		if kind == "uav":
			y = max(90.0, ground_y - random.uniform(165.0, 235.0))
			vx = -random.uniform(95.0, 135.0)
			ttl_s = 14.0
			max_health = 32.0
			vy = random.uniform(-4.0, 4.0)
			phase = "approach"
			weave_phase = random.uniform(0.0, math.pi * 2.0)
		else:
			if kind == "raider":
				y = ground_y  # Bottom-aligned to ground, same as city bus
				vx = -random.uniform(55.0, 80.0)
				ttl_s = 24.0
				max_health = 52.0
				vy = 0.0
				phase = "approach"
				weave_phase = 0.0
			else:
				# Raider mine: short-lived static ground hazard during escort.
				y = ground_y
				vx = 0.0
				ttl_s = 9.0
				max_health = 24.0
				vy = 0.0
				phase = "armed"
				weave_phase = 0.0

		enemy_state.enemies.append(
			AirportSpawnEnemy(
				x=spawn_x,
				y=y,
				vx=vx,
				kind=kind,
				ttl_s=ttl_s,
				max_health=max_health,
				health=max_health,
				vy=vy,
				base_y=y,
				phase=phase,
				weave_phase=weave_phase,
			)
		)
		enemy_state.total_spawned += 1
		enemy_state.spawn_cooldown_s = _next_spawn_delay(enemy_state.elapsed_s)

	bus_x = float(getattr(bus_state, "x", world_width * 0.5)) if bus_state is not None else world_width * 0.5
	target_ref_x = float(target_x) if target_x is not None else bus_x
	remaining: list[AirportSpawnEnemy] = []
	for e in enemy_state.enemies:
		if float(getattr(e, "health", 1.0)) <= 0.0:
			continue
		dt_s = max(0.0, float(dt))
		e.ttl_s -= dt_s
		e.damage_flash_s = max(0.0, float(getattr(e, "damage_flash_s", 0.0)) - dt_s)

		if e.kind == "uav":
			if e.phase == "approach":
				e.weave_phase += dt_s * 4.2
				# Distinct UAV movement: stable forward speed + sinusoidal weave.
				e.vx = min(e.vx, -92.0)
				e.y = float(e.base_y) + math.sin(float(e.weave_phase)) * 16.0
				if e.x <= target_ref_x + 250.0:
					e.phase = "dive"
					e.vy = 28.0
					e.vx = min(e.vx, -118.0)
			else:
				# Lock and dive with increasing descent rate toward target line.
				e.vx *= 1.010
				e.vy = min(165.0, e.vy + 95.0 * dt_s)
				e.y += e.vy * dt_s

		e.x += e.vx * dt_s
		if e.kind != "uav":
			e.y += e.vy * dt_s

		if e.ttl_s <= 0.0:
			continue
		if bus_state is not None:
			dx = abs(e.x - target_ref_x)
			impact_radius = 18.0 if e.kind != "raider_mine" else 22.0
			if dx <= impact_radius:
				# UAV dive impacts are heavier than raiders/mines.
				if e.kind == "uav":
					base_damage = 12.0
				elif e.kind == "raider_mine":
					base_damage = 9.0
				else:
					base_damage = 5.0
				target_vehicle = bus_state
				target_is_bus = True
				if meal_truck_state is not None:
					truck_x = float(getattr(meal_truck_state, "x", target_ref_x + 99999.0))
					if abs(e.x - truck_x) <= 24.0:
						target_vehicle = meal_truck_state
						target_is_bus = False

				allow_damage = True
				if target_is_bus:
					allow_damage = is_airport_bus_vulnerable(mission)
				scale = airport_escort_damage_multiplier(mission) if target_is_bus else 1.0
				apply_vehicle_damage(
					target_vehicle,
					base_damage * scale,
					default_max_health=float(getattr(target_vehicle, "max_health", 100.0) or 100.0),
					allow_damage=allow_damage,
					source=f"{e.kind}_impact",
				)
				continue
		if e.x < -220.0:
			continue
		remaining.append(e)

	enemy_state.enemies = remaining
	return enemy_state


def draw_airport_enemies(target: pygame.Surface, enemy_state, *, camera_x: float) -> None:
	if enemy_state is None:
		return

	for e in enemy_state.enemies:
		health_ratio = vehicle_health_ratio(e, default_max_health=float(getattr(e, "max_health", 32.0) or 32.0))
		x = int(e.x - float(camera_x))
		y = int(e.y)
		if e.kind == "uav":
			nose = (255, 120, 120) if e.phase == "dive" else (230, 230, 230)
			wing = (205, 205, 205)
			pygame.draw.polygon(
				target,
				nose,
				[(x, y), (x - 10, y + 4), (x - 14, y + 1), (x - 10, y - 3)],
			)
			pygame.draw.line(target, wing, (x - 6, y), (x - 16, y - 5), 2)
			pygame.draw.line(target, wing, (x - 6, y), (x - 16, y + 5), 2)
			pygame.draw.polygon(
				target,
				(20, 20, 20),
				[(x, y), (x - 10, y + 4), (x - 14, y + 1), (x - 10, y - 3)],
				1,
			)
		elif e.kind == "raider":
			sprite = _get_raider_sprite()
			if sprite is not None:
				# Draw centred horizontally, bottom-aligned to ground position.
				draw_x = x - _RAIDER_RENDER_W // 2
				draw_y = y - _RAIDER_RENDER_H
				target.blit(sprite, (draw_x, draw_y))
			else:
				# Procedural triangle fallback when asset is unavailable.
				pygame.draw.polygon(
					target,
					(200, 40, 40),
					[(x, y), (x - 10, y + 20), (x + 10, y + 20)],
				)
				pygame.draw.polygon(
					target,
					(40, 10, 10),
					[(x, y), (x - 10, y + 20), (x + 10, y + 20)],
					1,
				)
		else:
			# Raider mine: armed ground explosive the player can pick off.
			mine_body = (170, 170, 185)
			mine_spike = (65, 65, 75)
			mine_y = y - 5
			pygame.draw.circle(target, mine_body, (x, mine_y), 7)
			for sx, sy in ((0, -10), (8, -4), (8, 4), (0, 10), (-8, 4), (-8, -4)):
				pygame.draw.line(target, mine_spike, (x, mine_y), (x + sx, mine_y + sy), 2)
			pygame.draw.circle(target, (32, 32, 38), (x, mine_y), 7, 1)

		if health_ratio <= 0.70:
			smoke_alpha = 120 if health_ratio > 0.35 else 180
			smoke_radius = 4 if e.kind == "uav" else 6
			smoke = pygame.Surface((smoke_radius * 4, smoke_radius * 3), pygame.SRCALPHA)
			pygame.draw.circle(smoke, (55, 55, 55, smoke_alpha), (smoke_radius * 2 - 1, smoke_radius), smoke_radius)
			target.blit(smoke, (x - smoke_radius * 2, y - smoke_radius * 3))

		if health_ratio <= 0.35:
			fire_color = (255, 145, 72)
			if e.kind == "raider":
				fire_x = x + 9
				fire_y = y - 18
			elif e.kind == "raider_mine":
				fire_x = x
				fire_y = y - 6
			else:
				fire_x = x - 3
				fire_y = y + 4
			pygame.draw.circle(target, fire_color, (fire_x, fire_y), 3)
			pygame.draw.circle(target, (255, 210, 120), (fire_x, fire_y), 1)
