# Executive Summary (Investor/Board)

## Vision

**Choplifter** is a fast, readable, mission-driven helicopter rescue action game: high-stakes extractions under pressure, where every decision trades off time, risk, and collateral outcomes.

The remake is built to be **logically faithful** to the classic feel (tight arcade pacing and immediately legible threats) while delivering a modern, configurable player experience (gamepad-first navigation, accessibility toggles, and extensible mission structure).

## Product Snapshot (Current Prototype)

- **Platform/Tech:** Python 3.13 + Pygame 2.6.1
- **Game Loop:** Fixed-step simulation (60Hz) with rendering decoupled
- **Core Loop:** Locate compounds, open them (combat), pick up hostages (doors + grounded), return to base, repeat
- **Mission Sentiment Model:** Live score (0-100) updates from rescue/casualty outcomes and now includes airport route-order bonus logic
- **Threats (Implemented):** Ground armor, fast air threats, and homing air mines
- **Weather/Particle SFX:** Robust Rain, Fog, Dust, and Lightning systems with tunable parameters and visual feedback.
- **Debug Mode & Commands:**
  - F3: Toggle debug mode (shows in-game overlay and enables debug features)
  - F5: Cycle weather mode forward (only in debug mode)
  - F6: Cycle weather mode backward (only in debug mode)
  - Debug overlay: Visible when debug mode is active; shows "DEBUG MODE" in red at the top left
  - Weather cycling: Instantly changes between [clear, rain, fog, dust, storm] for rapid SFX/particle testing
  - Debug state and weather persist across pause/unpause
- **Input Disablement:** All player input is locked on mission end to prevent accidental actions.
- **UX:** Gamepad support, mission restart/pause flows, chopper selection, accessibility toggles
- **Architecture:** Mission/main logic refactored into focused modules for safer iteration and reduced regression risk
- **QA/Validation:** Airport mission smoke suite is automated (`airport_smoke` pytest marker + `scripts/run_airport_smoke.ps1`) with a documented 10-minute manual follow-up pass
- **Packaging:** Windows onefile and onedir builds are operational via scripted PyInstaller pipeline

## Mission Sentiment Factors (Current Implementation)

Sentiment is a numeric mission-level score clamped to `0..100` and computed from outcome deltas each update tick.

- **Positive contributors:**
   `saved` hostages: `+2.5` each
- **Negative contributors:**
   `kia_by_player`: `-4.0` each
   `kia_by_enemy`: `-2.5` each
   `lost_in_transit`: `-3.5` each
- **Per-update guardrail:**
   Delta is clamped to `[-18.0, +18.0]` per update pass to avoid single-frame spikes

Airport-specific additions:

- **Route bonus (one-time, when both lower + elevated streams have progress):**
   Elevated-first route: `+3.0` (shown as Riskier Path Bonus)
   Lower-first route: `+2.0` (shown as Route Bonus)
- **End-game debrief visibility:**
   End screen now explicitly states whether Riskier Path Bonus was earned or not, and shows its sentiment contribution line item

Where sentiment currently matters in gameplay:

- Enemy pressure scaling by sentiment band (`Excellent/Good/Mixed/Poor/Critical`)
- HUD sentiment display during play
- End-game debrief sentiment total plus factorized reason lines

Current backlog candidate (optional, not blocking):

- Persist/propagate sentiment effects across a multi-mission campaign arc (meta progression impact beyond the current mission session)

## Why It’s Compelling

- **Strong core fantasy:** “Rescue under fire” is immediate, understandable, and replayable.
- **High signal-to-noise gameplay:** Clear hazards, clear objectives, minimal UI clutter.
- **Modular mission model:** Levels are defined via configuration and can scale content efficiently.

## Market Positioning (High-Level)

- Arcade-action players who value **tight controls + mission pressure**
- Streamable/clip-friendly emergent moments (narrow saves, last-second landings, chained threats)
- Accessible control defaults plus optional rebinding/tuning

## Roadmap (3 Missions)

The product will ship with three distinct missions the player can select before starting:

1. **City Center (Extraction Operations)**
   - Urban compounds, dense threat spacing, fast turnaround loops.
2. **Airport Special Ops**
   - Wider sightlines, higher-speed traversal, distinct “runway corridor” geometry and threat staging.
3. **Worship Center Warfare (Finale)**
   - High pressure, layered threats, and mission-ending stakes with the most demanding rescue cadence.

## Latest Gameplay Updates (Current Branch)

- Airport mission-tech flow now supports flexible rescue order (no hard lock), with soft guidance and route-based reward tuning.
- Mission Technician KIA behavior now mirrors City Siege-style fail overlay flow (non-terminal immediate sequence): gameplay continues until crash/fuel fail or mission completion path.
- Airport tower-LZ interactions were tightened and stabilized:
   Mission-tech reboard/deboard sequencing improvements
   Elevated pickup boundary tuning
   Auto-boarding cutoff when truck drifts beyond right LZ tolerance
- Lower-compound window lighting now reflects actual awaiting passengers and dims when cleared.
- Intro/cutscene hitch was reduced via async audio warmup; temporary loading overlay was removed per UX preference.
- End-game debrief now includes airport route-bonus messaging and explicit Riskier Path Bonus earned/not-earned status.

## Production Approach

- **Lean, gameplay-first iteration:** Prototype mechanics quickly, then polish readability and tuning.
- **Config-driven content:** Mission parameters are data-driven to enable rapid iteration.
- **Player trust:** Accessibility options (particles/flashes/screenshake) and control thresholds are supported.
- **Test discipline:** Automated smoke gating plus structured manual checklists reduce regression risk during rapid mission iteration.

## What We Need Next

- **Mission content build-out:** Visual identity per mission, unique objective cadence, tuned threat mixes.
- **Art/audio pass:** Replace placeholders and unify presentation across missions.
- **Distribution readiness:** Reduce onefile package size (media and runtime dependency optimization), then finalize signed release pipeline.

## Investment Thesis

This is a focused, technically proven prototype with a strong core loop and clear expansion path: three missions, scalable content iteration, and a modern UX foundation—positioned to become a polished, replayable arcade-action title with efficient content production.
