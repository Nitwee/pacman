"""Static Pac-Man maze visualizer with logo and walls."""

from collections.abc import Iterable, Sequence

import pygame

from characters import Character, Direction, Ghost
from game_engine import EngineState, GameEngine

from graphics.animation import Animation
from graphics.assets import AssetManager, PaletteColors
from maze import Maze, Position
from mazegen import Cell, Coordinate, WallBits
from enum import Enum

_DIRECTION_SUFFIX = {
    Direction.UP: "up",
    Direction.DOWN: "down",
    Direction.LEFT: "left",
    Direction.RIGHT: "right",
}


CELL_SIZE = 32
WALL_THICKNESS = 20
OUTLINE_THICKNESS = 2
WALL_RADIUS = WALL_THICKNESS // 2
CELL_STRIDE = CELL_SIZE + WALL_THICKNESS
PADDING = 16
HUD_PANEL_WIDTH = 260

# Development inspector's default palette. The main game can choose/switch
# palettes through AssetManager without depending on this constant.
THEME_PALETTE = "red-blue-white"

# Native sprites in the sheet are 16x16; we upscale by this factor so
# they fill our 32x32 cells (and 8x8 pacgums become a clean 16x16).
SPRITE_SCALE = CELL_SIZE // 16

# Only used when running the standalone inspector with:
# python3 -m graphics.renderer config.json
SPRITE_SHEET_PATH = (
    "assets/sprites/"
    "Arcade - Pac-Man - Miscellaneous - All Assets_Palettes.png"
)

GHOST_ANIMATIONS = (
    "blinky_walk_right",
    "pinky_walk_right",
    "inky_walk_right",
    "clyde_walk_right",
)
PACMAN_ANIMATION = "pacman_chomp_right"


class Colors(tuple[int, int, int], Enum):
    """Reusable RGB colors for UI and rendering."""

    GREEN = (0, 255, 0)
    RED = (255, 0, 0)
    BLUE = (0, 0, 255)
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    GREY = (200, 200, 200)
    GOLD = (255, 220, 120)
    YELLOW = (255, 255, 0)
    ORANGE = (255, 184, 82)
    PINK = (255, 105, 180)
    CYAN = (0, 255, 255)
    SKY_BLUE = (120, 200, 255)
    LIME = (160, 255, 120)
    PEACH = (255, 180, 160)
    PURPLE = (190, 120, 255)


# id(Surface) -> upscaled Surface. Module-level cache keyed by sprite
# identity (Surfaces returned by AssetManager.get_sprite are stable).
_scaled_cache: dict[int, pygame.Surface] = {}
_score_font: pygame.font.Font | None = None


def maze_pixel_size(maze: Maze) -> tuple[int, int]:
    """Pixel size occupied by a Maze including its outer walls.

    Args:
        maze: The Maze instance.

    Returns:
        ``(width, height)`` in pixels.
    """
    return (
        maze.width * CELL_STRIDE + WALL_THICKNESS,
        maze.height * CELL_STRIDE + WALL_THICKNESS,
    )


