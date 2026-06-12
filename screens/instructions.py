"""Instructions screen."""

import pygame

from graphics.assets import AssetManager
from graphics.renderer import Colors
from screens.common import (
    AnimatedLogo,
    ChaseLineAnimation,
    draw_lines,
)

INSTRUCTIONS_ITEMS = ("Back",)


class InstructionsScreen:
    """Draw the instructions page."""

    def __init__(self, font: pygame.font.Font, assets: AssetManager) -> None:
        """Store screen dependencies."""
        self.font = font
        self.logo = AnimatedLogo()
        self.page_anim = ChaseLineAnimation(assets)
        self.selected_index = 0

    def update(self, dt_ms: int) -> None:
        """Advance page animations."""
        self.page_anim.update(dt_ms)

    def move_cursor(self, offset: int) -> None:
        """Move the instructions cursor up or down."""
        self.selected_index = (self.selected_index + offset) % len(
            INSTRUCTIONS_ITEMS
        )

    def selected_item(self) -> str:
        """Return the currently selected instructions item."""
        return INSTRUCTIONS_ITEMS[self.selected_index]

    def draw(
        self,
        surface: pygame.Surface,
        elapsed_ms: int,
    ) -> None:
        """Draw the instructions text."""
        lines = (
            ("", Colors.BLUE),
            ("", Colors.BLUE),
            ("", Colors.BLUE),
            ("INSTRUCTIONS", Colors.GREEN),
            ("", Colors.BLUE),
            ("ARROWS / WASD : MOVE", Colors.BLUE),
            ("P / ESC : PAUSE", Colors.BLUE),
            ("CTRL + I : INVINCIBILITY", Colors.BLUE),
            ("CTRL + F : FREEZE GHOSTS", Colors.BLUE),
            ("CTRL + T : FREEZE TIMER", Colors.BLUE),
            ("CTRL + W : NOCLIP", Colors.BLUE),
            ("CTRL + E : EXTRA LIFE", Colors.BLUE),
            ("CTRL + UP / DOWN : PACMAN SPEED", Colors.BLUE),
            ("CTRL + L : CLEAR LEVEL", Colors.BLUE),
            ("CTRL + C : CHANGE COLORS", Colors.BLUE),
        )
        self.logo.draw(surface, elapsed_ms)
        draw_lines(surface, self.font, lines)
        self.page_anim.draw(surface, elapsed_ms, 730)
        self._draw_items(surface, elapsed_ms)

    def _draw_items(
        self,
        surface: pygame.Surface,
        elapsed_ms: int,
    ) -> None:
        """Draw selectable instructions actions."""
        center_x = surface.get_width() // 2
        y = 800

        for index, item in enumerate(INSTRUCTIONS_ITEMS):
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
