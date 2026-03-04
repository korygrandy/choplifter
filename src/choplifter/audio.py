from __future__ import annotations

from array import array
from dataclasses import dataclass, field
import math
from pathlib import Path
import random
from typing import Literal

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


BusName = Literal["sfx", "ui", "music"]




@dataclass
class AudioMixer:
    """Simple audio bus routing built on pygame mixer channels.

    Buses are implemented as pools of dedicated channels so different audio
    categories can play concurrently and later be mixed/controlled separately.
    """

    def __post_init__(self):
        # Initialize audio buses and active loops if not already present
        if not hasattr(self, 'buses'):
            self.buses = {"sfx": [], "ui": [], "music": []}
        if not hasattr(self, 'active_loops'):
            self.active_loops = {}

    def play(self, sound: pygame.mixer.Sound, bus: BusName = "sfx") -> None:
        """Play a one-shot sound on the specified bus."""
        channels = self.buses.get(bus, [])
        if channels:
            # If the bus is saturated, steal the first channel.
            channels[0].play(sound)
        else:
            sound.play()

        # ...existing code...

    def play_loop(self, sound: pygame.mixer.Sound, *, key: str, bus: BusName = "music", fade_in_ms: int = 500) -> None:
        if key in self.active_loops:
            ch = self.active_loops[key]
            if ch.get_busy():
                return

        channels = self.buses.get(bus, [])
        if not channels:
            sound.play(loops=-1, fade_ms=fade_in_ms)
            return

        ch = channels[0]
        ch.play(sound, loops=-1, fade_ms=fade_in_ms)
        self.active_loops[key] = ch

    def stop_loop(self, *, key: str, fade_out_ms: int = 650) -> None:
        ch = self.active_loops.pop(key, None)
        if ch is None:
            return
        try:
            ch.fadeout(max(0, int(fade_out_ms)))
        except Exception:
            try:
                ch.stop()
            except Exception:
                pass