def draw_maze(
    surface: pygame.Surface,
    maze: Maze,
    origin: tuple[int, int],
    am: AssetManager,
    pacman_anim: Animation,
    ghost_anims: Sequence[Animation],
    super_pacgum_anim: Animation,
    pacman_position: Coordinate | None = None,
    ghost_positions: Sequence[Coordinate] | None = None,
    pacgums: Iterable[Position] | None = None,
    super_pacgums: Iterable[Position] | None = None,
) -> None:
    """Draw the full Maze layout on ``surface``.

    Renders, in z-order: logo cells, walls, pacgums, super-pacgums,
    ghosts, and Pac-Man.

    Args:
        surface: Target Pygame surface.
        maze: The Maze instance to draw.
        origin: Top-left pixel of the maze area.
        am: AssetManager used to resolve sprite names to surfaces.
        pacman_anim: Animation for Pac-Man (drawn at the spawn cell).
        ghost_anims: Animations for the four ghosts, in the same
            order as ``maze.ghost_spawns``.
        super_pacgum_anim: Animation for the super-pacgum.
        pacman_position: Optional dynamic Pac-Man position. Defaults
            to ``maze.player_spawn`` for inspector usage.
        ghost_positions: Optional dynamic ghost positions. Defaults
            to ``maze.ghost_spawns``.
        pacgums: Optional remaining pacgum positions. Defaults to the
            static maze pacgum list.
        super_pacgums: Optional remaining super-pacgum positions.
            Defaults to the static maze corner list.
    """
    pacman_position = pacman_position or maze.player_spawn
    ghost_positions = ghost_positions or maze.ghost_spawns
    pacgums = pacgums if pacgums is not None else maze.pacgums
    super_pacgums = (
        super_pacgums if super_pacgums is not None else maze.super_pacgums
    )
    colors = am.get_palette_colors(am.current_palette)
    _draw_logo_cells(surface, maze, origin, colors)
    _draw_walls(surface, maze, origin, colors)
    pacgum = am.get_sprite("pacgum")
    for col, row in pacgums:
        _blit_centred(surface, pacgum, col, row, origin)
    for col, row in super_pacgums:
        sp_sprite = am.get_sprite(super_pacgum_anim.current_frame())
        _blit_centred(surface, sp_sprite, col, row, origin)
    for ghost_anim, (col, row) in zip(ghost_anims, ghost_positions):
        ghost_sprite = am.get_sprite(ghost_anim.current_frame())
        _blit_centred(surface, ghost_sprite, col, row, origin)
    col, row = pacman_position
    pacman_sprite = am.get_sprite(pacman_anim.current_frame())
    _blit_centred(surface, pacman_sprite, col, row, origin)


def draw_engine(
    surface: pygame.Surface,
    engine: GameEngine,
    origin: tuple[int, int],
    am: AssetManager,
    pacman_chomp_anim: Animation,
    pacman_death_anim: Animation,
    ghost_anims: Sequence[Animation],
    super_pacgum_anim: Animation,
) -> None:
    """Draw the current state of a :class:`GameEngine`.

    Unlike :func:`draw_maze` (which is the standalone inspector
    path drawing entities at static spawn cells), this function
    pulls dynamic state from the engine: per-character facing
    direction picks the matching animation, and per-character
    step progress lerps the on-screen pixel between previous and
    current cells for smooth movement.
    """
    colors = am.get_palette_colors(am.current_palette)
    _draw_logo_cells(surface, engine.maze, origin, colors)
    _draw_walls(surface, engine.maze, origin, colors)
    pacgum_sprite = am.get_sprite("pacgum")
    for col, row in engine.pacgums:
        _blit_centred(surface, pacgum_sprite, col, row, origin)
    super_pacgum_blink = am.get_animation("pacgum_blink")
    for col, row in engine.super_pacgums:
        super_pacgum_anim.set_definition(super_pacgum_blink)
        super_sprite = am.get_sprite(super_pacgum_anim.current_frame())
        _blit_centred(surface, super_sprite, col, row, origin)

    bonus_fruit_sprite = am.get_sprite(engine.bonus_fruit_sprite_name)
    for slot in engine.bonus_fruit_slots:
        if slot.position is None:
            continue
        _blit_centred(surface, bonus_fruit_sprite, *slot.position, origin)

    if engine.score_overlay.active and engine.last_eaten_item is not None:
        from game_engine import EdibleType

        item = engine.last_eaten_item
        if item.edible_type in (EdibleType.GHOST, EdibleType.BONUS_FRUIT):
            _draw_item_score(
                surface,
                item.points,
                _cell_centre(*item.position, origin),
                colors,
            )

    if engine.state == EngineState.DYING:
        # Pac-Man's death animation hides every ghost.
        ghost_iter: list[tuple[Animation, tuple[str, Ghost]]] = []
    else:
        ghost_iter = list(zip(ghost_anims, engine.characters.ghosts.items()))
    for ghost_anim, (ghost_name, ghost) in ghost_iter:
        ghost_pixel = _interpolated_pixel(ghost, origin, ghost.step_progress())
        # Skip drawing ghost if its score overlay is being displayed
        if (
            engine.score_overlay.active
            and engine.last_eaten_item is not None
            and ghost is engine.last_eaten_item.ghost
        ):
            continue
        kind = ghost.state.kind
        if kind == "eyes":
            ghost_sprite = am.get_sprite(
                _ghost_eyes_sprite_name(ghost.direction)
            )
        else:
            if kind == "frightened":
                anim_name = _frightened_animation_name(
                    engine.super_pacgum_timer.remaining_ms
                )
            else:
                anim_name = _ghost_walk_animation_name(
                    ghost_name, ghost.direction
                )
            ghost_anim.set_definition(am.get_animation(anim_name))
            ghost_sprite = am.get_sprite(ghost_anim.current_frame())
        _blit_at_pixel(
            surface,
            ghost_sprite,
            ghost_pixel,
        )

    pacman = engine.characters.pacman
    sprite: pygame.Surface | None
    if engine.state == EngineState.DYING:
        # Death animation: fixed sequence, no direction swap, no
        # interpolation (Pac-Man dies in place — engine snapped
        # previous_position to position when entering dying state).
        sprite = am.get_sprite(pacman_death_anim.current_frame())
    elif not engine.gameplay_freeze.active:
        pacman_chomp_anim.set_definition(
            am.get_animation(_pacman_animation_name(pacman.direction))
        )
        sprite = am.get_sprite(pacman_chomp_anim.current_frame())
    else:
        # Frozen during ghost eating
        sprite = None
    if sprite is not None:
        _blit_at_pixel(
            surface,
            sprite,
            _interpolated_pixel(pacman, origin, pacman.step_progress()),
        )


