# Planned Mission: Airport Special Ops

<!-- markdownlint-disable -->




## Fuselage Layering Workplan (2026-03-13)

- [x] Remove the fuselage terminal D4 label from the first elevated compound.
- [x] Render `airplane-backdrop.png` behind the fuselage compound.
- [ ] Tune backdrop placement offsets to align with compound position during playtest.
- [x] Reskin fuselage compound to a black square silhouette.
- [x] Add two-stage fuselage damage sequence rendering:
  - stage 1 asset: `plan-fuselage-half-damaged.png`
  - stage 2 asset: `plane-fuselage-totally-amaged.png`
- [x] Add fuselage damage particle animation hooks for each stage transition.
- [x] Gate meal-cart passenger boarding until fuselage damage stage 2 is complete.
- [x] Add/adjust tests for damage-stage progression and boarding gate behavior.

## Audit Update (2026-03-10)

This file contains legacy planning notes and backlog items. The current implemented airport gameplay is:

- Airport mission uses a combined rescue target of `16` civilians.

- Civilians are randomized per mission start/reset between:
  - lower terminals (helicopter rescue flow)
  - elevated jetway (meal-truck -> bus transfer flow)

- Lower-level hostages are not part of airport truck/bus transfer.

- Elevated hostages are not rescued directly by chopper; they require truck/bus pipeline.

- Airport mission success uses combined lower + elevated rescued totals (not generic saved>=20).

- Passenger visuals are moving to animated stick-figure representation across mission contexts.

Use `LLM_HANDOFF.md` as the canonical implementation snapshot. Treat the sections below as historical planning/backlog unless explicitly marked complete.

## Open Airport TODOs (Active)

This is the active Airport Special Ops checklist. If an item here conflicts with legacy notes below, this section wins.

### Engineering Status (2026-03-12)

- Main-loop context refactor was stabilized after sync-order and stale-accumulator rollback fixes in `src/choplifter/main.py`.
- Airport mission bleed/artifact contamination caused by context overwrite timing has been addressed.
- Vehicle input/gating orchestration moved out of `main.py` into `src/choplifter/app/driver_inputs.py` as part of continued modularization.
- Keyboard/gamepad event-result state assignment boilerplate moved out of `main.py` into `src/choplifter/app/loop_state_updates.py`.
- Main-loop context load/store code moved out of `main.py` into `src/choplifter/app/main_loop_context_sync.py`.
- Weather runtime assignment/toast application moved out of `main.py` into `src/choplifter/app/frame_update.py` via `apply_weather_runtime_update(...)`.
- Mode-transition side effects and camera result application moved out of `main.py` into helper functions in `src/choplifter/app/mode_update.py` and `src/choplifter/app/frame_update.py`.
- Gamepad snapshot and previous menu-axis sync moved out of `main.py` into `src/choplifter/app/gamepad_state_sync.py`.
- Post-input mode adjustment logic (cutscene fallback + deferred city satellite SFX trigger) moved out of `main.py` into `src/choplifter/app/loop_mode_adjustments.py`.
- VIP overlay state assignment and frame render preparation blocks moved out of `main.py` into helpers in `src/choplifter/app/frame_update.py`.
- Shared world render branch orchestration moved out of `main.py` into `src/choplifter/app/frame_render.py` via `render_world_branch(...)` while preserving draw order.
- Intro/cutscene/world frame render dispatch moved out of `main.py` into `src/choplifter/app/frame_render.py` via `render_mode_frame(...)`.
- Main-loop render call-site argument bundle was reduced by adding `render_mode_frame_from_runtime(...)` in `src/choplifter/app/frame_render.py`.
- Main-loop pygame event routing block was moved out of `main.py` into `src/choplifter/app/event_loop.py` via `process_pygame_events(...)`.
- Active gamepad per-frame mode-routing block was moved out of `main.py` into `src/choplifter/app/gamepad_frame_flow.py` via `process_active_gamepad_frame(...)`.
- Keyboard polling + active-gamepad snapshot acquisition were moved out of `main.py` into `src/choplifter/app/frame_inputs.py` via `read_frame_input_snapshot(...)`.
- Fixed-step preamble setup (context reload, input assembly, runtime sync, accumulator clamp) was moved out of `main.py` into `src/choplifter/app/fixed_step_preamble.py` via `prepare_fixed_step_preamble(...)`.
- Playing fixed-step iteration + airport per-tick update wiring were moved out of `main.py` into `src/choplifter/app/fixed_step_iteration.py` via `run_playing_fixed_step_iteration(...)`.
- Post-fixed-step phase (toast tick, mode transition, frame prep/render, display flip, context persist) was moved out of `main.py` into `src/choplifter/app/post_fixed_step_phase.py` via `run_post_fixed_step_phase(...)`.
- Accumulator-driven fixed-step loop control was moved out of `main.py` into `src/choplifter/app/fixed_step_loop.py` via `run_fixed_step_loop(...)`.
- Mission preview/reset wrapper bodies were moved out of `main.py` into `src/choplifter/app/setup_wrappers.py` via `apply_mission_preview_to_context(...)` and `reset_game_to_context(...)`.
- Startup initialization and initial menu/runtime setup were moved out of `main.py` into `src/choplifter/app/run_bootstrap.py` via `initialize_run_bootstrap(...)`.
- Final app-exit cleanup was moved out of `main.py` into `src/choplifter/app/run_shutdown.py` via `finalize_run_shutdown(...)`.
- Initial mission/session context assembly was moved out of `main.py` into `src/choplifter/app/session.py` via `initialize_main_loop_context(...)`.
- Frame-start VIP/weather bookkeeping and skip-hint generation were moved out of `main.py` into `src/choplifter/app/frame_update.py` via `run_frame_preamble(...)`.
- Joypad startup regression (`NameError` on `handle_joy_device_added`) was fixed by restoring missing imports in `src/choplifter/app/event_loop.py`.
- P0 perf work completed: duplicate rain/fog/dust/lightning simulation was removed from render-prep path so weather sim runs once per frame.
- P0 perf work completed: frame-phase timing instrumentation + debug perf counters were added (main-loop EMA + debug overlay display).
- P1 perf work completed: transformed sprite caching was added for helicopter rotate/flip variants and meal-truck facing flips to reduce per-frame transform overhead.
- P1 perf work completed: temporary-surface reuse was extended across `render/overlays.py`, `render/hud.py`, `debug_overlay.py`, `render/helicopter.py`, and `render/world.py`, including volatile-surface clearing to prevent alpha/smoke persistence artifacts.
- P1 perf work completed: draw culling was added in `render/world.py` for hostages, projectiles, enemies, compounds, and the airport tower to skip off-screen composition work.
- P1 perf work completed: world-render font caching was added for repeated placard/LZ/end-screen text to avoid per-frame `SysFont(...)` recreation.

### Gameplay Validation (Highest Priority)

- [ ] Run full airport playtest matrix in `docs/AIRPORT_MISSION_PLAYTEST_GUIDE.md`.

- [ ] Submit smoke-pass report each cycle using the command card in `docs/AIRPORT_MISSION_PLAYTEST_GUIDE.md`.

- [ ] Validate no soft-locks across: tech deploy -> elevated extraction -> transfer -> bus LZ -> tech reboard -> lower rescue continuation.

- [ ] Verify keyboard and gamepad parity for door interactions and mission progression.

- [ ] Re-verify failure paths: bus destroyed, all passengers lost, deadline expiration.

### Performance Refactor Backlog (CPU/GPU)

- [x] `P0` Remove duplicate weather simulation updates per frame.
  - Current risk: weather systems are advanced in both frame preamble and frame render preparation.
  - Scope:
    - Keep weather simulation in one phase only (preferred: frame preamble / gameplay-time path).
    - Convert later phase to render-only consumption of already-updated weather state.
  - Targets:
    - `src/choplifter/app/frame_update.py`
    - `src/choplifter/app/post_fixed_step_phase.py`
  - Done criteria:
    - Rain/fog/dust/lightning each update at most once per frame in normal gameplay loop.
    - No weather behavior regressions in airport smoke and visual sanity check.

