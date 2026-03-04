# Executive Summary (Investor/Board)

## Vision
**Choplifter** is a fast, readable, mission-driven helicopter rescue action game: high-stakes extractions under pressure, where every decision trades off time, risk, and collateral outcomes.

The remake is built to be **logically faithful** to the classic feel (tight arcade pacing and immediately legible threats) while delivering a modern, configurable player experience (gamepad-first navigation, accessibility toggles, and extensible mission structure).

## Product Snapshot (Current Prototype)
- **Platform/Tech:** Python 3.13 + Pygame 2.6.1
- **Game Loop:** Fixed-step simulation (60Hz) with rendering decoupled
- **Core Loop:** Locate compounds, open them (combat), pick up hostages (doors + grounded), return to base, repeat
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

## Production Approach
- **Lean, gameplay-first iteration:** Prototype mechanics quickly, then polish readability and tuning.
- **Config-driven content:** Mission parameters are data-driven to enable rapid iteration.
- **Player trust:** Accessibility options (particles/flashes/screenshake) and control thresholds are supported.

## What We Need Next
- **Mission content build-out:** Visual identity per mission, unique objective cadence, tuned threat mixes.
- **Art/audio pass:** Replace placeholders and unify presentation across missions.
- **Distribution readiness:** Packaging + build pipeline + basic analytics/telemetry (opt-in) for tuning.

## Investment Thesis
This is a focused, technically proven prototype with a strong core loop and clear expansion path: three missions, scalable content iteration, and a modern UX foundation—positioned to become a polished, replayable arcade-action title with efficient content production.
