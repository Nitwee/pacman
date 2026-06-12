"""Pac-Man-specific wrapper around the external mazegen package.

Encapsulates maze generation with ``perfect=False`` (Pac-Man corridors
have cycles) and derives the static layout of one level: player spawn,
ghost spawns, super-pacgums and pacgums.

The 42 logo placed automatically by mazegen at the centre of the maze
is **kept** — its closed cells are simply considered unreachable. The
player spawns in the middle column of the logo block, in the gap
between the "4" and the "2" which mazegen leaves as a passable
corridor.
"""

import logging
import random
from typing import Optional

from mazegen import (
    Coordinate,
    LOGO_HEIGHT as _MAZEGEN_LOGO_HEIGHT,
    LOGO_WIDTH as _MAZEGEN_LOGO_WIDTH,
    MazeGenerator,
    MazeGrid,
    WallBits,
)

# mazegen has no py.typed marker, so its constants come back as Any.
# Re-bind them as ints so comparisons stay typed.
LOGO_HEIGHT: int = _MAZEGEN_LOGO_HEIGHT
LOGO_WIDTH: int = _MAZEGEN_LOGO_WIDTH

# A sub-cell location. Grid cells (mazegen.Coordinate = tuple[int, int])
# are valid Positions, but pacgums also live at corridor mid-points
# (half-cells), so the full pickup geometry is float-valued.
Position = tuple[float, float]

logger = logging.getLogger(__name__)


class MazeError(Exception):
    """Raised when the external maze generator fails to produce a grid."""

    pass


