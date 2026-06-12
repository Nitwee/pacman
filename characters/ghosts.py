"""Ghost entities and their simple movement strategies."""

from abc import abstractmethod
import random

from mazegen import Coordinate

from characters.characters import Character, Direction
from characters.ghost_states import ChaseState, GhostState
from characters.step_context import StepContext
from maze import Maze


class Ghost(Character):
    """Base ghost that can choose and apply one-cell moves.

    A :class:`GhostState` instance drives pace, behaviour and sprite
    selection. The ghost defers ``step`` and ``step_interval_ms`` to
    the current state — see :mod:`characters.ghost_states`.
    """

    def __init__(
        self,
        position: Coordinate,
        target: Character,
        direction: Direction,
        maze: Maze,
    ) -> None:
        """Create a ghost at ``position`` chasing ``target``."""
        super().__init__(position, direction, position)
        self.target = target
        self.maze = maze
        self.last_position: Coordinate | None = None
        self.state: GhostState = ChaseState()

    @property
    def step_interval_ms(self) -> int:
        """Delegate the pace to the current state."""
        return self.state.step_interval_ms

    def step(self, ctx: StepContext) -> None:
        """Delegate the per-step behaviour to the current state."""
        self.state.step(self, ctx)

    @abstractmethod
    def choose_next_position(
        self,
        choices: list[tuple[Coordinate, Direction]],
    ) -> Coordinate:
        """Pick the next cell from reachable ``choices``."""
        ...

    def move(
        self,
        frightened: bool = False,
        blocked_positions: set[Coordinate] | None = None,
    ) -> None:
        """Move the ghost one cell through the maze."""
        choices = self._reachable_choices()
        choices = self._without_blocked_positions(choices, blocked_positions)
        if not choices:
            self.previous_position = self.position
            return
        directions_by_position = {
            position: direction for position, direction in choices
        }
        if len(choices) == 1:
            next_position = choices[0][0]
        else:
            if frightened:
                next_position = self.frightened_next_step(choices)
            else:
                next_position = self.choose_next_position(choices)
            if next_position not in directions_by_position:
                if frightened:
                    next_position = self._manhattan_inversed(choices)
                else:
                    next_position = self._closest_to_target(choices)[0]
        direction = directions_by_position[next_position]
        self.last_position = self.position
        self.move_to(next_position, direction)

    def move_to_spawn(
        self,
        blocked_positions: set[Coordinate] | None = None,
    ) -> None:
        """Move an eaten ghost one cell back toward its spawn.

        The arrival transition (back to :class:`ChaseState`) is the
        responsibility of :class:`EyesState`, which checks
        ``position == spawn`` before delegating here.
        """
        choices = self._reachable_choices(avoid_backtracking=False)
        choices = self._without_blocked_positions(choices, blocked_positions)
        if not choices:
            self.previous_position = self.position
            return

        directions_by_position = {
            position: direction for position, direction in choices
        }
        next_position = self.bfs_next_step(self.position, self.spawn)
        if next_position not in directions_by_position:
            next_position = self._closest_to_position(choices, self.spawn)[0]

        direction = directions_by_position[next_position]
        self.last_position = self.position
        self.move_to(next_position, direction)

    def _reachable_choices(
        self,
        avoid_backtracking: bool = True,
    ) -> list[tuple[Coordinate, Direction]]:
        """Return reachable neighbours, avoiding immediate backtracking."""
        choices = []
        for position, wall in self.maze.reachable_neighbors(self.position):
            direction = Direction.from_wall(wall)
            choice = (position, direction)
            choices.append(choice)

        if not avoid_backtracking:
            return choices

        forward_choices = [
            choice for choice in choices if choice[0] != self.last_position
        ]
        if forward_choices:
            return forward_choices
        return choices

    def _without_blocked_positions(
        self,
        choices: list[tuple[Coordinate, Direction]],
        blocked_positions: set[Coordinate] | None,
    ) -> list[tuple[Coordinate, Direction]]:
        """Prefer choices that are not already occupied by another ghost."""
        if not blocked_positions:
            return choices

        free_choices = [
            choice for choice in choices if choice[0] not in blocked_positions
        ]
        if free_choices:
            return free_choices
        return choices

    def _closest_to_target(
        self,
        choices: list[tuple[Coordinate, Direction]],
    ) -> tuple[Coordinate, float]:
        """Return the candidate with the shortest Manhattan distance."""
        return self._closest_to_position(choices, self.target.position)

    def _closest_to_position(
        self,
        choices: list[tuple[Coordinate, Direction]],
        target: Coordinate,
    ) -> tuple[Coordinate, float]:
        """Return the candidate with the shortest Manhattan distance."""
        best_position = self.position
        best_dist = float("inf")
        for position, _ in choices:
            dist = abs(position[0] - target[0]) + abs(
                position[1] - target[1]
            )
            if dist < best_dist:
                best_dist = dist
                best_position = position
        return (best_position, best_dist)

    def bfs_next_step(
        self, position: Coordinate, target: Coordinate
    ) -> Coordinate:
        """Return the first step from ``position`` toward ``target``."""
        queue = [position]
        visited = {position}
        parent: dict[Coordinate, Coordinate] = {}
        while queue:
            curr = queue.pop(0)
            if curr == target:
                break
            for neighbor, _ in self.maze.reachable_neighbors(curr):
                if neighbor not in visited:
                    visited.add(neighbor)
                    parent[neighbor] = curr
                    queue.append(neighbor)

        if target not in parent:
            return position
        curr = target
        while parent[curr] != position:
            curr = parent[curr]
        return curr

    def frightened_next_step(
        self,
        choices: list[tuple[Coordinate, Direction]],
    ) -> Coordinate:
        """Move toward a cell roughly opposite Pac-Man."""
        ghost_col, ghost_row = self.position
        pac_col, pac_row = self.target.position

        flee_target = (
            ghost_col + (ghost_col - pac_col),
            ghost_row + (ghost_row - pac_row),
        )

        next_position = self.bfs_next_step(self.position, flee_target)

        if next_position == self.position:
            return self._manhattan_inversed(choices)

        return next_position

    def _manhattan_inversed(
        self,
        choices: list[tuple[Coordinate, Direction]],
    ) -> Coordinate:
        """Return the candidate with the greatest Manhattan distance."""
        best_position = self.position
        best_dist = -1

        for position, _ in choices:
            dist = abs(position[0] - self.target.position[0]) + abs(
                position[1] - self.target.position[1]
            )

            if dist > best_dist:
                best_dist = dist
                best_position = position

        return best_position