- [x] `P0` Add frame-phase timing instrumentation and lightweight perf HUD counters.
  - Scope:
    - Track ms per phase: event dispatch, input/gamepad, fixed-step, frame preamble, render prep, draw/present.
    - Log moving averages and expose in debug overlay only.
  - Targets:
    - `src/choplifter/main.py`
    - `src/choplifter/debug_overlay.py`
    - `src/choplifter/app/post_fixed_step_phase.py`
  - Done criteria:
    - Debug overlay shows stable rolling averages.
    - Baseline profile captured and attached to handoff notes.

- [x] `P1` Cache transformed helicopter/vehicle sprites (flip/rotate) with bounded memory.
  - Scope:
    - Add quantized-angle cache for rotated helicopter sprites.
    - Cache facing variants for frequently flipped vehicle assets.
    - Use LRU or size cap to avoid unbounded growth.
  - Targets:
    - `src/choplifter/render/helicopter.py`
    - `src/choplifter/vehicle_assets.py`
  - Done criteria:
    - Significant reduction in per-frame `pygame.transform.rotate/flip` calls.
    - No visual drift/artifact across facing and roll transitions.

- [x] `P1` Reduce per-frame temporary surface allocations in hot render paths.
  - Scope:
    - Reuse alpha panels/overlays where dimensions are stable.
    - Replace repeated `pygame.Surface(...)` construction with cached buffers.
  - Targets:
    - `src/choplifter/render/hud.py`
    - `src/choplifter/render/overlays.py`
    - `src/choplifter/render/particles.py`
    - `src/choplifter/debug_overlay.py`
    - `src/choplifter/render/helicopter.py`
    - `src/choplifter/render/world.py`
  - Done criteria:
    - Fewer transient allocations in profile snapshots.
    - No UI layering or alpha-blend regressions.
  - Status:
    - Completed with bounded scratch/overlay caches, reusable volatile surfaces in world rendering, cached helicopter door panels, and a follow-up fix to clear reused volatile surfaces before draw.

- [x] `P1` Add draw culling for off-screen entities/effects before expensive composition.
  - Scope:
    - Introduce shared viewport visibility helper.
    - Skip transform/composite work when object bounds are outside camera view + padding.
  - Targets:
    - `src/choplifter/render/world.py`
    - `src/choplifter/app/frame_render.py`
  - Done criteria:
    - Reduced draw-call count in dense scenes.
    - No pop-in for fast-moving entities at screen edges.
  - Status:
    - Completed in `src/choplifter/render/world.py` via shared `_is_on_screen(...)` culling for hostages, projectiles, enemies, compounds, and the airport tower; no additional `frame_render.py` culling was required for closure.

- [ ] `P2` Add adaptive particle quality budget tied to frame time.
  - Scope:
    - Lower spawn/update density when moving-average frame time exceeds budget.
    - Restore full quality automatically when frame time recovers.
  - Targets:
    - `src/choplifter/mission_particles.py`
    - `src/choplifter/render/particles.py`
    - `src/choplifter/sky_smoke.py`
  - Done criteria:
    - Noticeably smoother frame pacing under heavy effects.
    - Effect readability preserved at reduced quality.

- [ ] `P2` Split cosmetic-only update cadence from gameplay-critical updates.
  - Scope:
    - Keep mission/physics logic on fixed-step.
    - Optionally throttle non-critical cosmetic updates (selected weather layers, decorative overlays).
  - Targets:
    - `src/choplifter/app/frame_update.py`
    - `src/choplifter/fx/storm_clouds.py`
  - Done criteria:
    - Lower CPU time in heavy scenes without changing gameplay outcomes.
    - Deterministic mission behavior maintained.

### Airport Pivot: Dual Elevated Compounds (Risk-First)

- [ ] `P0` Add second elevated extraction compound (`elevated_fuselage_passenger_compound`) on the left side with parity behavior to the existing `elevated_jetway_passenger_compound`.

- [ ] `P0` Update elevated passenger allocation to distribute civilians across both elevated compounds at mission start/reset (not a single elevated pickup point).

- [ ] `P0` Update mission-tech and meal-truck extraction sequencing so both elevated compounds can be serviced without soft-locks:
  - pickup targeting/order for terminal A/B
  - truck loading/retraction/transferring loops per terminal
  - completion gate only after both elevated compounds are emptied.

- [ ] `P0` Expand objective/event flow text and state progression to explicitly handle dual elevated extraction before transfer completion.

- [ ] `P0` Add regression tests for dual elevated flow (distribution, terminal switching, transfer completion, rescue aggregation, and interruption/reboard paths).

- [ ] `P1` Add burning plane fuselage visual set and overlay composition under the new raised left elevated compound (layering + collision/readability validation).

- [ ] `P1` Add elevated compound window flicker when passengers are present (both `fuselage` and `jetway` compounds) with reduced/disabled flicker when empty.

- [ ] `P1` Update airport cutscene markers and mission prompts to identify the active elevated compound (`fuselage` vs `jetway`) and avoid ambiguous routing.

- [ ] `P1` Add playtest matrix rows for two-elevated-compound scenarios, including edge timing and recovery from interrupted extraction.

- [ ] `P2` Replace procedural indicator icons with PNG assets in prioritized order (objective marker, pickup marker, truck/bus passenger marker, mission-tech markers).

- [ ] `P2` Replace the ground-moving red chevron placeholder (current raider triangle renderer in `src/choplifter/enemy_spawns.py`) with a dedicated PNG sprite + fallback draw path.

### Immediate Bug Fixes (Priority Order)

- [x] `P0` Barak missile overlap-hit bug: when chopper and bus overlap, missiles currently miss both targets.
  - Expected rule: if player is controlling helicopter flight (not driving truck/bus), Barak missiles always prioritize chopper collision.
  - If player is driving a ground vehicle, use normal target selection and allow bus hits.
  - Add deterministic tests for overlap and non-overlap cases.

- [x] `P1` Chopper select -> mission select navigation: `Esc` should return to mission select UI.
  - Add keyboard regression test for this UI transition.

- [x] `P1` End-game screen: pause button should open/toggle pause menu, including quit path.
  - Verify keyboard and gamepad parity on end-game screen.

- [x] `P2` Bus door visual polish: fade transition between `city-bus.png` and `city-bus-doors-open.png` on open/close.
  - Add blend timing for opening and closing states (for example 0.2s-0.3s each).

- [x] `P2` City Siege mission-start satellite SFX timing: `satellite-reallocating.ogg` now triggers after mission intro cutscene completion (or skip), not at cutscene start.
  - Applied in gamepad mission confirmation flow through deferred mode-based playback.

### UX and Messaging

- [ ] Add Airport bus shift feel polish: soft-jerk body animation, short shift smoke plumes, and subtle shift rumble with tuned intensity/duration.

- [x] Consolidate player-critical mission prompts into the top-center objective strip (avoid split messaging with temporary cutscene cue text).

- [x] Normalize wording/typos for airport mission cues and objective statuses.

- [x] Keep airport objective phase text aligned with current flow (including mission tech reboard gate).

### Onboarding and Tutorial

- [ ] Create a `Ground School` interactive walkthrough tutorial + overlay that guides players through gameplay and controls in sequenced steps.

- [ ] Add a Mission Select `Pre-check UI` overlay that opens before mission start with a helicopter blowout diagram and labeled gameplay/control icons to teach core interactions.

- [ ] Define `Pre-check UI` trigger and flow: auto-open on mission start preview, with `Skip` and `Start Mission` actions.

- [ ] Add `Pre-check UI` reopen affordance on Mission Select (for example a `Controls/Pre-check` button or keybind prompt).

- [ ] Validate keyboard/gamepad parity for `Pre-check UI` navigation, dismissal, and mission launch handoff.

### Test Coverage

