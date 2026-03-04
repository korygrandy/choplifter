from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ToastState:
    message: str = ""
    remaining_s: float = 0.0

    def set(self, message: str, *, duration_s: float = 3.0) -> None:
        self.message = message
        self.remaining_s = float(duration_s)

    def update(self, dt: float) -> None:
        if self.remaining_s <= 0.0:
            return
        self.remaining_s -= float(dt)
        if self.remaining_s <= 0.0:
            self.message = ""
            self.remaining_s = 0.0
