# Choplifter Sequel — Game Plan (Working Doc)

## 0) Goals & Non-Goals

**Goal:** Build a *sequel* that preserves the original’s signature feel (tilt-to-accelerate inertia flight + tense rescues) while adding modern mission variety and a small amount of systemic consequence.

**Non-goals (for MVP):** Open world, crafting, RPG stats, complex narrative branching, online multiplayer.

## 1) Design Pillars

1. **Flight first:** The helicopter should feel weighty, “fudged,” and learnable—not sim-like, not twitch-arcade.
2. **Rescue is the point:** Combat exists to create pressure around extraction, not to become the main objective.
3. **Clarity under stress:** Readable threats, readable landing, readable hostage state.
4. **Consequences without bookkeeping:** A small number of meaningful counters (fuel, damage, evac capacity, public sentiment) that drive decisions.

## 2) Player Fantasy & Core Loop

**Fantasy:** A pilot who threads a fragile aircraft through hostile airspace to extract civilians/POWs under time pressure.

**Core loop (one mission):**
- Ingress → locate/confirm extraction site(s) → suppress threats → land + load → egress to safe zone → debrief.

**Failure pressures:** fuel, damage, time window, air defenses, hostage risk.

### 2.1 Success / Grading (No Traditional “Score”)

- Track outcomes as **stats**, not points: `rescued`, `lost_in_transit`, `KIA_by_enemy`, `KIA_by_player`.
- Mission completion is based on **minimum rescued** (classic reference: 20+ is “success”, 40+ is “legendary”).
- End-of-run presentation uses **“The End”** (not “Game Over”), then a stat summary.

## 3) Setting & Tone (Modern Real-World Framing)

- Use contemporary aesthetics and threats (drones, MANPADS, EW), but keep depiction **neutral** and **human-first**.
- Avoid named real-world factions as protagonists/antagonists in the mechanics; keep adversaries as “hostile forces” with recognizable gear, and keep the focus on rescue outcomes.
- Optional (later): a short disclaimer that the game is fiction and does not endorse violence.

### 3.1 Legacy Lore Nods (Optional, Keep Original Text)

Use the classic manual’s tone and motifs as **inspiration** (write new text; don’t copy manual prose verbatim):

- **Antagonist codename:** “Bungeling Empire” as a satirical umbrella label for hostile forces.
- **Cover story / base logic:** helicopter smuggled in as “mail sorting equipment,” which justifies the **Post Office** home base.
- **Inciting incident:** a time-sensitive window opens when an enemy holding site “catches fire” (often player-caused via break-in).
- **Manual humor:** light, punny control explanations and mission briefings to contrast the on-screen tension.

## 4) Game Structure

### 4.1 View / Format
- **2D side-scrolling** with horizontal traversal as the default, plus optional vertical segments for modern mission variety.
- **Deterministic 60 Hz logic tick** (even if rendering >60).
- **Prototype resolution:** **1280×720** (16:9).

### 4.2 Mission Template
Each mission defines:
- Map bounds (width + optional height bands)
- 1–4 extraction sites (compounds/vehicles/rooftops)
- Hostage count + behavior modifiers
- Threat budget (ground + air + air defense)
- Weather state (clear/sandstorm/wind)
- Win condition (minimum extracted) + bonus targets

Also define:
- **Home base / safe zone** position (classic: far right) and whether enemies can pursue into it (classic: yes).
- **Hostage vulnerability rules:** whether enemies can target hostages on foot and what (if any) player weapons can harm hostages.

### 4.3 Mission Objective Variants (MVP-Friendly)

The current prototype already has the key counters to support objective variety with minimal new systems:
- `mission.stats.saved` (rescue progress)
- `mission.stats.tanks_destroyed` / `mission.stats.enemies_destroyed` (suppression progress)
- `mission.elapsed_seconds` (time pressure)
- Existing failure states: crash loss, out of fuel

Start with a small set of objective “templates” that re-use the same level content (compounds + base zone + enemy spawners), so variety is authored mostly through config.