- [ ] Add playflow regression coverage for transfer pacing and bus escort transitions.

- [ ] Add focused regression tests for airport failure outcomes and objective state transitions under edge timing.

- [ ] Keep existing airport unit suites green:
  - `tests/test_airport_objective_flow.py`
  - `tests/test_airport_tech_boarding_gate.py`
  - `tests/test_mission_tech_transitions.py`

### Assets and Content

- [x] Create/integrate `city-bus-doors-open.png` (integrated for finalized door visual state).

- [ ] Complete remaining airport placeholder art/audio polish items as needed by playtest feedback.

### Phase 2 Backlog (Deferred)

- [ ] Stack objectives for win conditions.

- [ ] Add multiple bus routes.

- [ ] Add risk/reward for leaving bus to engage enemies.

- [ ] Add unique airport mission audio/music.

- [ ] Add bonus-objective parity updates for City Siege.

### Thermal Mode (Deferred)

- [ ] Define nearest-bunker thermal reveal behavior and gating.

- [ ] Add nearest-bunker selection logic + UI indicator.

- [ ] Add reveal rendering rules for unopened bunkers.

- [ ] Add optional thermal gameplay constraints (cooldown/energy).

- [ ] Add tests for nearest-bunker selection and reveal gating.

## Mission Concept

Escort/Convoy: A ground vehicle (bus) moves across the screen. The player must hover above it, destroying incoming rockets and MRAPs before they reach the convoy. The mission is set at an airport with a crashed plane and jetway, guarded by militants with hostages inside. The bus is a rectangle placeholder until a sprite is available.

## Mission Flow (REDESIGNED)

1. **Mission Start:**
   - Intro cutscene: assets/cutscene-airport-special-ops.mpg
   - Helicopter starts WITH Mission Tech engineer on board
   - Visual indicator above chopper (wrench or colored symbol) shows tech is present
   - Bus starts on right side (x=~2200), begins driving LEFT at 80 px/s
   - Yellow diamond above bus = primary objective indicator
   - Meal truck parked at initial position (x=~1800)

2. **Tech Deployment Phase:**
   - Player flies to meal truck location
   - Lands helicopter near truck (within 120px proximity)
   - Opens doors (E key / A button on gamepad)
   - Mission Tech engineer EXITS helicopter, ENTERS meal truck
   - Tech indicator transfers from chopper to meal truck
   - Helicopter is now free to move independently and defend

3. **Extraction Phase (Meal Truck → Elevated Jetway):**
   - AI-controlled meal truck drives RIGHT to elevated jetway at hostage location (x=~1232)
   - Elevated jetway: floor height matches bottom edge of airport-meal-cart-box.png
   - When truck reaches extraction LZ (within ~30px of jetway):
     - **Box Extension Animation** (duration: ~1.8 seconds):
       - Base sprite: `airport-meal-cart.png` (always visible)
       - Overlay sprite: `airport-meal-cart-box.png` starts at y_offset=0
       - Box moves UP 53 pixels over animation duration
       - Simultaneously, `airport-meal-cart-extended.png` fades IN (alpha 0 → 255)
       - Animation completes when box at +53px and extended sprite fully opaque
     - Hostages begin boarding meal truck (one at a time, ~0.5s each)
     - **Passenger Indicators (Extended Position):**
       - Render starting at position (31, 21) relative to truck base
       - Indicators arranged in rows (4 per row, spacing ~8px)
       - Use hostage sprites/icons to show passenger count and types

4. **Retraction Phase:**
   - Once all available hostages boarded (or boarding complete):
     - **Box Retraction Animation** (duration: ~1.8 seconds):
       - `airport-meal-cart-extended.png` fades OUT (alpha 255 → 0)
       - `airport-meal-cart-box.png` moves DOWN 53 pixels
       - Returns to base `airport-meal-cart.png` appearance
     - **Passenger Indicators (Retracted Position):**
       - Move down with box animation
       - Final position: (31, 74) relative to truck base
       - Indicators persist and render on base truck sprite

5. **Transfer Phase (Meal Truck → Bus):**
   - Meal truck AI drives LEFT to intercept bus (which has passed extraction zone)
   - When truck within transfer range of bus (~50px proximity):
     - Bus AI stops moving
     - Bus doors open: sprite switches to `city-bus-doors-open.png`
     - Passengers transfer from meal truck to bus (one at a time, ~0.4s each)
     - Passenger indicators update to render on bus
     - Once all transferred:
       - Bus doors close (return to `city-bus.png`)
       - Meal truck becomes inactive (or returns to LZ)

6. **Escort Phase (Bus Under Fire):**
   - Bus resumes driving toward safe LZ on RIGHT side of screen (x=~2400)
   - Enemy waves spawn and attack bus:
     - UAV drones with weaving approach → dive attack
     - Ground enemies (future: Merkava tanks, infantry)
   - Player must defend bus from:
     - Enemy projectiles (bullets, missiles, bombs)
     - Direct collision attacks (UAV kamikaze dives)
   - Bus health deteriorates under fire
   - **IMPORTANT:** Player can also damage bus via friendly fire (bullets = 4.0 dmg, bombs = 18.0 dmg)

7. **Mission End:**
   - **SUCCESS:** Bus reaches safe LZ (right side) with passengers alive
   - **FAILURE CONDITIONS:**
     - Bus health reaches 0 (destroyed)
     - All passengers killed
     - 120-second deadline expires before extraction complete (optional)
   - Mission debrief shows:
     - Passengers rescued
     - Bus health remaining
     - Enemies defeated
     - Mission time

## Design Answers & Clarifications

### How does the mission start?

- Intro cutscene: assets/cutscene-airport-special-ops.mpg

### Win/Lose Conditions

- WIN: All hostages rescued (for now; future: stack objectives, add to TODO)

- LOSE: Bus destroyed or all hostages KIA

- Bonus objectives: rescue all hostages, no bus damage, defeat all militants (add similar bonus objectives to City Siege mission)

### Enemy & Obstacle Design

- Militants: stationary, patrolling, and armed with different weapons

- New "one way drone UAV": nose-dives at an angle, detonates on impact, targets bus

- New patrolling Merkava battle tank: 360° turret, mine placing

- New assets: f35-idf.png (enemy F35), f35l-adir.png (ally F35)

- Varied missile munitions: smaller missiles from plane belly

- Environmental hazards: barricades that must be removed for bus to reach hostages

- Enemies attack both bus and player

### Bus & Hostage Mechanics

- Bus: AI path, stops at obstacles, algorithmic speed changes

- Hostages: board/deboard via timed event (120s to reach), can be interrupted by enemies

- Damage: Bus can take damage (like chopper); hostages are 1-hit KIA

### Player Role & Abilities

- Player has haptics and air support (F35l-arid ally delivers precision strike on immediate threat)

- Player deploys Mission Tech by landing near meal truck and opening doors

- Player must defend bus during escort phase (avoid friendly fire!)

- Player can use flares, bombs, and bullets to clear threats

### Risk/Reward for Leaving Bus

- Not in phase 1; consider for phase 2

### Level Layout & Progression

- LZ/tower: acts as cover, Delta Squad on ground with machine guns

- Only one route for bus (phase 1); multiple routes in phase 2

- Crashed plane/jetway: multi-stage area; some hostages require Mission Tech to drive airport luggage/meal car to secondary LZ for rescue

### Pacing & Challenge

- Tension: based on bus health

- Downtime: allow realistic/opportunistic moments for playability

- Difficulty: more enemies to start, scales with progression

### Visuals & Feedback

- Bus: city bus with hydraulic door (asset to be provided)

- Luggage/meal car: asset to be provided

- Crashed airplane, jetway: asset to be provided

- Feedback: similar to City Siege mission

- Unique audio/music: planned as follow-on enhancement

### Technical/Implementation

### Animation System Specifications

#### Meal Truck Box Extension/Retraction

- Animation duration: 1.8 seconds (both extend and retract)

