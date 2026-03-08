from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.choplifter.barak_mrad import (
    BARAK_STATE_DEPLOY,
    BARAK_STATE_LAUNCH,
    BARAK_STATE_MOVE,
    BARAK_STATE_RELOAD,
    BARAK_STATE_RETRACT,
)
from src.choplifter.entities import Enemy
from src.choplifter.game_types import EnemyKind
from src.choplifter.helicopter import Facing
from src.choplifter.math2d import Vec2
from src.choplifter.mission_configs import MissionTuning
from src.choplifter.enemy_update import _barak_next_reload_seconds, _update_enemies


class _DummyAudio:
    def __init__(self) -> None:
        self.deploy_calls = 0
        self.launch_calls = 0

    def play_barak_mrad_deploy(self) -> None:
        self.deploy_calls += 1

    def play_barak_mrad_launch(self) -> None:
        self.launch_calls += 1


class _DummySparks:
    def emit_hit(self, *_args, **_kwargs) -> None:
        return


class BarakMradStateCycleTests(unittest.TestCase):
    def test_next_reload_seconds_within_configured_bounds(self) -> None:
        tuning = MissionTuning(barak_reload_min_seconds=4.0, barak_reload_max_seconds=6.0)
        for _ in range(64):
            value = _barak_next_reload_seconds(tuning)
            self.assertGreaterEqual(value, 4.0)
            self.assertLessEqual(value, 6.0)

    def _build_mission(self, tuning: MissionTuning, enemy: Enemy) -> SimpleNamespace:
        return SimpleNamespace(
            sentiment=50.0,
            elapsed_seconds=0.0,
            tank_warning_seconds=0.0,
            tank_warning_cooldown_s=0.0,
            jet_warning_seconds=0.0,
            jet_warning_cooldown_s=0.0,
            mine_warning_seconds=0.0,
            mine_warning_cooldown_s=0.0,
            mine_warning_distance=9999.0,
            pending_air_mine_pos=None,
            pending_air_mine_seconds=0.0,
            mine_spawn_seconds=9999.0,
            jet_spawn_seconds=9999.0,
            enemies=[enemy],
            compounds=[SimpleNamespace(pos=Vec2(300.0, 0.0), width=80.0)],
            projectiles=[],
            tuning=tuning,
            world_width=2200.0,
            impact_sparks=_DummySparks(),
            jet_trails=SimpleNamespace(emit_trail=lambda *_a, **_k: None),
            stats=SimpleNamespace(artillery_fired=0, jets_entered=0),
            audio=_DummyAudio(),
        )

    def test_cycle_transitions_retract_move_deploy_launch_retract_reload(self) -> None:
        tuning = MissionTuning(
            barak_reload_seconds=0.4,
            barak_reload_min_seconds=0.4,
            barak_reload_max_seconds=0.4,
            barak_state_fail_safe_s=6.0,
            barak_deploy_angle_speed_rad_s=3.0,
            barak_deploy_extension_speed_s=3.0,
            barak_retract_angle_speed_rad_s=3.0,
            barak_retract_extension_speed_s=3.0,
        )
        enemy = Enemy(
            kind=EnemyKind.BARAK_MRAD,
            pos=Vec2(404.0, 260.0),
            vel=Vec2(32.0, 0.0),
            health=100.0,
        )
        mission = self._build_mission(tuning, enemy)
        heli = SimpleNamespace(ground_y=300.0)
        helicopter = SimpleNamespace(pos=Vec2(700.0, 190.0), facing=Facing.RIGHT, grounded=False)

        seen_states: list[str] = []
        for _ in range(160):
            mission.elapsed_seconds += 0.05
            _update_enemies(
                mission,
                helicopter,
                0.05,
                heli,
                logger=None,
                mine_explode=lambda *_a, **_k: None,
                spawn_enemy_bullet_toward=lambda *_a, **_k: None,
                damage_helicopter=lambda *_a, **_k: None,
            )
            s = enemy.mrad_state
            if not seen_states or seen_states[-1] != s:
                seen_states.append(s)

        self.assertIn(BARAK_STATE_DEPLOY, seen_states)
        self.assertIn(BARAK_STATE_LAUNCH, seen_states)
        self.assertIn(BARAK_STATE_RETRACT, seen_states)
        self.assertIn(BARAK_STATE_RELOAD, seen_states)
        self.assertGreaterEqual(len(mission.projectiles), 1)
        self.assertGreaterEqual(mission.audio.deploy_calls, 1)
        self.assertGreaterEqual(mission.audio.launch_calls, 1)

    def test_fail_safe_recovers_stuck_deploy_state(self) -> None:
        tuning = MissionTuning(
            barak_state_fail_safe_s=0.15,
            barak_deploy_angle_speed_rad_s=0.0,
            barak_deploy_extension_speed_s=0.0,
        )
        enemy = Enemy(
            kind=EnemyKind.BARAK_MRAD,
            pos=Vec2(404.0, 260.0),
            vel=Vec2(0.0, 0.0),
            health=100.0,
            mrad_state=BARAK_STATE_DEPLOY,
        )
        mission = self._build_mission(tuning, enemy)
        heli = SimpleNamespace(ground_y=300.0)
        helicopter = SimpleNamespace(pos=Vec2(700.0, 190.0), facing=Facing.RIGHT, grounded=False)

        for _ in range(12):
            mission.elapsed_seconds += 0.05
            _update_enemies(
                mission,
                helicopter,
                0.05,
                heli,
                logger=None,
                mine_explode=lambda *_a, **_k: None,
                spawn_enemy_bullet_toward=lambda *_a, **_k: None,
                damage_helicopter=lambda *_a, **_k: None,
            )

        self.assertIn(enemy.mrad_state, {BARAK_STATE_RETRACT, BARAK_STATE_RELOAD, BARAK_STATE_MOVE})


if __name__ == "__main__":
    unittest.main()
