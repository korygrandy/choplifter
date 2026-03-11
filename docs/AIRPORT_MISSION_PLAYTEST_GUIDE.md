# Airport Special Ops - End-to-End Playtest Guide

**Branch:** `feature/airport-special-ops-mission`  
**Mission IDs:** `airport` / `airport_special_ops`  
**Validated End-to-End Flow:** Tech deploy -> meal-truck extraction -> bus transfer -> escort/deboard -> tech reboard -> lower rescue continuation -> combined-rescue win

---

## How To Run

```powershell
# From workspace root with venv active
py run.py
# Select "Airport Special Ops"
```

---

## Airport Gameplay Truth

Use this as the acceptance baseline:

- Total airport win target is combined rescued civilians `16` (lower terminals + elevated transfer path).
- Elevated civilians must use the meal-truck -> bus pipeline.
- Lower civilians must be rescued via helicopter compound flow.
- Bus reaching tower LZ/deboard is a major phase gate, not automatic full mission completion when lower rescues remain.
- Mission tech must be reboarded at tower LZ before lower-rescue continuation messaging appears.

---

## Global Pass Criteria

- No soft-locks across any phase transition.
- Objective strip text stays aligned with phase progression.
- Keyboard/gamepad parity holds for mission-critical interactions.
- Driver modes lock helicopter weapons (gun + flare).
- Crash/respawn keeps mission continuity and applies temporary escort-risk tuning.
- Mission ends only when combined rescued reaches `16`.

---

## Objective Text Sequence Check

At minimum, objective strip should progress through these key statuses in the correct context:

1. `Deploy mission tech to meal truck`
2. `Drive meal truck to damaged plane`
3. `Extend meal-truck lift at damaged plane` (when at jetway with lift not extended)
4. `Load civilians onto meal truck`
5. `Drive meal truck to bus transfer lane`
6. `Transfer civilians to bus`
7. `Escort bus to tower LZ`
8. `Land at tower LZ and pick up mission tech`
9. `Resume lower-terminal rescues` (when combined rescued is still below `16`)
10. `All civilians rescued` (when combined rescued reaches `16`)

---

## Full End-To-End Functional Matrix

| # | Action | Expected Result |
|---|--------|-----------------|
| 1 | Start `Airport Special Ops` | Airport world loads with mission tech on chopper and normal HUD state |
| 2 | Confirm initial entities | Bus, meal truck, objective marker, and airport hostages render without errors |
| 3 | Land near meal truck and open doors (`E` / gamepad `A`) | Tech deploys from chopper to truck; tech state leaves `on_chopper` |
| 4 | Observe post-deploy control state | Chopper remains flyable; truck path logic activates |
| 5 | Follow truck to elevated jetway area | Truck enters extraction zone; lift extension behavior begins |
| 6 | Validate lift extraction behavior | Hostage loading starts only when truck/lift/tech conditions are met |
| 7 | Validate loading pacing | Passengers board meal truck one-by-one around `~0.5s` cadence |
| 8 | Validate interrupted-transfer recovery | Recalling/interrupting tech resets hostage transfer state without soft-lock |
| 9 | After load complete, observe truck moving toward bus | Truck transitions to transfer lane behavior |
| 10 | Validate transfer gate | Bus transfer starts only when truck is near bus and loaded passengers exist |
| 11 | During transfer, observe bus door visuals | Door open/close transitions and blend timing are smooth; no stuck door state |
| 12 | Validate transfer completion | Hostages move from truck count to bus count; tech reaches bus transfer-complete path |
| 13 | Let escort run to tower LZ (auto or manual) | Bus advances toward `stop_x~500`; objective reflects escort phase |
| 14 | Validate deboard trigger | Deboard/rescue at tower LZ occurs reliably even if bus is still moving in LZ band |
| 15 | Validate tech disembark/reboard gate | Objective switches to pickup prompt until grounded + doors-open reboard occurs |
| 16 | Reboard tech at tower LZ | Objective switches to lower-rescue continuation when total is below `16` |
| 17 | Rescue lower-terminal civilians via chopper compounds | Lower-rescue flow increments combined rescue total normally |
| 18 | Reach combined rescued `16` | Mission ends with success debrief (`All civilians rescued`) |

---

## Mission-Specific Controls And Modes

### Meal Truck Driver Mode

| # | Action | Expected Result |
|---|--------|-----------------|
| 19 | Enter meal-truck driver mode at valid gate | Camera follows truck; truck responds to directional input |
| 20 | While driving truck, attempt gun/flare | Chopper gun + flare are blocked |
| 21 | Exit truck mode | Camera and control ownership return cleanly to helicopter |

