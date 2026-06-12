# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Pac-Man clone built in Python 3.10+ for the 42 school curriculum. The game uses the external maze generator package (A-Maze-ing, shipped as the `mazegen-0.2.0-py3-none-any.whl` wheel at the repo root, imported as `import mazegen`) and the **Pygame** graphical library. The full specification is in [en.subject.pdf](en.subject.pdf) — it is the only authoritative requirements source for this project (no Norme 42 adaptation applies).

## Commands

```bash
make install      # Install dependencies
make run          # Run the game: python3 pac-man.py config.json
make debug        # Run with pdb
make lint         # flake8 with mypy type checking
make lint-strict  # Stricter mypy --strict pass
make clean        # Remove __pycache__, .mypy_cache, .pytest_cache
```

Direct execution:
```bash
python3 pac-man.py config.json
```

## Code Standards

- **flake8** compliant; **mypy** must pass without errors (strict mode preferred)
- Type hints required on all functions using the `typing` module
- **Google-style docstrings** (PEP 257-compliant) on all public modules, classes and functions — sections `Args:`, `Returns:`, `Raises:` when relevant. Verified by `flake8-docstrings` with `docstring-convention = google`.
- All errors caught with try-except — no Python tracebacks may reach the user

## Architecture

The game is structured around a central game loop with these modules:

**`pac-man.py`** — Entry point. Validates the single CLI argument (config file path), loads config, launches the game.

**Config module** — Parses a JSON file that supports `#`-prefixed comment lines. Invalid/missing values are clamped to safe defaults with logged warnings (never crash). Key config fields:
- `highscore_filename`, `lives` (default 3), `pacgum` count (default 42)
- `points_per_pacgum` (10), `points_per_super_pacgum` (50), `points_per_ghost` (200)
- `seed` (42), `level_max_time` (90 seconds)
- `level`: array of `{width, height}` objects — minimum 10 entries

**Maze module** — Wraps the external **A-Maze-ing** package (must not be modified or reimplemented). Use `PERFECT=False` to generate Pac-Man-compatible corridors. Derives from the generated maze:
- Pacgum positions (all corridors)
- Super-pacgum positions (4 corners)
- Ghost spawn points (one per corner)
- Player spawn point (maze center)

**Game state module** — Drives the state machine: `MainMenu → Playing → Paused → Win/Lose → HighscoreEntry → MainMenu`. Tracks lives, score, current level index, and remaining time.

**Player module** — Arrow/WASD movement restricted to corridors. Eating all pacgums = level win. Losing all lives = game over. Respawn at center after each life loss.

**Ghost module** — 4 autonomous ghosts starting at corners. Chase player when normal; flee when edible (triggered by super-pacgum). Respawn at their corner 5–10 s after being eaten. Movement is corridor-only.

**Scoring/highscore module** — Score never decreases. Persists top-10 scores (with player names, max 10 alphanumeric chars + spaces) to a JSON file. Loaded at startup, saved at game end. Must be robust to file errors.

**UI module** — Manages all screens:
- *Main menu*: Start, View Highscores, Instructions, Exit
- *HUD*: score, lives, level, time remaining (always visible during play)
- *Pause menu*: Resume, Return to Main Menu
- *Game over / Victory screens*: final score + name entry for highscore

**Cheat mode** — Optional debug mode for peer-evaluation; suggested features: invincibility, level skip, ghost freeze, extra lives, speed boost.

## Level Progression

- Level 1 always uses seed 42 (deterministic for grading)
- Subsequent levels use randomly generated mazes
- Player carries score and lives across levels
- Minimum 10 levels; timeout behavior (restart vs. skip) is implementer's choice

## Key Constraints

- Game must be packaged for Steam or Itch.io (free, unlisted/private build) with a packaging script at repo root
- README.md must start with "This project has been created as part of the 42 curriculum by …" and include architecture, maze generation, highscore, and project management sections
