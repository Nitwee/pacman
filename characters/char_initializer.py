"""Factory and container for gameplay characters."""

from mazegen import Coordinate

from characters.characters import Character, Direction
from characters.ghosts import Blinky, Clyde, Ghost, Inky, Pinky
from characters.pacman_char import Pacman
from characters.step_context import StepContext
from maze import Maze


class CharacterManager:
    """Owns Pac-Man and the four ghosts for one level."""

    def __init__(self, maze: Maze) -> None:
        """Create all characters from the maze's spawn positions."""
        blinky_pos, pinky_pos, clyde_pos, inky_pos = maze.ghost_spawns
        clyde_threshold = maze.width // 4 + maze.height // 4

        self.pacman = Pacman(maze.player_spawn, Direction.LEFT)
        self.ghosts: dict[str, Ghost] = {
            "blinky": Blinky(blinky_pos, self.pacman, Direction.RIGHT, maze),
            "pinky": Pinky(pinky_pos, self.pacman, Direction.LEFT, maze),
            "inky": Inky(inky_pos, self.pacman, Direction.RIGHT, maze),
            "clyde": Clyde(
                clyde_pos, self.pacman, Direction.LEFT, clyde_threshold, maze
            ),
        }

    def reset_positions(self) -> None:
        """Respawn Pac-Man and ghosts at their level starts."""
        self.pacman.reset_to_spawn()
        for ghost in self.ghosts.values():
            ghost.reset_to_spawn()

    def step_all(self, dt_ms: int, ctx: StepContext) -> None:
        """Advance every character by ``dt_ms`` of game time.

        Each character owns its step interval and accumulator, so a
        single loop is enough — Pac-Man (boosted or not), alive
        ghosts and eyes all pick the right pace through polymorphism.
        When ``ctx.ghost_freeze`` is set the ghosts are skipped
        entirely so they neither move nor build up step credit.
        """
        self.pacman.tick(dt_ms, ctx)
        if ctx.ghost_freeze:
            return
        for ghost in self.ghosts.values():
            ghost.tick(dt_ms, ctx)

    def blocked_positions_for(self, ghost: Ghost) -> set[Coordinate]:
        """Return cells occupied by other ghosts, for collision avoidance."""
        return {
            other.position
            for other in self.ghosts.values()
            if other is not ghost
            and other.state.kind != "eyes"
        }

    def all_characters(self) -> list[Character]:
        """Return every character as a flat list."""
        return [self.pacman, *self.ghosts.values()]

    def ghost_positions(self) -> list[Coordinate]:
        """Return ghost positions in renderer order."""
        return [ghost.position for ghost in self.ghosts.values()]
