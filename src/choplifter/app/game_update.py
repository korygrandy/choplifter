from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..helicopter import HelicopterInput
from .stats_snapshot import MissionStatsSnapshot, count_open_compounds


def build_helicopter_input(
    *,
    mode: str,
    kb_tilt_left: bool,
    kb_tilt_right: bool,
    kb_lift_up: bool,
    kb_lift_down: bool,
    kb_brake: bool,
    gp_tilt_left: bool,
    gp_tilt_right: bool,
    gp_lift_up: bool,
    gp_lift_down: bool,
) -> HelicopterInput:
    """Gate helicopter controls by current mode."""
    playing = mode == "playing"
    return HelicopterInput(
        tilt_left=(kb_tilt_left or gp_tilt_left) if playing else False,
        tilt_right=(kb_tilt_right or gp_tilt_right) if playing else False,
        lift_up=(kb_lift_up or gp_lift_up) if playing else False,
        lift_down=(kb_lift_down or gp_lift_down) if playing else False,
        brake=kb_brake if playing else False,
    )


@dataclass
class PlayingMissionEndTransition:
    ended: bool
    next_mode: str | None
    next_mission_end_return_seconds: float | None
    toast_message: str | None
    campaign_sentiment: float | None


@dataclass
class PlayingHelicopterStepResult:
    landed: bool
    landing_vy: float


def resolve_playing_mission_end_transition(*, mission_ended: bool, sentiment: float, mission_end_delay_s: float = 5.0) -> PlayingMissionEndTransition:
    """Resolve mode/timer/toast changes when a playing mission ends."""
    if not mission_ended:
        return PlayingMissionEndTransition(
            ended=False,
            next_mode=None,
            next_mission_end_return_seconds=None,
            toast_message=None,
            campaign_sentiment=None,
        )

    return PlayingMissionEndTransition(
        ended=True,
        next_mode="mission_end",
        next_mission_end_return_seconds=float(mission_end_delay_s),
        toast_message=f"Mission ended. Returning to Mission Select in {int(mission_end_delay_s)}s.",
        campaign_sentiment=float(sentiment),
    )


def step_playing_helicopter(
    *,
    mission: object,
    helicopter: object,
    helicopter_input: HelicopterInput,
    tick_dt: float,
    physics: object,
    heli_settings: object,
    audio: object,
    update_helicopter_fn: Callable[..., None],
) -> PlayingHelicopterStepResult:
    """Advance helicopter motion/audio one fixed tick in playing mode."""
    if bool(getattr(mission, "crash_active", False)):
        # Crash animation drives helicopter pose; flight loop/warnings must stop.
        getattr(audio, "stop_flying")()
        getattr(audio, "stop_chopper_warning_beeps")()
        return PlayingHelicopterStepResult(landed=False, landing_vy=0.0)

    was_grounded = bool(getattr(helicopter, "grounded", False))

    # If the helicopter starts airborne, there may be no ground->air transition
    # to kick off the flying loop. Start it as soon as lift is applied.
    if (helicopter_input.lift_up or helicopter_input.lift_down) and not was_grounded:
        getattr(audio, "start_flying")()

    update_helicopter_fn(
        helicopter,
        helicopter_input,
        tick_dt,
        physics,
        heli_settings,
        world_width=float(getattr(mission, "world_width", 0.0)),
        invulnerable=(float(getattr(mission, "invuln_seconds", 0.0)) > 0.0 or bool(getattr(mission, "ended", False))),
    )

    is_grounded = bool(getattr(helicopter, "grounded", False))
    if was_grounded and not is_grounded:
        getattr(audio, "start_flying")()

    landed = bool((not was_grounded) and is_grounded)
    landing_vy = float(getattr(helicopter, "last_landing_vy", 0.0)) if landed else 0.0
    if landed:
        getattr(audio, "stop_flying")()

    return PlayingHelicopterStepResult(landed=landed, landing_vy=landing_vy)


@dataclass
class PlayingStatEvents:
    saved_delta: int
    boarded_now: int
    boarded_delta: int
    open_compounds_delta: int
    tank_delta: int
    artillery_delta: int
    artillery_hit_delta: int
    jets_entered_delta: int
    mine_delta: int
    crash_changed: bool
    crash_toast_message: str | None
    crash_play_audio: bool
    lost_delta: int


