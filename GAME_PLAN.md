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

## 5) Systems (MVP vs Later)

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

## 9) Open Decisions (Next)
- How strict landing should be (arcade vs punishing)
- Whether sentiment affects unlocks or only difficulty
