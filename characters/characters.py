"""Base character types shared by Pac-Man and ghosts."""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from mazegen import Coordinate, WallBits

if TYPE_CHECKING:
    from characters.step_context import StepContext


class Direction(Enum):
    """Cardinal movement directions used by characters."""

    UP = 1
    RIGHT = 2
    DOWN = 3
    LEFT = 4

    def to_wall(self) -> WallBits:
        """Convert this direction into the matching maze wall direction."""
        if self == Direction.UP:
            return WallBits.NORTH
        if self == Direction.RIGHT:
            return WallBits.EAST
        if self == Direction.DOWN:
            return WallBits.SOUTH
        return WallBits.WEST

    @classmethod
    def from_wall(cls, wall: WallBits) -> "Direction":
        """Convert a :class:`mazegen.WallBits` value into a Direction."""
        if wall == WallBits.NORTH:
            return cls.UP
        if wall == WallBits.EAST:
            return cls.RIGHT
        if wall == WallBits.SOUTH:
            return cls.DOWN
        return cls.LEFT


@dataclass
class Character:
    """A moving entity located on a maze cell.

    Attributes:
        position: Current cell as ``(col, row)``.
        direction: Current facing/movement direction.
        spawn: Cell used when the character respawns.
        previous_position: Cell occupied just before the latest
            :meth:`move_to`. Used by the renderer to interpolate the
            on-screen sprite between two cells over a step interval,
            producing smooth movement instead of cell-to-cell jumps.
        step_interval_ms: Time (ms) between two logical steps.
            Exposed as a ``@property`` so subclasses can return a
            dynamic value (eyes faster than alive ghosts, Pac-Man
            boosted during a super pacgum window).
    """

    position: Coordinate
    direction: Direction
    spawn: Coordinate
    previous_position: Coordinate = field(init=False)
    # Accumulated time since the last logical step; consumed by
    # :meth:`tick`. ``init=False`` keeps subclasses' ``__init__``
    # signatures untouched.
    _step_elapsed_ms: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        """Initialise the interpolation source to the spawn cell."""
        self.previous_position = self.position

    @property
    def step_interval_ms(self) -> int:
        """Default step interval; overridden by subclasses."""
        return 250

    def step_progress(self) -> float:
        """Fraction of the current step elapsed (0.0 to 1.0).

        Used by the renderer to interpolate the sprite between
        :attr:`previous_position` and :attr:`position` for smooth
        movement.
        """
        interval = self.step_interval_ms or 1
        return min(1.0, self._step_elapsed_ms / interval)

    def tick(self, dt_ms: int, ctx: "StepContext") -> None:
        """Accumulate ``dt_ms`` and apply every step now due.

        Subclasses don't override this — they implement :meth:`step`
        instead. The base loop honours :attr:`step_interval_ms` (which
        may be dynamic via a subclass property).
        """
        self._step_elapsed_ms += dt_ms
        interval = self.step_interval_ms
        if interval <= 0:
            return
        while self._step_elapsed_ms >= interval:
            self._step_elapsed_ms -= interval
            self.step(ctx)
            # Re-read the interval: a step can change ``dead`` /
            # ``boosted`` and therefore the property value.
            interval = self.step_interval_ms
            if interval <= 0:
                return

    def step(self, ctx: "StepContext") -> None:
        """Perform one logical step. No-op on the base class."""
        return

    def move_to(
        self,
        position: Coordinate,
        direction: Direction,
    ) -> None:
        """Move the character to ``position`` and update its direction.

        Records the cell we came from in
        :attr:`previous_position` so the renderer can interpolate.
        """
        self.previous_position = self.position
        self.position = position
        self.direction = direction

    def reset_to_spawn(self) -> None:
        """Move the character back to its spawn cell.

        Both :attr:`position` and :attr:`previous_position` snap to
        the spawn so no interpolation tail drags the sprite across
        the maze.
        """
        self.position = self.spawn
        self.previous_position = self.spawn
