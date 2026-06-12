"""Main menu screen."""

import pygame

from graphics.animation import Animation
from graphics.assets import AssetManager, PaletteColors
from graphics.renderer import Colors
from screens.common import AnimatedLogo, blit_scaled

CELL = 52
MAZE_COLUMNS = 7
MAZE_ROWS = 5
LOGO_TO_MAZE_GAP = 34
MENU_GAP = 34
MENU_ROW_HEIGHT = 34
MENU_CYCLE_MS = 6500
PACMAN_RUN_MS = 4200
GHOST_DELAY_MS = 450
DEATH_START_MS = PACMAN_RUN_MS + GHOST_DELAY_MS - 220
MENU_ITEMS = ("Play", "Options", "Leaderboard", "Instructions", "Quit")
CELLS = [
    (0, 0),
    (0, 1),
    (0, 2),
    (1, 2),
    (2, 2),
    (2, 3),
    (2, 4),
    (4, 4),
    (5, 4),
    (6, 4),
    (3, 4),
    (4, 3),
    (4, 2),
    (5, 2),
    (6, 2),
    (6, 1),
    (6, 0),
    (5, 0),
    (4, 0),
]
PACMAN_PATH = [
    (0, 0),
    (0, 1),
    (0, 2),
    (1, 2),
    (2, 2),
    (2, 3),
    (2, 4),
    (3, 4),
    (4, 4),
    (5, 4),
    (6, 4),
]
GHOST_PATH = [
    (4, 0),
    (5, 0),
    (6, 0),
    (6, 1),
    (6, 2),
    (5, 2),
    (4, 2),
    (4, 3),
    (4, 4),
    (5, 4),
    (6, 4),
]


