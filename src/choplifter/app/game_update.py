from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..helicopter import HelicopterInput
from . import cutscene_config
from .feedback import consume_mission_feedback
from .stats_snapshot import MissionStatsSnapshot, count_open_compounds
from .ui_constants import MISSION_END_RETURN_DELAY_S


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
class PlayingProgressionResult:
    ended: bool
    next_mode: str | None
    next_mission_end_return_seconds: float | None
    campaign_sentiment: float | None
    boarded_now: int


@dataclass
class HostageRescueCutsceneResult:
    started: bool
    doors_open_before_cutscene: bool | None


@dataclass
class PlayingFixedStepResult:
    next_mode: str
    campaign_sentiment: float
    mission_end_return_seconds: float
    doors_open_before_cutscene: bool
    continue_fixed_loop: bool


def apply_landing_aftermath(
    *,
    landed: bool,
    landing_vy: float,
    mission: object,
    helicopter: object,
    physics: object,
    screenshake: object,
    audio: object,
    screenshake_enabled: bool,
    logger: object,
    hostage_crush_check_fn: Callable[..., None],
    rough_landing_feedback_fn: Callable[..., None],
) -> None:
    """Apply mission/audio feedback associated with a landing transition."""
    if not landed:
        return

    hostage_crush_check_fn(
        mission,
        helicopter,
        landing_vy,
        safe_landing_vy=getattr(physics, "safe_landing_vy", 0.0),
        logger=logger,
    )
    rough_landing_feedback_fn(
        state=screenshake,
        landing_vy=landing_vy,
        safe_landing_vy=float(getattr(physics, "safe_landing_vy", 0.0)),
        invuln_seconds=float(getattr(mission, "invuln_seconds", 0.0)),
        ended=bool(getattr(mission, "ended", False)),
        audio=audio,
        screenshake_enabled=screenshake_enabled,
    )


@dataclass
class PlayingHelicopterStepResult:
    landed: bool
    landing_vy: float


def resolve_playing_mission_end_transition(
    *,
    mission_ended: bool,
    sentiment: float,
    mission_end_delay_s: float = MISSION_END_RETURN_DELAY_S,
) -> PlayingMissionEndTransition:
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
        invulnerable=(
            float(getattr(mission, "invuln_seconds", 0.0)) > 0.0
            or bool(getattr(mission, "ended", False))
            or bool(getattr(mission, "engineer_remote_control_active", False))
        ),
    )

    is_grounded = bool(getattr(helicopter, "grounded", False))
    if was_grounded and not is_grounded:
        getattr(audio, "start_flying")()

    landed = bool((not was_grounded) and is_grounded)
    landing_vy = float(getattr(helicopter, "last_landing_vy", 0.0)) if landed else 0.0
    if landed:
        getattr(audio, "stop_flying")()

    return PlayingHelicopterStepResult(landed=landed, landing_vy=landing_vy)


def process_playing_progression(
    *,
    mission: object,
    helicopter: object,
    tick_dt: float,
    mission_end_delay_s: float,
    prev_stats: MissionStatsSnapshot,
    boarded_count: Callable[[object], int],
    audio: object,
    set_toast: Callable[[str], None],
    screenshake: object,
    screenshake_enabled: bool,
) -> PlayingProgressionResult:
    """Process post-update playing progression and return control-flow outcomes."""
    playing_end = resolve_playing_mission_end_transition(
        mission_ended=bool(getattr(mission, "ended", False)),
        sentiment=float(getattr(mission, "sentiment", 0.0)),
        mission_end_delay_s=mission_end_delay_s,
    )
    if playing_end.ended:
        # Stop warning beeps immediately on mission end.
        getattr(audio, "stop_chopper_warning_beeps")()
        if playing_end.toast_message:
            set_toast(playing_end.toast_message)
        return PlayingProgressionResult(
            ended=True,
            next_mode=playing_end.next_mode,
            next_mission_end_return_seconds=playing_end.next_mission_end_return_seconds,
            campaign_sentiment=playing_end.campaign_sentiment,
            boarded_now=0,
        )

    # Keep warning beeps in sync with current health state even after heals/repairs.
    if float(getattr(helicopter, "damage", 0.0)) < 70.0:
        stop_warning_beeps = getattr(audio, "stop_chopper_warning_beeps", None)
        if callable(stop_warning_beeps):
            stop_warning_beeps()

    # Consume cinematic feedback impulses produced by mission damage events.
    consume_mission_feedback(
        state=screenshake,
        mission=mission,
        audio=audio,
        screenshake_enabled=screenshake_enabled,
    )

    damage_flash_seconds = float(getattr(helicopter, "damage_flash_seconds", 0.0))
    setattr(helicopter, "damage_flash_seconds", max(0.0, damage_flash_seconds - tick_dt))

    stat_events = collect_playing_stat_events(
        mission=mission,
        prev_stats=prev_stats,
        boarded_count=boarded_count,
    )
    apply_playing_stat_events_feedback(
        stat_events=stat_events,
        audio=audio,
        set_toast=set_toast,
    )

    return PlayingProgressionResult(
        ended=False,
        next_mode=None,
        next_mission_end_return_seconds=None,
        campaign_sentiment=None,
        boarded_now=stat_events.boarded_now,
    )


