# Windows (64-bit) EXE Build

This project can be packaged into a Windows executable using **PyInstaller**.

## Prereqs

- Windows 10/11 64-bit
- Python installed (you already have a project venv at `.venv`)

## 1) Install dependencies

From the repo root:

- `.venv\Scripts\python.exe -m pip install -r requirements.txt`

## 2) Build an executable

A build script is included:

- **One-folder build (recommended while iterating):**
  - `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_exe.ps1 -Mode onedir`

- **One-file build (single EXE):**
  - `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_exe.ps1 -Mode onefile`

By default, this produces a windowed app (no console). To build a console version:

- `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_exe.ps1 -Mode onedir -Console`

## 3) Find the output

The output is placed in:

- `pyinstaller-dist\Choplifter\` (onedir)
- `pyinstaller-dist\Choplifter.exe` (onefile)
- `pyinstaller-dist\choplifter.zip` (convenience zip; contents may include the onedir build)

## Notes

- Assets are bundled from `src/choplifter/assets`.
- Logs are written to a per-user folder when possible (e.g. `%LOCALAPPDATA%\Choplifter\logs`).

## Troubleshooting

- If you see missing DLL errors on another machine, install the **Microsoft Visual C++ Redistributable**.
- If audio is missing, ensure `pygame.mixer` initializes correctly on that machine (some audio devices/drivers can block init).