"""Gameplay screen."""

import pygame

from game_engine import EngineState, GameEngine, Timer
from graphics.animation import Animation
from graphics.assets import AssetManager
from graphics.renderer import (
    Colors,
    GHOST_ANIMATIONS,
    HUD_PANEL_WIDTH,
    PACMAN_ANIMATION,
    PADDING,
    draw_engine,
    maze_pixel_size,
)
from screens.common import draw_lines, draw_overlay


class PlayingScreen:
    """Draw the maze, characters and HUD."""

    PALETTE_FLICKER_INTERVAL_MS = 80

    def __init__(
        self,
        font: pygame.font.Font,
        assets: AssetManager,
    ) -> None:
        """Create the gameplay screen and its animations."""
        self.font = font
        self.assets = assets
        self.pacman_chomp_anim = Animation(
            assets.get_animation(PACMAN_ANIMATION)
        )
        self.pacman_death_anim = Animation(
            assets.get_animation("pacman_death")
        )
        self.ghost_anims = [
            Animation(assets.get_animation(name)) for name in GHOST_ANIMATIONS
        ]
        self.super_pacgum_anim = Animation(
            assets.get_animation("pacgum_blink")
        )
        self._palette_flicker_tick = Timer()
        self._palette_flicker_saved: str | None = None

    @property
    def palette_flicker_pending(self) -> bool:
        """Whether a flicker snapshot is awaiting restoration."""
        return self._palette_flicker_saved is not None

    def tick_palette_flicker(self, dt_ms: int, in_transition: bool) -> None:
        """Cycle palettes while ``in_transition``; restore on exit.

        Snapshots the active palette the first frame the level
        transition is seen, rotates through every registered palette
        every :attr:`PALETTE_FLICKER_INTERVAL_MS`, and restores the
        snapshot the first frame the transition ends — so the
        flicker is bounded by the ``intermission`` jingle that drives
        the engine hold.
        """
        if not in_transition:
            if self._palette_flicker_saved is not None:
                self.assets.set_palette(self._palette_flicker_saved)
                self._palette_flicker_saved = None
                self._palette_flicker_tick.stop()
            return
        if self._palette_flicker_saved is None:
            self._palette_flicker_saved = self.assets.current_palette
            self._palette_flicker_tick.start(self.PALETTE_FLICKER_INTERVAL_MS)
            return
        if self._palette_flicker_tick.tick(dt_ms):
            self.assets.set_palette(self.assets.next_palette())
            self._palette_flicker_tick.start(self.PALETTE_FLICKER_INTERVAL_MS)

    def update(self, dt_ms: int) -> None:
        """Advance gameplay animations."""
        self.pacman_chomp_anim.update(dt_ms)
        self.pacman_death_anim.update(dt_ms)
        for anim in self.ghost_anims:
            anim.update(dt_ms)
        self.super_pacgum_anim.update(dt_ms)

    def reset_death_animation(self) -> None:
        """Restart Pac-Man's death animation from frame zero."""
        self.pacman_death_anim.reset()

    HUD_LIVES_MAX_ICONS = 5
    HUD_ICON_SIZE = 28
    HUD_ICON_GAP = 4
    HUD_SECTION_GAP = 16
    HUD_LINE_GAP = 4
    HUD_CHEAT_LINE_GAP = 2
    HUD_MAX_CHEAT_LINES = 5

    def draw(
        self,
        surface: pygame.Surface,
        engine: GameEngine,
        elapsed_ms: int,
        highscore_top: int = 0,
    ) -> None:
        """Draw gameplay and HUD."""
        self._draw_game(surface, engine)
        self._draw_hud(surface, engine, highscore_top)
        if engine.state == EngineState.LEVEL_TRANSITION:
            self._draw_level_transition(surface, engine)

    def _draw_game(
        self,
        surface: pygame.Surface,
        engine: GameEngine,
    ) -> pygame.Rect:
        """Draw the maze, scaled down only when it exceeds the canvas."""
        maze_width, maze_height = maze_pixel_size(engine.maze)
        game_area_width = (
            surface.get_width() - HUD_PANEL_WIDTH - 3 * PADDING
        )
        game_area_height = surface.get_height() - 2 * PADDING
        scale = min(
            game_area_width / maze_width,
            game_area_height / maze_height,
            1.0,
        )
        scaled_size = (
            max(1, int(maze_width * scale)),
            max(1, int(maze_height * scale)),
        )

        game_surface = pygame.Surface(
            (maze_width, maze_height),
            pygame.SRCALPHA,
        )
        draw_engine(
            game_surface,
            engine,
            (0, 0),
            self.assets,
            self.pacman_chomp_anim,
            self.pacman_death_anim,
            self.ghost_anims,
            self.super_pacgum_anim,
        )

        if scaled_size != (maze_width, maze_height):
            game_surface = pygame.transform.scale(game_surface, scaled_size)

        x = PADDING + (game_area_width - scaled_size[0]) // 2
        y = PADDING + (game_area_height - scaled_size[1]) // 2
        surface.blit(game_surface, (x, y))
        return pygame.Rect(x, y, *scaled_size)

    def _draw_hud(
        self,
        surface: pygame.Surface,
        engine: GameEngine,
        highscore_top: int,
    ) -> None:
        """Draw the right-side HUD panel."""
        panel_x = surface.get_width() - HUD_PANEL_WIDTH - PADDING
        # Pin the HUD vertically using the panel's worst-case height
        # (all cheats active) so sections don't jump when cheats toggle.
        y = max(
            PADDING,
            (surface.get_height() - self._hud_max_height()) // 2,
        )
        displayed_high = max(highscore_top, engine.score)
        y = self._draw_hud_kv(
            surface, "HIGH SCORE", str(displayed_high), panel_x, y, Colors.RED
        )
        y += self.HUD_SECTION_GAP
        y = self._draw_hud_kv(
            surface, "SCORE", str(engine.score), panel_x, y, Colors.WHITE
        )
        y += self.HUD_SECTION_GAP
        y = self._draw_hud_kv(
            surface,
            "LEVEL",
            str(engine.level_index + 1),
            panel_x,
            y,
            Colors.WHITE,
        )
        y += self.HUD_SECTION_GAP
        time_secs = (engine.remaining_time_ms + 999) // 1000
        y = self._draw_hud_kv(
            surface, "TIME", str(time_secs), panel_x, y, Colors.WHITE
        )
        y += self.HUD_SECTION_GAP
        y = self._draw_hud_lives(surface, engine.lives, panel_x, y)
        y += self.HUD_SECTION_GAP
        y = self._draw_hud_fruits(
            surface, engine.collected_fruits_in_level, panel_x, y
        )
        cheat_lines = self._cheat_lines(engine)
        if cheat_lines:
            y += self.HUD_SECTION_GAP
            self._draw_hud_cheats(surface, cheat_lines, panel_x, y)

    def _panel_center_x(self, panel_x: int) -> int:
        """Return the horizontal centre of the HUD panel."""
        return panel_x + HUD_PANEL_WIDTH // 2

    def _draw_hud_label(
        self,
        surface: pygame.Surface,
        label: str,
        panel_x: int,
        y: int,
    ) -> int:
        """Render a small grey label centred on the panel."""
        center_x = self._panel_center_x(panel_x)
        label_surf = self.font.render(label, True, Colors.GREY)
        surface.blit(label_surf, label_surf.get_rect(midtop=(center_x, y)))
        return y + label_surf.get_height() + self.HUD_LINE_GAP

    def _draw_hud_kv(
        self,
        surface: pygame.Surface,
        label: str,
        value: str,
        panel_x: int,
        y: int,
        value_color: Colors,
    ) -> int:
        """Render a label / value pair stacked and panel-centred."""
        y = self._draw_hud_label(surface, label, panel_x, y)
        center_x = self._panel_center_x(panel_x)
        value_surf = self.font.render(value, True, value_color)
        surface.blit(value_surf, value_surf.get_rect(midtop=(center_x, y)))
        return y + value_surf.get_height()

    def _hud_max_height(self) -> int:
        """Worst-case HUD panel height (all cheats active).

        Used to pin the panel's vertical position so it stays
        centred on the window regardless of how many cheat lines
        are currently visible.
        """
        line_h = self.font.get_height()
        kv_h = 2 * line_h + self.HUD_LINE_GAP
        lives_h = line_h + self.HUD_LINE_GAP + self.HUD_ICON_SIZE
        fruits_h = lives_h
        cheats_h = (
            line_h
            + self.HUD_LINE_GAP
            + self.HUD_MAX_CHEAT_LINES * line_h
            + (self.HUD_MAX_CHEAT_LINES - 1) * self.HUD_CHEAT_LINE_GAP
        )
        sections = (kv_h, kv_h, kv_h, kv_h, lives_h, fruits_h, cheats_h)
        return sum(sections) + (len(sections) - 1) * self.HUD_SECTION_GAP

    def _draw_hud_lives(
        self,
        surface: pygame.Surface,
        count: int,
        panel_x: int,
        y: int,
    ) -> int:
        """Draw the lives section: pac-man sprites + overflow tag, centred."""
        y = self._draw_hud_label(surface, "LIVES", panel_x, y)
        icon = pygame.transform.scale(
            self.assets.get_sprite("pacman_right_0"),
            (self.HUD_ICON_SIZE, self.HUD_ICON_SIZE),
        )
        shown = min(count, self.HUD_LIVES_MAX_ICONS)
        row_width = (
            shown * self.HUD_ICON_SIZE
            + max(0, shown - 1) * self.HUD_ICON_GAP
        )
        overflow_surf: pygame.Surface | None = None
        if count > self.HUD_LIVES_MAX_ICONS:
            overflow_surf = self.font.render(f"x{count}", True, Colors.WHITE)
            row_width += self.HUD_ICON_GAP + overflow_surf.get_width()
        start_x = self._panel_center_x(panel_x) - row_width // 2
        for i in range(shown):
            surface.blit(
                icon,
                (start_x + i * (self.HUD_ICON_SIZE + self.HUD_ICON_GAP), y),
            )
        if overflow_surf is not None:
            overflow_x = (
                start_x + shown * (self.HUD_ICON_SIZE + self.HUD_ICON_GAP)
            )
            overflow_y = (
                y + (self.HUD_ICON_SIZE - overflow_surf.get_height()) // 2
            )
            surface.blit(overflow_surf, (overflow_x, overflow_y))
        return y + self.HUD_ICON_SIZE

    def _draw_hud_fruits(
        self,
        surface: pygame.Surface,
        fruit_sprites: list[str],
        panel_x: int,
        y: int,
    ) -> int:
        """Draw the fruits collected this level, centred on the panel."""
        y = self._draw_hud_label(surface, "FRUITS", panel_x, y)
        center_x = self._panel_center_x(panel_x)
        if not fruit_sprites:
            placeholder = self.font.render("---", True, Colors.GREY)
            surface.blit(
                placeholder, placeholder.get_rect(midtop=(center_x, y))
            )
            return y + placeholder.get_height()
        size = self.HUD_ICON_SIZE
        n = len(fruit_sprites)
        row_width = n * size + (n - 1) * self.HUD_ICON_GAP
        start_x = center_x - row_width // 2
        for i, sprite_name in enumerate(fruit_sprites):
            sprite = pygame.transform.scale(
                self.assets.get_sprite(sprite_name), (size, size)
            )
            surface.blit(sprite, (start_x + i * (size + self.HUD_ICON_GAP), y))
        return y + size

    def _draw_hud_cheats(
        self,
        surface: pygame.Surface,
        cheat_lines: list[str],
        panel_x: int,
        y: int,
    ) -> int:
        """Draw the active-cheat list (only called when non-empty)."""
        y = self._draw_hud_label(surface, "CHEATS", panel_x, y)
        center_x = self._panel_center_x(panel_x)
        for line in cheat_lines:
            line_surf = self.font.render(line, True, Colors.GOLD)
            surface.blit(line_surf, line_surf.get_rect(midtop=(center_x, y)))
            y += line_surf.get_height() + self.HUD_CHEAT_LINE_GAP
        return y

    @staticmethod
    def _cheat_lines(engine: GameEngine) -> list[str]:
        """Build the list of active cheat labels (empty when none)."""
        lines: list[str] = []
        if engine.cheats.invincibility:
            lines.append("INVINCIBLE")
        if engine.cheats.ghost_freeze:
            lines.append("GHOST FREEZE")
        if engine.cheats.timer_freeze:
            lines.append("TIMER FREEZE")
        pacman = engine.characters.pacman
        if pacman.noclip:
            lines.append("NOCLIP")
        if pacman.speed_multiplier != 1.0:
            percent = int(round(pacman.speed_multiplier * 100))
            lines.append(f"SPEED {percent}%")
        return lines

    def _draw_level_transition(
        self,
        surface: pygame.Surface,
        engine: GameEngine,
    ) -> None:
        """Draw the overlay shown between two levels."""
        transition_elapsed_ms = (
            engine.level_transition_duration_ms
            - engine.level_transition_hold.remaining_ms
        )

        draw_overlay(surface, transition_elapsed_ms)

        draw_lines(
            surface,
            self.font,
            (
                (
                    f"LEVEL {engine.level_index + 1} COMPLETE",
                    Colors.GOLD,
                ),
                (f"LEVEL {engine.level_index + 2}", Colors.GREY),
            ),
        )