def _pacman_animation_name(direction: Direction) -> str:
    """Return the animation name for Pac-Man facing ``direction``."""
    return f"pacman_chomp_{_DIRECTION_SUFFIX[direction]}"


def _ghost_walk_animation_name(
    ghost_name: str,
    direction: Direction,
) -> str:
    """Return the walking animation name for a chasing ghost."""
    return f"{ghost_name}_walk_{_DIRECTION_SUFFIX[direction]}"


def _frightened_animation_name(super_pacgum_timer_ms: int) -> str:
    """Return the frightened animation, blinking near expiry."""
    if super_pacgum_timer_ms <= 2000:
        return "ghost_almost_scared"
    return "ghost_scared"


def _ghost_eyes_sprite_name(direction: Direction) -> str:
    """Return the eyes-only sprite name for a dead ghost."""
    return f"ghost_eyes_{_DIRECTION_SUFFIX[direction]}"


def _draw_item_score(
    surface: pygame.Surface,
    score: int,
    pixel: tuple[int, int],
    colors: PaletteColors,
) -> None:
    """Draw an eaten item's score centered at ``pixel``.

    Used for both eaten ghosts and bonus fruits — the overlay is
    visually identical, only the trigger context differs (ghosts
    also freeze gameplay, fruits don't).
    """
    text = f"+{score}"
    font = _score_overlay_font()
    shadow = font.render(text, True, Colors.BLACK)
    label = font.render(text, True, colors.secondary)
    shadow_rect = shadow.get_rect(center=(pixel[0] + 1, pixel[1] + 1))
    label_rect = label.get_rect(center=pixel)
    surface.blit(shadow, shadow_rect)
    surface.blit(label, label_rect)


def _score_overlay_font() -> pygame.font.Font:
    """Return the cached font used for the eaten-item score overlay."""
    global _score_font
    if _score_font is None:
        _score_font = pygame.font.Font(None, 30)
    return _score_font


