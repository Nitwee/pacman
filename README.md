*This project has been created as part of the 42 curriculum by jbarthel, qrios.*

# Pac-Man

## Description

Arcade Pac-Man clone written in Python 3.10+ with **Pygame**. The maze
is generated dynamically by the `mazegen` (A-Maze-ing) package
provided as a local wheel, and gameplay follows the spec in
[en.subject.pdf](en.subject.pdf). Score and lives carry over from one
level to the next; reaching the last level wins the run, and running
out of lives ends it. If the level timer expires, Pac-Man loses a life
and respawns unless no life remains.

**Authors**: jbarthel (branch `jerome`), qrios (branch `quentin`).

**Play it**: [pacman — Itch.io](https://jeromebarthelemy.itch.io/pac-man-42-edition) *(free, unlisted build)*

## Instructions

### Requirements

- Python ≥ 3.10
- [`uv`](https://docs.astral.sh/uv/) for environment and dependency management
- OS: Linux (tested on Ubuntu); macOS and Windows supported as long as
  Pygame builds

### Installation

The environment and dependencies are managed with `uv`. The `mazegen`
wheel is resolved locally from the repository root (see
`pyproject.toml` → `tool.uv.sources`).

```bash
make install          # alias for `uv sync`
```

For users without `uv`, a pip fallback is available:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Run

```bash
make run              # uv run python pac-man.py config.json
make debug            # run under pdb
make lint             # flake8 + mypy (with mandatory flags)
make lint-strict      # flake8 + mypy --strict
make test             # pytest
make clean            # remove caches
make clean-all        # clean + remove the virtualenv
```

Direct invocation also works:

```bash
python3 pac-man.py config.json
```

### Packaging

```bash
make install          # install all dependencies including PyInstaller
./package.sh          # build dist/pacman/ (standalone folder)
./package.sh --zip    # also create dist/pacman-linux.zip for Itch.io upload
```

The bundle in `dist/pacman/` is self-contained: no Python installation required
on the target machine. `GAME_README.txt`, `config.json` and all assets are
included automatically.

### Controls

| Key | Action |
|---|---|
| Arrow keys / WASD | Move Pac-Man |
| P | Pause / resume |
| Esc | Pause (during play), resume (during pause), back from Instructions / Leaderboard / Options, otherwise open the quit-confirmation overlay |
| Enter / Y | Confirm menu selection or confirm-dialog answer; dismiss Game Over / Victory |
| N / Backspace | Cancel a confirm-dialog (quit or back-to-main-menu) |
| Up/Down (W/S) | Move the cursor on any menu screen |

Cheat shortcuts (held with `LCtrl`, available only in the `PLAYING`
state). Active cheats appear as a centred list inside the right-side
HUD panel:

| Combo | Effect |
|---|---|
| `LCtrl` + `I` | Toggle invincibility |
| `LCtrl` + `F` | Toggle ghost freeze |
| `LCtrl` + `T` | Toggle level-timer freeze |
| `LCtrl` + `W` | Toggle noclip (walk through walls) |
| `LCtrl` + `E` | Grant one extra life |
| `LCtrl` + `↑` | Speed Pac-Man up by one 25 % notch |
| `LCtrl` + `↓` | Slow Pac-Man down by one 25 % notch |
| `LCtrl` + `L` | Collect all pacgums (auto-complete level) |
| `LCtrl` + `C` | Cycle to the next visual palette |

## Configuration

The game takes a single CLI argument: a JSON config file
([config.json](config.json) is provided as the default). Lines starting
with `#` are stripped before parsing. Any missing or invalid value is
replaced by a safe default and a warning is logged on `stderr` — the
game never crashes on a malformed config.

| Key | Default | Description |
|---|---|---|
| `highscore_filename` | `"highscore.json"` | Persistence target for the top-10 highscore table. |
| `lives` | `3` | Starting lives. |
| `pacgum` | `42` | Pacgum count drawn from the maze's corridors (excluding the four corners which host super-pacgums). |
| `points_per_pacgum` | `10` | Score per pacgum. |
| `points_per_super_pacgum` | `50` | Score per super-pacgum. |
| `points_per_ghost` | `200` | Score per ghost eaten while in super mode. |
| `seed` | `42` | RNG seed for level 1 (deterministic for grading). |
| `level_max_time` | `90` | Time limit per level, in seconds. |
| `level` | array (10+) | List of `{width, height}` pairs. Minimum 10 entries; each dimension ≥ 10. |

## Maze Generation

Maze generation uses the `mazegen` package shipped as
[`mazegen-0.2.0-py3-none-any.whl`](mazegen-0.2.0-py3-none-any.whl). The
wheel **must not be modified or reimplemented**.

- Instantiated with `perfect=False` so the maze has loops (Pac-Man
  corridors are not a perfect tree).
- **Level 1** uses `seed=42` from the config for a reproducible maze.
- Subsequent levels use a random seed.
- From the generated grid we derive: the 42-logo cells (kept as
  decorative obstacles), the four corners (super-pacgums and ghost
  spawns), the maze centre (player spawn), and a random subset of the
  remaining corridor cells and corridor mid-points (pacgums).
- If the generator raises an exception, `MazeError` is caught in
  `game_engine.py`, logged, and the engine transitions to `GAME_OVER`
  cleanly — no traceback reaches the user.

## Highscore

The highscore system persists the top 10 scores across sessions in a
JSON file (path set by `highscore_filename` in the config, default
`highscore.json`).

**File format** — a JSON array of objects:

```json
[{"name": "PLAYER", "score": 1110}, ...]
```

**Name validation** — only alphanumeric characters and spaces are kept;
names are uppercased and capped at 10 characters. An empty result falls
back to `"PLAYER"`.

**Score validation** — scores are clamped to non-negative integers.

**Resilience** — a missing file, a malformed JSON document, or
individual invalid entries are silently skipped; the game starts with
an empty table and overwrites the file on first save.

**Why JSON** — human-readable, covered by the standard library (`json`),
trivially inspectable during peer review, and robust to partial
corruption because each entry is validated independently.

## General Software Architecture

```
App  (State: MAIN_MENU | PLAYING | PAUSED | INSTRUCTIONS |
              GAME_OVER | VICTORY | HIGHSCORE_ENTRY |
              LEADERBOARD | OPTIONS | CONFIRM_QUIT |
              CONFIRM_MAIN_MENU)
├── ConfigManager   (parser, validator, Pydantic models)
├── HighscoreStore  (top-10 entries, JSON-backed)
├── AssetManager    (sprite sheet, palettes, animations, fonts)
├── SoundManager    (SFX + background music, intro-to-loop chain)
├── GameEngine      (created on each new game)
│   ├── EngineState    (STARTING → PLAYING ↔ DYING / LEVEL_TRANSITION
│   │                   → GAME_OVER / GAME_WON)
│   ├── Maze           (wraps mazegen; derives spawns / pacgums)
│   ├── CharacterManager
│   │   ├── Pacman     (intended direction, smooth step,
│   │   │               cheat speed multiplier)
│   │   └── Ghost ×4   (Blinky / Pinky / Inky / Clyde)
│   ├── Timer ×6       (intro / death / level transition /
│   │                   gameplay freeze / score overlay /
│   │                   super-pacgum window)
│   ├── Cheats         (invincibility, ghost_freeze, timer_freeze)
│   ├── events list    (ItemEatenEvent, GameEvent — one frame)
│   └── music_cue      (MusicCue enum read by App each frame)
└── ScreenManager
    ├── MainMenuScreen     (animated logo, cycling Pac-Man chase)
    ├── PlayingScreen      (maze + right-side HUD + level-transition
    │                       overlay + inter-level palette flicker)
    ├── PauseScreen        (pause menu + confirm-quit overlay +
    │                       confirm-back-to-main-menu overlay)
    ├── GameOverScreen     /  VictoryScreen
    ├── HighscoreEntryScreen
    ├── LeaderboardScreen
    ├── InstructionsScreen
    └── OptionsScreen      (resolution / fullscreen / sound)
```

See [docs/architecture.md](docs/architecture.md) for the full Mermaid diagram.

## Implementation

Key design decisions taken during development:

- **Two-level state machine**: `App.dispatch` matches `(State, Event)`
  pairs for menu / pause / end-of-game routing; the engine owns its
  own `EngineState` for in-play phases (intro hold, dying animation,
  level transition, end). App reads `engine.state` and `engine.events`
  every frame, never writes engine internals directly.
- **`MusicCue` enum** decouples audio decisions: the engine publishes
  `NONE | GHOST_RETURN | FRIGHT | SIREN` and App maps each cue to a
  `.wav` name. Engine has no audio vocabulary in its API.
- **`Timer` helper**: every countdown in the engine (intro, death,
  level transition, ghost-eat freeze, score overlay, super-pacgum
  window) is a `Timer` instance with `start`/`extend`/`tick`/`active`,
  replacing six copies of the `if x > 0: x = max(0, x - dt)` idiom.
- **`Cheats` dataclass + action methods**: cheat flags live in a
  dedicated dataclass read via `engine.cheats.*`; mutations go through
  named methods (`toggle_invincibility`, `toggle_ghost_freeze`,
  `gain_life`, `speed_up_pacman`, `slow_down_pacman`). App never
  writes engine attributes directly.
- **Smooth movement**: characters store both `position` and
  `previous_position`. Each character exposes a step-progress fraction
  and the renderer lerps the sprite between the two cells. Collisions
  read the same lerped positions, so visual and logical collision agree.
- **Ghost AI** — per-ghost personality:
  - **Blinky** (red) chases Pac-Man via Manhattan distance, falling
    back to BFS when far.
  - **Pinky** (pink) targets a cell 4 steps ahead of Pac-Man.
  - **Inky** (cyan) wanders randomly.
  - **Clyde** (orange) chases from afar and scatters when close.
- **Frightened mode**: super-pacgum sets a 5-second timer; in the
  last 2 seconds the ghost sprite alternates blue/white as a warning.
  Eaten ghosts walk back to their spawn as eyes, then revive.
- **Palette pinning**: ghost colours are gameplay-defined (Blinky =
  red, Pinky = pink, …), not theme-defined. The
  `AssetManager` pins those sprites to specific palettes so the
  user-facing palette switch (`LCtrl+C`) only restyles the maze.
- **Inter-level palette flicker**: while the intermission jingle plays
  between two levels, `PlayingScreen` snapshots the active palette,
  cycles through every registered palette every 80 ms, and restores
  the snapshot the frame the engine leaves `LEVEL_TRANSITION`.
- **No tracebacks reach the user**: every I/O and config-parse path
  is wrapped in `try/except` that logs and falls back. Maze generation
  errors are caught in `game_engine.py` and transition to `GAME_OVER`.

## Tests and code quality

```bash
make test             # pytest — 151 tests, ~1 s
make lint             # flake8 + mypy (mandatory flags)
make lint-strict      # flake8 + mypy --strict
```

Conventions: flake8 clean (Google-style docstrings via
`flake8-docstrings`), `mypy --strict` passing on every source file,
type hints required, zero `# type: ignore` outside one test mock case.

## Project Management

Development was tracked with **Linear** (issues, milestones, Kanban
board) and **GitHub** (branches, pull requests, code review). Each
feature was developed on a personal branch and merged into `main` via
a reviewed PR.

Full details — timeline, risk analysis, team organisation, acceptance
test plan — are in [docs/project-management.md](docs/project-management.md).

## Resources

- [Pygame documentation](https://www.pygame.org/docs/)
- Sprite sheet — [Spriters Resource: Pac-Man Miscellaneous & Palettes](https://www.spriters-resource.com/arcade/pacman/asset/159361/).
- Sound effects and music — [Spriters Resource: Pac-Man sounds](https://sounds.spriters-resource.com/arcade/pacman/asset/404131/).
- Original arcade gameplay reference — [Pac-Man (1980) longplay on YouTube](https://www.youtube.com/watch?v=WbqC-sP3eUQ).
- Official Pac-Man licence holder — [pacman.com](https://pacman.com/en/) (Bandai Namco).
- A-Maze-ing / `mazegen` package — local wheel
  [`mazegen-0.2.0-py3-none-any.whl`](mazegen-0.2.0-py3-none-any.whl);
  see its `METADATA` for the API reference.
- [PEP 8](https://peps.python.org/pep-0008/) and
  [PEP 257](https://peps.python.org/pep-0257/) for style and docstrings.

### AI usage

AI was used during this project for the following tasks:

- Cross-checking the project setup against the 42 subject.
- Occasional code review and refactoring suggestions during development.

Game logic (state machine, ghost AI, collision, scoring, rendering)
is implemented and understood by the team. AI is used as a
pair-programming aid, never as a substitute for understanding the
code we ship.

## License

MIT.