- Box vertical movement: 53 pixels up (extend) / 53 pixels down (retract)

- Sprite fade timing: synchronized with box movement

- Rendering layers (bottom to top):
  1. Base sprite: `airport-meal-cart.png` (always visible, y_offset = 0)
  2. Box overlay: `airport-meal-cart-box.png` (y_offset animates: 0 → -53 → 0)
  3. Extended platform: `airport-meal-cart-extended.png` (alpha animates: 0 → 255 → 0)

#### Passenger Indicator Positioning

- When box extended: render at (31, 21) relative to truck origin

- When box retracted: render at (31, 74) relative to truck origin

- During animation: lerp position smoothly with box movement

- Layout: 4 indicators per row, 8px horizontal spacing

- Use hostage sprite icons for visual clarity

#### Tech Indicator Positioning

- Above helicopter: (helicopter.x, helicopter.y - 60)

- Above meal truck: (truck.x, truck.y - 60)

- Icon: wrench or colored symbol (12x12 or 16x16)

- Render with slight pulse/glow for visibility

#### Bus Door Animation

- Sprite swap: `city-bus.png` ↔ `city-bus-doors-open.png`

- Door state machine: closed → opening (0.3s) → open → closing (0.3s) → closed

- Passenger transfer occurs only when state = "open"

### Module Responsibilities

- `bus_ai.py`: Bus movement, door states, health, transfer LZ stops

- `hostage_logic.py`: Hostage boarding workflow, indicator rendering with position offsets

- `enemy_spawns.py`: Enemy wave logic, UAV drone, Merkava tank, jet adversaries

- `mission_tech.py`: Tech lifecycle state machine (on_chopper → deployed_to_truck → transferring → complete)

- `vehicle_assets.py`: Meal truck animation state (box_state, animation_progress, sprite compositing)

- `objective_manager.py`: Mission phase tracking (tech_deployment → extraction → transfer → escort → complete)

- `cutscene_manager.py`: Jetway visual markers, extraction window triggers

### Testing Strategy

- Unit tests for animation lerp calculations (box position, alpha fade)

- Visual tests for each mission phase (tech deploy, extraction, transfer, escort)

- Regression tests for friendly fire, passenger transfers, mission end conditions

- Debug overlay to show: tech state, box animation_progress, passenger counts

## Asset Requirements

### Required Assets (Core Gameplay)

- `city-bus.png` - Bus sprite (doors closed) ✅ EXISTS

- `city-bus-doors-open.png` - Bus with hydraulic doors open ❌ NEEDS CREATION

- `airport-meal-cart.png` - Base meal truck sprite (box retracted) ✅ EXISTS

- `airport-meal-cart-box.png` - Lift box overlay (animates up/down 53px) ✅ EXISTS

- `airport-meal-cart-extended.png` - Extended platform sprite (fades in/out) ✅ EXISTS

### Placeholder Assets (Can Use Fallback)

- Crashed airplane (simple polygon or image)

- Airport jetway elevated platform (rectangle or simple shape)

- Merkava tank (rectangle or recolored tank)

- UAV drone (white version of fighter jet) ✅ BASIC IMPLEMENTATION DONE

- F35 adversary and ally jets (use new assets or placeholders)

- Barricades (simple blocks)

- Flame/fire animation (basic sprite or color effect)

- Mission Tech visual indicator (wrench icon or colored symbol above chopper/truck)

- Airport tower (existing or simple block for LZ)

- Delta Squad (simple soldier sprites or recolored hostages)

## Phase 2 / Follow-On Enhancements (TODO)

- Stack objectives for win conditions

- Add multiple bus routes

- Add risk/reward for leaving bus to engage enemies

- Add unique audio cues/music for this mission

- Add bonus objectives to City Siege mission

### Thermal Mode (Hostage Reveal) TODO

- [ ] Define thermal mode behavior: when enabled, reveal hostages only in the nearest unopened bunker to the player helicopter

- [ ] Add nearest-bunker selection logic (distance from helicopter x to compound center x)

- [ ] Render hidden hostages in selected bunker with thermal silhouettes/highlight markers while keeping other unopened bunkers hidden

- [ ] Add UI indicator in HUD/debug overlay when thermal mode is active and which bunker index is currently selected

- [ ] Add gameplay constraints (optional tuning): energy drain/cooldown or no penalty in prototype mode

- [ ] Add tests for nearest-bunker selection and reveal gating (opened bunker should not require thermal reveal)

## Implementation Status (Phase 1)

### Completed

- ✅ New branch created: `feature/airport-special-ops-mission`

- ✅ Mission selection: "Airport Special Ops" added to mission select menu

- ✅ Mission config: `create_airport_special_ops_config()` created with wider lanes, longer distances

- ✅ Module scaffolds created with docstrings and TODOs:
  - `bus_ai.py`
  - `hostage_logic.py`
  - `enemy_spawns.py`
  - `mission_tech.py`
  - `vehicle_assets.py`
  - `objective_manager.py`
  - `cutscene_manager.py`

- ✅ Integration into `main.py`:
  - Imports for all new modules
  - Placeholder state variables for airport entities
  - Conditional update logic in fixed-step loop
  - Conditional rendering with placeholder shapes

- ✅ Placeholder rendering working:
  - Blue rectangle (bus) at x=1200
  - White circle (hostage) at x=1232
  - Red triangle (enemy) at x=1280
  - Green square (tech) at x=1250
  - Gold circle (objective) at x=1300
  - Yellow star (cutscene trigger) at x=1320

- ✅ Base game logic functional: helicopter physics, enemies, projectiles, compounds, hostages all working

- ✅ Visual testing confirmed: All entities render correctly, placeholders visible

### Next Steps (Redesigned Implementation)

### Phase 1: Mission Tech State Machine (HIGH PRIORITY)

- [ ] Refactor `mission_tech.py` to track tech lifecycle:
  - State: `on_chopper` (mission start) 
  - State: `deployed_to_truck` (when doors open near truck)
  - State: `driving_to_extraction` (truck en route to jetway)
  - State: `extracting` (box extending + hostages boarding)
  - State: `transferring` (box retracting + driving to bus)
  - State: `transfer_complete` (passengers on bus)

- [ ] Add visual indicator above chopper when tech on board (wrench icon at y-60)

- [ ] Add visual indicator above meal truck when tech deployed

- [ ] Update tech deployment trigger: chopper grounded + doors open + near meal truck (not bus)

### Phase 2: Meal Truck Animation System (HIGH PRIORITY)

- [ ] Refactor `vehicle_assets.py` for box animation:
  - Add `box_state` field: `retracted` / `extending` / `extended` / `retracting`
  - Add `box_animation_progress` (0.0 to 1.0 for 53px movement)
  - Add `extended_sprite_alpha` (0 to 255 for fade in/out)

- [ ] Implement box extension animation:
  - Duration: 1.8 seconds
  - Box y_offset = lerp(0, -53, progress)
  - Extended sprite alpha = lerp(0, 255, progress)

- [ ] Implement box retraction animation:
  - Duration: 1.8 seconds  
  - Box y_offset = lerp(-53, 0, progress)
  - Extended sprite alpha = lerp(255, 0, progress)

- [ ] Update rendering to composite: base + box_overlay + extended_overlay

### Phase 3: Passenger Indicator Positioning (HIGH PRIORITY)

- [ ] Refactor `hostage_logic.py` passenger indicators:
  - When box extended: render at (31, 21) relative to truck base
  - When box retracted: render at (31, 74) relative to truck base
  - During animation: lerp indicator position with box movement

- [ ] Add passenger row layout (4 per row, 8px spacing)

- [ ] Use hostage sprites/icons for visual clarity

### Phase 4: Transfer System (MEDIUM PRIORITY)

- [ ] Add transfer LZ detection in `vehicle_assets.py`:
  - Distance check: meal_truck.x ± 50px of bus.x

- [ ] Create `city-bus-doors-open.png` sprite asset

