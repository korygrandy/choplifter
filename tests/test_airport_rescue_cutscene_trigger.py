from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from src.choplifter.app.game_update import try_start_hostage_rescue_cutscene


class AirportRescueCutsceneTriggerTests(unittest.TestCase):
    def _start_stub(self, *_args, **kwargs) -> bool:
        self.started_kwargs = kwargs
        return True

    def test_airport_cutscene_starts_on_first_lower_rescue(self) -> None:
        mission = SimpleNamespace(
            mission_id="airport",
            stats=SimpleNamespace(saved=1),
            airport_hostage_state=SimpleNamespace(rescued_hostages=0),
            cutscenes_played=set(),
        )
        helicopter = SimpleNamespace(doors_open=False)

        with TemporaryDirectory() as td:
            assets_dir = Path(td)
            (assets_dir / "airport-fuselage-rescue-cutscene.avi").write_bytes(b"avi")
            (assets_dir / "hostage-rescue-cutscene.mpg").write_bytes(b"mpg")

            result = try_start_hostage_rescue_cutscene(
                mission=mission,
                helicopter=helicopter,
                boarded_now=0,
                mission_cutscene_state=SimpleNamespace(),
                assets_dir=assets_dir,
                logger=None,
                start_mission_cutscene_fn=self._start_stub,
            )

        self.assertTrue(result.started)
        self.assertIn("hostage_rescue_16", mission.cutscenes_played)
        self.assertEqual(self.started_kwargs["cutscene_path"].name, "airport-fuselage-rescue-cutscene.avi")

    def test_airport_trigger_does_not_wait_for_legacy_boarded_threshold(self) -> None:
        mission = SimpleNamespace(
            mission_id="airport",
            stats=SimpleNamespace(saved=1),
            airport_hostage_state=SimpleNamespace(rescued_hostages=0),
            cutscenes_played=set(),
        )
        helicopter = SimpleNamespace(doors_open=False)

        with TemporaryDirectory() as td:
            assets_dir = Path(td)
            (assets_dir / "airport-fuselage-rescue-cutscene.avi").write_bytes(b"avi")
            (assets_dir / "hostage-rescue-cutscene.mpg").write_bytes(b"mpg")

            result = try_start_hostage_rescue_cutscene(
                mission=mission,
                helicopter=helicopter,
                boarded_now=0,
                mission_cutscene_state=SimpleNamespace(),
                assets_dir=assets_dir,
                logger=None,
                start_mission_cutscene_fn=self._start_stub,
            )

        self.assertTrue(result.started)

    def test_airport_cutscene_starts_on_first_elevated_rescue_when_lower_not_rescued(self) -> None:
        mission = SimpleNamespace(
            mission_id="airport",
            stats=SimpleNamespace(saved=0),
            airport_hostage_state=SimpleNamespace(rescued_hostages=1),
            cutscenes_played=set(),
        )
        helicopter = SimpleNamespace(doors_open=True)

        with TemporaryDirectory() as td:
            assets_dir = Path(td)
            (assets_dir / "airport-fuselage-rescue-cutscene.avi").write_bytes(b"avi")
            (assets_dir / "hostage-rescue-cutscene.mpg").write_bytes(b"mpg")

            result = try_start_hostage_rescue_cutscene(
                mission=mission,
                helicopter=helicopter,
                boarded_now=0,
                mission_cutscene_state=SimpleNamespace(),
                assets_dir=assets_dir,
                logger=None,
                start_mission_cutscene_fn=self._start_stub,
            )

        self.assertTrue(result.started)
        self.assertEqual(result.doors_open_before_cutscene, True)

    def test_non_airport_mission_still_uses_boarded_threshold(self) -> None:
        mission = SimpleNamespace(
            mission_id="city",
            stats=SimpleNamespace(saved=1),
            airport_hostage_state=SimpleNamespace(rescued_hostages=1),
            cutscenes_played=set(),
        )
        helicopter = SimpleNamespace(doors_open=False)

        with TemporaryDirectory() as td:
            assets_dir = Path(td)
            (assets_dir / "city-seige-cutscene.avi").write_bytes(b"avi")
            (assets_dir / "hostage-rescue-cutscene.mpg").write_bytes(b"mpg")

            result = try_start_hostage_rescue_cutscene(
                mission=mission,
                helicopter=helicopter,
                boarded_now=15,
                mission_cutscene_state=SimpleNamespace(),
                assets_dir=assets_dir,
                logger=None,
                start_mission_cutscene_fn=self._start_stub,
            )

        self.assertFalse(result.started)


if __name__ == "__main__":
    unittest.main()
