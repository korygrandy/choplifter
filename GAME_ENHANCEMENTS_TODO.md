# Planned Mission: Airport Special Ops

## Mission Concept
Escort a transport bus across an airport tarmac to rescue hostages from a crashed plane and jetway guarded by militants. The player must protect the bus as it travels from right to left, allow hostages to board, then escort the bus and hostages back to the LZ (modeled after an airport tower). The bus is a rectangle placeholder until a sprite is available.

## Mission Flow
1. Mission start: player and bus at right side, bus begins moving left.
2. Bus must reach the crashed plane/jetway, under fire from militants.
3. Hostages board the bus (timed or triggered event).
4. Player protects bus and hostages as bus returns to LZ.
5. At LZ, bus doors open and hostages deboard.
6. Mission success/failure based on hostages rescued, bus survival, and other conditions.

## Open Design Questions & Clarifications
- How does the mission start? (cutscene, briefing, immediate action)
- What are the win/lose conditions? (all hostages rescued, bus destroyed, time limit, etc.)
- Are there optional/bonus objectives? (e.g., no bus damage, defeat all militants)
- What types of militants are present? (stationary, patrolling, weapon types)
- Are there environmental hazards? (wreckage, fire, barricades, mines)
- Will enemies attack the bus, player, or both?
- How is the bus controlled? (AI path, stops at obstacles, player-escorted)
- How do hostages board/deboard? (timed, triggered, can be interrupted)
- Can the bus or hostages take damage? What are the consequences?
- What tools does the player have to protect the bus? (weapons, air support, haptics)
- Can the player interact with the environment? (clear obstacles, repair bus, open jetway)
- Is there risk/reward for leaving the bus to engage enemies?
- How is the airport LZ/tower area structured? (cover, sightlines, enemy positions)
- Are there multiple routes or just one path for the bus?
- Is the crashed plane/jetway a single setpiece or multi-stage area?
- How is tension maintained? (enemy waves, timed events, bus health)
- Are there moments of downtime or constant action?
- How does difficulty scale? (more/tougher enemies, environmental changes)
- How will the bus, hostages, and LZ be visually distinguished?
- What feedback will the player get for protecting/failing the bus/hostages?
- Are there unique audio cues or music for this mission?
- What new code modules or data structures are needed? (bus AI, hostage logic, enemy spawns)
- What placeholder assets are required before final art?
- How will you test and debug the mission flow?

## Implementation Notes
- Bus uses rectangle placeholder until sprite is ready.
- LZ modeled after airport tower.
- Hostage, bus, and enemy logic may require new or updated modules.
- Track all clarifications and design decisions here as they are resolved.

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
- [ ] Evaluate a "lite media" build mode that skips video dependencies for smaller distribution builds. (deferred/skipped for now)
- [ ] Convert largest WAV effects to compressed audio where quality remains acceptable. (deferred/skipped for now; `.ogg` assets already integrated and playing)

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
	- `chopper-flying.wav` about `9.92 MB`
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
- [ ] Compress/convert WAV SFX to OGG. (deferred/skipped for now)
	- Convert largest SFX (`chopper-flying.wav`, `fighter-jet-flyby.wav`, etc.) to `.ogg`.
	- Update asset loading in `src/choplifter/audio.py` and `src/choplifter/audio_extra.py` to prefer `.ogg`.
	- Expected win: usually `-10 MB` to `-25 MB` depending quality settings.
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
