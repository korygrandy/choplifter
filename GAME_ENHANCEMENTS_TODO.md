#+#+#+#+markdown
# Game Enhancements — TODO / Backlog

This is the working backlog for incremental improvements on top of the current playable build.

It includes both:
- **Gameplay & engagement** ideas (mission variety, progression, mastery)
- **Shippable maintenance** tasks (build pipeline, onboarding, polish)

## Mission Variety

- [ ] **Objective variants (MVP-friendly)**
  - [ ] Classic Rescue (baseline): rescue at least `N` hostages
  - [ ] Time-Window Rescue: rescue at least `N` within `T` seconds
  - [ ] Rescue + Suppression: rescue at least `N` and destroy at least `K` tanks (or `K` enemies)
  - [ ] Holdout Evac: survive `T` seconds after a trigger (mission start / first compound opened / first hostage boarded)
- [ ] Add minimal objective HUD line (e.g., `Rescued 12/20`, `Time 01:34`, `Tanks 1/3`)

## Progression Loop (Lightweight)

- [ ] Between-mission upgrade choice (pick 1 of 2)
- [ ] Small upgrade set (examples)
  - [ ] Flare capacity / cooldown
  - [ ] Faster boarding / winch assist
  - [ ] Slight armor vs bullets (not jets)
  - [ ] Fuel tank / refuel rate

## Enemy Behavior Readability + Counterplay

- [ ] Clearer telegraphs (artillery lead-in, jet approach commitment)
- [ ] Ensure each threat has a reliable counterplay option

## Risk/Reward Scoring (Combos / Mastery)

- [ ] Streaks and challenge-style bonuses (no traditional score required)
  - [ ] “3 rescues without taking damage”
  - [ ] “Low-altitude extraction”
  - [ ] “No flares used”

## Dynamic Difficulty / Director

- [ ] Adaptive threat budget based on player performance
- [ ] Safety valves when player is struggling (more pickups / less pressure)

## Onboarding / First Mission

- [ ] Mission 1 teaches: boarding flow, flare window, jet avoidance, safe landing
- [ ] Reduce early confusion without adding a formal tutorial UI

## One New Toy Mechanic

- [ ] Pick one new player tool (examples)
  - [ ] EMP burst
  - [ ] Pickup drone
  - [ ] Smoke marker for safe landing zone

---

## Baseline (now)

- Windows build: PyInstaller **onefile** works.
- Intro video: `src/choplifter/assets/intro.mpg` is the active intro.
- Repo note: `intro.mpg` is tracked via **Git LFS** (required for full asset checkout).

## Next (small, shippable steps)

- [x] Add a short README note about Git LFS (`git lfs install` + `git lfs pull`) so new clones get `intro.mpg`.
- [x] Add/verify an in-game “Skip Intro” hint + ensure skip works instantly on keypress.
- [x] Tune helicopter feel (document the knobs and current values): `engine_power`, `friction`, `max_speed`, `tilt_rate`, `max_tilt`.
- [x] Mission flow polish: clear “start mission / retry / back to mission select” loop.

## Gameplay (Milestone-driven)

- [ ] Rescue loop polish: hostage movement caps + clearer grounded/doors-open feedback.
- [ ] Threat readability pass: ensure tanks/jets/mines have distinct audio/visual tells.
- [ ] Add a simple global consequence meter (start with **Sentiment**) and show it in debrief.

## Later

- [ ] Weather: sandstorm visibility + wind gusts affecting vertical velocity.
- [ ] Vertical mission segments (rooftop extractions).
- [ ] Mission-specific cutscenes (in-engine timeline, not video).
