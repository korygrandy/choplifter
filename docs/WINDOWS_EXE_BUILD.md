# Windows (64-bit) EXE Build

This project packages with PyInstaller using `scripts/build_windows_exe.ps1`.

## Prerequisites

- Windows 10/11 x64
- Project virtual environment at `.venv`
- Dependencies installed:
  - `.venv\Scripts\python.exe -m pip install -r requirements.txt`

## Build Commands

From repo root:

- Onedir (recommended during iteration):
  - `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_exe.ps1 -Mode onedir`
- Onefile:
  - `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_exe.ps1 -Mode onefile`
- Console variant (debugging/log visibility):
  - `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_exe.ps1 -Mode onedir -Console`

## Build Outputs

- Onedir EXE: `pyinstaller-dist/Choplifter/Choplifter.exe`
- Onefile EXE: `pyinstaller-dist/Choplifter.exe`

## Signing (Optional but Recommended)

The build script supports signing with `-Sign`.

### PFX file mode

- Set password env var (example):
  - `setx CHOPLIFTER_PFX_PASSWORD "<password>"`
- Build and sign:
  - `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_exe.ps1 -Mode onefile -Sign -PfxPath .\path\to\cert.pfx`

### Windows cert store mode

- `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_exe.ps1 -Mode onefile -Sign -CertThumbprint <SHA1THUMBPRINT>`

## SmartScreen Notes

Unsigned executables can trigger SmartScreen warnings. Signing plus consistent publisher identity is the practical mitigation path.

## Build Size (Important)

Recent onefile builds are large (about 300MB+) primarily due to media and video runtime dependencies.

Largest contributors typically include:
- `src/choplifter/assets/intro.mpg`
- `src/choplifter/assets/hostage-rescue-cutscene.mpg`
- bundled `imageio-ffmpeg` executable/runtime
- large WAV files

## Size Reduction Plan

1. Re-encode large MPG files to compressed MP4.
2. Add optional "lite media" build profile (skip video runtime/deps, use cutscene fallback).
3. Convert heavy WAV assets to compressed OGG where acceptable.
4. Include runtime assets explicitly rather than bundling broad source trees.

## Troubleshooting

- Missing DLL/runtime issues on target machine:
  - Install Microsoft Visual C++ Redistributable.
- No audio on target machine:
  - Verify audio device and mixer initialization.
- Missing large media assets after clone:
  - Run `git lfs install` then `git lfs pull`.
