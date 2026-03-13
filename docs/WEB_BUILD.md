# Web Build (Playable in Browser)

This project is a Python + Pygame game. The current browser path is **`pygbag`**, which packages to WebAssembly + static site output.

## Prereqs

- Python 3.11+ (this repo currently uses 3.13 in the venv)
- Create/activate venv and install deps:
  - `pip install -r requirements.txt`
  - `pip install pygbag`

## Build with pygbag

From the repo root:

Note:
- This repo includes a local `.venv` folder. `pygbag` will try to scan everything under the project root unless told to ignore directories.
- A `pygbag.ini` is included to ignore `.venv` and other non-game folders so web builds are reliable.

- Build command:
  - `pygbag --build --disable-sound-format-error run.py`

Note:
- `pygbag` prefers `.ogg` for web audio. The runtime SFX assets are now `.ogg`, so the browser audio path aligns with the packaged desktop assets.

Notes:
- If you run into asset-loading issues in the browser, ensure assets are referenced via package-relative paths.
- Browser builds may differ from desktop for audio timing/performance and heavy FX.
- Large video assets can increase download/startup time significantly.

## Test locally

`pygbag` produces a static site folder; serve it with any static server.

Example (Python built-in server):

- `python -m http.server 8000`

Then open `http://localhost:8000` in your browser.

## Deploy (two easy options)

### Option A: GitHub Pages (manual upload)

1. Build with `pygbag`.
2. Locate the build output folder produced by `pygbag`.
3. Publish it:
   - Either commit the built site into a `gh-pages` branch, or
   - Copy the built site into a folder GitHub Pages serves (commonly `/docs`) and enable Pages in repo settings.

### Option B: itch.io (HTML5)

1. Build with `pygbag`.
2. Zip the build output folder.
3. Upload as an **HTML5** project on itch.io.

## Troubleshooting

- **Black screen / nothing loads**: check browser console for missing files; verify all required assets are included in the build output.
- **Audio doesn’t play**: browsers often require a user gesture before audio; test after pressing a button.
- **Performance**: reduce particle counts / expensive per-frame allocations; prefer cached Surfaces.