**A) Classic Rescue (baseline)**
- Win: rescue at least `N` hostages (prototype uses `N=20`).
- Authoring knobs: `required_saved`, enemy tuning (jets/mines spawn), compound count.

**B) Time-Window Rescue**
- Win: rescue at least `N` within `T` seconds.
- Lose: time expires (end text still uses `THE END`).
- Authoring knobs: `time_limit_s`, `required_saved`, fuel drain (to force routing decisions).

**C) Rescue + Threat Suppression (bonus target becomes required)**
- Win: rescue at least `N` AND destroy at least `K` tanks (or `K` total enemies).
- Authoring knobs: `required_saved`, `required_tanks_destroyed` (or `required_enemies_destroyed`).

**D) Holdout Evac (survival clock)**
- Premise: extraction is “hot”; you must survive until pickup window.
- Win: survive `T` seconds after an event trigger (simple options: mission start, first compound opened, first hostage boarded).
- Authoring knobs: `holdout_seconds`, spike enemy rates during the window.

Later (after the above works):
- **Sequential LZs** (extract from compound A then B, with different threat budgets)
- **Vertical segment objective** (rooftop extraction) once vertical scrolling is introduced

### 4.4 Objective System — Implementation Sketch (Prototype-Aligned)

Keep the implementation minimal and data-driven:
- Add an `objective_kind` plus a small set of numeric params to the mission/level config.
- Replace the hard-coded win check (`saved >= 20`) with a function like `objective_complete(mission)`.

Recommended first-pass config shape:
- `required_saved: int`
- `time_limit_s: float | None`
- `required_tanks_destroyed: int | None`
- `holdout_seconds: float | None` + `holdout_start: {mission_start|first_compound_opened|first_boarded}`

HUD needs only one new line for MVP:
- `Objective: Rescued 12/20` (+ optional `Time 01:34` or `Tanks 1/3` when relevant)

## 5) Systems (MVP vs Later)

### 5.0 Cutscenes / Intro Presentation

**Near-term (MVP-friendly):** Add a short, skippable **intro cutscene** ("trailer feel") that plays **before Mission Select**, ending on black with:
- `CHOPLIFTER`
- `Mission: Middle East Rescue`

Implementation bias: build as an in-engine timeline/state (not a video file) so it stays lightweight, resolution-independent, and easy to theme.

**Later:** Add **mission-specific cutscenes** that play **after a mission is selected** (future TODO; implement in its own feature branch).

### 5.1 Helicopter Physics (MVP)
- **Inertia / friction:** $v_{t+1} = v_t \times friction$
- **Tilt-to-accelerate:** $a_x = \sin(\theta) \times engine\_power$
- **Landing sensitivity:** hard landings damage helicopter; landing on hostage can kill.
- **Ground effect (optional in MVP, easy toggle):** small lift bonus near ground, with dust reducing visibility.

Tunable constants to expose early:
- `engine_power`, `friction`, `max_speed`, `tilt_rate`, `max_tilt`, `gravity`, `lift`, `safe_landing_vy`

### 5.1.1 Facing / Flight Modes (MVP)

Anchor to the classic 3-facing readability:
- **Left-facing / right-facing:** travel + air-to-air gunning
- **Forward-facing:** bombing / landing / loading

Implementation note (prototype-friendly): facing can be *stateful* (explicit toggle) or *contextual* (auto-switch when bombing/doors).

### 5.2 Hostage Model (MVP)
- Maintain a fixed-size array (64) of structs: `[state, x, y, health, target]`.
- States: `IDLE`, `PANIC`, `MOVING_TO_LZ`, `WAITING`, `BOARDED`, `SAVED`, `KIA`.
- Rules:
  - Hostages only move when an LZ is available (helicopter grounded + doors open).
  - Crowd control: cap simultaneous movers to keep readability.
  - Hostages are vulnerable while on foot (classic pressure). The helicopter can physically interpose (“shield”) incoming fire at the cost of taking damage.

