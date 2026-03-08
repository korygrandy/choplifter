from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.choplifter.math2d import Vec2
from src.choplifter.supply_drops import SupplyDrop, SupplyDropManager, consume_player_weapon


class SupplyDropsTests(unittest.TestCase):
    def test_manager_spawns_drop_on_timer(self) -> None:
        manager = SupplyDropManager(spawn_timer_s=0.0, max_alive=2)
        mission = SimpleNamespace(world_width=2200.0, munitions_bullets=0, munitions_bombs=0)
        helicopter = SimpleNamespace(pos=Vec2(600.0, 180.0), facing=SimpleNamespace(value=1.0))

        manager.update(mission=mission, helicopter=helicopter, dt=0.1, ground_y=360.0)

        self.assertGreaterEqual(len(manager.drops), 1)

    def test_drop_moves_with_sway_and_gravity(self) -> None:
        manager = SupplyDropManager(spawn_timer_s=999.0)
        drop = SupplyDrop(pos=Vec2(600.0, 140.0), vel=Vec2(0.0, 10.0), kind="bullets", sway_amp_px=20.0)
        manager.drops = [drop]

        mission = SimpleNamespace(world_width=2200.0, munitions_bullets=0, munitions_bombs=0)
        helicopter = SimpleNamespace(pos=Vec2(50.0, 50.0), facing=SimpleNamespace(value=1.0))

        x0, y0 = drop.pos.x, drop.pos.y
        manager.update(mission=mission, helicopter=helicopter, dt=0.25, ground_y=360.0)

        self.assertNotEqual(drop.pos.x, x0)
        self.assertGreater(drop.pos.y, y0)
        self.assertLess(drop.vel.y, 20.0)

    def test_landed_drop_persists_for_five_seconds_then_despawns(self) -> None:
        manager = SupplyDropManager(spawn_timer_s=999.0, ground_lifetime_s=5.0)
        drop = SupplyDrop(pos=Vec2(500.0, 350.0), vel=Vec2(0.0, 80.0), kind="bullets")
        manager.drops = [drop]

        mission = SimpleNamespace(world_width=2200.0, munitions_bullets=0, munitions_bombs=0)
        helicopter = SimpleNamespace(pos=Vec2(50.0, 50.0), facing=SimpleNamespace(value=1.0))

        manager.update(mission=mission, helicopter=helicopter, dt=0.2, ground_y=360.0)
        self.assertTrue(drop.landed)
        self.assertEqual(len(manager.drops), 1)

        manager.update(mission=mission, helicopter=helicopter, dt=4.8, ground_y=360.0)
        self.assertEqual(len(manager.drops), 1)

        manager.update(mission=mission, helicopter=helicopter, dt=0.2, ground_y=360.0)
        self.assertEqual(len(manager.drops), 0)

    def test_collecting_drop_grants_munitions(self) -> None:
        manager = SupplyDropManager(spawn_timer_s=999.0, collect_radius_px=60.0)
        manager.drops = [SupplyDrop(pos=Vec2(610.0, 200.0), vel=Vec2(0.0, 0.0), kind="bombs")]
        mission = SimpleNamespace(world_width=2200.0, munitions_bullets=10, munitions_bombs=2)
        helicopter = SimpleNamespace(pos=Vec2(600.0, 200.0), facing=SimpleNamespace(value=1.0), damage=0.0)

        manager.update(mission=mission, helicopter=helicopter, dt=0.1, ground_y=360.0)

        self.assertEqual(len(manager.drops), 0)
        self.assertEqual(mission.munitions_bombs, 6)

    def test_collecting_health_drop_reduces_damage_and_clamps(self) -> None:
        manager = SupplyDropManager(spawn_timer_s=999.0, collect_radius_px=60.0, health_restore_amount=30.0)
        manager.drops = [SupplyDrop(pos=Vec2(610.0, 200.0), vel=Vec2(0.0, 0.0), kind="health")]
        mission = SimpleNamespace(world_width=2200.0, munitions_bullets=10, munitions_bombs=2)
        helicopter = SimpleNamespace(pos=Vec2(600.0, 200.0), facing=SimpleNamespace(value=1.0), damage=22.0)

        manager.update(mission=mission, helicopter=helicopter, dt=0.1, ground_y=360.0)

        self.assertEqual(len(manager.drops), 0)
        self.assertEqual(helicopter.damage, 0.0)

    def test_spawn_kind_is_health_only_for_now(self) -> None:
        manager = SupplyDropManager(spawn_timer_s=999.0)
        self.assertEqual(manager._next_drop_kind(), "health")
        manager._spawn_counter += 1
        self.assertEqual(manager._next_drop_kind(), "health")
        manager._spawn_counter += 1
        self.assertEqual(manager._next_drop_kind(), "health")
        manager._spawn_counter += 1
        self.assertEqual(manager._next_drop_kind(), "health")

    def test_consume_player_weapon_respects_inventory(self) -> None:
        mission = SimpleNamespace(munitions_bullets=1, munitions_bombs=1)

        self.assertTrue(consume_player_weapon(mission, facing_name="RIGHT"))
        self.assertEqual(mission.munitions_bullets, 0)
        self.assertFalse(consume_player_weapon(mission, facing_name="LEFT"))

        self.assertTrue(consume_player_weapon(mission, facing_name="FORWARD"))
        self.assertEqual(mission.munitions_bombs, 0)
        self.assertFalse(consume_player_weapon(mission, facing_name="FORWARD"))


if __name__ == "__main__":
    unittest.main()