class MainMenuScreen:
    """Animated main menu."""

    def __init__(
        self,
        font: pygame.font.Font,
        assets: AssetManager,
    ) -> None:
        """Create the menu screen and its animations."""
        self.font = font
        self.assets = assets
        self.logo = AnimatedLogo()
        self.selected_index = 0
        self.pacman_anim = Animation(
            assets.get_animation("pacman_chomp_right")
        )
        self.ghost_anim = Animation(assets.get_animation("blinky_walk_down"))

    def update(self, dt_ms: int) -> None:
        """Advance menu-only animations."""
        self.pacman_anim.update(dt_ms)
        self.ghost_anim.update(dt_ms)

    def move_cursor(self, offset: int) -> None:
        """Move the menu cursor up or down."""
        new_index = self.selected_index + offset
        number_of_items = len(MENU_ITEMS)
        self.selected_index = new_index % number_of_items

    def selected_item(self) -> str:
        """Return the currently selected menu item."""
        return MENU_ITEMS[self.selected_index]

    def draw(self, surface: pygame.Surface, elapsed_ms: int) -> None:
        """Draw the main menu."""
        origin = self._maze_origin(surface)
        self._draw_title(surface, elapsed_ms, origin)
        self._draw_fake_maze(surface, elapsed_ms, origin)
        self._draw_menu(surface, elapsed_ms, origin)

    def _draw_title(
        self,
        surface: pygame.Surface,
        elapsed_ms: int,
        origin: tuple[int, int],
    ) -> None:
        """Draw the animated Pac-Man logo above the fake maze."""
        logo_center_y = origin[1] - LOGO_TO_MAZE_GAP
        logo_center_y -= self.logo.image.get_height() // 2
        self.logo.draw(surface, elapsed_ms, logo_center_y)

    def _draw_menu(
        self,
        surface: pygame.Surface,
        elapsed_ms: int,
        origin: tuple[int, int],
    ) -> None:
        """Draw the selectable menu entries."""
        center_x = origin[0] + MAZE_COLUMNS * CELL // 2
        start_y = origin[1] + MAZE_ROWS * CELL + MENU_GAP

        for index, item in enumerate(MENU_ITEMS):
            y = start_y + index * MENU_ROW_HEIGHT
            selected = index == self.selected_index
            color = Colors.GOLD if selected else Colors.GREY
            text = self.font.render(item, True, color)
            text_rect = text.get_rect(center=(center_x, y))
            surface.blit(text, text_rect)

            if selected and elapsed_ms % 900 < 650:
                cursor = self.font.render(">", True, color)
                cursor_rect = cursor.get_rect(
                    midright=(text_rect.left - 12, text_rect.centery)
                )
                surface.blit(cursor, cursor_rect)

    def _draw_fake_cell(
        self,
        surface: pygame.Surface,
        col: int,
        row: int,
        colors: PaletteColors,
        origin: tuple[int, int],
        is_bridge: bool = False,
    ) -> None:
        """Draw one cell of the decorative maze with the given palette."""
        x = origin[0] + col * CELL
        y = origin[1] + row * CELL

        outer = pygame.Rect(x, y, CELL, CELL)
        inner = pygame.Rect(x + 6, y + 6, CELL - 12, CELL - 12)

        pygame.draw.rect(surface, colors.primary, outer)

        if is_bridge:
            pygame.draw.rect(surface, (0, 0, 0), inner)
        else:
            pygame.draw.rect(surface, colors.wall_fill, inner)

    def _draw_fake_cell_connections(
        self,
        surface: pygame.Surface,
        colors: PaletteColors,
        origin: tuple[int, int],
    ) -> None:
        """Draw corridor bridges between adjacent cells of the fake maze."""
        cells = set(CELLS)
        bridge = (3, 4)

        for col, row in cells:
            current_cell = (col, row)
            right_cell = (col + 1, row)
            bottom_cell = (col, row + 1)

            if right_cell in cells:
                x = origin[0] + (col + 1) * CELL - 6
                y = origin[1] + row * CELL + 6
                color = colors.wall_fill
                if bridge in (current_cell, right_cell):
                    color = (0, 0, 0)
                pygame.draw.rect(surface, color, (x, y, 12, CELL - 12))

            if bottom_cell in cells:
                x = origin[0] + col * CELL + 6
                y = origin[1] + (row + 1) * CELL - 6
                color = colors.wall_fill
                if bridge in (current_cell, bottom_cell):
                    color = (0, 0, 0)
                pygame.draw.rect(surface, color, (x, y, CELL - 12, 12))

    def _draw_fake_maze(
        self,
        surface: pygame.Surface,
        elapsed_ms: int,
        origin: tuple[int, int],
    ) -> None:
        """Draw the animated decorative maze with the chasing Pac-Man scene."""
        colors = self.assets.get_palette_colors(self.assets.current_palette)

        for col, row in CELLS:
            is_bridge = col == 3 and row == 4
            self._draw_fake_cell(
                surface,
                col,
                row,
                colors,
                origin,
                is_bridge,
            )

        self._draw_fake_cell_connections(surface, colors, origin)

        cycle = elapsed_ms % MENU_CYCLE_MS
        progress = min(cycle / PACMAN_RUN_MS, 1.0)

        progress = max(0.0, min(1.0, progress))
        last_path_index = len(PACMAN_PATH) - 1
        pacman_index = int(progress * last_path_index)
        pacman_pixel = self._position_between_grid_cells(
            PACMAN_PATH,
            progress,
            origin,
        )
        pacman_direction = self._direction_on_path(PACMAN_PATH, progress)

        self._draw_pacgums(surface, pacman_index, origin)

        ghost_progress = 0.0
        if cycle >= GHOST_DELAY_MS:
            ghost_time = min(cycle, DEATH_START_MS) - GHOST_DELAY_MS
            ghost_progress = min(
                ghost_time / PACMAN_RUN_MS,
                1.0,
            )
        ghost_pixel = self._position_between_grid_cells(
            GHOST_PATH,
            ghost_progress,
            origin,
        )
        ghost_direction = self._direction_on_path(GHOST_PATH, ghost_progress)

        self._draw_ghost(surface, ghost_pixel, ghost_direction)
        if cycle >= DEATH_START_MS:
            death_elapsed_ms = cycle - DEATH_START_MS
            self._draw_pacman_death(surface, pacman_pixel, death_elapsed_ms)
        else:
            self._draw_pacman(surface, pacman_pixel, pacman_direction)

    def _draw_pacgums(
        self,
        surface: pygame.Surface,
        pacman_index: int,
        origin: tuple[int, int],
    ) -> None:
        """Draw pacgums along the path that Pac-Man has not yet eaten."""
        for index, cell in enumerate(PACMAN_PATH):
            if index <= pacman_index:
                continue
            pygame.draw.circle(
                surface,
                (255, 220, 120),
                self._cell_center(cell, origin),
                5,
            )

    def _draw_pacman(
        self,
        surface: pygame.Surface,
        position: tuple[int, int],
        direction: str,
    ) -> None:
        """Draw the chomping Pac-Man sprite at ``position``."""
        self.pacman_anim.set_definition(
            self.assets.get_animation(f"pacman_chomp_{direction}")
        )
        sprite = self.assets.get_sprite(self.pacman_anim.current_frame())
        blit_scaled(surface, sprite, position)

    def _draw_ghost(
        self,
        surface: pygame.Surface,
        position: tuple[int, int],
        direction: str,
    ) -> None:
        """Draw the Blinky walking sprite at ``position`` facing direction."""
        self.ghost_anim.set_definition(
            self.assets.get_animation(f"blinky_walk_{direction}")
        )
        sprite = self.assets.get_sprite(self.ghost_anim.current_frame())
        blit_scaled(surface, sprite, position)

    def _draw_pacman_death(
        self,
        surface: pygame.Surface,
        position: tuple[int, int],
        elapsed_ms: int,
    ) -> None:
        """Draw the death animation frame matching ``elapsed_ms``."""
        death_animation = self.assets.get_animation("pacman_death")
        frame_index = elapsed_ms // death_animation.frame_duration_ms
        frame_index = min(frame_index, len(death_animation.frames) - 1)
        sprite_name = death_animation.frames[frame_index]
        sprite = self.assets.get_sprite(sprite_name)
        blit_scaled(surface, sprite, position)

    def _position_between_grid_cells(
        self,
        path: list[tuple[int, int]],
        progress: float,
        origin: tuple[int, int],
    ) -> tuple[int, int]:
        """Return the pixel position along ``path`` at normalised progress."""
        progress = max(0.0, min(1.0, progress))

        number_of_steps = len(path) - 1
        path_position = progress * number_of_steps

        start_index = int(path_position)
        end_index = min(start_index + 1, number_of_steps)

        progress_between_cells = path_position - start_index

        start = self._cell_center(path[start_index], origin)
        end = self._cell_center(path[end_index], origin)

        x = start[0] + (end[0] - start[0]) * progress_between_cells
        y = start[1] + (end[1] - start[1]) * progress_between_cells

        return (int(x), int(y))

    def _direction_on_path(
        self,
        path: list[tuple[int, int]],
        progress: float,
    ) -> str:
        """Return the facing direction string at progress along ``path``."""
        progress = max(0.0, min(1.0, progress))

        number_of_steps = len(path) - 1
        path_position = progress * number_of_steps
        start_index = min(int(path_position), number_of_steps - 1)
        end_index = start_index + 1

        start_col, start_row = path[start_index]
        end_col, end_row = path[end_index]

        if end_col > start_col:
            return "right"
        if end_col < start_col:
            return "left"
        if end_row > start_row:
            return "down"
        return "up"

    def _cell_center(
        self,
        cell: tuple[int, int],
        origin: tuple[int, int],
    ) -> tuple[int, int]:
        """Return the pixel centre of ``cell`` relative to ``origin``."""
        col, row = cell
        return (
            origin[0] + col * CELL + CELL // 2,
            origin[1] + row * CELL + CELL // 2,
        )

    def _maze_origin(self, surface: pygame.Surface) -> tuple[int, int]:
        """Return the fake maze origin centered inside the menu screen."""
        maze_width = MAZE_COLUMNS * CELL
        maze_height = MAZE_ROWS * CELL
        menu_height = len(MENU_ITEMS) * MENU_ROW_HEIGHT
        logo_height = self.logo.image.get_height()

        total_height = (
            logo_height
            + LOGO_TO_MAZE_GAP
            + maze_height
            + MENU_GAP
            + menu_height
        )
        content_top = (surface.get_height() - total_height) // 2

        x = (surface.get_width() - maze_width) // 2
        y = content_top + logo_height + LOGO_TO_MAZE_GAP
        return (x, y)