def try_start_hostage_rescue_cutscene(
    *,
    mission: object,
    helicopter: object,
    boarded_now: int,
    mission_cutscene_state: object,
    assets_dir: Path,
    logger: object,
    start_mission_cutscene_fn: Callable[..., bool],
) -> HostageRescueCutsceneResult:
    """Start the one-shot hostage rescue cutscene when threshold is reached."""
    mission_id = str(getattr(mission, "mission_id", "")).strip().lower()
    is_airport = mission_id in (
        "airport",
        "airport_special_ops",
        "airportspecialops",
        "mission2",
        "m2",
    )

    if is_airport:
        stats = getattr(mission, "stats", None)
        lower_rescued = int(getattr(stats, "saved", 0)) if stats is not None else 0
        hostage_state = getattr(mission, "airport_hostage_state", None)
        elevated_rescued = int(getattr(hostage_state, "rescued_hostages", 0)) if hostage_state is not None else 0

        # Airport-specific trigger: play once when the first rescue route resolves as either
        # lower-first (any lower rescue) or elevated-first (elevated rescued before any lower rescue).
        airport_triggered = lower_rescued > 0 or (elevated_rescued > 0 and lower_rescued <= 0)
        if not airport_triggered:
            return HostageRescueCutsceneResult(started=False, doors_open_before_cutscene=None)
    else:
        if boarded_now < cutscene_config.HOSTAGE_RESCUE_CUTSCENE_THRESHOLD:
            return HostageRescueCutsceneResult(started=False, doors_open_before_cutscene=None)

    cutscenes_played = getattr(mission, "cutscenes_played", set())
    if cutscene_config.HOSTAGE_RESCUE_CUTSCENE_EVENT_ID in cutscenes_played:
        return HostageRescueCutsceneResult(started=False, doors_open_before_cutscene=None)

    cutscenes_played.add(cutscene_config.HOSTAGE_RESCUE_CUTSCENE_EVENT_ID)

    cutscene_path = cutscene_config.get_hostage_rescue_cutscene_path(
        str(getattr(mission, "mission_id", "")),
        assets_dir,
        cutscene_config.HOSTAGE_RESCUE_CUTSCENE_DEFAULT_ASSET,
        cutscene_config.HOSTAGE_RESCUE_CUTSCENE_BY_MISSION,
    )

    doors_before = bool(getattr(helicopter, "doors_open", False))
    started = bool(
        start_mission_cutscene_fn(
            mission_cutscene_state,
            cutscene_path=cutscene_path,
            logger=logger,
            event_id=cutscene_config.HOSTAGE_RESCUE_CUTSCENE_EVENT_ID,
            mission_id=str(getattr(mission, "mission_id", "")),
        )
    )
    if not started:
        return HostageRescueCutsceneResult(started=False, doors_open_before_cutscene=None)

    return HostageRescueCutsceneResult(started=True, doors_open_before_cutscene=doors_before)


