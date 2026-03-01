from __future__ import annotations

from array import array
from dataclasses import dataclass
import math

import pygame


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def _sine_pcm16(
    *,
    freq_hz: float,
    duration_s: float,
    volume: float,
    sample_rate: int,
    fade_out_s: float = 0.03,
) -> bytes:
    n = max(1, int(duration_s * sample_rate))
    fade_n = max(1, int(fade_out_s * sample_rate))

    vol = _clamp(volume, 0.0, 1.0)
    amp = int(32767 * vol)

    buf = array("h")
    two_pi = math.tau
    for i in range(n):
        t = i / sample_rate
        s = math.sin(two_pi * freq_hz * t)
        # Linear fade out at end to avoid clicks.
        if i >= n - fade_n:
            fade = (n - i) / float(fade_n)
        else:
            fade = 1.0
        buf.append(int(amp * s * fade))

    return buf.tobytes()


def _mix_pcm16(buffers: list[bytes], *, volume: float) -> bytes:
    if not buffers:
        return b""
    # Mix by sample; assumes same sample rate and duration.
    samples = [array("h") for _ in buffers]
    for i, b in enumerate(buffers):
        samples[i].frombytes(b)

    out = array("h")
    n = min(len(s) for s in samples)
    vol = _clamp(volume, 0.0, 1.0)

    for i in range(n):
        mixed = 0
        for s in samples:
            mixed += s[i]
        mixed = int(mixed * vol)
        if mixed > 32767:
            mixed = 32767
        elif mixed < -32768:
            mixed = -32768
        out.append(mixed)

    return out.tobytes()


@dataclass
class AudioBank:
    shoot: pygame.mixer.Sound | None
    bomb: pygame.mixer.Sound | None
    explosion: pygame.mixer.Sound | None
    rescue: pygame.mixer.Sound | None
    crash: pygame.mixer.Sound | None

    @staticmethod
    def try_create() -> "AudioBank":
        # No external assets: generate simple placeholder tones.
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except Exception:
            return AudioBank(None, None, None, None, None)

        try:
            sample_rate = 22050

            shoot_b = _sine_pcm16(freq_hz=880.0, duration_s=0.055, volume=0.30, sample_rate=sample_rate)
            shoot = pygame.mixer.Sound(buffer=shoot_b)

            bomb_a = _sine_pcm16(freq_hz=110.0, duration_s=0.22, volume=0.35, sample_rate=sample_rate, fade_out_s=0.08)
            bomb_b = _sine_pcm16(freq_hz=55.0, duration_s=0.22, volume=0.25, sample_rate=sample_rate, fade_out_s=0.10)
            bomb = pygame.mixer.Sound(buffer=_mix_pcm16([bomb_a, bomb_b], volume=0.75))

            exp_a = _sine_pcm16(freq_hz=70.0, duration_s=0.32, volume=0.35, sample_rate=sample_rate, fade_out_s=0.18)
            exp_b = _sine_pcm16(freq_hz=140.0, duration_s=0.18, volume=0.20, sample_rate=sample_rate, fade_out_s=0.10)
            explosion = pygame.mixer.Sound(buffer=_mix_pcm16([exp_a, exp_b], volume=0.75))

            r1 = _sine_pcm16(freq_hz=784.0, duration_s=0.08, volume=0.25, sample_rate=sample_rate)
            r2 = _sine_pcm16(freq_hz=988.0, duration_s=0.10, volume=0.22, sample_rate=sample_rate)
            rescue = pygame.mixer.Sound(buffer=_mix_pcm16([r1, r2], volume=0.85))

            crash_a = _sine_pcm16(freq_hz=48.0, duration_s=0.40, volume=0.42, sample_rate=sample_rate, fade_out_s=0.25)
            crash = pygame.mixer.Sound(buffer=crash_a)

            # Keep levels conservative.
            shoot.set_volume(0.35)
            bomb.set_volume(0.45)
            explosion.set_volume(0.55)
            rescue.set_volume(0.40)
            crash.set_volume(0.55)

            return AudioBank(shoot=shoot, bomb=bomb, explosion=explosion, rescue=rescue, crash=crash)
        except Exception:
            return AudioBank(None, None, None, None, None)

    def play_shoot(self) -> None:
        if self.shoot is not None:
            self.shoot.play()

    def play_bomb(self) -> None:
        if self.bomb is not None:
            self.bomb.play()

    def play_explosion(self) -> None:
        if self.explosion is not None:
            self.explosion.play()

    def play_rescue(self) -> None:
        if self.rescue is not None:
            self.rescue.play()

    def play_crash(self) -> None:
        if self.crash is not None:
            self.crash.play()
