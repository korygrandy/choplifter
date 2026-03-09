"""Airport mission enemy wave helpers (lightweight phase-1 implementation)."""

from __future__ import annotations

from dataclasses import dataclass, field
import random

import pygame


@dataclass
class AirportSpawnEnemy:
	x: float
	y: float
	vx: float
	kind: str  # "uav" or "raider"
	ttl_s: float


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


def update_airport_enemy_spawns(enemy_state, dt: float, *, mission=None, bus_state=None):
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
			y = max(90.0, ground_y - random.uniform(150.0, 220.0))
			vx = -random.uniform(95.0, 135.0)
			ttl_s = 14.0
		else:
			y = ground_y - random.uniform(22.0, 36.0)
			vx = -random.uniform(55.0, 80.0)
			ttl_s = 24.0

		enemy_state.enemies.append(AirportSpawnEnemy(x=spawn_x, y=y, vx=vx, kind=kind, ttl_s=ttl_s))
		enemy_state.total_spawned += 1
		enemy_state.spawn_cooldown_s = _next_spawn_delay(enemy_state.elapsed_s)

	bus_x = float(getattr(bus_state, "x", world_width * 0.5)) if bus_state is not None else world_width * 0.5
	remaining: list[AirportSpawnEnemy] = []
	for e in enemy_state.enemies:
		e.x += e.vx * max(0.0, float(dt))
		e.ttl_s -= max(0.0, float(dt))

		if e.kind == "uav" and e.x < bus_x + 130.0:
			# Nose-dive hint: accelerate and descend near bus line.
			e.vx *= 1.015
			e.y += 46.0 * max(0.0, float(dt))

		if e.ttl_s <= 0.0:
			continue
		if bus_state is not None:
			dx = abs(e.x - float(getattr(bus_state, "x", bus_x)))
			if dx <= 18.0:
				# Basic phase-1 damage model: enemy impacts shave bus health.
				impact_damage = 9.0 if e.kind == "uav" else 5.0
				bus_health = float(getattr(bus_state, "health", 100.0))
				setattr(bus_state, "health", max(0.0, bus_health - impact_damage))
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
		x = int(e.x - float(camera_x))
		y = int(e.y)
		if e.kind == "uav":
			pygame.draw.polygon(
				target,
				(230, 230, 230),
				[(x, y), (x - 10, y + 4), (x - 14, y + 1), (x - 10, y - 3)],
			)
			pygame.draw.polygon(
				target,
				(20, 20, 20),
				[(x, y), (x - 10, y + 4), (x - 14, y + 1), (x - 10, y - 3)],
				1,
			)
		else:
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