class Blinky(Ghost):
    """Red ghost: directly chases Pac-Man."""

    def choose_next_position(
        self,
        choices: list[tuple[Coordinate, Direction]],
    ) -> Coordinate:
        """Choose the reachable cell closest to Pac-Man."""
        best_position, best_dist = self._closest_to_target(choices)
        if best_dist > 5:
            return self.bfs_next_step(self.position, self.target.position)
        return best_position


class Pinky(Ghost):
    """Pink ghost: tries to ambush Pac-Man."""

    def choose_next_position(
        self,
        choices: list[tuple[Coordinate, Direction]],
    ) -> Coordinate:
        """Choose the next step toward Pac-Man's future position."""
        target = self._ambush_target()
        next_position = self.bfs_next_step(self.position, target)

        if next_position == self.position:
            return self._closest_to_target(choices)[0]
        return next_position

    def _ambush_target(self) -> Coordinate:
        """Return a cell ahead of Pac-Man."""
        col, row = self.target.position
        ambush_dist = 4
        if self.target.direction == Direction.UP:
            return (col, row - ambush_dist)
        if self.target.direction == Direction.RIGHT:
            return (col + ambush_dist, row)
        if self.target.direction == Direction.DOWN:
            return (col, row + ambush_dist)
        return (col - ambush_dist, row)


class Inky(Ghost):
    """Cyan ghost: picks a random open corridor."""

    def choose_next_position(
        self,
        choices: list[tuple[Coordinate, Direction]],
    ) -> Coordinate:
        """Choose a random reachable cell."""
        return random.choice(choices)[0]


class Clyde(Ghost):
    """Orange ghost: chases from afar and wanders when close."""

    def __init__(
        self,
        position: Coordinate,
        target: Character,
        direction: Direction,
        accepted_dist: int,
        maze: Maze,
    ) -> None:
        """Create Clyde with a distance threshold for wandering."""
        super().__init__(position, target, direction, maze)
        self.accepted_dist = accepted_dist

    def choose_next_position(
        self,
        choices: list[tuple[Coordinate, Direction]],
    ) -> Coordinate:
        """Chase when far away; wander randomly when too close."""
        best_position, best_dist = self._closest_to_target(choices)
        if best_dist < self.accepted_dist:
            return random.choice(choices)[0]
        return best_position
