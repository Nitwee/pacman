"""Highscore name entry screen."""

import pygame

from graphics.renderer import Colors
from screens.common import AnimatedLogo, draw_blinking_line, draw_lines


class HighscoreEntryScreen:
    """Draw the name entry form for a new highscore."""

    def __init__(self, font: pygame.font.Font) -> None:
        """Store screen dependencies."""
        self.font = font
        self.logo = AnimatedLogo()

    def draw(
        self,
        surface: pygame.Surface,
        score: int,
        name: str,
        elapsed_ms: int,
    ) -> None:
        """Draw the score and current typed name."""
        self.logo.draw(surface, elapsed_ms)
        displayed_name = name or "_"
        if elapsed_ms % 900 < 650:
            displayed_name = f"{displayed_name}_"
        lines = (
            ("NEW HIGHSCORE", Colors.GOLD),
            ("", Colors.GREY),
            (f"SCORE {score:06d}", Colors.GREY),
            ("", Colors.GREY),
            (displayed_name, Colors.GREEN),
        )
        draw_lines(
            surface,
            self.font,
            lines,
            center=(surface.get_width() // 2, 320),
        )
        draw_blinking_line(
            surface,
            self.font,
            ("Enter to confirm",),
            570,
            elapsed_ms,
        )
