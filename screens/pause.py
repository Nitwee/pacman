"""Pause screen overlay."""

import pygame

from graphics.renderer import Colors
from screens.common import draw_lines, draw_overlay

PAUSE_ITEMS = ("Resume", "Sound", "Main Menu", "Quit")


class PauseScreen:
    """Draw the pause overlay."""

    def __init__(self, font: pygame.font.Font) -> None:
        """Store screen dependencies."""
        self.font = font
        self.selected_index = 0

    def move_cursor(self, offset: int) -> None:
        """Move the pause cursor up or down."""
        self.selected_index = (
            self.selected_index + offset
        ) % len(PAUSE_ITEMS)

    def selected_item(self) -> str:
        """Return the currently selected pause menu item."""
        return PAUSE_ITEMS[self.selected_index]

    def draw(
        self,
        surface: pygame.Surface,
        elapsed_ms: int,
        sound_enabled: bool,
    ) -> None:
        """Draw the pause overlay menu."""
        draw_overlay(surface, elapsed_ms)
        draw_lines(
            surface,
            self.font,
            (("PAUSED", Colors.GOLD),),
            center=(surface.get_width() // 2, 300),
        )
        self._draw_items(surface, sound_enabled, elapsed_ms)

    def draw_confirm_quit(
        self,
        surface: pygame.Surface,
        elapsed_ms: int,
    ) -> None:
        """Draw the quit confirmation overlay."""
        draw_overlay(surface, elapsed_ms)
        draw_lines(
            surface,
            self.font,
            (
                ("QUIT GAME?", Colors.GOLD),
                ("ENTER : YES", Colors.GREY),
                ("ESC : NO", Colors.GREY),
            ),
        )

    def draw_confirm_main_menu(
        self,
        surface: pygame.Surface,
        elapsed_ms: int,
    ) -> None:
        """Draw the return-to-menu confirmation overlay."""
        draw_overlay(surface, elapsed_ms)
        draw_lines(
            surface,
            self.font,
            (
                ("RETURN TO MENU?", Colors.GOLD),
                ("ENTER : YES", Colors.GREY),
                ("ESC : NO", Colors.GREY),
            ),
        )

    def _draw_items(
        self,
        surface: pygame.Surface,
        sound_enabled: bool,
        elapsed_ms: int,
    ) -> None:
        """Draw pause menu options and cursor."""
        center_x = surface.get_width() // 2
        y = 370
        row_height = 42

        for index, item in enumerate(PAUSE_ITEMS):
            selected = index == self.selected_index
            color = Colors.GOLD if selected else Colors.GREY
            label = item
            if item == "Sound":
                label = f"Sound {'ON' if sound_enabled else 'OFF'}"

            text = self.font.render(label, True, color)
            rect = text.get_rect(center=(center_x, y))
            surface.blit(text, rect)

            if selected and elapsed_ms % 900 < 650:
                cursor = self.font.render(">", True, color)
                cursor_rect = cursor.get_rect(
                    midright=(rect.left - 16, rect.centery)
                )
                surface.blit(cursor, cursor_rect)

            y += row_height
