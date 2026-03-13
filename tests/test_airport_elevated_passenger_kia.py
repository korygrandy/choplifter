from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.choplifter.entities import Compound, Projectile
from src.choplifter.game_types import ProjectileKind
from src.choplifter.math2d import Vec2
from src.choplifter.mission_configs import MissionTuning
from src.choplifter.mission_projectiles import _update_projectiles


class AirportElevatedPassengerKiaTests(unittest.TestCase):
    def _base_mission(self, *, projectile: Projectile, compounds: list[Compound], hostage_state: object) -> SimpleNamespace:
        return SimpleNamespace(
            projectiles=[projectile],
            enemies=[],
            tuning=MissionTuning(),
            stats=SimpleNamespace(
                enemies_destroyed=0,
                tanks_destroyed=0,
                artillery_hits=0,
                kia_by_player=0,
                kia_by_enemy=0,
            ),
            impact_sparks=SimpleNamespace(emit_hit=lambda *_a, **_k: None),
            burning=SimpleNamespace(add_site=lambda *_a, **_k: None),
            hostages=[],
            compounds=compounds,
            base=SimpleNamespace(contains_point=lambda _p: False),
            mission_id="airport",
            flare_invuln_seconds=0.0,
            explosions=SimpleNamespace(
                emit_fire_plume=lambda *_a, **_k: None,
                emit_explosion=lambda *_a, **_k: None,
            ),
            enemy_damage_fx=SimpleNamespace(emit_hit_puff=lambda *_a, **_k: None),
            barak_suppressed=False,
            elapsed_seconds=0.0,
            airport_hostage_state=hostage_state,
            audio=None,
        )

    def test_player_bullet_hit_on_elevated_terminal_marks_one_kia(self) -> None:
        elevated_left = Compound(
            pos=Vec2(100.0, 120.0),
            width=90.0,
            height=44.0,
            health=100.0,
            is_open=True,
            hostage_start=0,
            hostage_count=0,
        )
        elevated_right = Compound(
            pos=Vec2(260.0, 120.0),
            width=90.0,
            height=44.0,
            health=100.0,
            is_open=True,
            hostage_start=0,
            hostage_count=0,
        )
        lower_terminal = Compound(
            pos=Vec2(420.0, 180.0),
            width=90.0,
            height=44.0,
            health=100.0,
            is_open=False,
            hostage_start=0,
            hostage_count=0,
        )
        projectile = Projectile(
            kind=ProjectileKind.BULLET,
            pos=Vec2(130.0, 132.0),
            vel=Vec2(0.0, 0.0),
            ttl=1.0,
        )
        hostage_state = SimpleNamespace(
            terminal_pickup_xs=(145.0, 305.0),
            terminal_remaining=[2, 2],
        )
        mission = self._base_mission(
            projectile=projectile,
            compounds=[elevated_left, elevated_right, lower_terminal],
            hostage_state=hostage_state,
        )

        heli = SimpleNamespace(ground_y=500.0)
        helicopter = SimpleNamespace(pos=Vec2(0.0, 0.0), vel=Vec2(0.0, 0.0), facing=None, grounded=False)

        _update_projectiles(
            mission,
            0.0,
            heli,
            logger=None,
            helicopter=helicopter,
            damage_helicopter=lambda *_a, **_k: None,
        )

        self.assertEqual(hostage_state.terminal_remaining, [1, 2])
        self.assertEqual(hostage_state.terminal_kia, [1, 0])
        self.assertEqual(mission.stats.kia_by_player, 1)
        self.assertEqual(len(mission.airport_terminal_impact_sparks), 1)
        self.assertFalse(projectile.alive)

    def test_player_bullet_hit_on_closed_elevated_terminal_does_not_kia(self) -> None:
        elevated_left = Compound(
            pos=Vec2(100.0, 120.0),
            width=90.0,
            height=44.0,
            health=100.0,
            is_open=False,
            hostage_start=0,
            hostage_count=0,
        )
        elevated_right = Compound(
            pos=Vec2(260.0, 120.0),
            width=90.0,
            height=44.0,
            health=100.0,
            is_open=False,
            hostage_start=0,
            hostage_count=0,
        )
        lower_terminal = Compound(
            pos=Vec2(420.0, 180.0),
            width=90.0,
            height=44.0,
            health=100.0,
            is_open=False,
            hostage_start=0,
            hostage_count=0,
        )
        projectile = Projectile(
            kind=ProjectileKind.BULLET,
            pos=Vec2(130.0, 132.0),
            vel=Vec2(0.0, 0.0),
            ttl=1.0,
        )
        hostage_state = SimpleNamespace(
            terminal_pickup_xs=(145.0, 305.0),
            terminal_remaining=[2, 2],
            terminal_kia=[0, 0],
        )
        mission = self._base_mission(
            projectile=projectile,
            compounds=[elevated_left, elevated_right, lower_terminal],
            hostage_state=hostage_state,
        )

        heli = SimpleNamespace(ground_y=500.0)
        helicopter = SimpleNamespace(pos=Vec2(0.0, 0.0), vel=Vec2(0.0, 0.0), facing=None, grounded=False)

        _update_projectiles(
            mission,
            0.0,
            heli,
            logger=None,
            helicopter=helicopter,
            damage_helicopter=lambda *_a, **_k: None,
        )

        self.assertEqual(hostage_state.terminal_remaining, [2, 2])
        self.assertEqual(hostage_state.terminal_kia, [0, 0])
        self.assertEqual(mission.stats.kia_by_player, 0)
        self.assertEqual(len(mission.airport_terminal_impact_sparks), 1)
        self.assertFalse(projectile.alive)

    def test_player_bullet_hit_on_lower_terminal_does_not_consume_elevated_passengers(self) -> None:
        elevated_left = Compound(
            pos=Vec2(100.0, 120.0),
            width=90.0,
            height=44.0,
            health=100.0,
            is_open=False,
            hostage_start=0,
            hostage_count=0,
        )
        lower_terminal = Compound(
            pos=Vec2(420.0, 180.0),
            width=90.0,
            height=44.0,
            health=100.0,
            is_open=False,
            hostage_start=0,
            hostage_count=0,
        )
        projectile = Projectile(
            kind=ProjectileKind.BULLET,
            pos=Vec2(450.0, 192.0),
            vel=Vec2(0.0, 0.0),
            ttl=1.0,
        )
        hostage_state = SimpleNamespace(
            terminal_pickup_xs=(145.0,),
            terminal_remaining=[2],
            terminal_kia=[0],
        )
        mission = self._base_mission(
            projectile=projectile,
            compounds=[elevated_left, lower_terminal],
            hostage_state=hostage_state,
        )

        heli = SimpleNamespace(ground_y=500.0)
        helicopter = SimpleNamespace(pos=Vec2(0.0, 0.0), vel=Vec2(0.0, 0.0), facing=None, grounded=False)

        _update_projectiles(
            mission,
            0.0,
            heli,
            logger=None,
            helicopter=helicopter,
            damage_helicopter=lambda *_a, **_k: None,
        )

        self.assertEqual(hostage_state.terminal_remaining, [2])
        self.assertEqual(hostage_state.terminal_kia, [0])
        self.assertEqual(mission.stats.kia_by_player, 0)
        self.assertFalse(bool(getattr(mission, "airport_terminal_impact_sparks", [])))
        self.assertFalse(projectile.alive)


if __name__ == "__main__":
    unittest.main()