def _interpolated_pixel(
    character: Character,
    origin: tuple[int, int],
    progress: float,
) -> tuple[int, int]:
    """Lerp the character's on-screen pixel from previous to current cell."""
    prev_col, prev_row = character.previous_position
    curr_col, curr_row = character.position
    prev_x, prev_y = _cell_centre(prev_col, prev_row, origin)
    curr_x, curr_y = _cell_centre(curr_col, curr_row, origin)
    return (
        int(prev_x + (curr_x - prev_x) * progress),
        int(prev_y + (curr_y - prev_y) * progress),
    )


def _blit_at_pixel(
    surface: pygame.Surface,
    sprite: pygame.Surface,
    pixel: tuple[int, int],
) -> None:
    """Blit a scaled sprite centred at ``pixel``."""
    scaled = _scaled(sprite)
    sw, sh = scaled.get_size()
    surface.blit(scaled, (pixel[0] - sw // 2, pixel[1] - sh // 2))


def _scaled(sprite: pygame.Surface) -> pygame.Surface:
    """Return ``sprite`` upscaled by :data:`SPRITE_SCALE`, cached.

    Args:
        sprite: Source surface (typically from
            :meth:`AssetManager.get_sprite`).

    Returns:
        Cached upscaled surface.
    """
    key = id(sprite)
    if key not in _scaled_cache:
        sw, sh = sprite.get_size()
        _scaled_cache[key] = pygame.transform.scale(
            sprite, (sw * SPRITE_SCALE, sh * SPRITE_SCALE)
        )
    return _scaled_cache[key]


def _blit_centred(
    surface: pygame.Surface,
    sprite: pygame.Surface,
    col: float,
    row: float,
    origin: tuple[int, int],
) -> None:
    """Blit a scaled sprite centred at sub-cell ``(col, row)``.

    Accepts fractional indices so pacgums sitting on corridor
    mid-points render between two cells.
    """
    _blit_at_pixel(surface, sprite, _cell_centre(col, row, origin))


def _cell_top_left(
    col: float,
    row: float,
    origin: tuple[int, int],
) -> tuple[int, int]:
    """Return the pixel of the cell's top-left corner (inside its walls).

    Args:
        col: Cell column index (may be fractional for sub-cell sprites).
        row: Cell row index (may be fractional for sub-cell sprites).
        origin: Top-left pixel of the maze area.

    Returns:
        ``(x, y)`` in pixels.
    """
    ox, oy = origin
    return (
        int(ox + col * CELL_STRIDE + WALL_THICKNESS),
        int(oy + row * CELL_STRIDE + WALL_THICKNESS),
    )


def _cell_centre(
    col: float,
    row: float,
    origin: tuple[int, int],
) -> tuple[int, int]:
    """Return the pixel at the cell's centre.

    Args:
        col: Cell column index (may be fractional).
        row: Cell row index (may be fractional).
        origin: Top-left pixel of the maze area.

    Returns:
        ``(x, y)`` in pixels.
    """
    x, y = _cell_top_left(col, row, origin)
    return (x + CELL_SIZE // 2, y + CELL_SIZE // 2)


def _draw_logo_cells(
    surface: pygame.Surface,
    maze: Maze,
    origin: tuple[int, int],
    colors: PaletteColors,
) -> None:
    """Fill every ``is_pattern`` cell so the 42 logo is visible.

    Args:
        surface: Target Pygame surface.
        maze: The Maze instance.
        origin: Top-left pixel of the maze area.
        colors: PaletteColors instance.
    """
    for row in maze.grid:
        for cell in row:
            if cell.is_pattern:
                x, y = _cell_top_left(cell.col, cell.row, origin)
                pygame.draw.rect(
                    surface, colors.secondary, (x, y, CELL_SIZE, CELL_SIZE)
                )


def _draw_walls(
    surface: pygame.Surface,
    maze: Maze,
    origin: tuple[int, int],
    colors: PaletteColors,
) -> None:
    """Draw all walls with neighbour-aware rounded endpoints.

    A wall corner is rounded only if the wall does not continue in
    the adjacent cell — so straight runs stay flat, true endpoints
    pill out.

    Args:
        surface: Target Pygame surface.
        maze: The Maze instance.
        origin: Top-left pixel of the maze area.
        colors: PaletteColors instance.
    """
    # Two passes: all outline rects first, then all fill rects on
    # top. Drawing in this order lets adjacent walls' fills overlap
    # each other's inner outline edges, hiding the joints in
    # contiguous wall runs. Single-wall drawing would let the second
    # wall's outline overwrite the first wall's fill in the overlap
    # zone — leaving a visible seam.
    segments = list(_wall_segments(maze, origin))
    for is_pattern, rect, corners in segments:
        # Logo cells share wall_fill as both fill and outline so
        # they blend into a single solid block rather than being
        # divided by per-cell outlines.
        outline_color = colors.secondary if is_pattern else colors.primary
        outline_corners = (0, 0, 0, 0) if is_pattern else corners
        _draw_wall_outline(surface, outline_color, rect, outline_corners)
    for is_pattern, rect, corners in segments:
        if not is_pattern:
            _draw_wall_fill(surface, colors.wall_fill, rect, corners)


# (x, y, width, height) — matches what ``pygame.draw.rect`` accepts.
_RectInt = tuple[int, int, int, int]
# (top_left, top_right, bottom_left, bottom_right) border radii in px.
_CornerRadii = tuple[int, int, int, int]
# What ``_wall_segments`` yields per wall to render.
_WallSegment = tuple[bool, _RectInt, _CornerRadii]


def _wall_segments(
    maze: Maze,
    origin: tuple[int, int],
) -> Iterable[_WallSegment]:
    """Yield ``(is_pattern, rect, corners)`` for every wall to render.

    Centralises the per-cell setup (span, base coordinates, direction
    iteration, draw-eligibility check) so both passes of
    :func:`_draw_walls` consume the exact same segment list.
    """
    ox, oy = origin
    directions = (
        WallBits.NORTH,
        WallBits.SOUTH,
        WallBits.WEST,
        WallBits.EAST,
    )
    for row in maze.grid:
        for cell in row:
            span = (
                CELL_SIZE
                if cell.is_pattern
                else CELL_SIZE + 2 * WALL_THICKNESS
            )
            base_x = ox + cell.col * CELL_STRIDE
            base_y = oy + cell.row * CELL_STRIDE
            for direction in directions:
                if not cell.has_wall(direction):
                    continue
                if not _should_draw_wall(maze, cell, direction):
                    continue
                rect = _wall_rect(direction, base_x, base_y, span)
                corners = _wall_corner_radii(maze, cell, direction)
                yield cell.is_pattern, rect, corners


def _should_draw_wall(
    maze: Maze,
    cell: Cell,
    direction: WallBits,
) -> bool:
    """Whether ``cell`` should render its wall in ``direction``.

    Non-logo cells always draw their walls. Logo cells only draw
    walls that face another logo cell (interior of the logo block);
    walls bordering a corridor are left to the corridor cell on the
    other side, which has the proper primary outline and corner
    radii consistent with its own neighbourhood.
    """
    if not cell.is_pattern:
        return True
    return _neighbour_is_pattern(maze, cell, direction)


def _neighbour_is_pattern(
    maze: Maze,
    cell: Cell,
    direction: WallBits,
) -> bool:
    """Return True iff the neighbour in ``direction`` is a logo cell."""
    col = cell.col
    row = cell.row
    if direction == WallBits.NORTH:
        return row > 0 and bool(maze.grid[row - 1][col].is_pattern)
    if direction == WallBits.SOUTH:
        return row < maze.height - 1 and bool(
            maze.grid[row + 1][col].is_pattern
        )
    if direction == WallBits.WEST:
        return col > 0 and bool(maze.grid[row][col - 1].is_pattern)
    return col < maze.width - 1 and bool(maze.grid[row][col + 1].is_pattern)


def _wall_rect(
    direction: WallBits,
    base_x: int,
    base_y: int,
    span: int,
) -> tuple[int, int, int, int]:
    """Compute the (x, y, w, h) rect of a wall segment.

    When ``span`` is smaller than the full
    ``CELL_SIZE + 2 * WALL_THICKNESS`` (e.g. shrunk for logo
    interior walls), the wall is **centred** inside the cell's wall
    band by offsetting ``base_x`` (horizontal walls) or ``base_y``
    (vertical walls) by half the missing length. With full span the
    inset is 0 and behaviour is unchanged.
    """
    inset = (CELL_SIZE + 2 * WALL_THICKNESS - span) // 2
    if direction == WallBits.NORTH:
        return (base_x + inset, base_y, span, WALL_THICKNESS)
    if direction == WallBits.SOUTH:
        return (
            base_x + inset,
            base_y + CELL_SIZE + WALL_THICKNESS,
            span,
            WALL_THICKNESS,
        )
    if direction == WallBits.WEST:
        return (base_x, base_y + inset, WALL_THICKNESS, span)
    return (
        base_x + CELL_SIZE + WALL_THICKNESS,
        base_y + inset,
        WALL_THICKNESS,
        span,
    )


def _wall_corner_radii(
    maze: Maze,
    cell: Cell,
    direction: WallBits,
) -> tuple[int, int, int, int]:
    """Return ``(tl, tr, bl, br)`` border radii for a wall segment.

    A side is rounded only when no neighbour cell continues the wall
    in that direction; otherwise the corner is flat (radius 0) so
    runs of walls look continuous.
    """
    col, row = cell.col, cell.row
    grid = maze.grid
    radius = WALL_RADIUS
    if direction in (WallBits.NORTH, WallBits.SOUTH):
        west_cont = col > 0 and grid[row][col - 1].has_wall(direction)
        east_cont = col < maze.width - 1 and grid[row][col + 1].has_wall(
            direction
        )
        left = 0 if west_cont else radius
        right = 0 if east_cont else radius
        return (left, right, left, right)
    north_cont = row > 0 and grid[row - 1][col].has_wall(direction)
    south_cont = row < maze.height - 1 and grid[row + 1][col].has_wall(
        direction
    )
    top = 0 if north_cont else radius
    bottom = 0 if south_cont else radius
    return (top, top, bottom, bottom)


def _draw_wall_outline(
    surface: pygame.Surface,
    color: tuple[int, int, int],
    rect: tuple[int, int, int, int],
    corners: tuple[int, int, int, int],
) -> None:
    """Draw a wall pill's outline (filled rect at full size)."""
    tl, tr, bl, br = corners
    pygame.draw.rect(
        surface,
        color,
        rect,
        border_top_left_radius=tl,
        border_top_right_radius=tr,
        border_bottom_left_radius=bl,
        border_bottom_right_radius=br,
    )


def _draw_wall_fill(
    surface: pygame.Surface,
    color: tuple[int, int, int],
    rect: tuple[int, int, int, int],
    corners: tuple[int, int, int, int],
) -> None:
    """Draw a wall pill's fill (rect inset by OUTLINE_THICKNESS).

    Drawn AFTER all outlines so adjacent walls' fills overlap inside
    each other's outline border at joints, hiding the inner outline
    edges. The visible outline only remains on the actual silhouette
    of the merged wall mass.
    """
    tl, tr, bl, br = corners
    x, y, w, h = rect
    inset = (
        x + OUTLINE_THICKNESS,
        y + OUTLINE_THICKNESS,
        w - 2 * OUTLINE_THICKNESS,
        h - 2 * OUTLINE_THICKNESS,
    )
    pygame.draw.rect(
        surface,
        color,
        inset,
        border_top_left_radius=max(0, tl - OUTLINE_THICKNESS),
        border_top_right_radius=max(0, tr - OUTLINE_THICKNESS),
        border_bottom_left_radius=max(0, bl - OUTLINE_THICKNESS),
        border_bottom_right_radius=max(0, br - OUTLINE_THICKNESS),
    )
