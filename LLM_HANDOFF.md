# LLM Handoff (Current Engineering State)

Last updated: 2026-03-11

This file is the canonical engineering handoff for future AI/dev sessions.

## Project Snapshot

- Runtime: Python 3.13 + Pygame 2.6.1
- Entry point: `run.py` -> `src.choplifter.main:run`
- Branch context: active gameplay + mission iteration on `feature/airport-special-ops-mission`.

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
  - `& .\.venv\Scripts\python.exe .\run.py`

### Automated Airport Smoke Workflow

- Smoke suite marker is registered in `pytest.ini` as `airport_smoke`.
- One-command runner script: `scripts/run_airport_smoke.ps1`.
- Playtest guide and smoke report template: `docs/AIRPORT_MISSION_PLAYTEST_GUIDE.md`.

Primary command:

- `powershell -ExecutionPolicy Bypass -File .\scripts\run_airport_smoke.ps1`

Optional verbose command:

- `powershell -ExecutionPolicy Bypass -File .\scripts\run_airport_smoke.ps1 -VerboseOutput`

Direct pytest equivalent:

- `.\.venv\Scripts\python.exe -m pytest -q -m airport_smoke`

Expected behavior:

- Runs the curated airport mission smoke subset only.
- Prints `Airport smoke suite passed.` on success.
- Returns non-zero exit code on failure (CI-friendly gating).

Current baseline (as of this handoff update):

- `29 passed, 75 deselected`.

Recommended usage per cycle:

1. Run automated smoke suite before manual playtest.
2. If green, run 10-minute manual smoke in `docs/AIRPORT_MISSION_PLAYTEST_GUIDE.md`.
3. Submit smoke-pass report using the command card template.

## Current Work: Airport Special Ops Mission

### Branch: `feature/airport-special-ops-mission`

**Status:** Implemented and playable with split rescue paths.

### Current Gameplay Truth (Supersedes Older Notes)

1. Airport mission rescue target is a combined total of `16` civilians per run.
2. Civilian allocation is randomized on mission start/reset between:
   - lower terminal compounds (rescued by normal helicopter loop)
   - elevated jetway compound (rescued by meal-truck -> bus -> LZ transfer)
3. Lower-level civilians can only be rescued via chopper compound workflow.
4. Elevated civilians are tracked by airport hostage state and require truck/bus transfer.
5. Airport mission success is based on combined rescued total reaching `16`.
6. Generic mission auto-win (`saved >= 20`) is disabled for airport missions.
7. Passenger presentation has been shifted toward animated stick-figure visuals.

### Player Flow (Current)

1. Deploy Mission Tech from chopper to meal truck near truck position.
2. Use truck to extract elevated jetway civilians.
3. Transfer elevated civilians from truck to bus, then escort bus to LZ stop.
4. Independently open lower compounds and rescue lower-level civilians via chopper.
5. Mission ends in success when lower + elevated rescued total reaches 16.

### Airport Modules With Active Ownership

- `src/choplifter/main.py`: airport setup/reset distribution logic, mission-end aggregation.
- `src/choplifter/hostage_logic.py`: elevated-hostage flow, transfer state, airport passenger rendering.
- `src/choplifter/mission_tech.py`: tech lifecycle and transfer completion gating.
- `src/choplifter/objective_manager.py`: objective phase labels/status progression.
- `src/choplifter/render/world.py`: airport scene, terminals, tower, on-foot passenger rendering.

### Verification Commands Used

- Import smoke test:
  - `./.venv/Scripts/python.exe -c "from src.choplifter.main import run; print('import-ok')"`
- Run game:
  - `& .\.venv\Scripts\python.exe .\run.py`

### Notes

- Legacy design notes below are preserved for context, but the "Current Gameplay Truth" section above is authoritative.

**Mission Flow (Redesigned):**

1. **Mission Start:**
   - Helicopter starts WITH Mission Tech engineer on board
   - Visual indicator above chopper (wrench or colored symbol) shows tech is on board
   - Bus starts on right side, begins driving LEFT
   - Yellow diamond indicator above bus shows it's the objective

2. **Tech Deployment:**
   - Player lands chopper near meal truck (parked at start position)
   - Opens doors (E key / A button)
   - Tech EXITS chopper, ENTERS meal truck
   - Indicator disappears from chopper, appears on meal truck
   - Chopper is now free to move and defend