- [ ] Add bus door state to `bus_ai.py`: `closed` / `opening` / `open` / `closing`

- [ ] Implement passenger transfer logic:
  - Transfer rate: ~0.4s per passenger
  - Update indicators on both truck and bus

- [ ] Update bus AI to stop during transfer, resume after complete

### Phase 5: Objective & UI Updates (MEDIUM PRIORITY)

- [ ] Update `objective_manager.py` phases:
  - Phase 1: "Deploy Mission Tech to meal truck"
  - Phase 2: "Meal truck extracting hostages from jetway"
  - Phase 3: "Transfer hostages to bus"
  - Phase 4: "Escort bus to safe LZ"
  - Phase 5: "Mission success" or "Mission failed"

- [ ] Add tech deployment tutorial hint on first play

- [ ] Add passenger count overlay on truck and bus

### Phase 6: Enemy & Combat Balance (LOW PRIORITY)

- [x] UAV drone enemy type (weaving + dive attack) ✅ DONE

- [ ] Merkava tank enemy type

- [ ] Barricade obstacles

- [ ] Delta Squad cover at LZ

- [ ] Enemy retargeting (prioritize bus during escort phase)

- [ ] Difficulty scaling based on passenger count

### Phase 7: Barak MRAD Damage FX (MEDIUM PRIORITY)

- [ ] **Impact sparks on hit:** Emit `impact_sparks.emit_hit()` at the projectile impact point each time the Barak takes a bullet or bomb hit (identical visual to tank hit sparks)

- [ ] **Stage 1 – damage smoke (≤50% health):** When `e.health` drops to or below 50% of `barak_health`, continuously emit a light smoke particle stream from the vehicle position (`burning.add_site(e.pos, intensity=0.35)` or a dedicated rolling-smoke emitter) — persists until destruction

- [ ] **Stage 2 – heavy fire smoke (≤25% health):** When health drops to ≤25%, escalate smoke stream to heavier black/orange smoke (intensity ≈ 0.65); optionally add a small looping fire flicker render at the vehicle

- [ ] **Destruction sequence:** On `e.health <= 0`:
  - Emit large fire plume: `explosions.emit_fire_plume(e.pos, strength=1.2)`
  - Emit explosion burst: `explosions.emit_explosion(e.pos, strength=1.0)`
  - Emit heavy impact sparks: `impact_sparks.emit_hit(e.pos, vel=Vec2(0,-1), strength=1.8)`
  - Add persistent high-intensity burn site: `burning.add_site(e.pos, intensity=1.0)` (already done — keep)
  - Leave a tall rising smoke column: schedule a secondary `explosions.emit_fire_plume(e.pos, strength=0.55)` 0.6 s after destruction to simulate lingering plume

- [ ] **Per-tick damage threshold check:** Add a helper `_apply_barak_damage_fx(mission, e)` called from `_update_enemies` each tick while Barak is alive and below 50% health — drives the continuous smoke effect without coupling it to the hit path

### Phase 8: Polish & Assets (LOW PRIORITY)

- [ ] Bonus objectives (all passengers, no bus damage, time bonus)

- [ ] Create/integrate cutscene assets

- [ ] Sound effects for tech deployment, box extension, transfer

- [ ] Particle effects for meal truck drive dust

- [ ] Camera follow logic (track bus during escort phase)

### Completed (Previous Design - May Need Refactor):

- [x] Basic bus AI movement ⚠️ (needs door open/close states)

- [x] Enemy spawn waves ✅ (UAV implemented, works as intended)

- [x] Collision detection between bus and player fire ✅

- [x] Damage model for bus ✅

- [x] Hostage timer (120s deadline) ✅

- [x] Mission Tech deployment ⚠️ (needs complete refactor for new flow)

- [x] Meal truck extraction ⚠️ (needs animation system redesign)

- [x] Objective tracking ⚠️ (needs phase updates)

## Implementation Notes

- Bus uses `city-bus.png` sprite (with fallback rectangle if asset load fails)

- LZ modeled after airport tower

- `hostage_logic.py` now contains active Airport boarding/deboarding state and render hooks

- `mission_tech.py` now contains Mission Tech deploy/retrieve + bus repair logic

- `enemy_spawns.py` now applies basic bus damage on enemy impacts

- `objective_manager.py` now tracks objective phase + 120s hostage deadline

- Current rendering shows both base game entities and new placeholders

- Helicopter and core gameplay fully functional for testing

- Hostage, bus, and enemy logic may require new or updated modules

- Track all clarifications and design decisions here as they are resolved

## Game Enhancements - TODO / Backlog

This is the active backlog after the latest mission/main refactor and packaging pass.

## Baseline (Current)

- Playable rescue loop is stable.

- Mission logic has been split into dedicated modules.

- Main loop cleanup/dedupe completed.

- Weather/FX systems are integrated and tunable.

- Windows onedir + onefile builds complete successfully.

## Recently Completed

- [x] Main-file cleanup pass (input/pause state dedupe and stale block removal).

- [x] Documentation refresh for README + handoff/build docs.

- [x] Fresh onefile and onedir rebuild after cleanup.

- [x] Intro + hostage rescue cutscenes migrated to `.avi` assets.

- [x] Build script updated to prefer staged assets and skip legacy `.mpg` files when `.avi` variants exist.

- [x] Onefile rebuild after media migration with reduced output size.

## High Priority Next

- [x] Reduce onefile build size.

- [x] Re-encode intro and mission cutscene media to smaller formats (`intro.avi`, `hostage-rescue-cutscene.avi`).

- [ ] Evaluate a "lite media" build mode that skips video dependencies for smaller distribution builds. (deferred/skipped for now)

- [x] Convert largest SFX set to compressed OGG audio. (`.ogg` assets are integrated and runtime loading has been updated.)

### High Priority Gameplay Requests (Post-Merge)

- [x] Pause audio behavior: mute all sounds while paused, then restore on unpause unless player mute is enabled.
   - [x] On entering `paused`, hard-mute active channels/buses for gameplay + ambience + SFX.
  - [x] On resuming, restore previous volumes only when player mute toggle is OFF.
  - [x] Keep audio muted after unpause when player mute toggle is ON.
  - [x] Add regression checks for pause via keyboard and gamepad paths.

- [x] BARAK grounded-hit collision fix.
  - [x] Ensure BARAK missiles register damage when chopper is grounded outside the LZ.
  - [x] Preserve safe/no-hit behavior only when chopper is grounded inside the LZ.
  - [x] Add focused debug logging around grounded collision branch and LZ overlap evaluation.
  - [x] Add deterministic tests for airborne, grounded-in-LZ, and grounded-outside-LZ collision cases.

- [x] Update LZ texture/art to embassy-style building.
  - [x] Replace current LZ visual asset with embassy-style art variant.
  - [x] Verify readability at gameplay camera scales and with weather overlays.
  - [x] Confirm collision/landing bounds remain unchanged after art swap.
  - [x] Add unload-active animation pulse to embassy facade accents.
  - [x] Tune unload/ambient animation speeds after quick playtest pass.

- [x] Mission start objective overlay for City Siege.
  - [x] On City Siege mission start, show: `Rescue the VIP [VIP indicator] hostage`.
  - [x] Use the existing VIP indicator icon/crown style in the overlay text row.
  - [x] Ensure overlay timing, fade, and z-order do not conflict with cutscene or HUD.

### Onefile Size Reduction Baseline (Measured)

- Current onefile output:
  - Latest measured `pyinstaller-dist/Choplifter.exe` is about `318.34 MB`.
  - Previous baseline was about `330.56 MB`.
  - Net reduction so far is about `12.22 MB`.

- Largest media payloads in `src/choplifter/assets`:
  - `intro.mpg`.
  - `hostage-rescue-cutscene.mpg`.
  - `chopper-flying.ogg` remains one of the larger individual SFX assets after migration.

- Packaging/runtime contributors in onedir:
  - bundled ffmpeg from `imageio-ffmpeg` about `83.58 MB` (inside `_internal`)
  - `numpy` about `5.80 MB`

