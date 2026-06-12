"""Victory screen."""

import pygame

from graphics.renderer import Colors
from screens.common import draw_lines, draw_overlay


class VictoryScreen:
    """Draw the victory overlay."""

    def __init__(self, font: pygame.font.Font) -> None:
        """Store screen dependencies."""
        self.font = font

    def draw(
        self,
        surface: pygame.Surface,
        score: int,
        elapsed_ms: int,
    ) -> None:
        """Draw the victory text."""
        draw_overlay(surface, elapsed_ms)
        draw_lines(
            surface,
            self.font,
            (
                ("VICTORY", Colors.GREEN),
                (f"Score {score}", Colors.GREY),
                ("Enter", Colors.GREY),
            ),
        )
