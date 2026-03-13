from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.choplifter.mission_combat import _damage_helicopter


class _BaseZone:
    def __init__(self, inside: bool) -> None:
        self._inside = bool(inside)

    def contains_point(self, _pos: object) -> bool:
        return self._inside


class AirportTowerLzDamageImmunityTests(unittest.TestCase):
    def _mission(self, *, mission_id: str, in_lz: bool) -> SimpleNamespace:
        return SimpleNamespace(
            mission_id=mission_id,
            ended=False,
            crash_active=False,
            engineer_remote_control_active=False,
            invuln_seconds=0.0,
            flare_invuln_seconds=0.0,
            base=_BaseZone(in_lz),
            feedback_shake_impulse=0.0,
            feedback_duck_strength=0.0,
            audio=None,
        )

    def _helicopter(self) -> SimpleNamespace:
        return SimpleNamespace(
            pos=SimpleNamespace(x=500.0, y=320.0),
            damage=0.0,
            damage_flash_seconds=0.0,
            damage_flash_rgb=(0, 0, 0),
        )

    def test_airport_in_tower_lz_blocks_damage(self) -> None:
        mission = self._mission(mission_id="airport", in_lz=True)
        helicopter = self._helicopter()

        _damage_helicopter(mission, helicopter, 18.0, logger=None, source="BARAK_MISSILE")

        self.assertEqual(helicopter.damage, 0.0)

    def test_airport_outside_tower_lz_allows_damage(self) -> None:
        mission = self._mission(mission_id="airport", in_lz=False)
        helicopter = self._helicopter()

        _damage_helicopter(mission, helicopter, 10.0, logger=None, source="ENEMY_BULLET")

        self.assertEqual(helicopter.damage, 10.0)

    def test_non_airport_in_base_zone_does_not_get_new_immunity(self) -> None:
        mission = self._mission(mission_id="city", in_lz=True)
        helicopter = self._helicopter()

        _damage_helicopter(mission, helicopter, 10.0, logger=None, source="ENEMY_BULLET")

        self.assertEqual(helicopter.damage, 10.0)


if __name__ == "__main__":
    unittest.main()
