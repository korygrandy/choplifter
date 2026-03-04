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

## SmartScreen (“this app may be harmful”) and how to eliminate it

If you zip up `Choplifter.exe`, download it on another machine, and Windows warns that it may be harmful, that is typically **Windows SmartScreen**.

Why it happens:

- **Unsigned executable**: without an Authenticode signature, SmartScreen has no verified publisher identity.
- **Low reputation**: even signed apps can warn until enough users run it (reputation builds over time).
- **“Internet download” tag (MOTW)**: Windows marks downloaded files as coming from the internet; extracted executables may inherit that marking.
- **Onefile builds** can trigger more heuristics than onedir builds.

What “no warnings for public users” realistically requires:

- **Sign the EXE** with an Authenticode code signing certificate and **timestamp** it.
  - For best results with SmartScreen, many teams use an **EV code signing certificate** (typically improves trust/reputation behavior vs OV).
- Distribute from a stable channel (GitHub Releases, itch.io, your domain) and keep the publisher identity consistent.

Important: while signing is the only practical path, SmartScreen behavior is not something you can 100% guarantee across every machine immediately (reputation can still matter). EV certs typically minimize that pain.

### Optional: sign during build (recommended for public distribution)

The build script supports an optional signing step (it is **off by default**).

Prereqs:

- Install the Windows SDK Signing Tools (so `signtool.exe` exists), or set `SIGNTOOL_PATH` to your `signtool.exe`.
- Obtain a code signing certificate:
  - **EV** (best for SmartScreen) or **OV** (works, but may take longer to gain reputation).

#### Option A: Sign using a PFX file

1) Set your PFX password in an environment variable (avoid putting passwords in command history):

- `setx CHOPLIFTER_PFX_PASSWORD "<your password>"`

2) Build + sign:

- `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_exe.ps1 -Mode onefile -Sign -PfxPath .\path\to\cert.pfx`

Notes:

- The script reads the password from `CHOPLIFTER_PFX_PASSWORD` by default.
- Timestamping defaults to `http://timestamp.digicert.com` and can be overridden with `-TimestampUrl`.

#### Option B: Sign using a cert from the Windows Certificate Store

If your cert is installed in the cert store, sign with its thumbprint:

- `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_exe.ps1 -Mode onefile -Sign -CertThumbprint <SHA1THUMBPRINT>`

### Tester-only workaround (not a real public solution)

If you are sharing a zip with testers, they can remove the “downloaded from the internet” marker:

- Right-click the downloaded `.zip` → **Properties** → **Unblock** → Apply → then extract.

This can reduce prompts, but it does not replace signing for public distribution.

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