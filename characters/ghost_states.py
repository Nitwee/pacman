"""State pattern implementation for ghost behaviour modes.

Each :class:`GhostState` bundles together the data and the behaviour
that vary between a ghost's three modes:

- :class:`ChaseState` — the default pursuit behaviour.
- :class:`FrightenedState` — flees Pac-Man during a super pacgum.
- :class:`EyesState` — returns to the spawn after being eaten,
  faster than the chasing pace and non-collidable.

Transitions are explicit (``ghost.state = OtherState()``) and live
either inside a state's :meth:`step` (Eyes → Chase on reaching spawn)
or in the engine (Chase ↔ Frightened on super-pacgum events, → Eyes
when Pac-Man eats the ghost).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from characters.ghosts import Ghost
    from characters.step_context import StepContext


GhostStateKind = Literal["chase", "frightened", "eyes"]


class GhostState(ABC):
    """Polymorphic mode driving a ghost's pace, movement and sprite.

    Attributes:
        step_interval_ms: Time between two cell-sized steps in this
            state. Reads through :attr:`Ghost.step_interval_ms`.
        kind: Discriminator used by the renderer to pick the right
            sprite or animation.
        is_collidable: False for eyes — Pac-Man can phase through a
            ghost on its way back to spawn.
    """

    step_interval_ms: int
    kind: GhostStateKind
    is_collidable: bool

    @abstractmethod
    def step(self, ghost: Ghost, ctx: StepContext) -> None:
        """Advance the ghost one cell according to this state's rules."""
        ...


class ChaseState(GhostState):
    """Default mode: each ghost runs its own pursuit strategy."""

    step_interval_ms = 600
    kind: GhostStateKind = "chase"
    is_collidable = True

    def step(self, ghost: Ghost, ctx: StepContext) -> None:
        """Move toward Pac-Man using the ghost-specific AI."""
        blocked = ctx.manager.blocked_positions_for(ghost)
        ghost.move(frightened=False, blocked_positions=blocked)


class FrightenedState(GhostState):
    """Triggered by a super pacgum: ghost flees Pac-Man."""

    step_interval_ms = 600
    kind: GhostStateKind = "frightened"
    is_collidable = True

    def step(self, ghost: Ghost, ctx: StepContext) -> None:
        """Move away from Pac-Man (BFS to a cell roughly opposite)."""
        blocked = ctx.manager.blocked_positions_for(ghost)
        ghost.move(frightened=True, blocked_positions=blocked)


class EyesState(GhostState):
    """Eaten ghost returning to its spawn at double pace."""

    step_interval_ms = 300
    kind: GhostStateKind = "eyes"
    is_collidable = False

    def step(self, ghost: Ghost, ctx: StepContext) -> None:
        """Step toward spawn; flip back to :class:`ChaseState` on arrival."""
        if ghost.position == ghost.spawn:
            ghost.previous_position = ghost.position
            ghost.last_position = None
            ghost.state = ChaseState()
            return
        ghost.move_to_spawn(blocked_positions=None)
