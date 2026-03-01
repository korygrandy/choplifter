# Web Build (Playable in Browser)

This project is a Python + Pygame game. The simplest path to a web-playable build is **`pygbag`**, which packages it to WebAssembly + a static site.

## Prereqs

- Python 3.11+ (this repo uses 3.13 in the venv)
- Create/activate venv and install deps:
  - `pip install -r requirements.txt`
  - `pip install pygbag`

## Build with pygbag

From the repo root:

- Build:
  - `pygbag --build run.py`

Notes:
- If you run into asset-loading issues in the browser, ensure assets are referenced via package-relative paths (the build environment is not the same as desktop).
- Web builds can differ in audio behavior/perf; keep expectations realistic for the first pass.

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
