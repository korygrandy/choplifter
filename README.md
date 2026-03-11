# Choplifter (Python/Pygame Prototype)

This repository contains a playable Choplifter-style rescue prototype built with Python + Pygame.

The current branch includes a major mission/main refactor, weather and FX systems, cutscene playback, accessibility toggles, and Windows packaging support.

## Current Status

- Playable rescue loop: open compounds, board hostages, unload at base, complete mission.
- Mission logic modularized from monolithic flow into focused modules.
- Main loop cleanup completed (input/pause/menu flow more maintainable).
- Weather/FX systems: rain, fog, dust, lightning, storm clouds.
- Intro + mission cutscene playback with skip controls.
- Windows EXE builds (onefile and onedir) via PyInstaller.
- Airport Special Ops mission supports a split rescue objective with combined completion target:
  - total target: 16 civilians per mission
  - lower terminal civilians: helicopter rescue path
  - elevated jetway civilians: meal-truck to bus transfer path
  - airport run success is based on combined rescued count across both paths

## Quick Start (Windows)

1. Install dependencies into the project venv:
   - `./.venv/Scripts/python.exe -m pip install -r requirements.txt`
2. Run the game:

- `& .\.venv\Scripts\python.exe .\run.py`

Notes:

- If you activate first (`./.venv/Scripts/Activate.ps1`), then `python run.py` works.
- Avoid `py run.py` unless you intentionally want your global Python.

## QA Validation

Automated airport smoke suite (fast regression gate):

- `powershell -ExecutionPolicy Bypass -File .\scripts\run_airport_smoke.ps1`

Direct pytest equivalent:

- `.\.venv\Scripts\python.exe -m pytest -q -m airport_smoke`

Manual follow-up:

- Run the `10-Minute Smoke Pass` in `docs/AIRPORT_MISSION_PLAYTEST_GUIDE.md`
- Submit the smoke report using the command card template in `docs/AIRPORT_MISSION_PLAYTEST_GUIDE.md`

## Controls

### Keyboard

- Move/tilt: `A/D` or Left/Right arrows
- Lift: `W/S` or Up/Down arrows
- Brake/hover assist: `Shift`
- Fire: `Space`
- Flares: `F`
- Doors (grounded): `E`
- Cycle facing: `Tab`
- Reverse flip: `R`
- Pause: `Esc`
- Thermal mode: `T`

Debug-related:

- Toggle debug weather mode: `F3`
- Cycle weather while debug mode is on: `F5` / `F6`
- Toggle overlay via configurable control mapping (default `F1`)

### Gamepad (Xbox-style)

- Left stick X: tilt
- Triggers: lift down/up
- `A`: doors
- `X`: fire
- `B`: flares
- `Y`: reverse flip
- `Back`: cycle facing
- `Start`: pause/resume
- `LB`: debug overlay toggle
- D-pad: optional discrete input/menu navigation

Airport mission interaction notes:

- `E` / `A` near meal truck: deploy/return engineer and toggle truck driver mode.
- `Space` / `X` while driving meal truck: toggle lift extension command.
- `E` / `A` near bus (when tech is on bus): toggle bus driver mode.

## Optional Config Files

- `controls.json` (from `controls.example.json`)
- `accessibility.json` (from `accessibility.example.json`)
- `physics.json` (from `physics.example.json`)

If missing/invalid, defaults are used.

## Logging

Session logs are written to:

- Preferred: `%LOCALAPPDATA%/Choplifter/logs/session-*.log`
- Fallback: `./logs/session-*.log`

## Build Windows EXE

Use the included script:

- Onedir:
  - `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_exe.ps1 -Mode onedir`
- Onefile:
  - `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_exe.ps1 -Mode onefile`

Outputs:

- `pyinstaller-dist/Choplifter/Choplifter.exe` (onedir)
- `pyinstaller-dist/Choplifter.exe` (onefile)

Current packaging behavior:

- Assets are staged through an explicit runtime manifest at `pyinstaller-build/asset-staging` before PyInstaller runs.
- Included extensions: `.png`, `.jpg`, `.jpeg`, `.wav`, `.ogg`, `.avi`, `.mpg`, `.json`.
- Non-runtime source assets (for example `.xcf`) are excluded from staged output.
- Legacy `.mpg` files are excluded when same-path `.avi` variants exist.

## Build Size Notes

Current onefile size is primarily driven by media payload and ffmpeg/runtime dependencies.

Latest measured onefile baseline:

- `pyinstaller-dist/Choplifter.exe`: about `318.34 MB`

Largest contributors are typically:

- `src/choplifter/assets/intro.mpg`
- `src/choplifter/assets/hostage-rescue-cutscene.mpg`
- Bundled `imageio-ffmpeg` binary
- Uncompressed WAV files

See `docs/WINDOWS_EXE_BUILD.md` for optimization guidance.

## Git LFS Assets

Large media assets are tracked with Git LFS.

- `git lfs install`
- `git lfs pull`

Without LFS pull, intro/cutscene assets may be missing.

## Documentation Index

- `LLM_HANDOFF.md`: engineering handoff and architecture map
- `GAME_ENHANCEMENTS_TODO.md`: backlog and completion state
- `GAME_PLAN.md`: design direction and milestone framing
- `docs/WINDOWS_EXE_BUILD.md`: packaging and signing
- `docs/WEB_BUILD.md`: browser build notes
- `docs/EXECUTIVE_SUMMARY.md`: product-level summary
- `docs/AIRPORT_MISSION_PLAYTEST_GUIDE.md`: airport full matrix + smoke pass command card
