# Airport Special Ops - Playtest Guide (Polished State)

Last Updated: 2026-03-14
Branch: feature/airport-special-ops-mission
Mission IDs: airport / airport_special_ops

This guide is the current acceptance baseline for Airport Special Ops after the latest mission-flow stabilization and BARAK behavior updates.

---

## How To Run

```powershell
# From workspace root with venv active
py run.py
# Select Airport Special Ops
```

Optional smoke automation:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_airport_smoke.ps1
```

---

## Smoke Report Card

Capture these values for every pass:

- Input path: keyboard / gamepad / mixed
- Objective strip sequence: exact text seen at each major gate
- Bus health samples: start, first escort impact, post-respawn window
- Crash count: before and after escort crash window checks
- Passenger transfer evidence: visible xN marker and final rescue totals
- Result: PASS or FAIL

Template:

```text
Airport Smoke Report
- Input: <keyboard|gamepad|mixed>
- Objective sequence: <exact text checkpoints>
- Bus health samples: <values>
- Crash count: <before -> after>
- Passenger checks: <xN and final totals>
- Result: <PASS|FAIL>
- Notes: <optional>
```

---

## Mission Truth (Acceptance Baseline)

- Airport mission success uses combined rescued civilians target of 16.
- Rescue is split into two lanes:
  - Elevated compounds (fuselage + jetway) use meal truck -> bus pipeline.
  - Lower compounds use helicopter rescue flow.
- Elevated flow is complete only after both elevated compounds are emptied.
- Transfer and escort are phase-gated by objective state and runtime conditions.
- Engineer must end up on bus for escort phase logic and threat activation.
- Final elevated transfer behavior:
  - When the final elevated passenger handoff completes, engineer auto-transfers to bus.
  - Engineer boarding should visually target the bus front door (not the rear).
- Tower LZ sequence remains:
  - bus reaches LZ band -> engineer disembarks -> reboard gate for continuation.

---

## New/Important Behavioral Gates To Verify

### Transfer Control Handoff (Regression Guard)

Expected after elevated transfer completes:

- Engineer transitions onto the bus for escort.
- Player controls return to the helicopter (no lingering vehicle-driver lockout).
- Any stale bus-driver mode is cleared automatically once engineer is no longer on the bus.

Expected boarding visual:

- Engineer approaches/boards from the bus front-door side.

### Escort Threat Activation

Airport escort threats (drones, minesweepers/raiders, raider mines) are active only when:

- objective phase is escort_to_lz
- mission tech is on_bus
- bus is moving

Expected UX:

- Objective strip uses escort threat warning text during this phase.
- One-time toast appears on escort activation:
  Escort under attack: fend off drones, minesweepers, and raider mines

### BARAK Missile Behavior

- Pre-launch flare active: BARAK diversion sidewinds above chopper (~40 px high profile).
- Post-launch flare activation: keep current near-nose diverted detonation behavior.
- Nose-stick prevention: missiles should not remain vertically pinned to chopper nose; fallback detonation should resolve quickly.

---

## Global Pass Criteria

- No soft-locks through full route:
  tech deploy -> elevated extraction(s) -> transfer -> escort -> tower LZ -> tech reboard -> lower continuation -> win
- Objective strip text matches state progression without stale prompts.
- Keyboard and gamepad parity for mission-critical actions.
- Driver mode weapon lockouts still apply.
- Crash/respawn preserves mission continuity.
- Mission ends only on combined rescue target meeting 16.

---

## 10-Minute Quick Smoke

| # | Action | Expected |
| --- | --- | --- |
| Q1 | Start airport mission | Mission intro loader shows `MISSION:AIRPORT_SPECIAL_OPS` |
| Q2 | Deploy engineer to meal truck | Engineer exits chopper and truck phase begins |
| Q3 | Complete one elevated extraction and transfer cycle | Transfer lane works, doors and xN marker update |
| Q4 | Complete final elevated passenger handoff | Engineer auto-transfers with final handoff; helicopter controls are active |
| Q5 | Observe engineer boarding position | Boarding targets bus front door (not rear) |
| Q6 | Confirm escort phase starts with threats active | Threat warning objective text + one-time escort toast |
| Q7 | Trigger a BARAK engagement with flare before launch | Missile sidewinds above chopper |
| Q8 | Trigger flare after BARAK missile launch | Near-nose diversion behavior remains intact |
| Q9 | During escort, induce one crash and recover | Bus continues; post-respawn risk window observable |
| Q10 | Reach tower LZ and reboard engineer | Continuation prompt clears after valid reboard |
| Q11 | Finish remaining lower rescues (if needed) | Combined total reaches 16 and mission succeeds |

Optional 90-second regression probes (run after Q2 or Q3):

- Fuselage callouts:
  - On fuselage terminal unlock, hear `fuselage-about-to-collapse.ogg` once.
  - When fuselage has exactly 1 passenger remaining, hear `lets-go.ogg` once.
- Hostage KIA failure overlay:
  - If any hostage KIA occurs, mission-failed overlay appears immediately.
- Hostage rescue cutscene preload:
  - Hostage cutscenes preload with a black screen (no blue terminal loader).

Quick result:

- PASS: Q1-Q11 all valid with no blockers.
- FAIL: any objective mismatch, stuck transition, or unrecoverable state.

---

## Objective Text Checkpoints

Expected major checkpoints (contextual):

1. Deploy mission tech to meal truck
2. Drive meal truck to Fuselage Terminal or Jetway Terminal
3. Extend meal-truck lift at [active elevated terminal]
4. Load civilians onto meal truck at [active elevated terminal]
5. Drive meal truck to bus transfer lane
6. Transfer civilians to bus
7. Escort bus to tower LZ - fend off drones, minesweepers, and raider mines
8. Land at tower LZ and pick up mission tech
9. Resume Lower Terminal rescues (if combined total < 16)
10. All civilians rescued

Notes:

- Terminal labels should correctly reflect active elevated target (fuselage vs jetway).
- No regression to older placeholder terminal wording.

---

## Full Functional Matrix

### A. Core Flow

| # | Action | Expected |
| --- | --- | --- |
| A1 | Mission start | Airport entities initialize cleanly |
| A2 | Engineer deploy gate (land + doors near truck) | Engineer enters truck state |
| A3 | Truck drives to active elevated terminal | Active terminal routing works |
| A4 | Lift extension and loading | Loading only occurs under valid tech/truck/lift conditions |
| A5 | Interrupt/recover extraction once | No soft-lock, state resumes correctly |
| A6 | Truck returns to bus lane | Transfer gate triggers correctly |
| A7 | Transfer completes with xN visible | Bus passenger marker and counts update |
| A8 | Final elevated handoff | Engineer auto-transfers to bus |
| A9 | Escort to tower LZ | Escort phase and threat activation hold |
| A10 | Tower LZ disembark + reboard | Reboard prompt and handoff are correct |
| A11 | Lower rescue continuation | Lower flow progresses without elevated state corruption |
| A12 | Combined 16 reached | Success end state only at combined target |

### B. Controls and Driver Modes

| # | Action | Expected |
| --- | --- | --- |
| B1 | Enter/exit meal truck mode | Clean handoff, no camera/control desync |
| B2 | Enter/exit bus mode (valid gate only) | Gate rules enforced, clean exit |
| B3 | Attempt gun/flare while driving vehicle | Chopper weapons are blocked |
| B4 | Repeat B1-B3 on keyboard and gamepad | Parity holds |

### C. Combat/Threats

| # | Action | Expected |
| --- | --- | --- |
| C1 | Escort inactive state | Airport escort threats remain dormant |
| C2 | Escort active state | Threats spawn/engage as expected |
| C3 | BARAK pre-launch flare case | Sidewind above chopper profile |
| C4 | BARAK post-launch flare case | Near-nose diversion/detonation behavior |
| C5 | BARAK nose-stick repro attempts | No long vertical pin/sticky missile visuals |
| C6 | Friendly-fire bus checks | Damage routing follows current rules |

### D. Failure and Recovery

| # | Action | Expected |
| --- | --- | --- |
| D1 | Bus destruction path | Failure condition triggers correctly |
| D2 | Deadline expiration path | Failure condition triggers correctly |
| D3 | Crash threshold failure | Failure condition triggers correctly |
| D4 | Crash during active escort then recover | Continuity maintained; temporary risk window observed |

---

## Suggested Execution Passes

1. Pass A: Keyboard, mostly auto drive, full mission completion.
2. Pass B: Keyboard with manual truck + bus usage.
3. Pass C: Gamepad parity run of critical gates.
4. Pass D: Combat stress (BARAK + escort threats + crash/recovery).
5. Pass E: Failure-path run (bus destroy, deadline, crash limit).

---

## High-Value Telemetry To Capture During Runs

- Mission phase transitions with timestamps.
- Objective text at each transition.
- terminal_remaining and meal_truck_loaded_hostages during final elevated handoff.
- Engineer state transitions around transferring -> transfer_complete.
- Bus health deltas in escort and post-respawn risk windows.
- BARAK missile behavior clips for pre-launch flare and post-launch flare scenarios.

---

## Issue Filing Checklist

When filing a playtest issue, include:

- Input path (keyboard/gamepad/mixed)
- Exact objective text at failure moment
- Last known good phase and expected next phase
- Relevant counters (bus health, xN, crash count, rescued totals)
- Deterministic? (repro across at least 2 reruns)
- Short repro steps

---

## Exit Criteria For "Polished" Validation Cycle

A validation cycle is complete when:

- All Quick Smoke steps pass.
- No soft-locks in full matrix runs.
- BARAK behavior checks pass in both flare timing modes.
- Final elevated handoff auto-transfer is consistently correct.
- Keyboard/gamepad parity is verified.
- Smoke report card is submitted with PASS.
