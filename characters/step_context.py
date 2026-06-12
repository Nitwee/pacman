"""Per-frame inputs handed to every character's polymorphic step.

A single argument shared by all :meth:`Character.step` implementations
so the base method signature stays uniform across Pac-Man and the
ghosts. Each subclass picks from the context what it needs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from characters.char_initializer import CharacterManager
    from maze import Maze


@dataclass
class StepContext:
    """Snapshot of game state needed by characters during one step.

    Attributes:
        maze: The current maze, used for corridor lookups.
        super_pacgum_collected: Whether the super pacgum effect is
            currently active (frightens ghosts, speeds up Pac-Man).
        manager: The :class:`CharacterManager` owning every character,
            used by ghosts to compute the positions to avoid.
        ghost_freeze: When True, the manager skips ghost ticks so
            they hold their cell and accumulator. Cheat-driven.
    """

    maze: Maze
    super_pacgum_collected: bool
    manager: CharacterManager
    ghost_freeze: bool = False
