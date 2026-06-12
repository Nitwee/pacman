"""Tests for the Pac-Man Maze wrapper around mazegen."""

import pytest

from mazegen import LOGO_HEIGHT, LOGO_WIDTH, WallBits

from maze import Maze


def test_grid_dimensions_match_inputs() -> None:
    m = Maze(width=20, height=15, seed=42, pacgum_count=10)
    assert m.width == 20
    assert m.height == 15
    assert len(m.grid) == 15
    assert all(len(row) == 20 for row in m.grid)


def test_super_pacgums_are_four_corners() -> None:
    m = Maze(width=20, height=15, seed=42, pacgum_count=10)
    assert m.super_pacgums == [
        (0, 0),
        (19, 0),
        (0, 14),
        (19, 14),
    ]


def test_ghost_spawns_match_corners() -> None:
    m = Maze(width=20, height=15, seed=42, pacgum_count=10)
    assert m.ghost_spawns == m.super_pacgums


def test_player_spawn_in_logo_gap_when_logo_fits() -> None:
    m = Maze(width=20, height=15, seed=42, pacgum_count=10)
    start_col = (20 - LOGO_WIDTH) // 2
    start_row = (15 - LOGO_HEIGHT) // 2
    expected = (start_col + 3, start_row + 2)
    assert m.player_spawn == expected
    spawn_cell = m.grid[expected[1]][expected[0]]
    assert spawn_cell.is_pattern is False


def test_player_spawn_falls_back_to_centre_for_small_maze() -> None:
    m = Maze(width=5, height=4, seed=42, pacgum_count=2)
    assert m.player_spawn == (2, 2)


def test_pacgum_count_respected_when_below_eligible_max() -> None:
    m = Maze(width=20, height=15, seed=42, pacgum_count=42)
    assert len(m.pacgums) == 42


def test_pacgum_count_can_be_zero() -> None:
    """A zero pacgum count is allowed and leaves only super pacgums."""
    m = Maze(width=20, height=15, seed=42, pacgum_count=0)
    assert len(m.pacgums) == 0
    assert len(m.super_pacgums) == 4


def test_pacgum_count_clamped_to_max_with_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level("WARNING"):
        m = Maze(width=4, height=3, seed=42, pacgum_count=100)
    # 4*3 = 12 cells, 4 corners + 1 spawn excluded → 7 eligible cells.
    # Plus half-cells (boundary positions) between corridors → 18 total.
    assert len(m.pacgums) == 18
    assert "clamping" in caplog.text.lower()


def test_pacgums_exclude_logo_corners_and_spawn() -> None:
    m = Maze(width=20, height=15, seed=42, pacgum_count=42)
    excluded = set(m.super_pacgums) | {m.player_spawn}
    for col, row in m.pacgums:
        assert (col, row) not in excluded
        # For half-cells (float coordinates), verify the rounded cell.
        # For full cells, directly check the grid.
        cell_col, cell_row = int(col), int(row)
        if (col, row) == (cell_col, cell_row):
            # Full cell: check grid directly
            assert m.grid[cell_row][cell_col].is_pattern is False
        else:
            # Half-cell: check the cell it's in is not pattern
            if cell_col < m.width and cell_row < m.height:
                assert m.grid[cell_row][cell_col].is_pattern is False


def test_same_seed_yields_same_layout() -> None:
    a = Maze(width=20, height=15, seed=42, pacgum_count=42)
    b = Maze(width=20, height=15, seed=42, pacgum_count=42)
    assert a.pacgums == b.pacgums
    a_walls = [
        (cell.col, cell.row, int(cell.walls)) for row in a.grid for cell in row
    ]
    b_walls = [
        (cell.col, cell.row, int(cell.walls)) for row in b.grid for cell in row
    ]
    assert a_walls == b_walls


def test_can_move_agrees_with_cell_walls() -> None:
    m = Maze(width=20, height=15, seed=42, pacgum_count=42)
    cell = m.grid[5][7]
    for direction in (
        WallBits.NORTH,
        WallBits.EAST,
        WallBits.SOUTH,
        WallBits.WEST,
    ):
        assert m.can_move((7, 5), direction) is (not cell.has_wall(direction))


def test_reachable_neighbors_only_returns_open_adjacent_cells() -> None:
    m = Maze(width=20, height=15, seed=42, pacgum_count=42)
    position = m.player_spawn
    for neighbor, direction in m.reachable_neighbors(position):
        assert m.can_move(position, direction)
        assert m.neighbor(position, direction) == neighbor
