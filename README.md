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

## Quick Start (Windows)

1. Install dependencies into the project venv:
   - `./.venv/Scripts/python.exe -m pip install -r requirements.txt`
2. Run the game:
   - `./.venv/Scripts/python.exe run.py`

Notes:
- If you activate first (`./.venv/Scripts/Activate.ps1`), then `python run.py` works.
- Avoid `py run.py` unless you intentionally want your global Python.

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

## Build Size Notes

Current onefile size is primarily driven by media payload and ffmpeg/runtime dependencies.

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