#### 5.2.1 Barracks / Compounds (“Breaking In”) (MVP)

- Each extraction site starts **sealed**.
- Player must **damage the structure** to open it and release hostages.
- Weapons can cause hostage casualties (stray shots/explosions) to preserve classic tension.

### 5.3 Threats (MVP)
- **Ground units:** light vehicles with simple line-of-sight firing.
- **Air threats:** fast “pass” threats (jets/drones) with predictable approach vectors.
- **Air defense:** limited SAM/MANPADS zones that force altitude decisions.

Include the three classic-feeling archetypes early:
- **Tanks:** punish hovering/landing; can also threaten hostages on foot.
- **Jets:** high-altitude passes; pressure during transit and can chase to base.
- **Air mines:** homing “Sputnik-like” hazards that force evasive flying (can be Milestone C if needed).

Signature maneuver to preserve:
- **Reverse flip:** allow mid-air facing reversal without killing momentum; key to dodging missiles.

### 5.4 Resource & Consequence (MVP-lite)
Pick *one* global consequence variable for MVP:
- **Public Sentiment Meter** (from LLM_HANDOFF): increases with rescues, decreases with collateral.

MVP interpretation (simple):
- Sentiment only affects *debrief grade* and *next mission threat budget* (slightly easier/harder).

### 5.5 Weather (Later)
- Sandstorm reduces visibility + adds wind gusts affecting $v_y$.

### 5.6 Vertical Missions (Later)
- Rooftop extractions and limited vertical scrolling segments.

## 6) Controls (Prototype Defaults)

- Left/Right: tilt
- Up: increase lift
- Down: decrease lift / descend faster
- Face toggle: cycle `left/right/forward` (or hold modifier)
- Fire: mode-based weapon (see below)
- Door toggle: open/close (gated: only effective when grounded)
- (Optional) Brake/hover assist: small counter-force to reduce speed

Weapon mapping (classic-inspired):
- Side-facing: **machine gun** (best against jets)
- Forward-facing: **bombs/rockets** (best against tanks)

### 6.1 Gamepad Compatibility (Planned)

Goal: allow an Xbox controller to be turned on mid-game and be usable without restarting.

- **Connection UX:** show a small on-screen notification when a gamepad is connected or disconnected.
- **Default mapping (proposal):**
  - Left stick X: tilt left/right
  - Right trigger: increase lift
  - Left trigger: decrease lift
  - A: door toggle
  - X: fire
  - Y: cycle facing
  - B: reverse flip
  - D-pad: optional discrete tilt/lift for precision

Implementation note: keep keyboard controls active even when a gamepad is connected.

## 7) HUD / Feedback (Keep Minimal)
- Fuel bar
- Damage bar
- Passenger count (0…capacity)
- Doors state (open/closed)
- Altitude indicator (simple band)
- Sentiment meter (if included in MVP)

## 8) Milestones (Actionable Backlog)

### Milestone A — “Feels Like Choplifter” (prototype)
- 60 Hz fixed tick loop
- Helicopter physics + tilt visuals
- Basic ground + landing detection
- Facing modes + reverse flip responsiveness
- Debug overlay for velocity/tilt/altitude

### Milestone B — “Rescue Loop Works”
- Compounds spawn hostages
- Break-in (compound health → open)
- Doors + grounded state gating
- Hostage array + states
- Load/unload + win condition

### Milestone C — “Pressure + Threat”
- 3 enemy archetypes (tanks, jets, air mines)
- Damage + fuel + simple respawn
- Mission success/fail debrief with “The End” (not “Game Over”)

### Milestone D — “First Real Level”
- One polished mission with tuned pacing
- Audio placeholders
- Input rebinding + basic accessibility toggles (optional)
- Skippable intro cutscene before Mission Select (in-engine timeline)

## 9) Open Decisions (Next)
- How strict landing should be (arcade vs punishing)
- Whether sentiment affects unlocks or only difficulty
