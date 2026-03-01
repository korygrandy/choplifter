# Choplifter!

Choplifter! is a cornerstone of early 80s gaming, famously bridging the gap between home computing and the arcade. While it debuted on the Apple II, the Commodore 64 (C64) port remains one of the most celebrated versions due to the system's superior hardware capabilities at the time.

## 1. Development and Origins

- **The Creator:** Developed by Dan Gorlin, who was previously an AI researcher at the Rand Corporation.
- **The Inspiration:** Gorlin was fascinated by helicopter physics. Interestingly, the "rescue" mechanic was suggested by a local neighborhood kid who was repairing Gorlin's car and noted that the game Defender had "men to pick up."
- **The Narrative Pivot:** Unlike most shooters of 1982, Gorlin focused on the "human" element. He intentionally omitted a traditional score, believing that lives should be the only metric of success to make every casualty feel significant.
- **Cinematic Influence:** Gorlin was influenced by film techniques, including the use of "The End" instead of "Game Over," and the way the hostages would wave to the helicopter.

## 2. The Commodore 64 Port (1983)

The C64 version was ported by Dane Bigham and published by Brøderbund. It is often analyzed in contrast to the Apple II original:

| Feature      | Apple II (Original)                                      | Commodore 64 (Port)                                                          |
|--------------|----------------------------------------------------------|------------------------------------------------------------------------------|
| Graphics     | High-res but limited color (notably purple sand).        | Smoother scrolling and more vibrant, realistic color palettes.               |
| Performance  | Flickery sprites under heavy action.                     | Utilized C64's hardware sprites for much smoother animation.                 |
| Sound        | Basic internal speaker "beeps."                          | Leveraged the SID chip for more atmospheric sound and engine noise.          |
| Difficulty   | High; jet fighters are relentless.                       | Slightly improved playability, though still notoriously difficult due to "homing satellites." |

## 3. Key Gameplay Mechanics

- **Physics-Based Flight:** One of the first games to implement momentum. The helicopter doesn't just "move"; it tilts, accelerates, and requires counter-steering to land safely.
- **The Rescue Loop:**
  1. Fly to one of four barracks.
  2. Shoot the building to release the 16 hostages inside.
  3. Land (carefully) to board them. If you land on a hostage, they are crushed—a detail noted for its emotional impact on players.
  4. Return to the "Poste" (base) while dodging tanks and jets.
- **Winning Conditions:** There are 64 hostages in total. You must rescue at least 20 to "win," though 64 is the goal for a perfect game.

## 4. Cultural and Historical Impact

- **Reverse-Port Phenomenon:** In a rare move for the industry, Choplifter was a home game that became so popular it was turned into an arcade cabinet by Sega (1985), rather than the other way around.
- **Historical Timing:** Though unintentional, the game was released shortly after the Iran Hostage Crisis, which gave the game a layer of real-world relevance that resonated with the American public in 1982–83.
- **The "First Interactive Movie":** Contemporary magazines like *Softline* described it as the first "Interactive Computer-Assisted Animated Movie" because of its focus on storytelling and fluid animation.

## 5. Modern Research & Legacy

- **Reverse Engineering:** In 2024, the Blondihacks project performed a deep-dive reverse engineering of the code, revealing how Gorlin managed to squeeze complex physics and 64 independent AI "hostages" into just 48KB of RAM.
- **2021 Enhanced Hack:** A "30th Anniversary" enhanced version by Holy Moses was released for the C64 in 2021, fixing several original bugs and further smoothing the scrolling for modern retro-enthusiasts.

---

## Prototype (WIP)

This repo now contains a small Python/Pygame prototype scaffold (Milestone A).

### Run

1. Create/activate the venv and install dependencies:
  - `pip install -r requirements.txt`
2. Launch:
  - `python run.py`

### Controls (prototype)

- Move/tilt: Arrow keys or WASD
- Lift: Up/Down (or W/S)
- Brake/hover assist: Shift
- Cycle facing: Tab
- Reverse flip: R
- Fire: Space (side-facing = bullet, forward-facing = bomb)
- Toggle doors (only when grounded): E
- Toggle debug overlay: F1

