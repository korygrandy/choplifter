from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import logging
import math

from .helicopter import Facing, Helicopter
from .math2d import Vec2, clamp
from .settings import HelicopterSettings


class HostageState(Enum):
    IDLE = 0
    PANIC = 1
    MOVING_TO_LZ = 2
    WAITING = 3
    BOARDED = 4
    SAVED = 5
    KIA = 6


@dataclass
class Hostage:
    state: HostageState
    pos: Vec2
    health: float = 100.0


@dataclass
class Compound:
    pos: Vec2
    width: float
    height: float
    health: float
    is_open: bool
    hostage_start: int
    hostage_count: int
    log_bucket: int = -1

    def contains_point(self, p: Vec2) -> bool:
        return (
            self.pos.x <= p.x <= self.pos.x + self.width
            and self.pos.y <= p.y <= self.pos.y + self.height
        )


class ProjectileKind(Enum):
    BULLET = 1
    BOMB = 2


@dataclass
class Projectile:
    kind: ProjectileKind
    pos: Vec2
    vel: Vec2
    ttl: float
    alive: bool = True


@dataclass(frozen=True)
class BaseZone:
    pos: Vec2
    width: float
    height: float

    def contains_point(self, p: Vec2) -> bool:
        return (
            self.pos.x <= p.x <= self.pos.x + self.width
            and self.pos.y <= p.y <= self.pos.y + self.height
        )


@dataclass
class MissionStats:
    saved: int = 0
    kia_by_player: int = 0
    kia_by_enemy: int = 0
    lost_in_transit: int = 0


@dataclass
class MissionState:
    compounds: list[Compound]
    hostages: list[Hostage]
    projectiles: list[Projectile]
    base: BaseZone
    stats: MissionStats
    ended: bool = False
    end_text: str = ""
    _last_logged_boarded: int = 0
    _last_logged_saved: int = 0
    _last_logged_kia_player: int = 0

    @staticmethod
    def create_default(heli: HelicopterSettings) -> "MissionState":
        # Four compounds, 16 hostages each, like the classic.
        compounds: list[Compound] = []
        hostage_index = 0
        compound_w = 80.0
        compound_h = 60.0
        compound_y = heli.ground_y - compound_h

        for x in (140.0, 360.0, 580.0, 800.0):
            compounds.append(
                Compound(
                    pos=Vec2(x, compound_y),
                    width=compound_w,
                    height=compound_h,
                    health=120.0,
                    is_open=False,
                    hostage_start=hostage_index,
                    hostage_count=16,
                )
            )
            hostage_index += 16

        hostages = [Hostage(state=HostageState.IDLE, pos=Vec2(-9999.0, -9999.0)) for _ in range(64)]

        base_w = 170.0
        base_h = 90.0
        base = BaseZone(pos=Vec2(1280.0 - base_w - 20.0, heli.ground_y - base_h), width=base_w, height=base_h)

        return MissionState(
            compounds=compounds,
            hostages=hostages,
            projectiles=[],
            base=base,
            stats=MissionStats(),
        )


def boarded_count(mission: MissionState) -> int:
    return sum(1 for h in mission.hostages if h.state is HostageState.BOARDED)


def on_foot(hostage: Hostage) -> bool:
    return hostage.state in (HostageState.PANIC, HostageState.MOVING_TO_LZ, HostageState.WAITING)


def spawn_projectile_from_helicopter(mission: MissionState, helicopter: Helicopter) -> None:
    # Minimal: side-facing shoots bullets, forward-facing drops a bomb.
    if mission.ended:
        return

    if helicopter.facing is Facing.FORWARD:
        mission.projectiles.append(
            Projectile(
                kind=ProjectileKind.BOMB,
                pos=Vec2(helicopter.pos.x, helicopter.pos.y + 10.0),
                vel=Vec2(0.0, 3.0),
                ttl=2.5,
            )
        )
        return

    direction = -1.0 if helicopter.facing is Facing.LEFT else 1.0
    mission.projectiles.append(
        Projectile(
            kind=ProjectileKind.BULLET,
            pos=Vec2(helicopter.pos.x + direction * 40.0, helicopter.pos.y),
            vel=Vec2(direction * 95.0, 0.0),
            ttl=1.2,
        )
    )