3. **Meal Truck Extraction Phase:**
   - Tech drives meal truck to elevated jetway (second-to-last bunker, x=~1232)
   - Jetway floor is elevated to match bottom of airport-meal-cart-box.png
   - When truck reaches extraction LZ:
     - Box extension animation begins:
       - `airport-meal-cart-box.png` moves UP 53 pixels (animated)
       - Simultaneously, `airport-meal-cart-extended.png` fades IN
       - Both complete at same time
     - Once fully extended, hostages board the meal truck
     - Passenger indicators render on truck (at position 31, 21 when extended)
   
4. **Box Retraction:**
   - Once all available hostages board:
     - `airport-meal-cart-extended.png` fades OUT
     - `airport-meal-cart-box.png` moves DOWN 53 pixels
     - Returns to base `airport-meal-cart.png` sprite
     - Passenger indicators persist, move down with box (render at position 31, 74 when retracted)

5. **Transfer to Bus:**
   - Meal truck drives LEFT to rendezvous with bus
   - Bus has already driven past rescue operation
   - When truck reaches bus vicinity:
     - Bus stops, doors open (new sprite: `city-bus-doors-open.png`)
     - Passengers transfer from meal truck to bus
     - Passenger indicators update to show on bus

6. **Escort Phase:**
   - Once passengers are on bus, it becomes vulnerable to enemy attacks
   - Player must defend bus from UAV drones, enemy fire, etc.
   - Bus takes damage from enemy projectiles (and friendly fire from player)
   - Bus drives to safe LZ on RIGHT side of screen

7. **Mission Success:**
   - If bus reaches safe LZ with passengers alive: SUCCESS
   - If bus is destroyed or all passengers KIA: FAILURE

**What's Done:**
- Mission selection menu includes "Airport Special Ops"
- Mission config created in `mission_configs.py` with wider world (2800px), adjusted enemy timing
- Seven new module scaffolds created in `src/choplifter/`:
  - `bus_ai.py`, `hostage_logic.py`, `enemy_spawns.py`, `mission_tech.py`
  - `vehicle_assets.py`, `objective_manager.py`, `cutscene_manager.py`
- Integration into `main.py` for all airport objects
- Basic bus AI (drives left, stops for obstacles)
- Enemy spawns (UAV drones with weaving/dive behavior)
- Friendly fire detection on bus
- Objective tracking with timer
- UAV enemy type implemented

**What Needs Refactoring (New Design):**
- Mission Tech state machine (currently deploys when grounded near bus, needs to track: on_chopper → deployed_to_truck → driving → extracting → transferring → returned)
- Meal truck animation system (box extension/retraction with 53px movement + sprite fade)
- Passenger indicator positioning (must move with box: 31,21 extended / 31,74 retracted)
- Tech visual indicators (wrench/symbol above chopper when tech on board, above truck when deployed)
- Bus doors sprite system (add `city-bus-doors-open.png` sprite)
- Transfer LZ detection (meal truck proximity to bus)
- Mission phases (tech_deployment → extraction → transfer → escort → success/failure)

**Next Session Should:**
1. Refactor `mission_tech.py` to track tech state (on_chopper → in_truck → returned)
2. Update `vehicle_assets.py` for box animation (53px movement + fade)
3. Add passenger indicator positioning logic (moves with box)
4. Implement transfer LZ detection and bus door opening
5. Update objective phases to match new flow
6. Add tech visual indicators (wrench above chopper/truck)

**Testing:**
- Select "Airport Special Ops" from mission menu
- Land near meal truck, open doors (E / A button)
- Verify tech exits chopper, enters truck
- Watch meal truck drive to jetway
- Verify box extends 53px with fade animation
- Verify hostages board and indicators render at 31,21
- Verify box retracts with indicators moving to 31,74
- Verify truck drives to bus and transfer occurs
- Verify escort phase begins and bus can be defended

## Notes for Future Refactors

- Keep `mission.py` compatibility exports stable while migrating internals.
- Prefer small extraction steps with immediate diagnostics and smoke tests.
- Avoid broad behavior changes during structural refactors.
- If changing controls or mode flow, update `README.md` and this file in the same change.
- Airport mission modules use wildcard imports (`from .module import *`) - may need cleanup later.