def apply_playing_stat_events_feedback(
    *,
    stat_events: PlayingStatEvents,
    audio: object,
    set_toast: Callable[[str], None],
) -> None:
    """Apply audio/toast side effects for computed playing stat events."""
    if stat_events.saved_delta > 0:
        getattr(audio, "play_rescue")()
    if stat_events.boarded_delta > 0:
        getattr(audio, "play_board")()
    if stat_events.open_compounds_delta > 0:
        getattr(audio, "play_explosion_small")()
    if stat_events.tank_delta > 0:
        getattr(audio, "play_explosion_big")()

    for _ in range(max(0, stat_events.artillery_delta)):
        getattr(audio, "play_artillery_shot")()
    for _ in range(max(0, stat_events.artillery_hit_delta)):
        getattr(audio, "play_artillery_impact")()

    if stat_events.jets_entered_delta > 0:
        getattr(audio, "play_jet_flyby")()

    for _ in range(max(0, stat_events.mine_delta)):
        getattr(audio, "play_mine_explosion")()

    if stat_events.crash_changed and stat_events.crash_toast_message:
        set_toast(stat_events.crash_toast_message)
    if stat_events.crash_play_audio:
        getattr(audio, "play_crash")()

    if stat_events.lost_delta > 0:
        set_toast(f"Passengers lost in crash: +{stat_events.lost_delta}")


def collect_playing_stat_events(
    *,
    mission: object,
    prev_stats: MissionStatsSnapshot,
    boarded_count: Callable[[object], int],
) -> PlayingStatEvents:
    """Compute stat deltas and update snapshot values for consumed counters."""
    stats = getattr(mission, "stats", None)

    saved_now = int(getattr(stats, "saved", 0))
    saved_delta = saved_now - prev_stats.saved
    if saved_delta > 0:
        prev_stats.saved = saved_now

    boarded_now = int(boarded_count(mission))
    boarded_delta = boarded_now - prev_stats.boarded
    if boarded_delta > 0:
        prev_stats.boarded = boarded_now

    open_compounds_now = int(count_open_compounds(mission))
    open_compounds_delta = open_compounds_now - prev_stats.open_compounds
    if open_compounds_delta > 0:
        prev_stats.open_compounds = open_compounds_now

    tanks_now = int(getattr(stats, "tanks_destroyed", 0))
    tank_delta = tanks_now - prev_stats.tanks_destroyed
    if tank_delta > 0:
        prev_stats.tanks_destroyed = tanks_now

    artillery_fired_now = int(getattr(stats, "artillery_fired", 0))
    artillery_delta = artillery_fired_now - prev_stats.artillery_fired
    if artillery_delta > 0:
        prev_stats.artillery_fired = artillery_fired_now

    artillery_hits_now = int(getattr(stats, "artillery_hits", 0))
    artillery_hit_delta = artillery_hits_now - prev_stats.artillery_hits
    if artillery_hit_delta > 0:
        prev_stats.artillery_hits = artillery_hits_now

    jets_entered_now = int(getattr(stats, "jets_entered", 0))
    jets_entered_delta = jets_entered_now - prev_stats.jets_entered
    if jets_entered_delta > 0:
        prev_stats.jets_entered = jets_entered_now

    mines_detonated_now = int(getattr(stats, "mines_detonated", 0))
    mine_delta = mines_detonated_now - prev_stats.mines_detonated
    if mine_delta > 0:
        prev_stats.mines_detonated = mines_detonated_now

    crashes_now = int(getattr(mission, "crashes", 0))
    crash_changed = crashes_now != prev_stats.crashes
    crash_toast_message = None
    crash_play_audio = False
    if crash_changed:
        ended = bool(getattr(mission, "ended", False))
        end_reason = str(getattr(mission, "end_reason", ""))
        invuln = float(getattr(mission, "invuln_seconds", 0.0))
        if ended:
            crash_toast_message = f"THE END: {end_reason} (Enter/Esc/Start=Mission Select)"
        else:
            crash_toast_message = f"CRASH {crashes_now}/3 - respawn (invuln {invuln:0.1f}s)"
            crash_play_audio = True
        prev_stats.crashes = crashes_now

    lost_now = int(getattr(stats, "lost_in_transit", 0))
    lost_delta = lost_now - prev_stats.lost_in_transit
    if lost_delta > 0:
        prev_stats.lost_in_transit = lost_now

    return PlayingStatEvents(
        saved_delta=saved_delta,
        boarded_now=boarded_now,
        boarded_delta=boarded_delta,
        open_compounds_delta=open_compounds_delta,
        tank_delta=tank_delta,
        artillery_delta=artillery_delta,
        artillery_hit_delta=artillery_hit_delta,
        jets_entered_delta=jets_entered_delta,
        mine_delta=mine_delta,
        crash_changed=crash_changed,
        crash_toast_message=crash_toast_message,
        crash_play_audio=crash_play_audio,
        lost_delta=lost_delta,
    )
