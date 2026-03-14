from __future__ import annotations

from types import SimpleNamespace
import unittest
import pytest

from src.choplifter.enemy_spawns import AirportEnemyState, AirportSpawnEnemy, update_airport_enemy_spawns


pytestmark = pytest.mark.airport_smoke


class EnemySpawnEscortRiskTests(unittest.TestCase):
    def test_raider_impact_uses_scaled_damage_during_post_respawn_escort_window(self) -> None:
        enemy_state = AirportEnemyState(
            enemies=[AirportSpawnEnemy(x=100.0, y=120.0, vx=0.0, kind="raider", ttl_s=2.0)],
            spawn_cooldown_s=10.0,
            elapsed_s=0.0,
        )
        bus_state = SimpleNamespace(x=100.0, health=100.0, is_moving=True)
        mission = SimpleNamespace(
            mission_id="airport",
            world_width=2800.0,
            base=SimpleNamespace(pos=SimpleNamespace(y=400.0), height=20.0),
            post_respawn_escort_risk_seconds=2.0,
            airport_hostage_state=SimpleNamespace(state="boarded"),
            airport_objective_state=SimpleNamespace(mission_phase="escort_to_lz"),
            mission_tech=SimpleNamespace(on_bus=True),
        )

        update_airport_enemy_spawns(enemy_state, 0.0, mission=mission, bus_state=bus_state, target_x=100.0)

        self.assertAlmostEqual(bus_state.health, 93.25, places=2)

    def test_raider_impact_uses_base_damage_outside_escort_window(self) -> None:
        enemy_state = AirportEnemyState(
            enemies=[AirportSpawnEnemy(x=100.0, y=120.0, vx=0.0, kind="raider", ttl_s=2.0)],
            spawn_cooldown_s=10.0,
            elapsed_s=0.0,
        )
        bus_state = SimpleNamespace(x=100.0, health=100.0, is_moving=True)
        mission = SimpleNamespace(
            mission_id="airport",
            world_width=2800.0,
            base=SimpleNamespace(pos=SimpleNamespace(y=400.0), height=20.0),
            post_respawn_escort_risk_seconds=0.0,
            airport_hostage_state=SimpleNamespace(state="boarded"),
            airport_objective_state=SimpleNamespace(mission_phase="escort_to_lz"),
            mission_tech=SimpleNamespace(on_bus=True),
        )

        update_airport_enemy_spawns(enemy_state, 0.0, mission=mission, bus_state=bus_state, target_x=100.0)

        self.assertAlmostEqual(bus_state.health, 95.0, places=2)

    def test_bus_immune_before_escort_phase(self) -> None:
        enemy_state = AirportEnemyState(
            enemies=[AirportSpawnEnemy(x=100.0, y=120.0, vx=0.0, kind="raider", ttl_s=2.0)],
            spawn_cooldown_s=10.0,
            elapsed_s=0.0,
        )
        bus_state = SimpleNamespace(x=100.0, health=100.0, is_moving=False)
        mission = SimpleNamespace(
            mission_id="airport",
            world_width=2800.0,
            base=SimpleNamespace(pos=SimpleNamespace(y=400.0), height=20.0),
            post_respawn_escort_risk_seconds=2.0,
            airport_hostage_state=SimpleNamespace(state="waiting"),
            airport_objective_state=SimpleNamespace(mission_phase="waiting_for_tech_deploy"),
            mission_tech=SimpleNamespace(on_bus=False),
        )

        update_airport_enemy_spawns(enemy_state, 0.0, mission=mission, bus_state=bus_state, target_x=100.0)

        self.assertAlmostEqual(bus_state.health, 100.0, places=2)

    def test_attacks_stay_dormant_until_bus_is_mission_tech_driven(self) -> None:
        enemy_state = AirportEnemyState(
            enemies=[AirportSpawnEnemy(x=100.0, y=120.0, vx=0.0, kind="uav", ttl_s=2.0)],
            spawn_cooldown_s=0.0,
            elapsed_s=0.0,
        )
        bus_state = SimpleNamespace(x=100.0, health=100.0, is_moving=False)
        mission = SimpleNamespace(
            mission_id="airport",
            world_width=2800.0,
            base=SimpleNamespace(pos=SimpleNamespace(y=400.0), height=20.0),
            post_respawn_escort_risk_seconds=0.0,
            airport_hostage_state=SimpleNamespace(state="boarded"),
            airport_objective_state=SimpleNamespace(mission_phase="escort_to_lz"),
            mission_tech=SimpleNamespace(on_bus=True),
        )

        update_airport_enemy_spawns(enemy_state, 0.0, mission=mission, bus_state=bus_state, target_x=100.0)

        self.assertEqual(enemy_state.enemies, [])

    def test_attacks_activate_once_bus_moves_with_tech_on_board(self) -> None:
        enemy_state = AirportEnemyState(
            enemies=[AirportSpawnEnemy(x=100.0, y=120.0, vx=0.0, kind="raider", ttl_s=2.0)],
            spawn_cooldown_s=10.0,
            elapsed_s=0.0,
        )
        bus_state = SimpleNamespace(x=100.0, health=100.0, is_moving=True)
        mission = SimpleNamespace(
            mission_id="airport",
            world_width=2800.0,
            base=SimpleNamespace(pos=SimpleNamespace(y=400.0), height=20.0),
            post_respawn_escort_risk_seconds=0.0,
            airport_hostage_state=SimpleNamespace(state="boarded"),
            airport_objective_state=SimpleNamespace(mission_phase="escort_to_lz"),
            mission_tech=SimpleNamespace(on_bus=True),
        )

        update_airport_enemy_spawns(enemy_state, 0.0, mission=mission, bus_state=bus_state, target_x=100.0)

        self.assertAlmostEqual(bus_state.health, 95.0, places=2)


if __name__ == "__main__":
    unittest.main()
