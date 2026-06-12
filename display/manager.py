"""Real window and logical canvas management."""

import pygame

from display.settings import CANVAS_SIZE, DEFAULT_WINDOW_SIZE, Resolution


class DisplayManager:
    """Own the Pygame window and the fixed-size drawing canvas."""

    def __init__(self) -> None:
        """Create display state before Pygame opens the window."""
        self.window: pygame.Surface | None = None
        self.canvas: pygame.Surface | None = None
        self.window_size: Resolution = DEFAULT_WINDOW_SIZE
        self.fullscreen = False

    def setup(self) -> pygame.Surface:
        """Create the real window and the logical canvas."""
        self.apply_mode()
        self.canvas = pygame.Surface(CANVAS_SIZE)
        return self.canvas

    def apply_mode(self) -> None:
        """Apply the currently selected display mode to the real window."""
        flags = pygame.FULLSCREEN if self.fullscreen else 0
        size = (0, 0) if self.fullscreen else self.window_size
        self.window = pygame.display.set_mode(size, flags)

    def set_windowed_resolution(self, resolution: Resolution) -> None:
        """Switch to a windowed resolution."""
        self.window_size = resolution
        self.fullscreen = False
        self.apply_mode()

    def set_fullscreen(self) -> None:
        """Switch to fullscreen while keeping the logical canvas size."""
        self.fullscreen = True
        self.apply_mode()

    def present_canvas(self) -> None:
        """Scale the fixed canvas into the real window, preserving ratio."""
        if self.window is None or self.canvas is None:
            return

        window_width, window_height = self.window.get_size()
        canvas_width, canvas_height = self.canvas.get_size()
        scale = min(
            window_width / canvas_width,
            window_height / canvas_height,
        )
        scaled_size = (
            max(1, int(canvas_width * scale)),
            max(1, int(canvas_height * scale)),
        )

        if scaled_size == self.canvas.get_size():
            scaled_canvas = self.canvas
        else:
            scaled_canvas = pygame.transform.scale(
                self.canvas,
                scaled_size,
            )

        x = (window_width - scaled_size[0]) // 2
        y = (window_height - scaled_size[1]) // 2
        self.window.fill((0, 0, 0))
        self.window.blit(scaled_canvas, (x, y))
