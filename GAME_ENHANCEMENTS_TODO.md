# Game Enhancements — TODO / Backlog

This is the working backlog for incremental improvements on top of the current playable build.

## Baseline (now)

- Windows build: PyInstaller **onefile** works.
- Intro video: `src/choplifter/assets/intro.mpg` is the active intro.
- Repo note: `intro.mpg` is tracked via **Git LFS** (required for full asset checkout).

## Next (small, shippable steps)

- [ ] Add a short README note about Git LFS (`git lfs install` + `git lfs pull`) so new clones get `intro.mpg`.
- [ ] Add/verify an in-game “Skip Intro” hint + ensure skip works instantly on keypress.
- [ ] Tune helicopter feel (document the knobs and current values): `engine_power`, `friction`, `max_speed`, `tilt_rate`, `max_tilt`.
- [ ] Mission flow polish: clear “start mission / retry / back to mission select” loop.

## Gameplay (Milestone-driven)

- [ ] Rescue loop polish: hostage movement caps + clearer grounded/doors-open feedback.
- [ ] Threat readability pass: ensure tanks/jets/mines have distinct audio/visual tells.
- [ ] Add a simple global consequence meter (start with **Sentiment**) and show it in debrief.

## Later

- [ ] Weather: sandstorm visibility + wind gusts affecting vertical velocity.
- [ ] Vertical mission segments (rooftop extractions).
- [ ] Mission-specific cutscenes (in-engine timeline, not video).