def spawn_projectile_from_helicopter_logged(
    mission: MissionState,
    helicopter: Helicopter,
    logger: logging.Logger | None,
) -> None:
    spawn_projectile_from_helicopter(mission, helicopter)
    if logger is None:
        return
    if helicopter.facing is Facing.FORWARD:
        logger.info("Fire: BOMB")
    else:
        logger.info("Fire: BULLET")


def update_mission(
    mission: MissionState,
    helicopter: Helicopter,
    dt: float,
    heli: HelicopterSettings,
    logger: logging.Logger | None = None,
) -> None:
    if mission.ended:
        return

    _update_projectiles(mission, dt, heli, logger)
    _update_compounds_and_release(mission, heli, logger)
    _update_hostages(mission, helicopter, dt, heli)
    _handle_unload(mission, helicopter, heli)

    _log_progress_if_changed(mission, logger)

    if mission.stats.saved >= 20:
        mission.ended = True
        mission.end_text = "THE END"
        if logger is not None:
            logger.info("WIN: saved=%d (THE END)", mission.stats.saved)
            logger.info(
                "END_STATS: saved=%d boarded=%d kia_by_player=%d",
                mission.stats.saved,
                boarded_count(mission),
                mission.stats.kia_by_player,
            )


def _update_projectiles(
    mission: MissionState,
    dt: float,
    heli: HelicopterSettings,
    logger: logging.Logger | None,
) -> None:
    gravity = 28.0

    for p in mission.projectiles:
        if not p.alive:
            continue

        p.ttl -= dt
        if p.ttl <= 0.0:
            p.alive = False
            continue

        if p.kind is ProjectileKind.BOMB:
            p.vel.y += gravity * dt

        p.pos.x += p.vel.x * dt
        p.pos.y += p.vel.y * dt

        # Ground collision.
        if p.pos.y >= heli.ground_y - 6.0:
            if p.kind is ProjectileKind.BOMB:
                _bomb_explode(mission, p.pos, logger)
            p.alive = False
            continue

        # Compound collision.
        for c in mission.compounds:
            if c.health <= 0:
                continue
            if c.contains_point(p.pos):
                if p.kind is ProjectileKind.BULLET:
                    c.health -= 12.0
                else:
                    c.health -= 40.0
                _log_compound_health_if_needed(c, logger, reason="hit")
                p.alive = False
                break

        if not p.alive:
            continue

        # Hostage collateral (simple): bullets/bombs can kill hostages on foot.
        for h in mission.hostages:
            if not on_foot(h):
                continue
            dx = h.pos.x - p.pos.x
            dy = h.pos.y - p.pos.y
            if dx * dx + dy * dy <= 12.0 * 12.0:
                h.state = HostageState.KIA
                mission.stats.kia_by_player += 1
                p.alive = False
                break

    # Compact list.
    mission.projectiles = [p for p in mission.projectiles if p.alive]


def _bomb_explode(mission: MissionState, pos: Vec2, logger: logging.Logger | None) -> None:
    # Small AoE for collateral + compound damage.
    radius = 42.0
    r2 = radius * radius

    for c in mission.compounds:
        if c.health <= 0:
            continue
        cx = clamp(pos.x, c.pos.x, c.pos.x + c.width)
        cy = clamp(pos.y, c.pos.y, c.pos.y + c.height)
        dx = pos.x - cx
        dy = pos.y - cy
        if dx * dx + dy * dy <= r2:
            c.health -= 30.0
            _log_compound_health_if_needed(c, logger, reason="blast")

    for h in mission.hostages:
        if not on_foot(h):
            continue
        dx = h.pos.x - pos.x
        dy = h.pos.y - pos.y
        if dx * dx + dy * dy <= r2:
            h.state = HostageState.KIA
            mission.stats.kia_by_player += 1


def _update_compounds_and_release(mission: MissionState, heli: HelicopterSettings, logger: logging.Logger | None) -> None:
    for c in mission.compounds:
        if c.is_open:
            continue
        if c.health > 0.0:
            continue

        c.is_open = True
        if logger is not None:
            logger.info(
                "Compound opened: x=%.0f hostages=%d..%d",
                c.pos.x,
                c.hostage_start,
                c.hostage_start + c.hostage_count - 1,
            )
        # Spawn hostages at the compound entrance area.
        start = c.hostage_start
        end = start + c.hostage_count
        for i, h in enumerate(mission.hostages[start:end]):
            spread = (i % 8) * 10.0
            row = i // 8
            h.state = HostageState.PANIC
            h.pos = Vec2(c.pos.x + 10.0 + spread, heli.ground_y - 10.0 - row * 10.0)


