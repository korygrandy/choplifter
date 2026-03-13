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

# Dedicated channels reserved outside bus pools for persistent/key sounds.
DEDICATED_CH_WARNING_BEEPS = 7
DEDICATED_CH_FLYING_LOOP = 14
DEDICATED_CH_BARAK_DEPLOY = 16
DEDICATED_CH_BARAK_LAUNCH = 17
AUDIO_CHANNEL_DEBUG = False




@dataclass

class AudioMixer:
    """Simple audio bus routing built on pygame mixer channels.

    Buses are implemented as pools of dedicated channels so different audio
    categories can play concurrently and later be mixed/controlled separately.
    """

    def set_bus_volume(self, bus: BusName, volume: float) -> None:
        """Set the volume for all channels in the specified bus."""
        channels = self.buses.get(bus, [])
        for ch in channels:
            try:
                ch.set_volume(volume)
            except Exception:
                pass

    def __post_init__(self):
        # Assign dedicated channels to each bus for proper routing
        total_channels = 18
        pygame.mixer.set_num_channels(total_channels)
        # Keep 14/16/17 reserved for dedicated persistent/key sounds.
        bus_layout = {
            # Keep channel 7 reserved for low-health warning beeps.
            "sfx": list(range(0, 7)) + [15],
            "ui": list(range(8, 10)),
            "music": list(range(10, 14)),
        }
        self.buses = {bus: [pygame.mixer.Channel(idx) for idx in idxs] for bus, idxs in bus_layout.items()}
        self.active_loops = {}
        self._bus_cursor = {bus: 0 for bus in bus_layout}

    def play(self, sound: pygame.mixer.Sound, bus: BusName = "sfx", *, dedicated_channel: int = None) -> None:
        """Play a one-shot sound on the specified bus. If dedicated_channel is set, use that channel and do not interrupt it."""
        if dedicated_channel is not None:
            ch = pygame.mixer.Channel(dedicated_channel)
            # Dedicated channels are isolated from pooled transient SFX channels.
            ch.play(sound)
            return
        channels = self.buses.get(bus, [])
        if channels:
            # Prefer an idle channel in this bus; fall back to round-robin steal.
            for ch in channels:
                if not ch.get_busy():
                    ch.play(sound)
                    return

            cursor = int(self._bus_cursor.get(bus, 0))
            ch = channels[cursor % len(channels)]
            ch.play(sound)
            self._bus_cursor[bus] = (cursor + 1) % len(channels)
        else:
            sound.play()

        # ...existing code...

    def play_loop(
        self,
        sound: pygame.mixer.Sound,
        *,
        key: str,
        bus: BusName = "music",
        fade_in_ms: int = 500,
        dedicated_channel: int | None = None,
    ) -> None:
        if key in self.active_loops:
            ch = self.active_loops[key]
            if ch.get_busy():
                return

        if dedicated_channel is not None:
            ch = pygame.mixer.Channel(dedicated_channel)
            ch.play(sound, loops=-1, fade_ms=fade_in_ms)
            self.active_loops[key] = ch
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
    def stop_chopper_warning_beeps(self) -> None:
        """Stops the chopper warning beeps sound effect immediately (channel 7)."""
        try:
            if self.mixer is not None:
                # Stop dedicated channel 7 (used for warning beeps)
                pygame.mixer.Channel(DEDICATED_CH_WARNING_BEEPS).stop()
            elif self.chopper_warning_beeps is not None:
                pygame.mixer.Channel(DEDICATED_CH_WARNING_BEEPS).stop()
        except Exception:
            pass

    def log_audio_channel_snapshot(self, *, tag: str = "state", logger=None) -> None:
        """Opt-in debug snapshot for key mixer channels and bus occupancy."""
        if not AUDIO_CHANNEL_DEBUG:
            return
        try:
            pieces: list[str] = []
            for idx in (
                7,
                DEDICATED_CH_FLYING_LOOP,
                DEDICATED_CH_BARAK_DEPLOY,
                DEDICATED_CH_BARAK_LAUNCH,
            ):
                ch = pygame.mixer.Channel(idx)
                pieces.append(f"ch{idx}={'busy' if ch.get_busy() else 'idle'}")

            if self.mixer is not None:
                for bus in ("sfx", "ui", "music"):
                    channels = self.mixer.buses.get(bus, [])
                    busy = sum(1 for ch in channels if ch.get_busy())
                    pieces.append(f"{bus}={busy}/{len(channels)}")

            msg = f"AUDIO_CH[{tag}] " + " | ".join(pieces)
            if logger is not None:
                logger.info(msg)
            else:
                print(msg)
        except Exception:
            return
    def play_hostage_scream(self) -> None:
        """Play a random male or female scream SFX if available."""
        # Lazy-load scream sounds if not already loaded
        if not hasattr(self, '_hostage_scream_sounds'):
            import os
            module_dir = Path(__file__).resolve().parent
            asset_dir = module_dir / "assets"
            male = _try_load_asset_sound(asset_dir / "male-scream.ogg")
            female = _try_load_asset_sound(asset_dir / "female-scream.ogg")
            self._hostage_scream_sounds = [s for s in (male, female) if s is not None]
        if not self._hostage_scream_sounds:
            return
        sound = random.choice(self._hostage_scream_sounds)
        self._play(sound, bus="sfx")
    def play_midair_collision(self) -> None:
        # Use SFX channel 6 (never interrupted)
        if self.mixer is not None:
            self.mixer.play(self.midair_collision, bus="sfx", dedicated_channel=6)
        elif self.midair_collision is not None:
            pygame.mixer.Channel(6).play(self.midair_collision)

    def play_chopper_warning_beeps(self) -> None:
        # Use SFX channel 7 (never interrupted)
        if self.mixer is not None:
            self.mixer.play(self.chopper_warning_beeps, bus="sfx", dedicated_channel=7)
        elif self.chopper_warning_beeps is not None:
            pygame.mixer.Channel(DEDICATED_CH_WARNING_BEEPS).play(self.chopper_warning_beeps)
    # Ducking state variables (for audio ducking/fading)
    _duck_remaining_s: float = field(default=0.0, init=False, repr=False)
    _duck_total_s: float = field(default=0.0, init=False, repr=False)
    _duck_min_factor: float = field(default=1.0, init=False, repr=False)
    _duck_current_factor: float = field(default=1.0, init=False, repr=False)
    _cinematic_duck_factor: float = field(default=1.0, init=False, repr=False)
    mixer: AudioMixer | None
    _pause_menu_active: bool = field(default=False, init=False, repr=False)
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
    barak_mrad_deploy: pygame.mixer.Sound | None
    barak_mrad_launch: pygame.mixer.Sound | None
    bus_accelerate: pygame.mixer.Sound | None
    bus_brakes: pygame.mixer.Sound | None
    bus_door: pygame.mixer.Sound | None
    hang_on_yall: pygame.mixer.Sound | None
    carjacked_mealtruck: pygame.mixer.Sound | None
    airport_ai_mission_brief: pygame.mixer.Sound | None
    satellite_reallocating: pygame.mixer.Sound | None
    barak_explosion: pygame.mixer.Sound | None

    def play_barak_mrad_deploy(self) -> None:
        if self.barak_mrad_deploy is None:
            return
        if self.mixer is not None:
            # Separate dedicated lane keeps deploy and launch cues from stepping on each other.
            self.mixer.play(self.barak_mrad_deploy, bus="sfx", dedicated_channel=DEDICATED_CH_BARAK_DEPLOY)
        else:
            self.barak_mrad_deploy.play()

    def play_barak_mrad_launch(self) -> None:
        if self.barak_mrad_launch is None:
            return
        if self.mixer is not None:
            # Separate dedicated lanes allow deploy and launch cues to overlap.
            self.mixer.play(self.barak_mrad_launch, bus="sfx", dedicated_channel=DEDICATED_CH_BARAK_LAUNCH)
        else:
            self.barak_mrad_launch.play()

    def start_flying(self) -> None:
        """Starts the helicopter flying loop sound if available."""
        if hasattr(self, "mixer") and self.mixer is not None and self.flying_loop is not None:
            self.mixer.play_loop(
                self.flying_loop,
                key="flying_loop",
                bus="music",
                fade_in_ms=500,
                dedicated_channel=DEDICATED_CH_FLYING_LOOP,
            )
        elif self.flying_loop is not None:
            try:
                self.flying_loop.play(loops=-1, fade_ms=500)
            except Exception:
                pass

    def stop_persistent_channels(self) -> None:
        """Stop persistent dedicated channels explicitly (restart/cutscene safety)."""
        self.stop_flying()
        self.stop_chopper_warning_beeps()
        try:
            pygame.mixer.Channel(DEDICATED_CH_BARAK_LAUNCH).stop()
        except Exception:
            pass

    def set_cinematic_ducked(self, active: bool, *, factor: float = 0.5) -> None:
        """Sustain ducking during cutscenes/hostage cinematics."""
        target = float(_clamp(factor, 0.1, 1.0)) if active else 1.0
        if abs(target - float(self._cinematic_duck_factor)) <= 0.01:
            return
        self._cinematic_duck_factor = target
        self._apply_mute_state()

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
        # Explicitly initialize the mixer and set channels for bus routing
        try:
            pygame.mixer.quit()
        except Exception:
            pass
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        pygame.mixer.set_num_channels(18)  # Must match AudioMixer total_channels (needs channels 16-17 for Barak)
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

            mine_explosion = _try_load_asset_sound(asset_dir / "mine-explosion.ogg")
            flare_defense = _try_load_asset_sound(asset_dir / "flare-defense.ogg")

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

            artillery_shot = _try_load_asset_sound(asset_dir / "artillery-shot.ogg")
            artillery_impact_a = _try_load_asset_sound(asset_dir / "artillery-impact.ogg")
            artillery_impact_b = _try_load_asset_sound(asset_dir / "alternate-artillery-impact.ogg")
            jet_flyby = _try_load_asset_sound(asset_dir / "fighter-jet-flyby.ogg")

            menu_select = _try_load_asset_sound(asset_dir / "menu-select.ogg")
            pause = _try_load_asset_sound(asset_dir / "pause.ogg")
            midair_collision = _try_load_asset_sound(asset_dir / "midair-collission.ogg")
            chopper_warning_beeps = _try_load_asset_sound(asset_dir / "chopper-warning-beeps.ogg")

            explosion_big = _try_load_asset_sound(asset_dir / "explosion_big.ogg") or explosion_big
            explosion_small = _try_load_asset_sound(asset_dir / "explosion_small.ogg") or explosion_small
            shoot = (
                _try_load_asset_sound(asset_dir / "gunfire.ogg")
                or _try_load_asset_sound(asset_dir / "shoot.ogg")
                or shoot
            )
            bomb = _try_load_asset_sound(asset_dir / "bomb.ogg") or bomb
            rescue = _try_load_asset_sound(asset_dir / "rescue.ogg") or rescue
            crash = _try_load_asset_sound(asset_dir / "crash.ogg") or crash
            chopper_crash = _try_load_asset_sound(asset_dir / "chopper-crash.ogg")
            doors_open = _try_load_asset_sound(asset_dir / "doors_open.ogg") or doors_open
            doors_close = _try_load_asset_sound(asset_dir / "doors_close.ogg") or doors_close
            board = _try_load_asset_sound(asset_dir / "board.ogg") or board
            flying_loop = _try_load_asset_sound(asset_dir / "chopper-flying.ogg")

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

            barak_mrad_deploy = _try_load_asset_sound(asset_dir / "barak-deploying.ogg")
            if barak_mrad_deploy is not None:
                barak_mrad_deploy.set_volume(0.66)

            barak_mrad_launch = _try_load_asset_sound(asset_dir / "barak-launched.ogg")
            if barak_mrad_launch is not None:
                barak_mrad_launch.set_volume(0.58)

            # Bus sound effects for Airport mission
            bus_accelerate = _try_load_asset_sound(asset_dir / "bus-accelerate.ogg")
            if bus_accelerate is not None:
                bus_accelerate.set_volume(0.50)
            bus_brakes = _try_load_asset_sound(asset_dir / "bus-brakes.ogg")
            if bus_brakes is not None:
                bus_brakes.set_volume(0.50)
            bus_door = _try_load_asset_sound(asset_dir / "bus-door.ogg")
            if bus_door is not None:
                bus_door.set_volume(0.50)
            hang_on_yall = _try_load_asset_sound(asset_dir / "hang-on-yall.ogg")
            if hang_on_yall is not None:
                hang_on_yall.set_volume(0.58)
            carjacked_mealtruck = _try_load_asset_sound(asset_dir / "carjacked-mealtruck.ogg")
            if carjacked_mealtruck is not None:
                carjacked_mealtruck.set_volume(0.62)
            airport_ai_mission_brief = _try_load_asset_sound(asset_dir / "airport-ai-mission-brief.ogg")
            if airport_ai_mission_brief is not None:
                airport_ai_mission_brief.set_volume(0.64)
            satellite_reallocating = _try_load_asset_sound(asset_dir / "satellite-reallocating.ogg")
            if satellite_reallocating is not None:
                satellite_reallocating.set_volume(0.70)
            barak_explosion = (
                _try_load_asset_sound(asset_dir / "barak-explosion.ogg")
                or _try_load_asset_sound(asset_dir / "barrak-explosion.ogg")
            )
            if barak_explosion is not None:
                barak_explosion.set_volume(0.72)
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
                barak_mrad_deploy=barak_mrad_deploy,
                barak_mrad_launch=barak_mrad_launch,
                bus_accelerate=bus_accelerate,
                bus_brakes=bus_brakes,
                bus_door=bus_door,
                hang_on_yall=hang_on_yall,
                carjacked_mealtruck=carjacked_mealtruck,
                airport_ai_mission_brief=airport_ai_mission_brief,
                satellite_reallocating=satellite_reallocating,
                barak_explosion=barak_explosion,
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
                barak_mrad_deploy=None,
                barak_mrad_launch=None,
                bus_accelerate=None,
                bus_brakes=None,
                bus_door=None,
                hang_on_yall=None,
                carjacked_mealtruck=None,
                airport_ai_mission_brief=None,
                satellite_reallocating=None,
                barak_explosion=None,
            )
            r2 = _sine_pcm16(freq_hz=988.0, duration_s=0.10, volume=0.22, sample_rate=sample_rate)
            rescue = pygame.mixer.Sound(buffer=_mix_pcm16([r1, r2], volume=0.85))

            crash_a = _sine_pcm16(freq_hz=48.0, duration_s=0.40, volume=0.42, sample_rate=sample_rate, fade_out_s=0.25)
            crash = pygame.mixer.Sound(buffer=crash_a)

            artillery_shot = _try_load_asset_sound(asset_dir / "artillery-shot.ogg")
            artillery_impact_a = _try_load_asset_sound(asset_dir / "artillery-impact.ogg")
            artillery_impact_b = _try_load_asset_sound(asset_dir / "alternate-artillery-impact.ogg")
            jet_flyby = _try_load_asset_sound(asset_dir / "fighter-jet-flyby.ogg")

            menu_select = _try_load_asset_sound(asset_dir / "menu-select.ogg")
            pause = _try_load_asset_sound(asset_dir / "pause.ogg")
            midair_collision = _try_load_asset_sound(asset_dir / "midair-collission.ogg")
            chopper_warning_beeps = _try_load_asset_sound(asset_dir / "chopper-warning-beeps.ogg")

            # Override placeholders with external files if provided.
            # (These are optional: game stays playable without them.)
            explosion_big = _try_load_asset_sound(asset_dir / "explosion_big.ogg") or explosion_big
            explosion_small = _try_load_asset_sound(asset_dir / "explosion_small.ogg") or explosion_small
            shoot = (
                _try_load_asset_sound(asset_dir / "gunfire.ogg")
                or _try_load_asset_sound(asset_dir / "shoot.ogg")
                or shoot
            )
            bomb = _try_load_asset_sound(asset_dir / "bomb.ogg") or bomb
            rescue = _try_load_asset_sound(asset_dir / "rescue.ogg") or rescue
            crash = _try_load_asset_sound(asset_dir / "crash.ogg") or crash
            chopper_crash = _try_load_asset_sound(asset_dir / "chopper-crash.ogg")
            doors_open = _try_load_asset_sound(asset_dir / "doors_open.ogg") or doors_open
            doors_close = _try_load_asset_sound(asset_dir / "doors_close.ogg") or doors_close
            board = _try_load_asset_sound(asset_dir / "board.ogg") or board
            flying_loop = _try_load_asset_sound(asset_dir / "chopper-flying.ogg")

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
        # Pause behavior: mute gameplay channels while paused but keep UI cues
        # audible for pause-menu navigation. User mute always wins.
        paused = bool(self._pause_menu_active)
        user_muted = bool(self._muted)
        mute_sfx = paused or user_muted
        mute_ui = user_muted
        mute_music = paused or user_muted

        duck = float(self._duck_current_factor) * float(self._cinematic_duck_factor)
        if self.mixer is not None:
            sfx_vol = (0.0 if mute_sfx else 1.0) * duck
            ui_vol = 0.0 if mute_ui else 1.0
            music_vol = (0.0 if mute_music else 1.0) * duck
            self.mixer.set_bus_volume("sfx", sfx_vol)
            self.mixer.set_bus_volume("ui", ui_vol)
            self.mixer.set_bus_volume("music", music_vol)

            # Dedicated channels are not part of bus pools, so mirror the same
            # effective bus volumes explicitly to keep pause/mute behavior coherent.
            try:
                pygame.mixer.Channel(DEDICATED_CH_FLYING_LOOP).set_volume(music_vol)
                pygame.mixer.Channel(DEDICATED_CH_BARAK_DEPLOY).set_volume(sfx_vol)
                pygame.mixer.Channel(DEDICATED_CH_BARAK_LAUNCH).set_volume(sfx_vol)
                pygame.mixer.Channel(DEDICATED_CH_WARNING_BEEPS).set_volume(sfx_vol)
            except Exception:
                pass
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

    def play_bus_accelerate(self) -> None:
        self._play(self.bus_accelerate, bus="sfx")

    def play_bus_brakes(self) -> None:
        self._play(self.bus_brakes, bus="sfx")

    def play_bus_door(self) -> None:
        self._play(self.bus_door, bus="sfx")

    def play_hang_on_yall(self) -> None:
        self._play(self.hang_on_yall, bus="sfx")

    def play_carjacked_mealtruck(self) -> None:
        self._play(self.carjacked_mealtruck, bus="sfx")

    def play_airport_ai_mission_brief(self) -> None:
        self._play(self.airport_ai_mission_brief, bus="sfx")

    def play_satellite_reallocating(self) -> None:
        self._play(self.satellite_reallocating, bus="sfx")

    def play_barak_explosion(self) -> None:
        self._play(self.barak_explosion, bus="sfx")