### Bus Driver Mode

| # | Action | Expected Result |
|---|--------|-----------------|
| 22 | Enter bus mode after tech-on-bus gate is valid | Manual bus control activates |
| 23 | Drive bus left/right within clamps | Bus movement obeys world and stop clamps |
| 24 | While driving bus, attempt gun/flare | Chopper gun + flare remain blocked |
| 25 | Exit bus mode | Auto-drive resumes without desync |

### Input Parity

| # | Action | Expected Result |
|---|--------|-----------------|
| 26 | Repeat steps 19-25 on keyboard | Behavior is stable and consistent |
| 27 | Repeat steps 19-25 on gamepad | Same behavior as keyboard path |

---

## Combat And Threat Behavior (Airport-Specific)

| # | Action | Expected Result |
|---|--------|-----------------|
| 28 | Force BARAK overlap scenario (bus + chopper near same x) while flying helicopter | BARAK collision prioritizes helicopter when player is not driving ground vehicle |
| 29 | Repeat overlap while driving truck or bus | BARAK can target/damage bus per driving-state preference |
| 30 | Land chopper in tower LZ during airport escort threats | Tower-LZ immunity for helicopter damage is honored |
| 31 | Test friendly fire on bus with player weapons | Bus health decreases according to friendly-fire logic |
| 32 | Verify flare diversion path under pressure | BARAK/divertible missile behavior remains correct |

---

## Crash/Respawn Option 3 Validation

| # | Action | Expected Result |
|---|--------|-----------------|
| 33 | During active escort (`boarded`), intentionally crash chopper | Crash sequence runs, bus continues progressing (no mission pause) |
| 34 | During first `~3s` post-respawn, allow bus impacts | Bus takes increased damage (`1.35x`) in the active escort window |
| 35 | After window expires, allow similar impacts | Bus damage returns to baseline |
| 36 | Crash outside escort-active state (`waiting` / `truck_loading`) | Temporary escort-risk multiplier is not applied |

---

## Failure And Recovery Paths

| # | Action | Expected Result |
|---|--------|-----------------|
| 37 | Destroy bus before successful mission completion | Mission fails with bus-destroyed outcome |
| 38 | Trigger complete passenger-loss outcome where possible | Mission fails with passenger-loss outcome |
| 39 | Let extraction deadline expire before completion | Deadline failure triggers correctly |
| 40 | Accumulate chopper crashes to crash limit | Mission fails at configured crash threshold |

---

## UI And Stateflow Regressions

| # | Action | Expected Result |
|---|--------|-----------------|
| 41 | Pause during active airport phases and resume | No state corruption; mission flow continues correctly |
| 42 | Open pause from mission-end screen and navigate quit/cancel | Pause/menu behavior works on both keyboard and gamepad |
| 43 | From chopper-select screen press `Esc` | Returns to mission-select as expected |

---

## Suggested Execution Matrix

Run at least these four passes:

1. `Pass A (Keyboard Auto)`: no manual bus/truck driving, complete full flow to combined `16` rescue success.
2. `Pass B (Keyboard Manual)`: use truck + bus manual modes, verify weapon lockouts and clean exits.
3. `Pass C (Gamepad Mixed)`: repeat critical deployment/driver/reboard interactions on gamepad.
4. `Pass D (Crash Stress)`: force 2+ crashes during escort and verify Option 3 risk window behavior.

---

## Quick Reference Values

| Setting | Target |
|---------|--------|
| Combined rescue win target | `16` |
| Truck spawn area | `x~1060` |
| Elevated pickup area | `x~1500` |
| Tower LZ stop reference | `stop_x~500` (left side) |
| Bus creep speed (pre-escort) | `20 px/s` |
| Bus escort speed | `80 px/s` |
| Passenger transfer cadence | `~0.5s` per passenger |
| Bus entry gate | Tech on bus + helicopter within `~200px` |
| Post-respawn escort-risk window | `3.0s` |
| Escort-risk bus damage multiplier | `1.35x` (escort-active only) |

---

## Reporting Checklist

When filing an issue from this guide, include:

- Input device path (`keyboard`, `gamepad`, or both).
- Exact objective text shown at failure point.
- Last successful phase + next expected phase.
- Bus health, visible passenger count (`xN`), and crash count.
- Whether issue is deterministic across 2 reruns.
