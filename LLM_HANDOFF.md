# LLM Handoff (Current Engineering State)

Last updated: 2026-03-06

This file is the canonical engineering handoff for future AI/dev sessions.

## Project Snapshot

- Runtime: Python 3.13 + Pygame 2.6.1
- Entry point: `run.py` -> `src.choplifter.main:run`
- Branch context: refactor work merged, final cleanup completed, fresh onefile/onedir Windows builds generated.

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

Onefile size is currently high (roughly 300MB+) due mostly to media and video/runtime dependencies.

Main contributors:
- `src/choplifter/assets/intro.mpg` (very large)
- `src/choplifter/assets/hostage-rescue-cutscene.mpg`
- bundled `imageio-ffmpeg` executable
- large WAV assets

## Recommended Next Engineering Steps

1. Re-encode intro/cutscene media to compressed MP4.
2. Add optional "lite media" packaging mode (skip video dependencies, use cutscene fallback path).
3. Convert heavy WAV effects to OGG where acceptable.
4. Use explicit asset include lists to avoid shipping non-runtime source assets.

## Validation Commands

- Import smoke test:
  - `./.venv/Scripts/python.exe -c "from src.choplifter.main import run; print('import-ok')"`
- Run game:
  - `./.venv/Scripts/python.exe run.py`

## Notes for Future Refactors

- Keep `mission.py` compatibility exports stable while migrating internals.
- Prefer small extraction steps with immediate diagnostics and smoke tests.
- Avoid broad behavior changes during structural refactors.
- If changing controls or mode flow, update `README.md` and this file in the same change.
