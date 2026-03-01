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
    ENEMY_BULLET = 3


@dataclass
class Projectile:
    kind: ProjectileKind
    pos: Vec2
    vel: Vec2
    ttl: float
    alive: bool = True


class EnemyKind(Enum):
    TANK = 1
    JET = 2
    AIR_MINE = 3


@dataclass
class Enemy:
    kind: EnemyKind
    pos: Vec2
    vel: Vec2
    health: float
    cooldown: float = 0.0
    ttl: float = 999.0
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
    enemies: list[Enemy]
    base: BaseZone
    stats: MissionStats
    ended: bool = False
    end_text: str = ""
    end_reason: str = ""
    crashes: int = 0
    invuln_seconds: float = 0.0
    jet_spawn_seconds: float = 4.0
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

        enemies: list[Enemy] = []
        # Place a tank near each compound to create landing pressure.
        for c in compounds:
            enemies.append(
                Enemy(
                    kind=EnemyKind.TANK,
                    pos=Vec2(c.pos.x + c.width * 0.5, heli.ground_y - 8.0),
                    vel=Vec2(0.0, 0.0),
                    health=110.0,
                    cooldown=1.5,
                )
            )

        # One air mine early to demo the archetype.
        enemies.append(
            Enemy(
                kind=EnemyKind.AIR_MINE,
                pos=Vec2(520.0, 180.0),
                vel=Vec2(0.0, 0.0),
                health=1.0,
            )
        )

        return MissionState(
            compounds=compounds,
            hostages=hostages,
            projectiles=[],
            enemies=enemies,
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

    if mission.invuln_seconds > 0.0:
        mission.invuln_seconds = max(0.0, mission.invuln_seconds - dt)

    _update_fuel(mission, helicopter, dt, logger)
    if helicopter.fuel <= 0.0:
        _end_mission(mission, "THE END", "OUT OF FUEL", logger)
        return

    _update_enemies(mission, helicopter, dt, heli, logger)

    _update_projectiles(mission, dt, heli, logger, helicopter)
    _update_compounds_and_release(mission, heli, logger)
    _update_hostages(mission, helicopter, dt, heli)
    _handle_unload(mission, helicopter, heli)

    _handle_crash_and_respawn(mission, helicopter, heli, logger)
    if mission.ended:
        return

    _log_progress_if_changed(mission, logger)

    if mission.stats.saved >= 20:
        _end_mission(mission, "THE END", "RESCUE SUCCESS", logger)


def _update_projectiles(
    mission: MissionState,
    dt: float,
    heli: HelicopterSettings,
    logger: logging.Logger | None,
    helicopter: Helicopter,
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

        # Enemy collision (player projectiles only).
        if p.kind in (ProjectileKind.BULLET, ProjectileKind.BOMB):
            for e in mission.enemies:
                if not e.alive:
                    continue
                if _projectile_hits_enemy(p, e, heli):
                    if p.kind is ProjectileKind.BULLET:
                        e.health -= 10.0
                    else:
                        e.health -= 40.0
                    if e.health <= 0.0:
                        e.alive = False
                        if logger is not None:
                            logger.info("ENEMY_DOWN: %s", e.kind.name)
                    p.alive = False
                    break

        if not p.alive:
            continue

        # Helicopter collision (enemy projectiles only).
        if p.kind is ProjectileKind.ENEMY_BULLET:
            if _hits_circle(p.pos, helicopter.pos, radius=26.0):
                _damage_helicopter(mission, helicopter, 10.0, logger, source="ENEMY_BULLET")
                p.alive = False
                continue

        # Ground collision.
        if p.pos.y >= heli.ground_y - 6.0:
            if p.kind is ProjectileKind.BOMB:
                _bomb_explode(mission, p.pos, logger)
            p.alive = False
            continue

        # Compound collision (player projectiles only).
        for c in mission.compounds:
            if c.health <= 0:
                continue
            if c.contains_point(p.pos):
                if p.kind is ProjectileKind.BULLET:
                    c.health -= 12.0
                elif p.kind is ProjectileKind.BOMB:
                    c.health -= 40.0
                else:
                    continue
                _log_compound_health_if_needed(c, logger, reason="hit")
                p.alive = False
                break

        if not p.alive:
            continue

        # Hostage hits.
        for h in mission.hostages:
            if not on_foot(h):
                continue
            dx = h.pos.x - p.pos.x
            dy = h.pos.y - p.pos.y
            if dx * dx + dy * dy <= 12.0 * 12.0:
                h.state = HostageState.KIA
                if p.kind is ProjectileKind.ENEMY_BULLET:
                    mission.stats.kia_by_enemy += 1
                else:
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

    for e in mission.enemies:
        if not e.alive:
            continue
        dx = e.pos.x - pos.x
        dy = e.pos.y - pos.y
        if dx * dx + dy * dy <= r2:
            e.health -= 55.0
            if e.health <= 0.0:
                e.alive = False
                if logger is not None:
                    logger.info("ENEMY_DOWN: %s", e.kind.name)


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


def _update_fuel(mission: MissionState, helicopter: Helicopter, dt: float, logger: logging.Logger | None) -> None:
    if mission.ended:
        return

    # Minimal MVP-lite: fuel drains over time, refuels at base.
    drain_per_s = 1.0
    refuel_per_s = 18.0

    at_base = mission.base.contains_point(helicopter.pos) and helicopter.grounded
    if at_base:
        helicopter.fuel = min(100.0, helicopter.fuel + refuel_per_s * dt)
    else:
        helicopter.fuel = max(0.0, helicopter.fuel - drain_per_s * dt)

    if logger is not None:
        fuel_int = int(helicopter.fuel)
        if fuel_int in (75, 50, 25, 10, 5, 0):
            logger.info("FUEL: %d", fuel_int)


def _update_enemies(
    mission: MissionState,
    helicopter: Helicopter,
    dt: float,
    heli: HelicopterSettings,
    logger: logging.Logger | None,
) -> None:
    # Periodic jet spawns.
    mission.jet_spawn_seconds -= dt
    if mission.jet_spawn_seconds <= 0.0:
        mission.jet_spawn_seconds = 6.5
        y = 150.0
        if helicopter.pos.x > 640.0:
            x = -80.0
            vx = 280.0
        else:
            x = 1280.0 + 80.0
            vx = -280.0
        mission.enemies.append(
            Enemy(kind=EnemyKind.JET, pos=Vec2(x, y), vel=Vec2(vx, 0.0), health=30.0, cooldown=0.6, ttl=6.0)
        )
        if logger is not None:
            logger.info("JET: spawned")

    for e in mission.enemies:
        if not e.alive:
            continue

        e.ttl -= dt
        if e.ttl <= 0.0:
            e.alive = False
            continue

        e.cooldown = max(0.0, e.cooldown - dt)

        if e.kind is EnemyKind.TANK:
            dx = helicopter.pos.x - e.pos.x
            if abs(dx) <= 360.0 and helicopter.pos.y <= heli.ground_y - 40.0 and e.cooldown <= 0.0:
                e.cooldown = 1.25
                _spawn_enemy_bullet_toward(mission, e.pos, helicopter.pos)
                if logger is not None:
                    logger.info("TANK_FIRE")

        elif e.kind is EnemyKind.JET:
            e.pos.x += e.vel.x * dt
            e.pos.y += e.vel.y * dt

            if abs(helicopter.pos.x - e.pos.x) <= 240.0 and e.cooldown <= 0.0:
                e.cooldown = 0.35
                _spawn_enemy_bullet_toward(mission, e.pos, helicopter.pos)

            if _hits_circle(e.pos, helicopter.pos, radius=30.0):
                _damage_helicopter(mission, helicopter, 22.0, logger, source="JET")

        elif e.kind is EnemyKind.AIR_MINE:
            to_heli = Vec2(helicopter.pos.x - e.pos.x, helicopter.pos.y - e.pos.y)
            dist = math.hypot(to_heli.x, to_heli.y)
            if dist > 0.001:
                nx = to_heli.x / dist
                ny = to_heli.y / dist
            else:
                nx, ny = 0.0, 0.0

            desired_speed = 120.0
            desired_vx = nx * desired_speed
            desired_vy = ny * desired_speed
            steer = 3.5
            e.vel.x += (desired_vx - e.vel.x) * steer * dt
            e.vel.y += (desired_vy - e.vel.y) * steer * dt

            e.pos.x += e.vel.x * dt
            e.pos.y += e.vel.y * dt

            if _hits_circle(e.pos, helicopter.pos, radius=26.0):
                _mine_explode(mission, e.pos, helicopter, logger)
                e.alive = False

    mission.enemies = [e for e in mission.enemies if e.alive]


def _mine_explode(
    mission: MissionState,
    pos: Vec2,
    helicopter: Helicopter,
    logger: logging.Logger | None,
) -> None:
    if logger is not None:
        logger.info("MINE: detonate")

    _damage_helicopter(mission, helicopter, 28.0, logger, source="AIR_MINE")

    radius = 40.0
    r2 = radius * radius
    for h in mission.hostages:
        if not on_foot(h):
            continue
        dx = h.pos.x - pos.x
        dy = h.pos.y - pos.y
        if dx * dx + dy * dy <= r2:
            h.state = HostageState.KIA
            mission.stats.kia_by_enemy += 1


def _spawn_enemy_bullet_toward(mission: MissionState, start: Vec2, target: Vec2) -> None:
    dx = target.x - start.x
    dy = target.y - start.y
    dist = math.hypot(dx, dy)
    if dist <= 0.001:
        dist = 1.0
    speed = 140.0
    vx = (dx / dist) * speed
    vy = (dy / dist) * speed
    mission.projectiles.append(
        Projectile(kind=ProjectileKind.ENEMY_BULLET, pos=Vec2(start.x, start.y - 10.0), vel=Vec2(vx, vy), ttl=2.0)
    )


def _hits_circle(a: Vec2, b: Vec2, radius: float) -> bool:
    dx = a.x - b.x
    dy = a.y - b.y
    return dx * dx + dy * dy <= radius * radius


def _projectile_hits_enemy(p: Projectile, e: Enemy, heli: HelicopterSettings) -> bool:
    if e.kind is EnemyKind.TANK:
        w, h = 44.0, 18.0
        left = e.pos.x - w * 0.5
        top = heli.ground_y - h
        return left <= p.pos.x <= left + w and top <= p.pos.y <= top + h

    if e.kind is EnemyKind.JET:
        return _hits_circle(p.pos, e.pos, radius=20.0)

    if e.kind is EnemyKind.AIR_MINE:
        return _hits_circle(p.pos, e.pos, radius=14.0)

    return False


def _damage_helicopter(
    mission: MissionState,
    helicopter: Helicopter,
    amount: float,
    logger: logging.Logger | None,
    source: str,
) -> None:
    if mission.invuln_seconds > 0.0 or mission.ended:
        return

    before = helicopter.damage
    helicopter.damage = min(100.0, helicopter.damage + amount)
    if logger is not None and int(before) != int(helicopter.damage):
        logger.info("HIT: %s damage=%.0f", source, helicopter.damage)


def _handle_crash_and_respawn(
    mission: MissionState,
    helicopter: Helicopter,
    heli: HelicopterSettings,
    logger: logging.Logger | None,
) -> None:
    if mission.ended:
        return
    if helicopter.damage < 100.0:
        return

    mission.crashes += 1
    if logger is not None:
        logger.info("CRASH: count=%d", mission.crashes)

    if mission.crashes >= 3:
        _end_mission(mission, "THE END", "AIRCRAFT LOST", logger)
        return

    helicopter.damage = 0.0
    helicopter.fuel = max(0.0, helicopter.fuel - 20.0)
    helicopter.vel = Vec2(0.0, 0.0)
    helicopter.tilt_deg = 0.0
    helicopter.doors_open = False
    helicopter.facing = Facing.RIGHT
    helicopter.pos = Vec2(mission.base.pos.x + mission.base.width * 0.5, heli.ground_y - 120.0)
    mission.invuln_seconds = 2.0

    if logger is not None:
        logger.info("RESPAWN: invuln=%.1fs fuel=%.0f", mission.invuln_seconds, helicopter.fuel)


def _end_mission(mission: MissionState, end_text: str, reason: str, logger: logging.Logger | None) -> None:
    if mission.ended:
        return

    mission.ended = True
    mission.end_text = end_text
    mission.end_reason = reason

    if logger is not None:
        logger.info("END: %s", reason)
        logger.info(
            "END_STATS: saved=%d boarded=%d kia_by_player=%d kia_by_enemy=%d crashes=%d",
            mission.stats.saved,
            boarded_count(mission),
            mission.stats.kia_by_player,
            mission.stats.kia_by_enemy,
            mission.crashes,
        )