- Current script behavior:
  - `scripts/build_windows_exe.ps1` stages assets with an explicit include list and excludes non-runtime source files (for example `.xcf`).
  - Legacy `intro.mpg`/`hostage-rescue-cutscene.mpg` are skipped when `.avi` alternatives are present.
  - Latest staging stats: `31` staged runtime files from `32` source files (`1` source `.xcf`, `0` staged `.xcf`).
  - Video dependencies (`imageio`, `imageio-ffmpeg`) are still included by default.

### Onefile Size Reduction Plan (Highest Impact First)

- [x] Re-encode intro and mission cutscene videos first.
  - `intro.avi` and `hostage-rescue-cutscene.avi` are now used by default.
  - Legacy `.mpg` variants are excluded from build staging when `.avi` files are present.

- [ ] Create a "lite media" profile with no video playback dependency. (deferred/skipped for now)
  - Add a build flag in `scripts/build_windows_exe.ps1` (for example `-LiteMedia`).
  - In lite mode:
    - Do not include `imageio` / `imageio-ffmpeg` metadata collection.
    - Do not include large video files in `--add-data`.
    - Use existing fallback intro/title-card behavior when video is unavailable.
  - Expected win: roughly `-100 MB` more (ffmpeg + numpy + related hooks), plus skipped video assets.

- [x] Compress/convert WAV SFX to OGG.
  - Largest SFX were migrated to `.ogg` and runtime loading was updated in `src/choplifter/audio.py`, `src/choplifter/audio_extra.py`, and `src/choplifter/intro_video.py`.
  - Follow-up: re-measure onefile/onedir outputs to capture the actual size delta from the audio migration.

- [x] Stop shipping non-runtime source assets.
  - Exclude files such as `chopper-one.xcf` from packaged output.
  - Replace broad asset inclusion with explicit include patterns or an asset manifest.
  - Completed via explicit manifest staging in `scripts/build_windows_exe.ps1`; staged output now excludes `.xcf` files.

- [ ] Optimize images losslessly.
  - Run PNG/JPG optimization pass (for example `oxipng`, `jpegoptim`, or `mozjpeg`).
  - Expected win: modest (`~2 MB` to `~8 MB`) without visual quality loss.

- [ ] Keep onefile for distribution convenience only.
  - Onefile size will track total payload size; it is not an automatic size reduction format.
  - Use onedir for profiling and iteration, then generate final onefile deliverables.

### Recommended Execution Order

1. [x] Finalize explicit asset manifest/include list.

2. [x] Build and re-measure onefile and onedir outputs.

3. [ ] Optimize images losslessly if further reduction is needed.

4. [ ] Revisit `-LiteMedia` and/or audio conversion pipeline later if distribution size still needs major reduction.

## Cross-Platform Build Support (Windows + macOS)

### Overview & Goals

- **Primary Goal**: Support native executable builds for both Windows and macOS platforms.

- **Target Audience**: Maximize distribution reach to desktop players across both major PC operating systems.

- **Build Strategy**: Platform-specific builds generated on respective native hardware (Windows builds on Windows, macOS builds on macOS).

- **Deliverables**:
  - Windows: `.exe` onefile + onedir (current)
  - macOS: `.app` bundle + optional `.dmg` installer

### Current State

- ✅ Windows builds: Fully functional via `scripts/build_windows_exe.ps1`
  - Onefile: ~318 MB standalone executable
  - Onedir: ~6 MB exe + ~83 MB `_internal` folder
  - Video/audio playback tested and working
  - PyInstaller 6.19.0 with imageio/imageio-ffmpeg dependencies

- ❌ macOS builds: Not yet implemented

### macOS Build Requirements

#### Hardware/Environment

- [ ] macOS build machine (physical Mac or CI runner)
  - Recommended: macOS 10.15 (Catalina) or later for broad compatibility
  - Cannot cross-compile from Windows reliably
  - Options:
    - Local Mac hardware (MacBook, iMac, Mac Mini)
    - GitHub Actions runner with macOS (e.g., `macos-latest`)
    - Cloud CI provider (CircleCI, GitLab, etc.)

#### Software Stack

- [ ] Python 3.13.6 (match Windows version for consistency)

- [ ] Homebrew package manager (for dependency installation)

- [ ] PyInstaller 6.19.0+ (same version as Windows)

- [ ] Required Python packages: `pygame 2.6.1`, `imageio`, `imageio-ffmpeg`, etc.

- [ ] Xcode Command Line Tools (for compilation if needed)

### Implementation Steps

#### Phase 1: Basic macOS Build (Estimate: 1-3 hours)

- [ ] **Setup macOS development environment**
  - Install Homebrew: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
  - Install Python 3.13: `brew install python@3.13`
  - Create virtual environment in project: `python3.13 -m venv .venv`
  - Activate venv: `source .venv/bin/activate`
  - Install dependencies: `pip install -r requirements.txt`

- [ ] **Verify game functionality on macOS**
  - Test run game: `python run.py`
  - Validate video playback (intro cutscenes)
  - Validate audio playback (all channels)
  - Test gameplay (helicopter controls, missions, etc.)
  - Check for case-sensitivity issues (Windows vs macOS filesystem)

- [ ] **Create macOS build script**
  - Create `scripts/build_macos_app.sh` (bash equivalent to Windows PowerShell script)
  - Structure:
    ```bash
    #!/bin/bash
    # Build macOS .app bundle with PyInstaller
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Clean previous builds
    rm -rf build/ dist/ pyinstaller-dist/
    
    # Stage assets (same logic as Windows script)
    # ... copy assets to staging directory ...
    
    # Run PyInstaller
    pyinstaller \
      --name "Choplifter" \
      --windowed \
      --onefile \
      --icon="src/choplifter/assets/icon.icns" \
      --add-data "pyinstaller-build/asset-staging:choplifter/assets" \
      --copy-metadata pygame \
      --copy-metadata imageio \
      --copy-metadata imageio-ffmpeg \
      --collect-data imageio_ffmpeg \
      --hidden-import pygame \
      --hidden-import imageio_ffmpeg \
      run.py
    
    # Copy .app to distribution folder
    mkdir -p pyinstaller-dist/
    cp -r dist/Choplifter.app pyinstaller-dist/
    ```
  - Make executable: `chmod +x scripts/build_macos_app.sh`

- [ ] **Run initial macOS build**
  - Execute: `./scripts/build_macos_app.sh`
  - Expected output: `pyinstaller-dist/Choplifter.app`
  - Test: Double-click `.app` or run `open pyinstaller-dist/Choplifter.app`

#### Phase 2: Polished Distribution (Estimate: 0.5-1 day)

- [ ] **Create DMG installer (optional but recommended)**
  - Tool: `create-dmg` (install via: `brew install create-dmg`)
  - Script to create `.dmg`:
    ```bash
    create-dmg \
      --volname "Choplifter" \
      --window-pos 200 120 \
      --window-size 800 450 \
      --icon-size 100 \
      --icon "Choplifter.app" 200 190 \
      --hide-extension "Choplifter.app" \
      --app-drop-link 600 185 \
      "Choplifter-Installer.dmg" \
      "pyinstaller-dist/"
    ```
  - Result: Drag-and-drop DMG installer for easy installation

- [ ] **Create macOS app icon (`.icns` format)**
  - Convert existing icon to `.icns` format
  - Tool: `iconutil` (built into macOS)
  - Process:
    1. Create `icon.iconset/` folder with PNG sizes: 16x16, 32x32, 128x128, 256x256, 512x512, 1024x1024
    2. Convert: `iconutil -c icns icon.iconset -o icon.icns`
  - Update `--icon` parameter in build script

- [ ] **Bundle size optimization**
  - Expected: Similar to Windows (~300-350 MB with video assets)
  - Optimization strategies (same as Windows):
    - Re-encode video assets to smaller formats
    - Consider "lite media" build variant
    - Optimize image assets losslessly

