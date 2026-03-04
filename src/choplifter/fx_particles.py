from __future__ import annotations

"""Compatibility facade for FX particle systems.

Phase 2 refactor: the implementations live in the `choplifter.fx` package.
This module re-exports the original symbols so existing imports keep working.
"""

from .fx.particles import FxParticle
from .fx.impact_sparks import ImpactSparkSystem
from .fx.flares import FlareSystem
from .fx.jet_trails import JetTrailSystem
from .fx.dust_storm import DustStormSystem
from .fx.helicopter_damage_fx import HelicopterDamageFxSystem
from .fx.explosions import ExplosionSystem

__all__ = [
    "FxParticle",
    "ImpactSparkSystem",
    "FlareSystem",
    "JetTrailSystem",
    "DustStormSystem",
    "HelicopterDamageFxSystem",
    "ExplosionSystem",
]
