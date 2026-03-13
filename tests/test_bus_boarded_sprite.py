from __future__ import annotations

import unittest
from unittest.mock import patch

from src.choplifter import bus_ai


class BusBoardedSpriteTests(unittest.TestCase):
    def test_uses_boarded_sprite_when_passengers_on_bus(self) -> None:
        boarded = object()
        with patch("src.choplifter.bus_ai._load_bus_sprite_boarded", return_value=boarded), patch(
            "src.choplifter.bus_ai._load_bus_sprite", return_value=None
        ):
            selected = bus_ai._get_bus_closed_sprite(boarded_count=2)
        self.assertIs(selected, boarded)

    def test_falls_back_to_default_sprite_when_no_boarded_asset(self) -> None:
        default = object()
        with patch("src.choplifter.bus_ai._load_bus_sprite_boarded", return_value=None), patch(
            "src.choplifter.bus_ai._load_bus_sprite", return_value=default
        ):
            selected = bus_ai._get_bus_closed_sprite(boarded_count=3)
        self.assertIs(selected, default)

    def test_uses_default_sprite_when_no_boarded_passengers(self) -> None:
        default = object()
        with patch("src.choplifter.bus_ai._load_bus_sprite") as load_default, patch(
            "src.choplifter.bus_ai._load_bus_sprite_boarded"
        ) as load_boarded:
            load_default.return_value = default
            selected = bus_ai._get_bus_closed_sprite(boarded_count=0)

        self.assertIs(selected, default)
        load_default.assert_called_once_with()
        load_boarded.assert_not_called()


if __name__ == "__main__":
    unittest.main()