#### Phase 3: Code Signing & Notarization (Estimate: 1-2 days)

- [ ] **Apple Developer Account setup**
  - Required for: Code signing and notarization (removes Gatekeeper warnings)
  - Cost: $99/year for Apple Developer Program membership
  - Not required for testing/development, only for public distribution

- [ ] **Code signing**
  - Obtain Developer ID certificate from Apple
  - Sign app: `codesign --deep --force --verify --verbose --sign "Developer ID Application: Your Name" Choplifter.app`
  - Verify signature: `codesign --verify --verbose Choplifter.app`

- [ ] **Notarization** (removes "unidentified developer" warning)
  - Submit to Apple: `xcrun notarytool submit Choplifter.dmg --keychain-profile "notary-profile" --wait`
  - Staple ticket: `xcrun stapler staple Choplifter.dmg`
  - Note: Requires Apple Developer account ($99/year)

### Build Automation

#### Option A: Local Builds (Manual)

- [ ] Developer with Mac hardware runs `scripts/build_macos_app.sh` manually

- [ ] Upload macOS `.app` or `.dmg` alongside Windows `.exe` for each release

- **Pros**: Simple, no CI setup required

- **Cons**: Manual process, requires Mac access

#### Option B: GitHub Actions CI (Automated)

- [ ] Create `.github/workflows/build-release.yml`

- [ ] Strategy matrix for both platforms:
  ```yaml
  strategy:
    matrix:
      os: [windows-latest, macos-latest]
      include:
        - os: windows-latest
          build-script: scripts/build_windows_exe.ps1
          artifact-path: pyinstaller-dist/Choplifter.exe
        - os: macos-latest
          build-script: scripts/build_macos_app.sh
          artifact-path: pyinstaller-dist/Choplifter.app
  ```

- [ ] Upload artifacts for both platforms

- [ ] Optionally: Trigger on Git tags (`v1.0.0`) for release automation

- **Pros**: Automated, repeatable, both platforms built simultaneously

- **Cons**: GitHub Actions minutes usage (free tier: 2000 min/month)

### Platform-Specific Gotchas & Solutions

#### macOS-Specific Issues

- **Case-sensitive filesystem**: 
  - Solution: Test all asset paths on macOS, fix any case mismatches
  - Example: `Intro.avi` vs `intro.avi` matters on macOS, not on Windows
  

- **Gatekeeper warnings**: 
  - Issue: Unsigned apps show "unidentified developer" warning
  - Solution: Code signing + notarization (requires Apple Developer account)
  - Workaround: Users can right-click → "Open" → "Open Anyway" (first launch only)

- **Video/audio dependencies**:
  - Verify `imageio-ffmpeg` works on macOS (should be automatic)
  - Test audio playback with macOS-specific audio backends
  - Fallback: Use Pygame's default audio mixer if issues arise

- **Retina display scaling**:
  - Issue: UI may scale incorrectly on high-DPI displays
  - Solution: Set `pygame.SCALED` flag or handle DPI scaling explicitly
  - Test on various Mac displays (non-Retina vs Retina)

#### Cross-Platform Code Considerations

- [ ] **File path handling**:
  - Always use `os.path.join()` or `pathlib.Path` (never hardcoded `\\` or `/`)
  - Already using `Path` in most places (verify entire codebase)

- [ ] **Asset loading**:
  - Verify all asset references use case-consistent filenames
  - Run: `grep -r "\.avi\|\.png\|\.wav\|\.ogg" src/` and check capitalization

- [ ] **Keyboard/input mapping**:
  - Test gamepad support on macOS (controllers may map differently)
  - Verify keyboard shortcuts work (Command vs Ctrl)

### Testing & Validation

#### Pre-Release Checklist (macOS)

- [ ] Game launches without errors

- [ ] Intro video plays correctly

- [ ] Mission cutscenes play correctly

- [ ] Audio playback functional (all channels: music, SFX, helicopter, explosions)

- [ ] Helicopter controls responsive (keyboard + gamepad)

- [ ] All three missions playable end-to-end

- [ ] Graphics rendering correctly (no artifacts or scaling issues)

- [ ] Pause/resume functionality works

- [ ] Save/load game state (if applicable)

- [ ] Settings persistence (audio levels, controls, accessibility)

- [ ] Performance acceptable (60 FPS target)

- [ ] No crashes during extended play sessions

- [ ] .app bundle size acceptable (document final size)

- [ ] Gatekeeper behavior documented (signed vs unsigned)

#### Compatibility Testing

- [ ] Test on multiple macOS versions:
  - macOS 10.15 Catalina (minimum supported)
  - macOS 11 Big Sur
  - macOS 12 Monterey
  - macOS 13 Ventura
  - macOS 14 Sonoma (latest at time of release)

- [ ] Test on Intel and Apple Silicon (M1/M2/M3) Macs

- [ ] Document minimum system requirements

### Maintenance Plan

#### Ongoing Responsibilities

- [ ] **Parallel build maintenance**:
  - Keep `build_windows_exe.ps1` and `build_macos_app.sh` in sync
  - When adding new assets, update both staging scripts
  - When updating dependencies, test on both platforms

- [ ] **Dependency updates**:
  - Update `requirements.txt` with platform-agnostic versions
  - Test dependency updates on both Windows and macOS before release
  - Document any platform-specific dependency quirks

- [ ] **Release process**:
  - Build both platforms for each release
  - Test both builds before publishing
  - Upload both artifacts to GitHub Releases (or distribution platform)
  - Update README with download links for both platforms

- [ ] **Bug tracking**:
  - Label platform-specific bugs: `platform: windows` / `platform: macos`
  - Reproduce issues on native platform before attempting fixes
  - Test fixes on both platforms when possible

#### Documentation Updates Needed

- [ ] Update `README.md`:
  - Add macOS installation instructions
  - Add macOS build instructions for developers
  - Update system requirements section

- [ ] Update `docs/EXECUTIVE_SUMMARY.md`:
  - Note cross-platform support

- [ ] Create `docs/MACOS_BUILD.md`:
  - Detailed macOS build setup instructions
  - Troubleshooting guide for common macOS-specific issues
  - Code signing and notarization walkthrough

- [ ] Update `LLM_HANDOFF.md`:
  - Document macOS build process for AI assistant context

### Effort Estimate Summary

| Phase | Time Estimate | Dependencies |
| ------- | -------------- | -------------- |
| Basic macOS build (Phase 1) | 1-3 hours | Mac hardware or CI runner access |
| Polished distribution (Phase 2) | 0.5-1 day | Phase 1 complete |
| Code signing & notarization (Phase 3) | 1-2 days | Apple Developer account ($99/year) |
| CI automation setup | 0.5-1 day | GitHub Actions knowledge |
| Testing & validation | 0.5-1 day | Access to multiple Mac configurations |
| **Total (basic build)** | **1-3 hours** | **Mac access only** |
| **Total (production-ready)** | **3-5 days** | **Mac access + Apple Developer account** |

### Priority Recommendations

1. **Start with Phase 1** (basic build): Get a working `.app` bundle first, even if unsigned

2. **Defer Phase 3** (signing/notarization): Only necessary for public distribution without warnings; users can bypass Gatekeeper for testing

3. **Consider CI automation early**: GitHub Actions runner with `macos-latest` provides free build capacity

4. **Test thoroughly on macOS**: Video playback and audio are most likely pain points

## Gameplay / UX Improvements

- [ ] Rescue readability polish (boarding feedback, grounded/doors clarity).
  - [x] Define boarding UX states (`approaching`, `boarding`, `boarded`, `blocked`).
  - [x] Add clear boardability indicator when helicopter is in valid pickup conditions.
  - [x] Add outcome toasts for blocked boarding reasons (`Too high`, `Too fast`, `Doors closed`, `Not grounded`).
  - [x] Add/confirm grounded-state indicator in HUD.
  - [x] Add/confirm door-state indicator in HUD (`OPEN`/`CLOSED`).
  - [x] Add cooldown/debounce for prompt flicker to avoid noisy UI.
  - [x] Add accessibility pass for color + shape readability.
  - [x] Add telemetry counters for failed board attempts by reason.
  - [x] Tune boarding thresholds after playtest.

