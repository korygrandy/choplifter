# LLM Handoff (Current Engineering State)

Last updated: 2026-03-07

This file is the canonical engineering handoff for future AI/dev sessions.

## Project Snapshot

- Runtime: Python 3.13 + Pygame 2.6.1
- Entry point: `run.py` -> `src.choplifter.main:run`
- Branch context: refactor follow-up on `feature/missile-flare-diversion` with packaging-doc sync and fresh onefile/onedir rebuild.

## What Is Implemented

- Playable rescue loop with mission selection, chopper selection, pause flow, mission end/debrief behavior.
- Weather/FX systems: rain, fog, dust, lightning, storm clouds.
- Intro and mission cutscene playback with skip support.
- Gamepad connect/disconnect support and menu/gameplay mappings.
- Accessibility toggles (particles, flashes, screenshake), plus configurable deadzone/trigger thresholds.
- Logging to per-user location with local fallback.

## Architecture (Post-Refactor)

### Main App Layer

- `src/choplifter/main.py`
  - Owns top-level game loop, mode transitions, rendering orchestration, and integration wiring.
- `src/choplifter/app/`
  - `keyboard_events.py`: keyboard event handling
  - `cutscenes.py`, `state.py`: intro/mission cutscene state and flow
  - `gamepads.py`, `input.py`: joystick lifecycle and readouts
  - `flow.py`, `session.py`: mission/chopper session setup and reset helpers
  - `feedback.py`, `toast.py`, `flares.py`, `doors.py`, `menu_helpers.py`: UI/gameplay support modules

### Mission Layer

- `src/choplifter/mission.py`
  - Compatibility surface and thin wrapper.
- Ownership moved to focused modules:
  - `mission_flow.py`: core mission update orchestration
  - `mission_state.py`: MissionState dataclass/object state
  - `mission_helpers.py`: helper utilities (`boarded_count`, etc.)
  - `mission_crash.py`: crash/death/respawn flow
  - `mission_hostages.py`: hostage movement/unload/crush logic
  - `mission_combat.py`: mission damage/combat helpers
  - `mission_compounds.py`: compounds/open/release logic
  - `mission_player_fire.py`: player projectile spawning
  - `mission_particles.py`: world particle updates
  - `mission_ending.py`: mission end/debrief logic

### Render Layer

- `src/choplifter/rendering.py` plus `src/choplifter/render/` split modules (`hud.py`, `world.py`, `particles.py`).

## Build + Packaging

- Build script: `scripts/build_windows_exe.ps1`
- Commands:
  - Onefile: `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_exe.ps1 -Mode onefile`
  - Onedir: `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_exe.ps1 -Mode onedir`
- Output:
  - `pyinstaller-dist/Choplifter.exe`
  - `pyinstaller-dist/Choplifter/Choplifter.exe`

### Current Build Size Reality

Onefile size is currently high due mostly to media and video/runtime dependencies.

Current measured baseline:
- `pyinstaller-dist/Choplifter.exe`: about `318.34 MB`
- `pyinstaller-dist/Choplifter/Choplifter.exe`: about `5.97 MB`
- `pyinstaller-dist/Choplifter/_internal`: about `427.77 MB`

Main contributors:
- `src/choplifter/assets/intro.mpg` (very large)
- `src/choplifter/assets/hostage-rescue-cutscene.mpg`
- bundled `imageio-ffmpeg` executable (about `83.58 MB`)
- large WAV assets

Current script behavior (`scripts/build_windows_exe.ps1`):
- Stages runtime assets into `pyinstaller-build/asset-staging` using explicit extension allow-list.
- Excludes non-runtime source assets (for example `.xcf`) from packaged output.
- Excludes legacy `.mpg` variants when same-path `.avi` variants exist.
- Still includes `imageio` / `imageio-ffmpeg` metadata by default.

## Recommended Next Engineering Steps

1. Optimize PNG/JPG assets losslessly and re-measure package outputs.
2. Add optional "lite media" packaging mode if distribution size needs major further reduction.
3. Convert heavy WAV effects to OGG where acceptable.
4. Keep the explicit asset-manifest staging approach and update docs when include rules change.

## Validation Commands

- Import smoke test:
  - `./.venv/Scripts/python.exe -c "from src.choplifter.main import run; print('import-ok')"`
- Run game:
  - `& "C:\dev\choplifter\choplifter\.venv\Scripts\python.exe" "C:\dev\choplifter\choplifter\run.py"`

## Current Work: Airport Special Ops Mission (In Progress)

### Branch: `feature/airport-special-ops-mission`

**Status:** Phase 1 integration complete - base structure and placeholders working

**What's Done:**
- Mission selection menu includes "Airport Special Ops"
- Mission config created in `mission_configs.py` with wider world (2800px), adjusted enemy timing
- Seven new module scaffolds created in `src/choplifter/`:
  - `bus_ai.py`, `hostage_logic.py`, `enemy_spawns.py`, `mission_tech.py`
  - `vehicle_assets.py`, `objective_manager.py`, `cutscene_manager.py`
- Integration into `main.py`:
  - Imports for all new modules (using `from .module import *`)
  - Placeholder state variables initialized after mission creation
  - Conditional update logic in fixed-step loop (currently just `pass` placeholder)
  - Conditional rendering: `draw_mission()` always runs, then airport placeholders drawn on top
- Placeholder shapes render at specific world coordinates (x=1200-1320):
  - Blue rectangle = bus, white circle = hostage, red triangle = enemy
  - Green square = tech, gold circle = objective, yellow star = cutscene trigger
- Base game fully functional: helicopter physics, enemies, projectiles, all working

**What's Not Done:**
- All module logic (bus AI, hostage boarding, enemy spawns, etc.) - just TODOs
- Actual vehicle sprites/assets
- Collision detection for bus
- Damage model for bus
- New enemy types (UAV, Merkava)
- Mission Tech repair mechanic
- Cutscene integration
- Objective tracking system

**Next Session Should:**
1. Pick one module to implement first (recommend `bus_ai.py` for visible progress)
2. Add basic bus movement along a path
3. Test collision with obstacles
4. Iterate on one feature at a time

**Testing:**
- Select "Airport Special Ops" from mission menu
- Fly helicopter to x=1200-1320 to see placeholders
- All base game features working (enemies, shooting, compounds, etc.)

## Notes for Future Refactors

- Keep `mission.py` compatibility exports stable while migrating internals.
- Prefer small extraction steps with immediate diagnostics and smoke tests.
- Avoid broad behavior changes during structural refactors.
- If changing controls or mode flow, update `README.md` and this file in the same change.
- Airport mission modules use wildcard imports (`from .module import *`) - may need cleanup later.
