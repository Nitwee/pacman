"""State pattern implementation for Pac-Man's movement modes.

Three states only:

- :class:`IdlePacmanState` — before any input or right after respawn.
  Pac-Man stays put even though the timer accumulates.
- :class:`MovingPacmanState` — the default pace once the player has
  pressed a direction.
- :class:`BoostedPacmanState` — faster pace during a super pacgum.

Transitions are kept simple: Idle → Moving on first
:meth:`Pacman.queue_direction`; Moving ↔ Boosted on super pacgum
collection / expiration (driven by the engine); any → Idle on
respawn (``reset_to_spawn``).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from characters.pacman_char import Pacman
    from characters.step_context import StepContext


class PacmanState(ABC):
    """Polymorphic mode driving Pac-Man's pace and whether he steps.

    Attributes:
        step_interval_ms: Time between two cell-sized attempts.
            Read via :attr:`Pacman.step_interval_ms`.
    """

    step_interval_ms: int

    @abstractmethod
    def step(self, pacman: Pacman, ctx: StepContext) -> None:
        """Apply one step's worth of behaviour for this state."""
        ...


class IdlePacmanState(PacmanState):
    """Pre-input / post-respawn: no movement until the player commits."""

    # Interval still defined so the accumulator math is well-formed,
    # but :meth:`step` is a no-op so it never causes a cell move.
    step_interval_ms = 250

    def step(self, pacman: Pacman, ctx: StepContext) -> None:
        """No-op: Idle never moves Pac-Man."""
        return


class MovingPacmanState(PacmanState):
    """Default running pace, applied as soon as the player has input."""

    step_interval_ms = 250

    def step(self, pacman: Pacman, ctx: StepContext) -> None:
        """Try to advance Pac-Man one cell honouring his intent."""
        pacman.try_step(ctx.maze)


class BoostedPacmanState(PacmanState):
    """Super-pacgum-powered speed: same step logic, shorter interval."""

    step_interval_ms = 175

    def step(self, pacman: Pacman, ctx: StepContext) -> None:
        """Same step logic as :class:`MovingPacmanState`."""
        pacman.try_step(ctx.maze)