def _update_hostages(mission: MissionState, helicopter: Helicopter, dt: float, heli: HelicopterSettings) -> None:
    capacity = heli.capacity
    boarded = boarded_count(mission)

    lz_available = helicopter.grounded and helicopter.doors_open and boarded < capacity

    # Boarding radius around helicopter.
    load_radius = 58.0
    load_r2 = load_radius * load_radius

    # Hostage movement speed.
    speed = 42.0

    for h in mission.hostages:
        if h.state is HostageState.PANIC:
            h.state = HostageState.WAITING

        if h.state is HostageState.WAITING:
            if lz_available:
                # If close enough horizontally, start moving to LZ.
                if abs(h.pos.x - helicopter.pos.x) <= 240.0:
                    h.state = HostageState.MOVING_TO_LZ

        if h.state is HostageState.MOVING_TO_LZ:
            if not lz_available:
                h.state = HostageState.WAITING
                continue

            direction = -1.0 if h.pos.x > helicopter.pos.x else 1.0
            h.pos.x += direction * speed * dt

            # Snap to helicopter and board.
            dx = h.pos.x - helicopter.pos.x
            dy = h.pos.y - helicopter.pos.y
            if dx * dx + dy * dy <= load_r2:
                boarded = boarded_count(mission)
                if boarded < capacity:
                    h.state = HostageState.BOARDED
                    h.pos = Vec2(-9999.0, -9999.0)
                else:
                    h.state = HostageState.WAITING


def _handle_unload(mission: MissionState, helicopter: Helicopter, heli: HelicopterSettings) -> None:
    # Unload rule: must be grounded at base and doors open.
    if not helicopter.grounded or not helicopter.doors_open:
        return

    if not mission.base.contains_point(helicopter.pos):
        return

    for h in mission.hostages:
        if h.state is HostageState.BOARDED:
            h.state = HostageState.SAVED
            mission.stats.saved += 1


def hostage_crush_check(mission: MissionState, helicopter: Helicopter, last_landing_vy: float) -> None:
    # Called on a landing event. If the landing was hard and a hostage is under the helicopter, crush them.
    if mission.ended:
        return

    if abs(last_landing_vy) <= 1.5:
        return

    crush_radius = 28.0
    r2 = crush_radius * crush_radius

    for h in mission.hostages:
        if not on_foot(h):
            continue
        dx = h.pos.x - helicopter.pos.x
        dy = h.pos.y - helicopter.pos.y
        if dx * dx + dy * dy <= r2:
            h.state = HostageState.KIA
            mission.stats.kia_by_player += 1


def hostage_crush_check_logged(
    mission: MissionState,
    helicopter: Helicopter,
    last_landing_vy: float,
    logger: logging.Logger | None,
) -> None:
    before = mission.stats.kia_by_player
    hostage_crush_check(mission, helicopter, last_landing_vy)
    if logger is None:
        return
    if mission.stats.kia_by_player != before:
        logger.info("CRUSH: hard landing killed %d hostage(s)", mission.stats.kia_by_player - before)


def _log_progress_if_changed(mission: MissionState, logger: logging.Logger | None) -> None:
    if logger is None:
        return

    boarded = boarded_count(mission)
    if boarded != mission._last_logged_boarded:
        mission._last_logged_boarded = boarded
        logger.info("BOARDING: boarded=%d", boarded)

    if mission.stats.saved != mission._last_logged_saved:
        delta = mission.stats.saved - mission._last_logged_saved
        mission._last_logged_saved = mission.stats.saved
        logger.info("UNLOAD: +%d saved (total=%d)", delta, mission.stats.saved)

    if mission.stats.kia_by_player != mission._last_logged_kia_player:
        delta = mission.stats.kia_by_player - mission._last_logged_kia_player
        mission._last_logged_kia_player = mission.stats.kia_by_player
        logger.info("COLLATERAL: +%d KIA_by_player (total=%d)", delta, mission.stats.kia_by_player)


def _log_compound_health_if_needed(c: Compound, logger: logging.Logger | None, reason: str) -> None:
    if logger is None:
        return

    health = max(0.0, c.health)

    # Log only when health crosses buckets of 20 (avoids log spam).
    bucket = int(health // 20.0)
    if bucket == c.log_bucket:
        return

    c.log_bucket = bucket
    logger.info("Compound %s: x=%.0f health=%.0f", reason, c.pos.x, health)