class Maze:
    """Static layout of one Pac-Man level.

    Wraps :class:`mazegen.MazeGenerator` and derives every position the
    rest of the game needs.

    Attributes:
        width: Maze width in cells.
        height: Maze height in cells.
        grid: 2D grid of :class:`mazegen.Cell` indexed as
            ``grid[row][col]``.
        player_spawn: Cell where the player respawns each life.
        ghost_spawns: One spawn per maze corner (same positions as
            super-pacgums).
        super_pacgums: The four maze corners.
        pacgums: Random sample of corridor cells; excludes logo cells,
            super-pacgums and the player spawn.
    """

    def __init__(
        self,
        width: int,
        height: int,
        seed: Optional[int],
        pacgum_count: int,
        ratio: float = 0.1,
    ) -> None:
        """Generate the maze and derive the static layout.

        Args:
            width: Maze width in cells.
            height: Maze height in cells.
            seed: RNG seed for both maze generation and pacgum
                placement. ``None`` for non-deterministic generation.
            pacgum_count: Target number of pacgums. Clamped to the
                number of eligible cells with a logged warning if it
                exceeds it.
            ratio: Mazegen's ``ratio`` parameter controlling the sparseness
                of the maze. Must be between 0 and 1; higher values
                produce more corridors and fewer dead ends. Default 0.1.
        """
        self.width = width
        self.height = height
        try:
            gen = MazeGenerator(
                width=width,
                height=height,
                seed=seed,
                perfect=False,
                ratio=ratio,
            )
            # mazegen requires entry/exit but Pac-Man ignores them. Use
            # opposite corners as throwaway endpoints; the is_entry /
            # is_exit flags left on those cells are not consumed downstream.
            gen.generate(entry=(0, 0), exit_=(width - 1, height - 1))
            self.grid: MazeGrid = gen.get_structure()
        except Exception as exc:
            raise MazeError(
                f"Maze generator failed ({width}×{height}, seed={seed}): {exc}"
            ) from exc
        self.player_spawn: Coordinate = self._compute_player_spawn()
        corners = self._compute_corners()
        self.ghost_spawns: list[Coordinate] = corners
        # super_pacgums share the same coordinates as the corner spawns,
        # but expose them as Position so they sit in the same type as
        # pacgums (which include half-cell corridor mid-points).
        self.super_pacgums: list[Position] = [(c, r) for c, r in corners]
        self.pacgums: list[Position] = self._sample_pacgums(
            seed, pacgum_count
        )

    def can_move(
        self,
        position: Coordinate,
        direction: WallBits,
    ) -> bool:
        """Check whether moving from ``position`` in ``direction`` is allowed.

        Args:
            position: Starting cell as ``(col, row)``.
            direction: Direction of intended move.

        Returns:
            True if no wall blocks the move, False otherwise.
        """
        col, row = position
        cell = self.grid[row][col]
        return not bool(cell.has_wall(direction))

    def neighbor(
        self,
        position: Coordinate,
        direction: WallBits,
    ) -> Optional[Coordinate]:
        """Return the neighbouring coordinate in ``direction`` if valid.

        Args:
            position: Starting cell as ``(col, row)``.
            direction: Direction of the neighbour to resolve.

        Returns:
            The neighbouring ``(col, row)`` or ``None`` when it would
            fall outside the maze.
        """
        col, row = position
        if direction == WallBits.NORTH:
            row -= 1
        elif direction == WallBits.SOUTH:
            row += 1
        elif direction == WallBits.WEST:
            col -= 1
        else:
            col += 1
        if col < 0 or row < 0 or col >= self.width or row >= self.height:
            return None
        return (col, row)

    def reachable_neighbors(
        self,
        position: Coordinate,
    ) -> list[tuple[Coordinate, WallBits]]:
        """Return open neighbouring cells from ``position``.

        This is the movement API used by characters and ghost AI so
        they do not need to know how ``mazegen`` stores walls.

        Args:
            position: Starting cell as ``(col, row)``.

        Returns:
            List of ``(coordinate, direction)`` pairs for each open
            corridor.
        """
        neighbors: list[tuple[Coordinate, WallBits]] = []
        for direction in (
            WallBits.NORTH,
            WallBits.EAST,
            WallBits.SOUTH,
            WallBits.WEST,
        ):
            if not self.can_move(position, direction):
                continue
            next_position = self.neighbor(position, direction)
            if next_position is not None:
                neighbors.append((next_position, direction))
        return neighbors

    def _logo_fits(self) -> bool:
        """Mirror mazegen's own check for whether the 42 logo is placed.

        Returns:
            True if the maze is strictly larger than the logo footprint.
        """
        return self.width > LOGO_WIDTH and self.height > LOGO_HEIGHT

    def _compute_player_spawn(self) -> Coordinate:
        """Pick the spawn cell.

        For mazes that host the 42 logo, the spawn lands in the middle
        column of the logo block — the gap between the "4" and the "2"
        which mazegen leaves as a passable corridor (see
        ``LOGO_42_PATTERN`` column index 3 in mazegen). For smaller
        mazes where the logo is not placed, we fall back to the
        geometric centre.

        Returns:
            ``(col, row)`` of the spawn cell.
        """
        if self._logo_fits():
            start_col = (self.width - LOGO_WIDTH) // 2
            start_row = (self.height - LOGO_HEIGHT) // 2
            return (start_col + 3, start_row + 2)
        return (self.width // 2, self.height // 2)

    def _compute_corners(self) -> list[Coordinate]:
        """Return the four maze corners as ``(col, row)`` pairs.

        Returns:
            List of corner coordinates in clockwise order starting
            top-left.
        """
        return [
            (0, 0),
            (self.width - 1, 0),
            (0, self.height - 1),
            (self.width - 1, self.height - 1),
        ]

    def _sample_pacgums(
        self,
        seed: Optional[int],
        count: int,
    ) -> list[Position]:
        """Pick a deterministic random sample of corridor positions.

        Excludes logo cells, the four corners (super-pacgums) and the
        player spawn. Eligible positions are cell centres and corridor
        mid-points (half-cells between two adjacent corridor cells).
        If ``count`` exceeds the number of eligible positions, every
        eligible position is used and a warning is logged.

        Args:
            seed: RNG seed for reproducible placement.
            count: Target number of pacgums.

        Returns:
            List of ``(col, row)`` positions. Values may be half-cells.
        """
        excluded = set(self.super_pacgums) | {self.player_spawn}
        cell_centers: list[Coordinate] = [
            (cell.col, cell.row)
            for row in self.grid
            for cell in row
            if not cell.is_pattern and (cell.col, cell.row) not in excluded
        ]
        half_cells: set[Position] = set()
        for coord in cell_centers:
            half_cells |= {
                self._half_cell(neighbor, direction.opposite())
                for neighbor, direction in self.reachable_neighbors(coord)
            }
        eligible: list[Position] = [(c, r) for c, r in cell_centers]
        eligible.extend(half_cells)
        if count >= len(eligible):
            if count > len(eligible):
                logger.warning(
                    "pacgum_count %d exceeds eligible cells %d; "
                    "clamping to %d",
                    count,
                    len(eligible),
                    len(eligible),
                )
            return eligible
        rng = random.Random(seed)
        return rng.sample(eligible, count)

    def _half_cell(self, coord: Coordinate, direction: WallBits) -> Position:
        """Return the coordinate halfway to the neighbor in ``direction``.

        This is used to place pacgums in the middle of corridors.

        Args:
            coord: Starting cell as ``(col, row)``.
            direction: Direction of the neighbor to compute.

        Returns:
            The halfway coordinate as a pair of floats.
        """
        col, row = coord
        if direction == WallBits.NORTH:
            return (col, row - 0.5)
        if direction == WallBits.SOUTH:
            return (col, row + 0.5)
        if direction == WallBits.WEST:
            return (col - 0.5, row)
        return (col + 0.5, row)
