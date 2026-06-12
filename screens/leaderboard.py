"""Leaderboard screen."""

from collections.abc import Sequence

import pygame

from graphics.assets import AssetManager
from graphics.renderer import Colors
from highscore import HighscoreEntry
from screens.common import ChaseLineAnimation, draw_lines

LEADERBOARD_ITEMS = ("Back",)
ENTRY_COLORS = (
    Colors.YELLOW,
    Colors.CYAN,
    Colors.PINK,
    Colors.ORANGE,
    Colors.LIME,
    Colors.SKY_BLUE,
    Colors.PEACH,
    Colors.PURPLE,
    Colors.GREEN,
    Colors.GREY,
)


class LeaderboardScreen:
    """Draw the stored top scores."""

    def __init__(self, font: pygame.font.Font, assets: AssetManager) -> None:
        """Store screen dependencies."""
        self.font = font
        self.selected_index = 0
        self.page_anim = ChaseLineAnimation(assets)

    def update(self, dt_ms: int) -> None:
        """Advance page animations."""
        self.page_anim.update(dt_ms)

    def move_cursor(self, offset: int) -> None:
        """Move the leaderboard cursor up or down."""
        self.selected_index = (self.selected_index + offset) % len(
            LEADERBOARD_ITEMS
        )

    def selected_item(self) -> str:
        """Return the currently selected leaderboard item."""
        return LEADERBOARD_ITEMS[self.selected_index]

    def draw(
        self,
        surface: pygame.Surface,
        entries: Sequence[HighscoreEntry],
        elapsed_ms: int,
    ) -> None:
        """Draw leaderboard rows."""
        lines = [("LEADERBOARD", Colors.GOLD), ("", Colors.GREY)]
        if not entries:
            lines.append(("NO SCORE YET", Colors.GREY))
        else:
            for rank, entry in enumerate(entries, start=1):
                text = f"{rank:02d} {entry.name:<10} {entry.score:06d}"
                color = ENTRY_COLORS[(rank - 1) % len(ENTRY_COLORS)]
                lines.append((text, color))

        draw_lines(
            surface,
            self.font,
            tuple(lines),
            center=(surface.get_width() // 2, 320),
        )
        self._draw_items(surface, elapsed_ms)
        self.page_anim.draw(surface, elapsed_ms, 650)

    def _draw_items(
        self,
        surface: pygame.Surface,
        elapsed_ms: int,
    ) -> None:
        """Draw selectable leaderboard actions."""
        center_x = surface.get_width() // 2
        y = 570

        for index, item in enumerate(LEADERBOARD_ITEMS):
            selected = index == self.selected_index
            color = Colors.GOLD if selected else Colors.GREY
            text = self.font.render(item, True, color)
            rect = text.get_rect(center=(center_x, y))
            surface.blit(text, rect)

            if selected and elapsed_ms % 900 < 650:
                cursor = self.font.render(">", True, color)
                cursor_rect = cursor.get_rect(
                    midright=(rect.left - 16, rect.centery)
                )
                surface.blit(cursor, cursor_rect)
