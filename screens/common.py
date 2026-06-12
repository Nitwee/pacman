"""Shared drawing helpers for screen modules."""

import math
from pathlib import Path

import pygame

from graphics.animation import Animation
from graphics.assets import AssetManager
from graphics.renderer import Colors, SPRITE_SCALE

LOGO_PATH = Path("assets/pacman-logo.png")
LOGO_WIDTH = 360
Line = tuple[str, Colors]
CHASE_LINE_OUT_MS = 4200
CHASE_LINE_PAUSE_MS = 650
CHASE_LINE_RETURN_MS = 3600
CHASE_LINE_CYCLE_MS = (
    CHASE_LINE_OUT_MS + CHASE_LINE_PAUSE_MS + CHASE_LINE_RETURN_MS
)
CHASE_LINE_WIDTH = 520
CHASE_LINE_GAP = 64
CHASE_LINE_GHOSTS = ("blinky", "pinky", "inky", "clyde")


class AnimatedLogo:
    """Reusable animated Pac-Man logo."""

    def __init__(self, width: int = LOGO_WIDTH) -> None:
        """Load and resize the Pac-Man logo once."""
        logo = pygame.image.load(str(LOGO_PATH)).convert_alpha()
        logo_height = int(logo.get_height() * width / logo.get_width())
        self.image = pygame.transform.smoothscale(
            logo,
            (width, logo_height),
        )

    def draw(
        self,
        surface: pygame.Surface,
        elapsed_ms: int,
        center_y: int = 95,
    ) -> None:
        """Draw the logo with a small vertical pulse."""
        pulse = math.sin(elapsed_ms / 300) * 8
        rect = self.image.get_rect(
            center=(surface.get_width() // 2, center_y + int(pulse))
        )
        surface.blit(self.image, rect)


class ChaseLineAnimation:
    """Small three-step Pac-Man chase animation for menu-like screens."""

    def __init__(self, assets: AssetManager) -> None:
        """Create the reusable chase-line animation."""
        self.assets = assets
        self.pacman_anim = Animation(
            assets.get_animation("pacman_chomp_right")
        )
        self.ghost_anims: list[tuple[str, Animation]] = [
            (
                name,
                Animation(assets.get_animation(f"{name}_walk_right")),
            )
            for name in CHASE_LINE_GHOSTS
        ]
        self.frightened_anim = Animation(assets.get_animation("ghost_scared"))

    def update(self, dt_ms: int) -> None:
        """Advance sprite animation frames."""
        self.pacman_anim.update(dt_ms)
        for _, anim in self.ghost_anims:
            anim.update(dt_ms)
        self.frightened_anim.update(dt_ms)

    def draw(
        self,
        surface: pygame.Surface,
        elapsed_ms: int,
        y: int,
    ) -> None:
        """Draw the chase line centered at ``y``."""
        center_x = surface.get_width() // 2
        left = center_x - CHASE_LINE_WIDTH // 2
        right = center_x + CHASE_LINE_WIDTH // 2
        phase_time = elapsed_ms % CHASE_LINE_CYCLE_MS
        if phase_time < CHASE_LINE_OUT_MS:
            progress = phase_time / CHASE_LINE_OUT_MS
            sprite = self.assets.get_sprite("super_pacgum")
            blit_scaled(surface, sprite, (right, y))
            self._draw_pacman_chased(surface, left, right, y, progress)
        elif phase_time < CHASE_LINE_OUT_MS + CHASE_LINE_PAUSE_MS:
            self._draw_turnaround_pause(surface, left, right, y)
        else:
            return_time = phase_time - CHASE_LINE_OUT_MS - CHASE_LINE_PAUSE_MS
            progress = return_time / CHASE_LINE_RETURN_MS
            self._draw_ghost_chased(surface, left, right, y, progress)

    def _draw_pacman_chased(
        self,
        surface: pygame.Surface,
        left: int,
        right: int,
        y: int,
        progress: float,
    ) -> None:
        """Draw Pac-Man moving right while ghosts enter one by one."""
        span = right - left
        pacman_x = int(left + progress * span)

        self.pacman_anim.set_definition(
            self.assets.get_animation("pacman_chomp_right")
        )
        self._draw_normal_ghosts(surface, pacman_x, left, right, y)

        self._draw_pacman(surface, pacman_x, y)

    def _draw_turnaround_pause(
        self,
        surface: pygame.Surface,
        left: int,
        right: int,
        y: int,
    ) -> None:
        """Freeze briefly before Pac-Man chases frightened ghosts back."""
        self.pacman_anim.set_definition(
            self.assets.get_animation("pacman_chomp_left")
        )
        self._draw_frightened_ghosts(surface, right, left, right, y)
        self._draw_pacman(surface, right, y)

    def _draw_ghost_chased(
        self,
        surface: pygame.Surface,
        left: int,
        right: int,
        y: int,
        progress: float,
    ) -> None:
        """Draw frightened ghosts moving left while Pac-Man follows."""
        span = right - left
        pacman_x = int(right - progress * span)

        self.pacman_anim.set_definition(
            self.assets.get_animation("pacman_chomp_left")
        )

        self._draw_frightened_ghosts(surface, pacman_x, left, right, y)
        self._draw_pacman(surface, pacman_x, y)

    def _draw_normal_ghosts(
        self,
        surface: pygame.Surface,
        pacman_x: int,
        left: int,
        right: int,
        y: int,
    ) -> None:
        """Draw chasing ghosts entering the line one by one."""
        for index, (name, anim) in enumerate(self.ghost_anims):
            ghost_x = pacman_x - CHASE_LINE_GAP * (index + 1)
            if ghost_x < left or ghost_x > right:
                continue
            anim.set_definition(
                self.assets.get_animation(f"{name}_walk_right")
            )
            ghost = self.assets.get_sprite(anim.current_frame())
            blit_scaled(surface, ghost, (ghost_x, y))

    def _draw_frightened_ghosts(
        self,
        surface: pygame.Surface,
        pacman_x: int,
        left: int,
        right: int,
        y: int,
    ) -> None:
        """Draw frightened ghosts ahead of Pac-Man on the return path."""
        ghost = self.assets.get_sprite(self.frightened_anim.current_frame())
        for index in range(len(CHASE_LINE_GHOSTS)):
            ghost_x = pacman_x - CHASE_LINE_GAP * (index + 1)
            if ghost_x < left or ghost_x > right:
                continue
            blit_scaled(surface, ghost, (ghost_x, y))

    def _draw_pacman(
        self,
        surface: pygame.Surface,
        pacman_x: int,
        y: int,
    ) -> None:
        """Draw Pac-Man at the given chase-line coordinate."""
        pacman = self.assets.get_sprite(self.pacman_anim.current_frame())
        blit_scaled(surface, pacman, (pacman_x, y))


def blit_scaled(
    surface: pygame.Surface,
    sprite: pygame.Surface,
    position: tuple[int, int],
) -> None:
    """Blit a scaled sprite centered at ``position``."""
    width, height = sprite.get_size()
    scaled = pygame.transform.scale(
        sprite,
        (width * SPRITE_SCALE, height * SPRITE_SCALE),
    )
    rect = scaled.get_rect(center=position)
    surface.blit(scaled, rect)


def draw_lines(
    surface: pygame.Surface,
    font: pygame.font.Font,
    lines: tuple[Line, ...],
    center: tuple[int, int] | None = None,
) -> None:
    """Draw centered text lines."""
    width, height = surface.get_size()
    if center is None:
        center = (width // 2, height // 2)

    center_x, center_y = center
    line_height = 36
    y = center_y - len(lines) * line_height // 2

    for text_value, color in lines:
        text = font.render(text_value, True, color)
        rect = text.get_rect(center=(center_x, y))
        surface.blit(text, rect)
        y += line_height


def draw_blinking_line(
    surface: pygame.Surface,
    font: pygame.font.Font,
    lines: tuple[str, ...],
    height_pos: int,
    elapsed_ms: int,
) -> None:
    """Draw centered text lines that blink over time."""
    if elapsed_ms % 900 > 900 * 0.65:
        return
    width, height = surface.get_size()
    y = min(height_pos, height - 40)
    for line in lines:
        text = font.render(line, True, Colors.GREY)
        rect = text.get_rect(center=(width // 2, y))
        surface.blit(text, rect)
        y += 36


def draw_overlay(
    surface: pygame.Surface,
    elapsed_ms: int,
) -> None:
    """Draw a dark overlay over the whole surface."""
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 220))
    surface.blit(overlay, (0, 0))
