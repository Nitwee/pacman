"""Tests for character integration with the Maze wrapper."""

from characters import (
    CharacterManager,
    ChaseState,
    Direction,
    EyesState,
    Pacman,
)
from characters.step_context import StepContext
from maze import Maze
from mazegen import Coordinate, WallBits


class _BlockedMaze:
    """Minimal Maze stand-in where every move is refused."""

    def can_move(self, position: Coordinate, wall: WallBits) -> bool:
        return False

    def neighbor(
        self, position: Coordinate, wall: WallBits
    ) -> Coordinate | None:
        return None


def _open_cell_with_choices(
    maze: Maze,
) -> tuple[Coordinate, list[tuple[Coordinate, WallBits]]]:
    """Return a cell that has at least two reachable neighbours."""
    for row in range(maze.height):
        for col in range(maze.width):
            position = (col, row)
            choices = maze.reachable_neighbors(position)
            if len(choices) >= 2:
                return (position, choices)
    raise AssertionError("No cell with enough choices found")


def test_character_manager_uses_maze_spawns() -> None:
    """Pac-Man and ghosts spawn from Maze-derived coordinates."""
    maze = Maze(width=20, height=15, seed=42, pacgum_count=10)
    manager = CharacterManager(maze)

    assert manager.pacman.position == maze.player_spawn
    assert manager.ghost_positions() == [
        maze.ghost_spawns[0],
        maze.ghost_spawns[1],
        maze.ghost_spawns[3],
        maze.ghost_spawns[2],
    ]


def test_pacman_moves_only_through_open_corridors() -> None:
    """Pac-Man advances through open walls and refuses blocked walls."""
    maze = Maze(width=20, height=15, seed=42, pacgum_count=10)
    manager = CharacterManager(maze)
    start = manager.pacman.position
    neighbor, wall = maze.reachable_neighbors(start)[0]

    assert manager.pacman.try_move(maze, Direction.from_wall(wall))
    assert manager.pacman.position == neighbor

    blocked = [
        direction
        for direction in Direction
        if not maze.can_move(manager.pacman.position, direction.to_wall())
    ]
    if blocked:
        before = manager.pacman.position
        assert not manager.pacman.try_move(maze, blocked[0])
        assert manager.pacman.position == before


def test_blocked_pacman_step_snaps_previous_to_current() -> None:
    """A blocked step collapses the lerp source so the renderer halts.

    Without this, the renderer would keep interpolating from the
    previously committed cell, visually rewinding Pac-Man between
    his last cell and the wall on every blocked tick.
    """
    pacman = Pacman((5, 5), Direction.RIGHT)
    pacman.previous_position = (4, 5)
    pacman.queue_direction(Direction.RIGHT)

    moved = pacman.try_step(_BlockedMaze())  # type: ignore[arg-type]

    assert not moved
    assert pacman.position == (5, 5)
    assert pacman.previous_position == (5, 5)


def test_ghosts_move_without_exposing_mazegen_cells() -> None:
    """Ghost movement updates simple ``(col, row)`` positions."""
    maze = Maze(width=20, height=15, seed=42, pacgum_count=10)
    manager = CharacterManager(maze)
    before = manager.ghost_positions()
    ctx = StepContext(maze=maze, super_pacgum_collected=False, manager=manager)

    # One full step interval is enough to fire one ghost step.
    manager.step_all(ChaseState.step_interval_ms, ctx)

    assert manager.ghost_positions() != before
    assert all(isinstance(pos, tuple) for pos in manager.ghost_positions())


def test_ghost_avoids_blocked_position_when_possible() -> None:
    """A ghost avoids stepping into another ghost's reserved cell."""
    maze = Maze(width=20, height=15, seed=42, pacgum_count=10)
    manager = CharacterManager(maze)
    ghost = manager.ghosts["blinky"]
    start, choices = _open_cell_with_choices(maze)
    blocked_position = choices[0][0]

    ghost.position = start
    ghost.previous_position = start
    ghost.last_position = None
    manager.pacman.position = blocked_position

    ghost.move(blocked_positions={blocked_position})

    assert ghost.position != blocked_position


def test_dead_ghost_returns_to_spawn_without_teleporting() -> None:
    """An eyes ghost walks back to spawn before becoming alive again."""
    maze = Maze(width=20, height=15, seed=42, pacgum_count=10)
    manager = CharacterManager(maze)
    ghost = manager.ghosts["blinky"]
    start = manager.pacman.position

    ghost.position = start
    ghost.previous_position = start
    ghost.state = EyesState()

    ghost.move_to_spawn()

    assert ghost.previous_position == start
    assert ghost.position != start
    assert ghost.position != ghost.spawn
    assert isinstance(ghost.state, EyesState)
