"""Pac-Man player entity."""

from mazegen import Coordinate

from characters.characters import Character, Direction
from characters.pacman_states import (
    BoostedPacmanState,
    IdlePacmanState,
    MovingPacmanState,
    PacmanState,
)
from characters.step_context import StepContext
from maze import Maze


class Pacman(Character):
    """The player-controlled character.

    Pac-Man uses the classic arcade input model: a key press updates
    an *intended* direction rather than moving Pac-Man directly. On
    every step driven by the engine, Pac-Man tries the intended
    direction first and falls back to the current direction if a
    wall blocks it. The intent persists across steps so the player
    can press a direction a few cells before an intersection and the
    turn happens as soon as a corridor opens.

    A :class:`PacmanState` instance drives pace and whether ``step``
    actually moves Pac-Man (Idle stays put). See
    :mod:`characters.pacman_states` for the three modes and their
    transition rules.

    Attributes:
        intended_direction: Direction the player wants Pac-Man to
            face at the next step.
        state: Current :class:`PacmanState` (Idle, Moving or Boosted).
        speed_multiplier: Cheat-driven speed scale. ``1.0`` is the
            state's native pace; ``2.0`` doubles it (halves the step
            interval), ``0.5`` halves it (doubles the interval).
            Persists across state changes (Moving ↔ Boosted) so the
            cheat survives super-pacgum windows.
        noclip: Cheat that lets Pac-Man cross walls. Grid bounds are
            still enforced so he can never leave the maze.
    """

    MIN_STEP_INTERVAL_MS = 50
    MAX_STEP_INTERVAL_MS = 600

    intended_direction: Direction
    state: PacmanState
    speed_multiplier: float
    noclip: bool

    def __init__(self, position: Coordinate, direction: Direction) -> None:
        """Create Pac-Man at ``position`` facing ``direction``."""
        super().__init__(position, direction, position)
        self.intended_direction = direction
        self.state = IdlePacmanState()
        self.speed_multiplier = 1.0
        self.noclip = False

    @property
    def step_interval_ms(self) -> int:
        """Effective pace: state pace divided by the cheat multiplier.

        Division (rather than addition) happens here so each speed
        notch scales the pace relatively to the current state — the
        same multiplier yields a coherent boost in both Moving and
        Boosted modes. The result is clamped to a safe range.
        """
        effective = int(self.state.step_interval_ms / self.speed_multiplier)
        return max(
            self.MIN_STEP_INTERVAL_MS,
            min(self.MAX_STEP_INTERVAL_MS, effective),
        )

    @property
    def is_moving(self) -> bool:
        """True once the player has queued a direction (not Idle)."""
        return not isinstance(self.state, IdlePacmanState)

    @property
    def boosted(self) -> bool:
        """True while a super pacgum is shortening the step interval."""
        return isinstance(self.state, BoostedPacmanState)

    def step(self, ctx: StepContext) -> None:
        """Delegate the per-step behaviour to the current state."""
        self.state.step(self, ctx)

    def queue_direction(self, direction: Direction) -> None:
        """Set the player's intended direction.

        A single intent slot — each call overwrites the previous one,
        so accidental fat-finger presses don't accumulate. The
        intent is honoured at the next engine step that finds the
        intended corridor open.

        Calling :meth:`queue_direction` for the first time also exits
        :class:`IdlePacmanState` so Pac-Man actually starts moving.

        Args:
            direction: Direction the player wants Pac-Man to take.
        """
        self.intended_direction = direction
        if isinstance(self.state, IdlePacmanState):
            self.state = MovingPacmanState()

    def try_step(self, maze: Maze) -> bool:
        """Advance one cell, honouring the intended direction first.

        Returns:
            True when Pac-Man moved, False when both the intended
            and current directions are blocked.
        """
        if self.try_move(maze, self.intended_direction):
            return True
        if self.try_move(maze, self.direction):
            return True
        # Both directions blocked. Snap previous_position to current
        # so the renderer's lerp degenerates to (current, current) =
        # stay-put. Without this, the renderer would keep pulling
        # Pac-Man back to the cell he came from on every step.
        self.previous_position = self.position
        return False

    def try_move(self, maze: Maze, direction: Direction) -> bool:
        """Move one cell in ``direction`` if no wall blocks Pac-Man.

        With :attr:`noclip` set, the wall check is bypassed but grid
        bounds are still enforced (``maze.neighbor`` returns ``None``
        when stepping off the maze).

        Args:
            maze: Current maze wrapper.
            direction: Desired movement direction.

        Returns:
            True when Pac-Man moved, False when blocked.
        """
        wall = direction.to_wall()
        if not self.noclip and not maze.can_move(self.position, wall):
            return False
        next_position = maze.neighbor(self.position, wall)
        if next_position is None:
            return False
        self.move_to(next_position, direction)
        return True

    def reset_to_spawn(self) -> None:
        """Respawn Pac-Man and clear the intent (wait for new input)."""
        super().reset_to_spawn()
        self.state = IdlePacmanState()
        self.intended_direction = self.direction
        self._step_elapsed_ms = 0