- [x] Threat readability pass (distinct tells for tanks/jets/mines).
  - [x] Create threat tell matrix per enemy (cue, lead time, effective range).
  - [x] Tanks: add pre-fire turret tell and muzzle flash timing window.
  - [x] Jets: add early warning cue before attack run.
  - [x] Mines: add visibility pulse/glint and proximity warning cue.
  - [x] Ensure each threat has distinct visual + audio signature.
  - [x] Add colorblind-safe cue alternatives.
  - [x] Add debug overlay for active tell windows.
  - [x] Balance false positives vs missed warnings.

- [x] Sentiment/consequence meter in debrief and progression.
  - [x] Define sentiment inputs (rescues, losses, collateral, objective quality).
  - [x] Define scoring bands and labels (`Excellent`/`Good`/`Mixed`/`Poor`/`Critical`).
  - [x] Add debrief meter UI with reason breakdown lines.
  - [x] Persist sentiment across mission progression.
  - [x] Tie progression modifiers to sentiment bands.
  - [x] Add balancing guardrails so one event cannot dominate outcome unfairly.
  - [x] Add tests for score computation and persistence.

## Classic Choplifter Fidelity Audit (2026-03-12)

Priority additions to preserve 1982 rescue-first essence while improving modern presentation.

### P0 (Next Up)

- [x] City Siege objective/event overlay parity pass.
  - Refactor City Siege overlay flow to match Airport mission command-prompt style center-screen event HUD behavior.

- [x] Mission/background select messaging bug sweep.
  - Resolve missing UI selection message rendering and remove any stale legacy background/message lookup paths.

- [x] Tower LZ deboard placement correction.
  - Render deboarded passengers near the terminal frontage (left-side building area), not clustered in front of the ATC tower column.

- [x] Shared vehicle damage framework.
  - Add vehicle damage handling parity for bus, meal truck, raider, and drone entities (helicopter/ground-cannon style health/damage states).
  - Keep bus immune until escort-protection phase starts, then enable mission-appropriate damage intake.

- [x] BARAK visual damage progression.
  - Add damage-state VFX for BARAK vehicle: smoke density scales with damage, plus engine-front fire breakout at or below 70% health.

### P1 (Classic Flavor + Modern Presentation)

- [ ] Add Sikorsky HH-60W "Jolly Green II" selectable helicopter option.
  - Include selection card, runtime sprite integration, and baseline tuning parity with existing selectable helicopters.

- [ ] Add scrolling helicopter biography panel.
  - Show selected helicopter background/spec flavor text in a readable scrolling panel on selection/briefing flow.

- [ ] Mission Enhancements (final third mission style pass).
  - Add and balance `Search & Destroy` + `Sabotage/Infiltration` objective chain (for example: destroy power nodes to disable shield and expose main factory objective).

### P1/P2 Gap Follow-ups (Cross-Check from Prior Checklist)

- [ ] Boarding UX: add/confirm subtle helicopter-side boarding ring/zone visualization near skid level.
- [ ] Boarding UX: add explicit regression matrix for each board-failure reason plus successful board path in one suite.
- [ ] Boarding UX: validate door transition feedback sync (SFX + animation timing coherence).
- [ ] Threat readability: move tell timing windows into tunable config band (target 300-700ms learnable range) and run false-positive tuning pass.
- [ ] Sentiment progression: add mission-end event log panel and analytics hooks for outcome-band distribution during playtests.

## Reprioritized Game Enhancements (Pygame/PC)

Ordered from least complex to most complex.

### 1) UI & Visuals (Quick Wins)

- [x] VIP crown fix (priority quick win).
  - Move VIP crown draw call to the end of the UI/indicator draw sequence so it always renders on top.
  - Add pulsating alpha effect using sine wave timing.
  - Target formula: `alpha = 127.5 * (sin(time * speed) + 1)` (maps to 0..255).

- [x] HUD overlay migration (icon overlay implemented; final art swap pending).
  - Replace console-style text indicators with icon-based HUD (fuel, health, etc.) in top-left.
  - Use PNG icon assets exported from SVG source files.

- [x] Bunker and turret reskin.
  - Upgrade defensive structure visuals with improved polygons and/or new textures.

- [x] BARAK explosion animation.
  - Trigger a dedicated sprite sequence (fire plume) on collision/impact events.

### 2) Audio Overhaul (Mixer Layer)

- [x] Dedicated sound channels.
  - Assign helicopter hum and BARAK-launch sounds to dedicated `pygame.mixer.Channel` instances.
  - Prevent cutoff/stealing from transient SFX playback.

- [x] Restart and cutscene audio logic.
  - On restart, stop persistent channels explicitly (`channel.stop()`).
  - During hostage/cutscene sequences, duck key channels (`channel.set_volume(0.5)`).

### 3) Behavioral Logic (State Layer)

- [x] Missile/flar diversion behavior.
  - If flares are active, override BARAK target vector to decoy direction `(0, -1)`.
  - Normalize naming to `flare` across code/data (keep compatibility aliases if needed).
  - Define diversion eligibility (range, timing window, missile types).
  - Implement target override to decoy vector/position while flare is active.
  - Add smooth retargeting limits (turn-rate cap) to avoid unnatural snaps.
  - Add diversion feedback cue (trail bend + audio).
  - Handle edge cases (flare expiry mid-flight, no active flare, multiple flares).
  - Add tunables (chance, radius, max turn rate, flare lifetime).
  - Add tests for diversion success/failure branches.

- [x] MRAP and launcher state cycle.
  - Implement `Retract -> Move -> Deploy` state machine using timer/state variables.
  - Formalize full cycle (`Retract -> Move -> Deploy -> Launch -> Retract`).
  - Replace ad-hoc string transitions with explicit state constants.
  - Add per-state timers/guards and fail-safe transitions.
  - Implement synchronized deploy animation (angle + extension).
  - Keep launch one-shot logic isolated with clean reset path.
  - Add reload/cooldown behavior before next cycle.
  - Add transition event hooks for SFX/VFX.
  - Add debug state inspector and deterministic transition tests.

### 4) High Complexity (Systems Layer)

- [x] Supply drop physics + munitions manager.
  - Build manager for spawn timing, sway motion (`sin` horizontal offset), and gravity.

- [ ] Add bunker-buster ammo drop that grants bomb armament to the chopper.
  - Define pickup behavior and HUD/readiness feedback for bunker-buster-equipped state.

- [ ] Mission enhancements: escort and sabotage.
  - Add new objective types with new win/loss conditions and multi-entity coordination.

## Technical Deep-Dive Notes

- VIP crown layering:
  - Ensure `draw_vip_crown()` is called after standard hostage indicator rendering.

- VIP crown pulsation:
  - Use smooth alpha modulation each frame with sine timing.

## Open Prioritization Questions (Decision Inputs)

- [ ] VIP indicator architecture:
  - Are non-VIP indicators in the same sprite group as VIP?
  - If yes, evaluate `pygame.sprite.LayeredUpdates` to guarantee VIP front layer.

- [ ] SVG pipeline decision:
  - Confirm whether SVGs are converted at runtime or pre-exported to PNG.
  - Prefer pre-exported PNGs unless runtime SVG dependency is required.

- [ ] BARAK "searing heat" visual style:
  - Choose particle system (many small particles) vs animated sprite (single plume).

- [ ] Restart architecture check:
  - Confirm whether restart re-instantiates game/session objects or resets variables in-place.
  - Use this to finalize global channel-stop strategy and audio state reset.

## Later

- [ ] Weather gameplay modifiers (sandstorm visibility + wind impact).

- [ ] Vertical extraction mission segments.

- [ ] Additional mission-specific cutscenes/events.



