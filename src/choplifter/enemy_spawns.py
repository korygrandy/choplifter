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
	kind: str  # "uav" or "raider"
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


def update_airport_enemy_spawns(enemy_state, dt: float, *, mission=None, bus_state=None, meal_truck_state=None, target_x: float | None = None):
	if enemy_state is None:
		enemy_state = create_airport_enemy_state()

	enemy_state.elapsed_s += max(0.0, float(dt))
	enemy_state.spawn_cooldown_s -= max(0.0, float(dt))

	world_width = float(getattr(mission, "world_width", 2800.0))
	ground_y = float(getattr(getattr(mission, "base", None), "pos", type("P", (), {"y": 430.0})()).y)
	if mission is not None and hasattr(mission, "base"):
		ground_y = float(mission.base.pos.y + mission.base.height)

	if enemy_state.spawn_cooldown_s <= 0.0:
		spawn_x = world_width + random.uniform(40.0, 180.0)
		kind = "uav" if random.random() < 0.5 else "raider"

		if kind == "uav":
			y = max(90.0, ground_y - random.uniform(165.0, 235.0))
			vx = -random.uniform(95.0, 135.0)
			ttl_s = 14.0
			max_health = 32.0
			vy = random.uniform(-4.0, 4.0)
			phase = "approach"
			weave_phase = random.uniform(0.0, math.pi * 2.0)
		else:
			y = ground_y  # Bottom-aligned to ground, same as city bus
			vx = -random.uniform(55.0, 80.0)
			ttl_s = 24.0
			max_health = 52.0
			vy = 0.0
			phase = "approach"
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
			if dx <= 18.0:
				# UAV dive impacts are heavier than raider impacts.
				base_damage = 12.0 if e.kind == "uav" else 5.0
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
		else:
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

		if health_ratio <= 0.70:
			smoke_alpha = 120 if health_ratio > 0.35 else 180
			smoke_radius = 4 if e.kind == "uav" else 6
			smoke = pygame.Surface((smoke_radius * 4, smoke_radius * 3), pygame.SRCALPHA)
			pygame.draw.circle(smoke, (55, 55, 55, smoke_alpha), (smoke_radius * 2 - 1, smoke_radius), smoke_radius)
			target.blit(smoke, (x - smoke_radius * 2, y - smoke_radius * 3))

		if health_ratio <= 0.35:
			fire_color = (255, 145, 72)
			fire_x = x + (9 if e.kind == "raider" else -3)
			fire_y = y - (18 if e.kind == "raider" else 4)
			pygame.draw.circle(target, fire_color, (fire_x, fire_y), 3)
			pygame.draw.circle(target, (255, 210, 120), (fire_x, fire_y), 1)
