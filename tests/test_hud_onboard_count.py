from types import SimpleNamespace

from src.choplifter.render.hud import _airport_vehicle_onboard_count


class DummyMission(SimpleNamespace):
    pass


def test_airport_vehicle_onboard_waiting_is_zero() -> None:
    mission = DummyMission(
        airport_hostage_state=SimpleNamespace(
            state="waiting",
            meal_truck_loaded_hostages=0,
            boarded_hostages=0,
        )
    )

    assert _airport_vehicle_onboard_count(mission) == 0


def test_airport_vehicle_onboard_adds_truck_and_bus() -> None:
    mission = DummyMission(
        airport_hostage_state=SimpleNamespace(
            state="truck_loaded",
            meal_truck_loaded_hostages=6,
            boarded_hostages=3,
        )
    )

    assert _airport_vehicle_onboard_count(mission) == 9


def test_airport_vehicle_onboard_transferring_uses_batch_total() -> None:
    mission = DummyMission(
        airport_hostage_state=SimpleNamespace(
            state="transferring_to_bus",
            truck_load_base=4,
            transferring_hostages=5,
            meal_truck_loaded_hostages=5,
            boarded_hostages=7,
            transferred_so_far=3,
        )
    )

    assert _airport_vehicle_onboard_count(mission) == 9
