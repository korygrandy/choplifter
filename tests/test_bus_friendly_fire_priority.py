from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.choplifter.bus_ai import BusState, apply_airport_bus_friendly_fire
from src.choplifter.enemy_spawns import AirportEnemyState, AirportSpawnEnemy
from src.choplifter.entities import Projectile
from src.choplifter.game_types import ProjectileKind
from src.choplifter.math2d import Vec2


class _DummySparks:
    def emit_hit(self, *_args, **_kwargs) -> None:
        pass


class _DummyExplosions:
    def emit_explosion(self, *_args, **_kwargs) -> None:
        pass


class BusFriendlyFirePriorityTests(unittest.TestCase):
    def _make_mission(self, *, projectile: Projectile, enemy_state: AirportEnemyState) -> SimpleNamespace:
        return SimpleNamespace(
            projectiles=[projectile],
            airport_enemy_state=enemy_state,
            airport_hostage_state=SimpleNamespace(state="boarded"),
            airport_objective_state=SimpleNamespace(mission_phase="escort_to_lz"),
            mission_tech=SimpleNamespace(on_bus=True),
            stats=SimpleNamespace(enemies_destroyed=0),
            impact_sparks=_DummySparks(),
            explosions=_DummyExplosions(),
        )

    def test_raider_overlapping_bus_absorbs_bullet_with_enemy_damage(self) -> None:
        bus = BusState(x=100.0, y=220.0, width=64, height=24, health=100.0, max_health=100.0)
        projectile = Projectile(
            kind=ProjectileKind.BULLET,
            pos=Vec2(138.0, 212.0),
            vel=Vec2(220.0, 0.0),
            ttl=1.0,
        )
        enemy_state = AirportEnemyState(
            enemies=[AirportSpawnEnemy(x=150.0, y=220.0, vx=0.0, kind="raider", ttl_s=2.0, max_health=52.0, health=52.0)],
            spawn_cooldown_s=10.0,
            elapsed_s=0.0,
        )
        mission = self._make_mission(projectile=projectile, enemy_state=enemy_state)

        hits = apply_airport_bus_friendly_fire(bus, mission)

        self.assertEqual(hits, 1)
        self.assertFalse(projectile.alive)
        self.assertEqual(bus.health, 100.0)
        self.assertEqual(enemy_state.enemies[0].health, 41.0)

    def test_bus_takes_damage_when_no_raider_overlaps(self) -> None:
        bus = BusState(x=100.0, y=220.0, width=64, height=24, health=100.0, max_health=100.0)
        projectile = Projectile(
            kind=ProjectileKind.BULLET,
            pos=Vec2(138.0, 212.0),
            vel=Vec2(220.0, 0.0),
            ttl=1.0,
        )
        enemy_state = AirportEnemyState(
            enemies=[AirportSpawnEnemy(x=220.0, y=220.0, vx=0.0, kind="raider", ttl_s=2.0, max_health=52.0, health=52.0)],
            spawn_cooldown_s=10.0,
            elapsed_s=0.0,
        )
        mission = self._make_mission(projectile=projectile, enemy_state=enemy_state)

        hits = apply_airport_bus_friendly_fire(bus, mission)

        self.assertEqual(hits, 1)
        self.assertFalse(projectile.alive)
        self.assertEqual(bus.health, 96.0)
        self.assertEqual(enemy_state.enemies[0].health, 52.0)


if __name__ == "__main__":
    unittest.main()