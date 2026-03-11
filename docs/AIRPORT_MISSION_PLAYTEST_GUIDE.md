# Airport Special Ops - Gameplay Test Plan

**Branch:** `feature/airport-special-ops-mission`  
**Mission IDs:** `mission2` / `airport_special_ops`  
**Target Flow:** Truck extraction -> paced passenger transfer -> tech boards bus -> escort to left LZ (auto or manual)

---

## How To Run

```powershell
# From workspace root with venv active
py run.py
# Select "Airport Special Ops"
```

---

## Test Scope

This plan validates:

- Core mission progression from deployment through mission complete
- Passenger transfer pacing and live bus count updates
- Hybrid control model: bus auto-drive by default, optional manual bus driving
- Mission completion trigger at bus LZ arrival (no chopper proximity requirement)
- Regression checks for combat systems and failure paths

---

## Pass Criteria

- No soft-locks in any airport mission phase
- HUD/objective text progresses in expected sequence
- Passengers transfer one-by-one at roughly `0.5s` per passenger
- Bus can be manually entered/exited via doors input after tech is on bus
- Mission completes when bus reaches left LZ and stops

---

## Core End-To-End Path

| # | Action | Expected Result |
|---|--------|-----------------|
| 1 | Start `Airport Special Ops` | Airport background loads and mission begins normally |
| 2 | Verify spawn state | Tech/wrench indicator starts with helicopter |
| 3 | Fly to truck area (`x~1060`) and land near truck | Proximity gate is met |
| 4 | Press doors (`E` / gamepad `A`) | Tech deploy animation starts and reaches truck |
| 5 | Watch truck behavior after tech deploys | Truck transitions to bunker drive sequence |
| 6 | Observe elevated bunker interaction (`x~1500`) | Lift/box extends and hostages begin loading into truck |
| 7 | Wait for truck loading completion | Truck state moves to loaded, lift retract sequence runs |
| 8 | Observe truck route to bus | Truck drives toward bus transfer zone |
| 9 | Ensure transfer starts only when truck is near bus and retracted | Bus doors open and transfer phase begins |
| 10 | Observe transfer pacing | Passenger count above bus increments one-by-one (~`0.5s` each) |
| 11 | Wait until transfer completes | Tech boards bus last and bus escort phase begins |
| 12 | Follow bus toward left LZ (`stop_x~500`) | Bus proceeds to LZ; objective updates to mission completion state at stop |

---

## Bus Control Hybrid Tests

### A. Default Auto-Escort

| # | Action | Expected Result |
|---|--------|-----------------|
| 13 | Do not press doors near bus after tech boards | Bus drives itself toward LZ |
| 14 | Keep helicopter away from bus controls | Helicopter remains primary controllable vehicle |
| 15 | Let bus reach LZ under auto-drive | Mission completes successfully |

### B. Manual Bus Entry/Exit (Keyboard)

| # | Action | Expected Result |
|---|--------|-----------------|
| 16 | Bring helicopter within bus entry radius after tech is on bus | Entry gate is valid |
| 17 | Press doors (`E`) near bus | Manual bus mode activates |
| 18 | Press left/right movement while in bus mode | Bus responds to manual movement and respects world clamps |
| 19 | Confirm control lockout behavior | Helicopter controls are disabled while driving bus |
| 20 | Press doors (`E`) again | Bus mode exits; bus returns to auto-drive behavior |

### C. Manual Bus Entry/Exit (Gamepad)

| # | Action | Expected Result |
|---|--------|-----------------|
| 21 | Repeat steps 16-20 with gamepad `A` for doors | Same behavior as keyboard path |

---

## Camera Routing Tests

| # | Action | Expected Result |
|---|--------|-----------------|
| 22 | Drive meal truck mode | Camera follows truck smoothly |
| 23 | Exit truck mode and fly helicopter | Camera returns to helicopter tracking |
| 24 | Enter bus driver mode | Camera follows bus smoothly |
| 25 | Exit bus driver mode | Camera returns to helicopter tracking without abrupt jump |

---

## Mission Completion + Failure Conditions

| # | Action | Expected Result |
|---|--------|-----------------|
| 26 | Complete mission via auto-bus path | Success screen and end stats appear |
| 27 | Complete mission via manual-bus path | Success screen and end stats appear |
| 28 | Destroy bus before LZ | Mission fails with bus-destroyed outcome |
| 29 | Trigger all-passenger-loss path (if accessible) | Mission fails with hostage-loss outcome |
| 30 | Let mission deadline expire before extraction complete | Deadline failure triggers |

---

## Combat/Threat Regression Spot Checks

| # | Action | Expected Result |
|---|--------|-----------------|
| 31 | Damage Barak MRAD with bullets and bombs | Expected damage model and kill behavior remain intact |
| 32 | Use flares against homing missile | Missile can be diverted by flare |
| 33 | Allow tank/jet/mine systems to engage | Threat tells and attacks still function |

---

## Suggested Execution Matrix

Run at least these three passes:

1. `Pass A (Keyboard Auto)`: never enter bus mode, validate full auto-escort completion.
2. `Pass B (Keyboard Manual)`: enter/exit bus mode at least once, complete mission manually.
3. `Pass C (Gamepad Mixed)`: perform truck and bus entry/exit with gamepad buttons and complete mission.

---

## Quick Reference Values

| Setting | Target |
|---------|--------|
| Truck spawn | `x~1060` |
| Elevated bunker | `x~1500` |
| Bus escort destination | `stop_x~500` (left LZ) |
| Bus creep speed (pre-escort) | `20 px/s` |
| Bus escort speed | `80 px/s` |
| Passenger transfer pacing | `~0.5s` per passenger |
| Bus manual entry gate | Tech on bus + helicopter within `~200px` |

---

## Logging Notes (Optional)

- Capture any phase that stalls for more than 5 seconds after expected trigger conditions are met.
- Record whether issue is reproducible with keyboard, gamepad, or both.
- Include objective text and visible counts (`xN`) when reporting transfer/boarding defects.