def run_playing_fixed_step(
    *,
    mode: str,
    mission: object,
    helicopter: object,
    helicopter_input: HelicopterInput,
    tick_dt: float,
    physics: object,
    heli_settings: object,
    audio: object,
    flares: object,
    screenshake: object,
    screenshake_enabled: bool,
    logger: object,
    prev_stats: MissionStatsSnapshot,
    boarded_count: Callable[[object], int],
    set_toast: Callable[[str], None],
    mission_end_delay_s: float,
    campaign_sentiment: float,
    mission_end_return_seconds: float,
    doors_open_before_cutscene: bool,
    mission_cutscene_state: object,
    assets_dir: Path,
    update_flares_fn: Callable[..., None],
    update_helicopter_fn: Callable[..., None],
    hostage_crush_check_fn: Callable[..., None],
    rough_landing_feedback_fn: Callable[..., None],
    update_mission_fn: Callable[..., None],
    start_mission_cutscene_fn: Callable[..., bool],
) -> PlayingFixedStepResult:
    """Run one fixed-timestep update when in playing mode."""
    if mode != "playing":
        return PlayingFixedStepResult(
            next_mode=mode,
            campaign_sentiment=float(campaign_sentiment),
            mission_end_return_seconds=float(mission_end_return_seconds),
            doors_open_before_cutscene=bool(doors_open_before_cutscene),
            continue_fixed_loop=False,
        )

    update_flares_fn(flares, mission=mission, helicopter=helicopter, dt=tick_dt)

    heli_step = step_playing_helicopter(
        mission=mission,
        helicopter=helicopter,
        helicopter_input=helicopter_input,
        tick_dt=tick_dt,
        physics=physics,
        heli_settings=heli_settings,
        audio=audio,
        update_helicopter_fn=update_helicopter_fn,
    )

    apply_landing_aftermath(
        landed=heli_step.landed,
        landing_vy=heli_step.landing_vy,
        mission=mission,
        helicopter=helicopter,
        physics=physics,
        screenshake=screenshake,
        audio=audio,
        screenshake_enabled=screenshake_enabled,
        logger=logger,
        hostage_crush_check_fn=hostage_crush_check_fn,
        rough_landing_feedback_fn=rough_landing_feedback_fn,
    )

    update_mission_fn(mission, helicopter, tick_dt, heli_settings, logger=logger)

    playing_progress = process_playing_progression(
        mission=mission,
        helicopter=helicopter,
        tick_dt=tick_dt,
        mission_end_delay_s=mission_end_delay_s,
        prev_stats=prev_stats,
        boarded_count=boarded_count,
        audio=audio,
        set_toast=set_toast,
        screenshake=screenshake,
        screenshake_enabled=screenshake_enabled,
    )
    if playing_progress.ended:
        return PlayingFixedStepResult(
            next_mode=str(playing_progress.next_mode or mode),
            campaign_sentiment=float(
                playing_progress.campaign_sentiment
                if playing_progress.campaign_sentiment is not None
                else campaign_sentiment
            ),
            mission_end_return_seconds=float(
                playing_progress.next_mission_end_return_seconds
                if playing_progress.next_mission_end_return_seconds is not None
                else mission_end_return_seconds
            ),
            doors_open_before_cutscene=bool(doors_open_before_cutscene),
            continue_fixed_loop=True,
        )

    rescue_cutscene = try_start_hostage_rescue_cutscene(
        mission=mission,
        helicopter=helicopter,
        boarded_now=playing_progress.boarded_now,
        mission_cutscene_state=mission_cutscene_state,
        assets_dir=assets_dir,
        logger=logger,
        start_mission_cutscene_fn=start_mission_cutscene_fn,
    )
    if rescue_cutscene.started:
        next_doors = bool(
            rescue_cutscene.doors_open_before_cutscene
            if rescue_cutscene.doors_open_before_cutscene is not None
            else doors_open_before_cutscene
        )
        getattr(audio, "stop_flying")()
        getattr(audio, "log_audio_channel_snapshot")(tag="cutscene_enter", logger=logger)
        return PlayingFixedStepResult(
            next_mode="cutscene",
            campaign_sentiment=float(campaign_sentiment),
            mission_end_return_seconds=float(mission_end_return_seconds),
            doors_open_before_cutscene=next_doors,
            continue_fixed_loop=False,
        )

    return PlayingFixedStepResult(
        next_mode=mode,
        campaign_sentiment=float(campaign_sentiment),
        mission_end_return_seconds=float(mission_end_return_seconds),
        doors_open_before_cutscene=bool(doors_open_before_cutscene),
        continue_fixed_loop=False,
    )


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
