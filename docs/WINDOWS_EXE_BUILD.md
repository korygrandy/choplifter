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

## Asset Manifest Behavior

The build script now stages assets through an explicit runtime manifest before invoking PyInstaller.

- Source: `src/choplifter/assets`
- Staging folder: `pyinstaller-build/asset-staging`
- Included extensions: `.png`, `.jpg`, `.jpeg`, `.ogg`, `.avi`, `.mpg`, `.json`

Additional staging rule:
- If both `.avi` and `.mpg` exist for the same relative media path, the legacy `.mpg` variant is excluded.
- If any `.xcf` file is detected in staged assets, the build fails fast (guardrail for both onefile and onedir modes).

This prevents non-runtime source files (for example `.xcf`) from being bundled into distributable EXEs.

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

Recent onefile builds are large primarily due to media and video runtime dependencies.

Current measured baseline:
- `pyinstaller-dist/Choplifter.exe`: about `318.34 MB`
- `pyinstaller-dist/Choplifter/_internal` payload: about `427.77 MB`

Largest contributors typically include:
- `src/choplifter/assets/intro.mpg`
- `src/choplifter/assets/hostage-rescue-cutscene.mpg`
- bundled `imageio-ffmpeg` executable/runtime (about `83.58 MB`)
- compressed OGG sound assets

## Size Reduction Plan

1. Keep explicit runtime asset staging (already implemented) and monitor staged payload deltas after content changes.
2. Add optional "lite media" build profile (skip video runtime/deps, use cutscene fallback) if distribution size must drop further.
3. Continue monitoring audio payload size after the OGG migration and re-measure package outputs.
4. Optimize PNG/JPG assets losslessly for small incremental reductions.

## Troubleshooting

- Missing DLL/runtime issues on target machine:
  - Install Microsoft Visual C++ Redistributable.
- No audio on target machine:
  - Verify audio device and mixer initialization.
- Missing large media assets after clone:
  - Run `git lfs install` then `git lfs pull`.
