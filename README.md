# Pixel Slope Escape

Pixel Slope Escape is a 2D downhill arcade game built with Python and Pygame. It combines a single-player survival run with a shared-screen two-player race, star-powered attacks, health management, and a winter-to-summer world switch.

![Pixel Slope Escape menu](screenshots/menu.png)

## Project snapshot

- **Role:** Lead Developer and Game Designer
- **Core work:** gameplay systems, procedural terrain, collision logic, shared camera, two-player combat, health and scoring, seasonal switching, UI, audio integration, and iterative bug fixes
- **Collaboration:** character and environment artwork was developed with teammate support, including work by Xiang Qi
- **Tools:** Python, Pygame, Photoshop, Procreate, and Jimeng AI

The project began as a compact skiing prototype inspired by the arcade pace of *Ski Safari*. Team playtests then shaped the final version: jumps became more forgiving, obstacles were resized, the shared camera gained catch-up behavior, the two-player HUD was simplified, and the mystery box changed from a two-minute timer to a 1000m distance interval.

[Read the full portfolio case study](docs/Pixel_Slope_Escape_Case_Study.pdf)

## Final gameplay

### Single player

Stay ahead of the snow wall, use the terrain and ramps to maintain speed, and collect stars to build a score combo. The run ends when the wall catches the rider.

### Two players

Two riders compete inside one scrolling view. Each begins with 100 HP. Collisions and star attacks reduce health by 10, while collected stars restore one point. A match ends when one rider is eliminated or caught by the pursuing wall; if both are caught together, the result is Game Over.

### Seasonal switch

After every 1000m of leader distance, a mystery box appears. Collecting it changes the whole run between winter and summer while preserving score, health, speed, and position. The winter snow wall becomes a summer mudslide treatment without changing the chase rules.

![Single-player run](screenshots/single-player.png)

## Controls

| Mode | Player | Movement | Jump | Tuck | Attack |
| --- | --- | --- | --- | --- | --- |
| Single | P1 | `A` / `D` | `Space`, `W`, or `Up` | `S` or `Down` | - |
| Double | P1 | `A` / `D` | `W` | `S` | `E` |
| Double | P2 | `Left` / `Right` | `Up` | `Down` | `/` |

- Press `P` to pause.
- In the pause menu, use `A` / `D` or the arrow keys to choose **Continue** or **Menu**, then confirm with `Enter` or `Space`.
- Press `Esc` to quit.

## Run locally

1. Install Python 3.10 or newer.
2. Clone this repository and enter its folder.
3. Install the dependency:

   ```bash
   python3 -m pip install -r requirements.txt
   ```

4. Start the game:

   ```bash
   python3 pixel_slope_escape.py
   ```

The public portfolio build runs without external audio files. Audio loading is optional in the code, so missing music and sound effects do not prevent the game from starting. Audio files from the course submission were not published because their redistribution terms were not documented in the project folder.

## Design and iteration highlights

- **Readable feedback:** HUD and menu text render at full window resolution while the world keeps its pixel-art scale.
- **Shared-screen fairness:** camera constraints and catch-up logic keep both riders recoverable without splitting the view.
- **Clear competition:** health bars, temporary invincibility, attack cooldowns, and explicit winner states make outcomes understandable.
- **Visual variety:** winter and summer use different backgrounds, characters, obstacles, collectibles, and hazard treatments.
- **Feedback-led pacing:** obstacle sizes, movement speed, jump height, wall pressure, and mystery-box timing were revised from team playtests.

## Repository scope

This repository presents the final V3.3 build. Earlier course-development scripts were intentionally left out so the portfolio version stays focused and easy to run. Concept art and earlier UI iterations are preserved in the case-study PDF.

## Credits

- **James:** lead development, game design, integration, and iteration
- **XQ:** visual art collaboration
- Built as a COMM7960 group project

No open-source license is currently granted for the code or artwork. Please contact the project author before reuse or redistribution.
