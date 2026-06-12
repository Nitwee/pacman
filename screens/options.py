"""Options screen."""

import pygame

from display import Resolution, WINDOWED_RESOLUTIONS, resolution_label
from graphics.assets import AssetManager
from graphics.renderer import Colors
from screens.common import ChaseLineAnimation, draw_blinking_line, draw_lines

FULLSCREEN_LABEL = "Fullscreen"
SOUND_LABEL = "Sound"
BACK_LABEL = "Back"


class OptionsScreen:
    """Draw and navigate display options."""

    def __init__(self, font: pygame.font.Font, assets: AssetManager) -> None:
        """Store screen dependencies."""
        self.font = font
        self.selected_index = 0
        self.page_anim = ChaseLineAnimation(assets)

    def update(self, dt_ms: int) -> None:
        """Advance page animations."""
        self.page_anim.update(dt_ms)

    def move_cursor(self, offset: int) -> None:
        """Move the options cursor up or down."""
        self.selected_index = (
            self.selected_index + offset
        ) % self.item_count()

    def selected_resolution(self) -> Resolution | None:
        """Return the selected windowed resolution, if any."""
        if self.selected_index < len(WINDOWED_RESOLUTIONS):
            return WINDOWED_RESOLUTIONS[self.selected_index]
        return None

    def selected_fullscreen(self) -> bool:
        """Return True if the fullscreen row is selected."""
        return self.selected_index == len(WINDOWED_RESOLUTIONS)

    def selected_sound(self) -> bool:
        """Return True if the sound row is selected."""
        return self.selected_index == len(WINDOWED_RESOLUTIONS) + 1

    def selected_back(self) -> bool:
        """Return True if the back row is selected."""
        return self.selected_index == self.item_count() - 1

    def item_count(self) -> int:
        """Return the number of selectable rows."""
        return len(WINDOWED_RESOLUTIONS) + 3

    def draw(
        self,
        surface: pygame.Surface,
        current_resolution: Resolution,
        fullscreen: bool,
        sound_enabled: bool,
        elapsed_ms: int,
    ) -> None:
        """Draw the options page."""
        draw_lines(
            surface,
            self.font,
            (("OPTIONS", Colors.GOLD),),
            center=(surface.get_width() // 2, 180),
        )
        self._draw_items(
            surface,
            current_resolution,
            fullscreen,
            sound_enabled,
            elapsed_ms,
        )
        self.page_anim.draw(surface, elapsed_ms, 650)
        draw_blinking_line(
            surface,
            self.font,
            ("Press ENTER to apply",),
            760,
            elapsed_ms,
        )

    def _draw_items(
        self,
        surface: pygame.Surface,
        current_resolution: Resolution,
        fullscreen: bool,
        sound_enabled: bool,
        elapsed_ms: int,
    ) -> None:
        """Draw each selectable option row."""
        center_x = surface.get_width() // 2
        y = 300
        row_height = 48

        for index, label in enumerate(self._item_labels()):
            selected = index == self.selected_index
            active = self._is_active(
                index,
                current_resolution,
                fullscreen,
                sound_enabled,
            )
            color = self._item_color(selected, active)
            text = label
            if index == len(WINDOWED_RESOLUTIONS) + 1:
                text = f"{label} {'ON' if sound_enabled else 'OFF'}"
            elif active:
                text = f"{label} ON"

            text_surface = self.font.render(text, True, color)
            text_rect = text_surface.get_rect(center=(center_x, y))
            surface.blit(text_surface, text_rect)

            if selected and elapsed_ms % 900 < 650:
                cursor = self.font.render(">", True, color)
                cursor_rect = cursor.get_rect(
                    midright=(text_rect.left - 16, text_rect.centery)
                )
                surface.blit(cursor, cursor_rect)

            y += row_height

    def _item_labels(self) -> tuple[str, ...]:
        """Return option labels in display order."""
        resolution_labels = tuple(
            resolution_label(resolution) for resolution in WINDOWED_RESOLUTIONS
        )
        return (*resolution_labels, FULLSCREEN_LABEL, SOUND_LABEL, BACK_LABEL)

    def _is_active(
        self,
        index: int,
        current_resolution: Resolution,
        fullscreen: bool,
        sound_enabled: bool,
    ) -> bool:
        """Return whether the row represents the current display mode."""
        if index < len(WINDOWED_RESOLUTIONS):
            return (
                not fullscreen
                and WINDOWED_RESOLUTIONS[index] == current_resolution
            )
        if index == len(WINDOWED_RESOLUTIONS):
            return fullscreen
        if index == len(WINDOWED_RESOLUTIONS) + 1:
            return sound_enabled
        return False

    @staticmethod
    def _item_color(selected: bool, active: bool) -> Colors:
        """Return the color for one option row."""
        if selected:
            return Colors.GOLD
        if active:
            return Colors.GREEN
        return Colors.GREY
