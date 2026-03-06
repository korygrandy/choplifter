# Game Enhancements - TODO / Backlog

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
- [ ] Evaluate a "lite media" build mode that skips video dependencies for smaller distribution builds.
- [ ] Convert largest WAV effects to compressed audio where quality remains acceptable.

### Onefile Size Reduction Baseline (Measured)

- Current onefile output:
	- Latest measured `pyinstaller-dist/Choplifter.exe` is about `227.17 MB`.
	- Previous baseline was about `330.56 MB`.
	- Net reduction so far is about `103.39 MB`.
- Largest media payloads in `src/choplifter/assets`:
	- `intro.avi` (re-encoded, smaller than previous `intro.mpg`).
	- `hostage-rescue-cutscene.avi` (re-encoded, smaller than previous `hostage-rescue-cutscene.mpg`).
	- `chopper-flying.wav` about `9.92 MB`
- Packaging/runtime contributors in onedir:
	- bundled ffmpeg from `imageio-ffmpeg` about `83.58 MB` (inside `_internal`)
	- `numpy` about `19.46 MB`
- Current script behavior:
	- `scripts/build_windows_exe.ps1` stages assets and skips legacy `intro.mpg`/`hostage-rescue-cutscene.mpg` when `.avi` alternatives are present.
	- Video dependencies (`imageio`, `imageio-ffmpeg`) are still included by default.

### Onefile Size Reduction Plan (Highest Impact First)

- [x] Re-encode intro and mission cutscene videos first.
	- `intro.avi` and `hostage-rescue-cutscene.avi` are now used by default.
	- Legacy `.mpg` variants are excluded from build staging when `.avi` files are present.
- [ ] Create a "lite media" profile with no video playback dependency.
	- Add a build flag in `scripts/build_windows_exe.ps1` (for example `-LiteMedia`).
	- In lite mode:
		- Do not include `imageio` / `imageio-ffmpeg` metadata collection.
		- Do not include large video files in `--add-data`.
		- Use existing fallback intro/title-card behavior when video is unavailable.
	- Expected win: roughly `-100 MB` more (ffmpeg + numpy + related hooks), plus skipped video assets.
- [ ] Compress/convert WAV SFX to OGG.
	- Convert largest SFX (`chopper-flying.wav`, `fighter-jet-flyby.wav`, etc.) to `.ogg`.
	- Update asset loading in `src/choplifter/audio.py` and `src/choplifter/audio_extra.py` to prefer `.ogg`.
	- Expected win: usually `-10 MB` to `-25 MB` depending quality settings.
- [ ] Stop shipping non-runtime source assets.
	- Exclude files such as `chopper-one.xcf` from packaged output.
	- Replace broad asset inclusion with explicit include patterns or an asset manifest.
	- Expected win: small but clean (`~4.44 MB` immediate, plus long-term hygiene).
- [ ] Optimize images losslessly.
	- Run PNG/JPG optimization pass (for example `oxipng`, `jpegoptim`, or `mozjpeg`).
	- Expected win: modest (`~2 MB` to `~8 MB`) without visual quality loss.
- [ ] Keep onefile for distribution convenience only.
	- Onefile size will track total payload size; it is not an automatic size reduction format.
	- Use onedir for profiling and iteration, then generate final onefile deliverables.

### Recommended Execution Order

1. Add and validate `-LiteMedia` profile (no ffmpeg/imageio + fallback intro).
2. Optionally convert large SFX to OGG.
3. Finalize explicit asset manifest/include list.
4. Build and re-measure onefile and onedir outputs.

## Gameplay / UX Improvements

- [ ] Rescue readability polish (boarding feedback, grounded/doors clarity).
	- [ ] Define boarding UX states (`approaching`, `boarding`, `boarded`, `blocked`).
	- [x] Add clear boardability indicator when helicopter is in valid pickup conditions.
	- [x] Add outcome toasts for blocked boarding reasons (`Too high`, `Too fast`, `Doors closed`, `Not grounded`).
	- [x] Add/confirm grounded-state indicator in HUD.
	- [x] Add/confirm door-state indicator in HUD (`OPEN`/`CLOSED`).
	- [x] Add cooldown/debounce for prompt flicker to avoid noisy UI.
	- [ ] Add accessibility pass for color + shape readability.
	- [ ] Add telemetry counters for failed board attempts by reason.
	- [ ] Tune boarding thresholds after playtest.
- [ ] Threat readability pass (distinct tells for tanks/jets/mines).
	- [ ] Create threat tell matrix per enemy (cue, lead time, effective range).
	- [x] Tanks: add pre-fire turret tell and muzzle flash timing window.
	- [x] Jets: add early warning cue before attack run.
	- [x] Mines: add visibility pulse/glint and proximity warning cue.
	- [ ] Ensure each threat has distinct visual + audio signature.
	- [ ] Add colorblind-safe cue alternatives.
	- [x] Add debug overlay for active tell windows.
	- [ ] Balance false positives vs missed warnings.
- [ ] Sentiment/consequence meter in debrief and progression.
	- [ ] Define sentiment inputs (rescues, losses, collateral, objective quality).
	- [ ] Define scoring bands and labels (`Excellent`/`Good`/`Mixed`/`Poor`/`Critical`).
	- [ ] Add debrief meter UI with reason breakdown lines.
	- [ ] Persist sentiment across mission progression.
	- [ ] Tie progression modifiers to sentiment bands.
	- [ ] Add balancing guardrails so one event cannot dominate outcome unfairly.
	- [ ] Add tests for score computation and persistence.

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

- [ ] Missile/flar diversion behavior.
	- If flares are active, override BARAK target vector to decoy direction `(0, -1)`.
	- Normalize naming to `flare` across code/data (keep compatibility aliases if needed).
	- Define diversion eligibility (range, timing window, missile types).
	- Implement target override to decoy vector/position while flare is active.
	- Add smooth retargeting limits (turn-rate cap) to avoid unnatural snaps.
	- Add diversion feedback cue (trail bend + audio).
	- Handle edge cases (flare expiry mid-flight, no active flare, multiple flares).
	- Add tunables (chance, radius, max turn rate, flare lifetime).
	- Add tests for diversion success/failure branches.
- [ ] MRAP and launcher state cycle.
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

- [ ] Supply drop physics + munitions manager.
	- Build manager for spawn timing, sway motion (`sin` horizontal offset), and gravity.
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