@dataclass
class AudioBank:
    # Ducking state variables (for audio ducking/fading)
    _duck_remaining_s: float = field(default=0.0, init=False, repr=False)
    _duck_total_s: float = field(default=0.0, init=False, repr=False)
    _duck_min_factor: float = field(default=1.0, init=False, repr=False)
    _duck_current_factor: float = field(default=1.0, init=False, repr=False)
    mixer: AudioMixer | None
    shoot: pygame.mixer.Sound | None
    bomb: pygame.mixer.Sound | None
    explosion: pygame.mixer.Sound | None
    explosion_small: pygame.mixer.Sound | None
    explosion_big: pygame.mixer.Sound | None
    mine_explosion: pygame.mixer.Sound | None
    flare_defense: pygame.mixer.Sound | None
    artillery_shot: pygame.mixer.Sound | None
    artillery_impact_a: pygame.mixer.Sound | None
    artillery_impact_b: pygame.mixer.Sound | None
    jet_flyby: pygame.mixer.Sound | None
    midair_collision: pygame.mixer.Sound | None
    chopper_warning_beeps: pygame.mixer.Sound | None
    doors_open: pygame.mixer.Sound | None
    doors_close: pygame.mixer.Sound | None
    board: pygame.mixer.Sound | None
    rescue: pygame.mixer.Sound | None
    crash: pygame.mixer.Sound | None
    chopper_crash: pygame.mixer.Sound | None
    flying_loop: pygame.mixer.Sound | None
    menu_select: pygame.mixer.Sound | None
    pause: pygame.mixer.Sound | None

    def stop_flying(self) -> None:
        """Stops the helicopter flying loop sound if active."""
        if hasattr(self, "mixer") and self.mixer is not None:
            self.mixer.stop_loop(key="flying_loop")
        else:
            # Fallback: stop all channels if no mixer
            try:
                pygame.mixer.stop()
            except Exception:
                pass
    explosion_small: pygame.mixer.Sound | None
    explosion_big: pygame.mixer.Sound | None
    mine_explosion: pygame.mixer.Sound | None
    flare_defense: pygame.mixer.Sound | None
    artillery_shot: pygame.mixer.Sound | None
    artillery_impact_a: pygame.mixer.Sound | None
    artillery_impact_b: pygame.mixer.Sound | None
    jet_flyby: pygame.mixer.Sound | None
    midair_collision: pygame.mixer.Sound | None
    chopper_warning_beeps: pygame.mixer.Sound | None
    doors_open: pygame.mixer.Sound | None
    doors_close: pygame.mixer.Sound | None
    board: pygame.mixer.Sound | None
    rescue: pygame.mixer.Sound | None
    crash: pygame.mixer.Sound | None
    chopper_crash: pygame.mixer.Sound | None
    flying_loop: pygame.mixer.Sound | None
    menu_select: pygame.mixer.Sound | None
    pause: pygame.mixer.Sound | None

    def _play(self, sound: pygame.mixer.Sound | None, *, bus: BusName) -> None:
        if sound is None:
            return
        if self.mixer is not None:
            self.mixer.play(sound, bus=bus)
        else:
            sound.play()
    explosion_big: pygame.mixer.Sound | None
    mine_explosion: pygame.mixer.Sound | None
    flare_defense: pygame.mixer.Sound | None
    artillery_shot: pygame.mixer.Sound | None
    artillery_impact_a: pygame.mixer.Sound | None
    artillery_impact_b: pygame.mixer.Sound | None
    jet_flyby: pygame.mixer.Sound | None
    midair_collision: pygame.mixer.Sound | None
    chopper_warning_beeps: pygame.mixer.Sound | None
    doors_open: pygame.mixer.Sound | None
    doors_close: pygame.mixer.Sound | None
    board: pygame.mixer.Sound | None
    rescue: pygame.mixer.Sound | None
    crash: pygame.mixer.Sound | None
    chopper_crash: pygame.mixer.Sound | None
    flying_loop: pygame.mixer.Sound | None
    menu_select: pygame.mixer.Sound | None
    pause: pygame.mixer.Sound | None
    _flying_active: bool = field(default=False, init=False, repr=False)
    _last_artillery_impact_variant: int = field(default=-1, init=False, repr=False)
    _muted: bool = field(default=False, init=False, repr=False)
    @staticmethod
    def try_create():
        """
        Attempts to create and return an AudioBank instance, loading all required sounds.
        Returns the AudioBank object if successful, or a silent fallback if loading fails.
        """
        try:
            mixer = AudioMixer()
            sample_rate = 22050
            module_dir = Path(__file__).resolve().parent
            asset_dir = module_dir / "assets"

            shoot_b = _sine_pcm16(freq_hz=880.0, duration_s=0.055, volume=0.30, sample_rate=sample_rate)
            shoot = pygame.mixer.Sound(buffer=shoot_b)

            bomb_a = _sine_pcm16(freq_hz=110.0, duration_s=0.22, volume=0.35, sample_rate=sample_rate, fade_out_s=0.08)
            bomb_b = _sine_pcm16(freq_hz=55.0, duration_s=0.22, volume=0.25, sample_rate=sample_rate, fade_out_s=0.10)
            bomb = pygame.mixer.Sound(buffer=_mix_pcm16([bomb_a, bomb_b], volume=0.75))

            exp_s_a = _sine_pcm16(freq_hz=110.0, duration_s=0.22, volume=0.28, sample_rate=sample_rate, fade_out_s=0.10)
            exp_s_b = _sine_pcm16(freq_hz=220.0, duration_s=0.14, volume=0.16, sample_rate=sample_rate, fade_out_s=0.08)
            explosion_small = pygame.mixer.Sound(buffer=_mix_pcm16([exp_s_a, exp_s_b], volume=0.80))

            exp_b_a = _sine_pcm16(freq_hz=55.0, duration_s=0.42, volume=0.38, sample_rate=sample_rate, fade_out_s=0.22)
            exp_b_b = _sine_pcm16(freq_hz=110.0, duration_s=0.26, volume=0.22, sample_rate=sample_rate, fade_out_s=0.16)
            explosion_big = pygame.mixer.Sound(buffer=_mix_pcm16([exp_b_a, exp_b_b], volume=0.80))

            explosion = explosion_big

            mine_explosion = _try_load_asset_sound(asset_dir / "mine-explosion.wav")
            flare_defense = _try_load_asset_sound(asset_dir / "flare-defense.wav")

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

            artillery_shot = _try_load_asset_sound(asset_dir / "artillery-shot.wav")
            artillery_impact_a = _try_load_asset_sound(asset_dir / "artillery-impact.wav")
            artillery_impact_b = _try_load_asset_sound(asset_dir / "alternate-artillery-impact.wav")
            jet_flyby = _try_load_asset_sound(asset_dir / "fighter-jet-flyby.wav")

            menu_select = _try_load_asset_sound(asset_dir / "menu-select.wav")
            pause = _try_load_asset_sound(asset_dir / "pause.wav")
            midair_collision = _try_load_asset_sound(asset_dir / "midair-collission.wav")
            chopper_warning_beeps = _try_load_asset_sound(asset_dir / "chopper-warning-beeps.wav")

            explosion_big = _try_load_asset_sound(asset_dir / "explosion_big.wav") or explosion_big
            explosion_small = _try_load_asset_sound(asset_dir / "explosion_small.wav") or explosion_small
            shoot = (
                _try_load_asset_sound(asset_dir / "gunfire.wav")
                or _try_load_asset_sound(asset_dir / "shoot.wav")
                or shoot
            )
            bomb = _try_load_asset_sound(asset_dir / "bomb.wav") or bomb
            rescue = _try_load_asset_sound(asset_dir / "rescue.wav") or rescue
            crash = _try_load_asset_sound(asset_dir / "crash.wav") or crash
            chopper_crash = _try_load_asset_sound(asset_dir / "chopper-crash.wav")
            doors_open = _try_load_asset_sound(asset_dir / "doors_open.wav") or doors_open
            doors_close = _try_load_asset_sound(asset_dir / "doors_close.wav") or doors_close
            board = _try_load_asset_sound(asset_dir / "board.wav") or board
            flying_loop = _try_load_asset_sound(asset_dir / "chopper-flying.wav")

            shoot.set_volume(0.35)
            bomb.set_volume(0.45)
            explosion_small.set_volume(0.45)
            explosion_big.set_volume(0.60)
            explosion.set_volume(0.60)
            if mine_explosion is not None:
                mine_explosion.set_volume(0.60)
            if flare_defense is not None:
                flare_defense.set_volume(0.60)
            doors_open.set_volume(0.25)
            doors_close.set_volume(0.25)
            board.set_volume(0.22)
            rescue.set_volume(0.40)
            crash.set_volume(0.55)
            if chopper_crash is not None:
                chopper_crash.set_volume(0.70)
            if artillery_shot is not None:
                artillery_shot.set_volume(0.55)
            if artillery_impact_a is not None:
                artillery_impact_a.set_volume(0.55)
            if artillery_impact_b is not None:
                artillery_impact_b.set_volume(0.55)
            if jet_flyby is not None:
                jet_flyby.set_volume(0.55)
            if flying_loop is not None:
                flying_loop.set_volume(0.28)
            if menu_select is not None:
                menu_select.set_volume(0.45)
            if pause is not None:
                pause.set_volume(0.55)

            return AudioBank(
                mixer=mixer,
                shoot=shoot,
                bomb=bomb,
                explosion=explosion,
                explosion_small=explosion_small,
                explosion_big=explosion_big,
                mine_explosion=mine_explosion,
                flare_defense=flare_defense,
                artillery_shot=artillery_shot,
                artillery_impact_a=artillery_impact_a,
                artillery_impact_b=artillery_impact_b,
                jet_flyby=jet_flyby,
                doors_open=doors_open,
                doors_close=doors_close,
                board=board,
                rescue=rescue,
                crash=crash,
                chopper_crash=chopper_crash,
                flying_loop=flying_loop,
                menu_select=menu_select,
                pause=pause,
                midair_collision=midair_collision,
                chopper_warning_beeps=chopper_warning_beeps,
            )
        except Exception as e:
            print(f"[AudioBank] Failed to initialize: {e}")
            return AudioBank(
                mixer=None,
                shoot=None,
                bomb=None,
                explosion=None,
                explosion_small=None,
                explosion_big=None,
                mine_explosion=None,
                flare_defense=None,
                artillery_shot=None,
                artillery_impact_a=None,
                artillery_impact_b=None,
                jet_flyby=None,
                doors_open=None,
                doors_close=None,
                board=None,
                rescue=None,
                crash=None,
                chopper_crash=None,
                flying_loop=None,
                menu_select=None,
                pause=None,
                midair_collision=None,
                chopper_warning_beeps=None,
            )
            r2 = _sine_pcm16(freq_hz=988.0, duration_s=0.10, volume=0.22, sample_rate=sample_rate)
            rescue = pygame.mixer.Sound(buffer=_mix_pcm16([r1, r2], volume=0.85))

            crash_a = _sine_pcm16(freq_hz=48.0, duration_s=0.40, volume=0.42, sample_rate=sample_rate, fade_out_s=0.25)
            crash = pygame.mixer.Sound(buffer=crash_a)

            artillery_shot = _try_load_asset_sound(asset_dir / "artillery-shot.wav")
            artillery_impact_a = _try_load_asset_sound(asset_dir / "artillery-impact.wav")
            artillery_impact_b = _try_load_asset_sound(asset_dir / "alternate-artillery-impact.wav")
            jet_flyby = _try_load_asset_sound(asset_dir / "fighter-jet-flyby.wav")

            menu_select = _try_load_asset_sound(asset_dir / "menu-select.wav")
            pause = _try_load_asset_sound(asset_dir / "pause.wav")
            midair_collision = _try_load_asset_sound(asset_dir / "midair-collission.wav")
            chopper_warning_beeps = _try_load_asset_sound(asset_dir / "chopper-warning-beeps.wav")

            # Override placeholders with external files if provided.
            # (These are optional: game stays playable without them.)
            explosion_big = _try_load_asset_sound(asset_dir / "explosion_big.wav") or explosion_big
            explosion_small = _try_load_asset_sound(asset_dir / "explosion_small.wav") or explosion_small
            shoot = (
                _try_load_asset_sound(asset_dir / "gunfire.wav")
                or _try_load_asset_sound(asset_dir / "shoot.wav")
                or shoot
            )
            bomb = _try_load_asset_sound(asset_dir / "bomb.wav") or bomb
            rescue = _try_load_asset_sound(asset_dir / "rescue.wav") or rescue
            crash = _try_load_asset_sound(asset_dir / "crash.wav") or crash
            chopper_crash = _try_load_asset_sound(asset_dir / "chopper-crash.wav")
            doors_open = _try_load_asset_sound(asset_dir / "doors_open.wav") or doors_open
            doors_close = _try_load_asset_sound(asset_dir / "doors_close.wav") or doors_close
            board = _try_load_asset_sound(asset_dir / "board.wav") or board
            flying_loop = _try_load_asset_sound(asset_dir / "chopper-flying.wav")

            # Keep levels conservative.
            shoot.set_volume(0.35)
            bomb.set_volume(0.45)
            explosion_small.set_volume(0.45)
            explosion_big.set_volume(0.60)
            explosion = explosion_big
            explosion.set_volume(0.60)
            if mine_explosion is not None:
                mine_explosion.set_volume(0.60)
            if flare_defense is not None:
                flare_defense.set_volume(0.60)
            doors_open.set_volume(0.25)
            doors_close.set_volume(0.25)
            board.set_volume(0.22)
            rescue.set_volume(0.40)
            crash.set_volume(0.55)
            if chopper_crash is not None:
                chopper_crash.set_volume(0.70)
            if artillery_shot is not None:
                artillery_shot.set_volume(0.55)
            if artillery_impact_a is not None:
                artillery_impact_a.set_volume(0.55)
            if artillery_impact_b is not None:
                artillery_impact_b.set_volume(0.55)
            if jet_flyby is not None:
                jet_flyby.set_volume(0.55)
            if flying_loop is not None:
                flying_loop.set_volume(0.28)
            if menu_select is not None:
                menu_select.set_volume(0.45)
            if pause is not None:
                pause.set_volume(0.55)

            # ...existing code...

    def _apply_mute_state(self) -> None:
        # When muted, mute everything.
        # When pause menu is active, mute gameplay (sfx/music) but keep UI audible.
        if self._muted:
            mute_sfx = True
            mute_ui = True
            mute_music = True
        else:
            mute_sfx = bool(self._pause_menu_active)
            mute_ui = False
            mute_music = bool(self._pause_menu_active)

        duck = float(self._duck_current_factor)
        if self.mixer is not None:
            self.mixer.set_bus_volume("sfx", (0.0 if mute_sfx else 1.0) * duck)
            self.mixer.set_bus_volume("ui", 0.0 if mute_ui else 1.0)
            self.mixer.set_bus_volume("music", (0.0 if mute_music else 1.0) * duck)
            return

        # Fallback: global pause/unpause (not bus-aware).
        try:
            if self._pause_menu_active or self._muted:
                pygame.mixer.pause()
            else:
                pygame.mixer.unpause()
        except Exception:
            return AudioBank(
                mixer=None,
                shoot=None,
                bomb=None,
                explosion=None,
                explosion_small=None,
                explosion_big=None,
                mine_explosion=None,
                flare_defense=None,
                artillery_shot=None,
                artillery_impact_a=None,
                artillery_impact_b=None,
                jet_flyby=None,
                doors_open=None,
                doors_close=None,
                board=None,
                rescue=None,
                crash=None,
                chopper_crash=None,
                flying_loop=None,
                menu_select=None,
                pause=None,
                midair_collision=None,
                chopper_warning_beeps=None,
            )

        # Best-effort duck for the non-bus fallback.
        if not self._pause_menu_active and not self._muted:
            try:
                for i in range(int(pygame.mixer.get_num_channels())):
                    pygame.mixer.Channel(i).set_volume(duck)
            except Exception:
                pass

    def trigger_duck(self, *, strength: float = 1.0) -> None:
        """Briefly lower gameplay audio volume on big impacts/crashes.

        Strength is in [0..1] where 1.0 is the strongest duck.
        """

        s = _clamp(float(strength), 0.0, 1.0)
        if s <= 0.0:
            return

        # Keep it subtle: at max strength, duck to ~55% and recover quickly.
        factor = _clamp(1.0 - 0.45 * s, 0.40, 1.0)
        duration_s = 0.14 + 0.16 * s

        self._duck_min_factor = min(self._duck_min_factor, factor)
        self._duck_remaining_s = max(self._duck_remaining_s, duration_s)
        self._duck_total_s = max(self._duck_total_s, self._duck_remaining_s)

    def update(self, dt: float) -> None:
        if dt <= 0.0:
            return

        if self._duck_remaining_s > 0.0:
            self._duck_remaining_s = max(0.0, self._duck_remaining_s - dt)

            total = max(0.001, float(self._duck_total_s))
            t = 1.0 - (float(self._duck_remaining_s) / total)
            factor = float(self._duck_min_factor) + (1.0 - float(self._duck_min_factor)) * _clamp(t, 0.0, 1.0)
        else:
            factor = 1.0
            self._duck_total_s = 0.0
            self._duck_min_factor = 1.0

        # Only reapply volumes if the effective factor changed.
        if abs(factor - float(self._duck_current_factor)) > 0.01:
            self._duck_current_factor = factor
            self._apply_mute_state()

    def set_muted(self, muted: bool) -> None:
        self._muted = bool(muted)
        self._apply_mute_state()

    def set_pause_menu_active(self, active: bool) -> None:
        self._pause_menu_active = bool(active)
        self._apply_mute_state()

    def play_shoot(self) -> None:
        self._play(self.shoot, bus="sfx")

    def play_bomb(self) -> None:
        self._play(self.bomb, bus="sfx")

    def play_explosion(self) -> None:
        self._play(self.explosion, bus="sfx")

    def play_explosion_small(self) -> None:
        self._play(self.explosion_small, bus="sfx")

    def play_explosion_big(self) -> None:
        self._play(self.explosion_big, bus="sfx")

    def play_mine_explosion(self) -> None:
        self._play(self.mine_explosion, bus="sfx")

    def play_flare_defense(self) -> None:
        self._play(self.flare_defense, bus="sfx")

    def play_artillery_shot(self) -> None:
        self._play(self.artillery_shot, bus="sfx")

    def play_artillery_impact(self) -> None:
        # Randomize between two optional variants; avoid immediate repeats when both exist.
        variants: list[pygame.mixer.Sound] = []
        if self.artillery_impact_a is not None:
            variants.append(self.artillery_impact_a)
        if self.artillery_impact_b is not None:
            variants.append(self.artillery_impact_b)
        if not variants:
            return

        if len(variants) == 1:
            self._play(variants[0], bus="sfx")
            self._last_artillery_impact_variant = 0
            return

        idx = random.randrange(2)
        if idx == self._last_artillery_impact_variant:
            idx = 1 - idx
        self._last_artillery_impact_variant = idx
        self._play(variants[idx], bus="sfx")

    def play_doors_open(self) -> None:
        self._play(self.doors_open, bus="sfx")

    def play_doors_close(self) -> None:
        self._play(self.doors_close, bus="sfx")

    def play_board(self) -> None:
        self._play(self.board, bus="sfx")

    def play_rescue(self) -> None:
        self._play(self.rescue, bus="sfx")

    def play_crash(self) -> None:
        self._play(self.crash, bus="sfx")

    def play_chopper_crash(self) -> None:
        self._play(self.chopper_crash, bus="sfx")

    def play_jet_flyby(self) -> None:
        self._play(self.jet_flyby, bus="sfx")

    def play_menu_select(self) -> None:
        self._play(self.menu_select, bus="ui")

    def play_pause_toggle(self) -> None:
        self._play(self.pause, bus="ui")
