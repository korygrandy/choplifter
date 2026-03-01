from __future__ import annotations

from array import array
from dataclasses import dataclass
import math
from pathlib import Path

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


def _try_load_asset_sound(path: Path) -> pygame.mixer.Sound | None:
    try:
        if not path.exists():
            return None
        return pygame.mixer.Sound(str(path))
    except Exception:
        return None


@dataclass
class AudioBank:
    shoot: pygame.mixer.Sound | None
    bomb: pygame.mixer.Sound | None
    explosion: pygame.mixer.Sound | None
    explosion_small: pygame.mixer.Sound | None
    explosion_big: pygame.mixer.Sound | None
    doors_open: pygame.mixer.Sound | None
    doors_close: pygame.mixer.Sound | None
    board: pygame.mixer.Sound | None
    rescue: pygame.mixer.Sound | None
    crash: pygame.mixer.Sound | None

    @staticmethod
    def try_create() -> "AudioBank":
        # No external assets: generate simple placeholder tones.
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except Exception:
            return AudioBank(None, None, None, None, None, None, None, None, None, None)

        try:
            sample_rate = 22050

            # Optional external assets (preferred when present).
            module_dir = Path(__file__).resolve().parent
            asset_dir = module_dir / "assets"

            shoot_b = _sine_pcm16(freq_hz=880.0, duration_s=0.055, volume=0.30, sample_rate=sample_rate)
            shoot = pygame.mixer.Sound(buffer=shoot_b)

            bomb_a = _sine_pcm16(freq_hz=110.0, duration_s=0.22, volume=0.35, sample_rate=sample_rate, fade_out_s=0.08)
            bomb_b = _sine_pcm16(freq_hz=55.0, duration_s=0.22, volume=0.25, sample_rate=sample_rate, fade_out_s=0.10)
            bomb = pygame.mixer.Sound(buffer=_mix_pcm16([bomb_a, bomb_b], volume=0.75))

            # Two distinct explosion flavors:
            # - small: compound opening / light blast
            # - big: tank destroyed / heavier boom
            exp_s_a = _sine_pcm16(freq_hz=110.0, duration_s=0.22, volume=0.28, sample_rate=sample_rate, fade_out_s=0.10)
            exp_s_b = _sine_pcm16(freq_hz=220.0, duration_s=0.14, volume=0.16, sample_rate=sample_rate, fade_out_s=0.08)
            explosion_small = pygame.mixer.Sound(buffer=_mix_pcm16([exp_s_a, exp_s_b], volume=0.80))

            exp_b_a = _sine_pcm16(freq_hz=55.0, duration_s=0.42, volume=0.38, sample_rate=sample_rate, fade_out_s=0.22)
            exp_b_b = _sine_pcm16(freq_hz=110.0, duration_s=0.26, volume=0.22, sample_rate=sample_rate, fade_out_s=0.16)
            explosion_big = pygame.mixer.Sound(buffer=_mix_pcm16([exp_b_a, exp_b_b], volume=0.80))

            # Backward compatible alias.
            explosion = explosion_big

            door_o = _sine_pcm16(freq_hz=392.0, duration_s=0.06, volume=0.22, sample_rate=sample_rate)
            door_c = _sine_pcm16(freq_hz=294.0, duration_s=0.06, volume=0.22, sample_rate=sample_rate)
            doors_open = pygame.mixer.Sound(buffer=door_o)
            doors_close = pygame.mixer.Sound(buffer=door_c)

            b1 = _sine_pcm16(freq_hz=660.0, duration_s=0.05, volume=0.18, sample_rate=sample_rate)
            b2 = _sine_pcm16(freq_hz=880.0, duration_s=0.05, volume=0.14, sample_rate=sample_rate)
            board = pygame.mixer.Sound(buffer=_mix_pcm16([b1, b2], volume=0.90))

            r1 = _sine_pcm16(freq_hz=784.0, duration_s=0.08, volume=0.25, sample_rate=sample_rate)
            r2 = _sine_pcm16(freq_hz=988.0, duration_s=0.10, volume=0.22, sample_rate=sample_rate)
            rescue = pygame.mixer.Sound(buffer=_mix_pcm16([r1, r2], volume=0.85))

            crash_a = _sine_pcm16(freq_hz=48.0, duration_s=0.40, volume=0.42, sample_rate=sample_rate, fade_out_s=0.25)
            crash = pygame.mixer.Sound(buffer=crash_a)

            # Override placeholders with external files if provided.
            # (These are optional: game stays playable without them.)
            explosion_big = _try_load_asset_sound(asset_dir / "explosion_big.wav") or explosion_big
            explosion_small = _try_load_asset_sound(asset_dir / "explosion_small.wav") or explosion_small
            shoot = _try_load_asset_sound(asset_dir / "shoot.wav") or shoot
            bomb = _try_load_asset_sound(asset_dir / "bomb.wav") or bomb
            rescue = _try_load_asset_sound(asset_dir / "rescue.wav") or rescue
            crash = _try_load_asset_sound(asset_dir / "crash.wav") or crash
            doors_open = _try_load_asset_sound(asset_dir / "doors_open.wav") or doors_open
            doors_close = _try_load_asset_sound(asset_dir / "doors_close.wav") or doors_close
            board = _try_load_asset_sound(asset_dir / "board.wav") or board

            # Keep levels conservative.
            shoot.set_volume(0.35)
            bomb.set_volume(0.45)
            explosion_small.set_volume(0.45)
            explosion_big.set_volume(0.60)
            explosion = explosion_big
            explosion.set_volume(0.60)
            doors_open.set_volume(0.25)
            doors_close.set_volume(0.25)
            board.set_volume(0.22)
            rescue.set_volume(0.40)
            crash.set_volume(0.55)

            return AudioBank(
                shoot=shoot,
                bomb=bomb,
                explosion=explosion,
                explosion_small=explosion_small,
                explosion_big=explosion_big,
                doors_open=doors_open,
                doors_close=doors_close,
                board=board,
                rescue=rescue,
                crash=crash,
            )
        except Exception:
            return AudioBank(None, None, None, None, None, None, None, None, None, None)

    def play_shoot(self) -> None:
        if self.shoot is not None:
            self.shoot.play()

    def play_bomb(self) -> None:
        if self.bomb is not None:
            self.bomb.play()

    def play_explosion(self) -> None:
        if self.explosion is not None:
            self.explosion.play()

    def play_explosion_small(self) -> None:
        if self.explosion_small is not None:
            self.explosion_small.play()

    def play_explosion_big(self) -> None:
        if self.explosion_big is not None:
            self.explosion_big.play()

    def play_doors_open(self) -> None:
        if self.doors_open is not None:
            self.doors_open.play()

    def play_doors_close(self) -> None:
        if self.doors_close is not None:
            self.doors_close.play()

    def play_board(self) -> None:
        if self.board is not None:
            self.board.play()

    def play_rescue(self) -> None:
        if self.rescue is not None:
            self.rescue.play()

    def play_crash(self) -> None:
        if self.crash is not None:
            self.crash.play()
