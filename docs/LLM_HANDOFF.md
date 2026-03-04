# LLM Handoff (Docs Copy)

This file is a working copy of the repo-root `LLM_HANDOFF.md`, placed under `docs/` so project documentation can live in one predictable location.

If you update one version, consider updating the other to keep them consistent.

---

This document, `LLM_HANDOFF.md`, is designed to provide a high-level technical and thematic bridge for a modern AI-assisted development workflow. It translates the 1982 assembly-level logic of *Choplifter* (based on Quinn Dunki’s reverse engineering) into a 2026-ready architectural framework for **Choplifter: The Middle East Recall**.

---

# LLM_HANDOFF.md: Choplifter Reconstruction Project

## 1. Project Overview

* **Title:** Choplifter: The Middle East Recall (2026)
* **Objective:** A "Logically Faithful" remake of the Commodore 64/Apple II classic.
* **Core Philosophy:** Maintain the 1982 physics-based "feel" and the "Human-First" (No Score) scoring system while modernizing the combat environment for 2026 Middle East geopolitical themes.

---

## 2. Reverse Engineering Core Logic (The "Brain")

To maintain the authentic "Choplifter feel," the following logic must be ported from the original 6502 assembly research:

### A. The "Fudged" Physics Model

* **Inertia State Machine:** The helicopter should not stop instantly. Implement a velocity decay function: $v_{t+1} = v_t \times \text{friction}$.
* **The Pitch-Roll Variable:** The sprite/model tilt must dictate horizontal acceleration. $a_x = \sin(\theta) \times \text{engine\_power}$.
* **Ground Effect:** (New 2026 Logic) When $Altitude < 5m$, increase upward force by **15%** but decrease visibility due to particulate (sand) displacement.

### B. Hostage AI (The "64-Thinker" Array)

* **Memory Structure:** Maintain a 64-element array tracking `[State, X_Pos, Y_Pos, Health, Target]`.
* **States:** `IDLE` (in barracks), `PANIC` (running toward chopper), `BOARDED`, `SAVED`, or `KIA`.
* **Priority Logic:** Hostages prioritize the nearest "Landing Zone" (LZ) provided the helicopter is grounded and the bay doors are open.

---

## 3. 2026 Technical Stack & Integration

The LLM should prioritize the following modern implementation strategies:

* **Logic Bridge:** Use a "Middle-Out" approach. The core game loop should run at **60Hz**, mirroring the original NTSC/PAL cycles, even if the visual renderer runs higher.
* **Modern Entities (Mapping):**
* `Enemy_Tank` $\rightarrow$ **Autonomous UGV** (with IR jamming).
* `Enemy_Jet` $\rightarrow$ **Loitering Munition Drones** (High speed, kamikaze behavior).
* `Barracks` $\rightarrow$ **Secured Compounds/Safehouses**.

---

## 4. Feature Requirements (The "Recall" Enhancements)

* **Media Narrative System:** Replace the "Score" with a **Global Sentiment Meter**.
* *Saving Hostages:* Increases "International Support" (Unlockable armor/fuel).
* *Collateral Damage:* Decreases "Support," triggering **No-Fly Zones** (SAM sites) that the player must navigate.

* **The Vertical Expansion:** Restore the "lost" vertical scrolling found in the assembly code. Missions should now include **Skyscraper Extractions** and **Subterranean Extraction Points**.
* **Dynamic Weather:** Implement a "Sandstorm" mechanic that affects the `Physics Model` (Wind gusts affecting $v_y$) and limits the player's radar range.

---

## 5. Developer Prompting Instructions (For next AI Session)

> "Referencing the `LLM_HANDOFF.md` for *Choplifter: The Middle East Recall*, please generate a **Python/Pygame** (or C++/SFML) prototype for the **Helicopter Physics Controller**. Ensure the 'Tilt-to-Accelerate' logic uses the momentum decay variables specified. Additionally, draft a class for the **Hostage AI** that manages a 64-index array to track state changes from 'Barracks' to 'Safe Zone'."

---

## 6. Critical Constraints

* **The "End" Clause:** Never use "Game Over." The game must conclude with a cinematic "The End," followed by a statistical summary of lives saved vs. lives lost.
* **Landing Sensitivity:** The helicopter "CRUSH" collision box must be active. If the `Vertical Velocity` exceeds a threshold of $1.5 \text{m/s}$ upon contact with a hostage entity, the hostage state changes to `KIA`.

---

## 7. Repository Reality Check (Current Prototype)

This section is for future LLMs working on the *actual* code in this repository.

### What exists today

- Python + Pygame prototype with a playable rescue loop (open compounds → board hostages → unload at base → win at 20 saved).
- Intro cutscene video playback (with optional audio extraction/playback) and a skip hint.
- Windows packaging via PyInstaller (both onefile and onedir builds).

### Entry points & layout

- Entrypoint: `run.py` imports `src.choplifter.main:run`.
- Game loop/state: `src/choplifter/main.py`.
- App helpers (early modularization): `src/choplifter/app/` (cutscene state + helpers).
- Mission/rescue logic: `src/choplifter/mission.py`.
- Mission configs/tuning: `src/choplifter/mission_configs.py` (LevelConfig + MissionTuning + `get_mission_config_by_id`).
- Helicopter physics: `src/choplifter/helicopter.py` (plus tuning in `src/choplifter/settings.py`).
- Rendering/HUD: `src/choplifter/rendering.py`.
- Logging helper: `src/choplifter/game_logging.py`.
- Intro: `src/choplifter/intro_video.py`.

### Cutscenes (current)

- Intro video plays on launch (skippable).
- Mission cutscene: when the first 16 hostages are boarded, the game attempts to play `src/choplifter/assets/hostage-rescue-cutscene.mpg` once per mission run (skippable; will not replay until mission reset).

### Running (Windows)

- Recommended (always uses the repo venv): `./.venv/Scripts/python.exe run.py`
- If you activate first (`./.venv/Scripts/Activate.ps1`), then `python run.py` works.
- Avoid `py run.py` unless you intentionally want to use the global Python install (it will not see venv packages like `pygame`).

### Logs

- Preferred location on Windows: `%LOCALAPPDATA%\Choplifter\logs\session-*.log`
- Development fallback: `./logs/session-*.log`

### Assets (Git LFS)

- Large assets (notably `src/choplifter/assets/intro.mpg`) are tracked via Git LFS.
- Fresh clones typically need `git lfs install` and `git lfs pull`.

### Optional JSON configs (no in-game UI)

- `controls.json` (copy from `controls.example.json`)
- `accessibility.json` (copy from `accessibility.example.json`)
- `physics.json` (copy from `physics.example.json`)

### Packaging (Windows EXE)

- Build script: `scripts/build_windows_exe.ps1`
- Onefile: `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_exe.ps1 -Mode onefile`
- Onedir: `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_exe.ps1 -Mode onedir`
- Outputs: `pyinstaller-dist/Choplifter.exe` (onefile), `pyinstaller-dist/Choplifter/Choplifter.exe` (onedir)

### Recent merged gameplay polish (important context)

- Rescue loop readability: HUD displays grounded/doors state during missions.
- Hostage movement: when hostages begin moving to the helicopter, the game mixes a more controlled “queue” behavior with an occasional chaotic rush. This is controlled by `MissionTuning` fields in `src/choplifter/mission.py`:
	- `hostage_controlled_*`, `hostage_chaotic_*`, `hostage_chaos_probability`
