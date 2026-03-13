from __future__ import annotations

import unittest

from src.choplifter.render.world import _airport_terminal_sign_label


class AirportTerminalSignageTests(unittest.TestCase):
    def test_fuselage_elevated_terminal_has_no_label(self) -> None:
        self.assertEqual(
            _airport_terminal_sign_label(is_elevated_terminal=True, is_fuselage_terminal=True),
            "",
        )

    def test_jetway_elevated_terminal_maps_to_d5(self) -> None:
        self.assertEqual(
            _airport_terminal_sign_label(is_elevated_terminal=True, is_fuselage_terminal=False),
            "D5",
        )

    def test_lower_compound_maps_to_d6(self) -> None:
        self.assertEqual(
            _airport_terminal_sign_label(is_elevated_terminal=False, is_fuselage_terminal=False),
            "D6",
        )


if __name__ == "__main__":
    unittest.main()
