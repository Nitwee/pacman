"""Screen manager used by :mod:`app`.

The manager routes update/draw calls to the active screen. Each screen
owns the animations it needs.
"""

import pygame

from display import Resolution
from game_engine import GameEngine
from graphics.assets import AssetManager
from highscore import HighscoreEntry
from screens.game_over import GameOverScreen
from screens.highscore_entry import HighscoreEntryScreen
from screens.instructions import InstructionsScreen
from screens.leaderboard import LeaderboardScreen
from screens.main_menu import MainMenuScreen
from screens.options import OptionsScreen
from screens.pause import PauseScreen
from screens.playing import PlayingScreen
from screens.victory import VictoryScreen


class ScreenManager:
    """Owns screen objects and routes drawing to the current screen."""

    def __init__(
        self,
        assets: AssetManager,
        font: pygame.font.Font,
    ) -> None:
        """Create all screen objects."""
        self.main_menu = MainMenuScreen(font, assets)
        self.playing = PlayingScreen(font, assets)
        self.pause = PauseScreen(font)
        self.game_over = GameOverScreen(font)
        self.victory = VictoryScreen(font)
        self.instructions = InstructionsScreen(font, assets)
        self.leaderboard = LeaderboardScreen(font, assets)
        self.highscore_entry = HighscoreEntryScreen(font)
        self.options = OptionsScreen(font, assets)

    def update(self, dt_ms: int, state_name: str) -> None:
        """Advance animations owned by the active screen."""
        if state_name == "MAIN_MENU":
            self.main_menu.update(dt_ms)
            return

        if state_name == "INSTRUCTIONS":
            self.instructions.update(dt_ms)
            return

        if state_name == "LEADERBOARD":
            self.leaderboard.update(dt_ms)
            return

        if state_name == "OPTIONS":
            self.options.update(dt_ms)
            return

        if state_name in (
            "PLAYING",
            "PAUSED",
            "GAME_OVER",
            "VICTORY",
            "CONFIRM_QUIT",
            "CONFIRM_MAIN_MENU",
        ):
            self.playing.update(dt_ms)

    def reset_death_animation(self) -> None:
        """Restart Pac-Man's death animation from frame zero."""
        self.playing.reset_death_animation()

    def move_menu_cursor(self, offset: int) -> None:
        """Move the main menu cursor up or down."""
        self.main_menu.move_cursor(offset)

    def selected_menu_item(self) -> str:
        """Return the currently selected main menu item."""
        return self.main_menu.selected_item()

    def move_options_cursor(self, offset: int) -> None:
        """Move the options cursor up or down."""
        self.options.move_cursor(offset)

    def selected_option_resolution(self) -> Resolution | None:
        """Return the selected windowed resolution, if any."""
        return self.options.selected_resolution()

    def selected_option_fullscreen(self) -> bool:
        """Return True if fullscreen is selected."""
        return self.options.selected_fullscreen()

    def selected_option_sound(self) -> bool:
        """Return True if sound is selected."""
        return self.options.selected_sound()

    def selected_option_back(self) -> bool:
        """Return True if the back row is selected."""
        return self.options.selected_back()

    def move_instructions_cursor(self, offset: int) -> None:
        """Move the instructions cursor up or down."""
        self.instructions.move_cursor(offset)

    def selected_instructions_item(self) -> str:
        """Return the currently selected instructions item."""
        return self.instructions.selected_item()

    def move_leaderboard_cursor(self, offset: int) -> None:
        """Move the leaderboard cursor up or down."""
        self.leaderboard.move_cursor(offset)

    def selected_leaderboard_item(self) -> str:
        """Return the currently selected leaderboard item."""
        return self.leaderboard.selected_item()

    def move_pause_cursor(self, offset: int) -> None:
        """Move the pause cursor up or down."""
        self.pause.move_cursor(offset)

    def selected_pause_item(self) -> str:
        """Return the currently selected pause menu item."""
        return self.pause.selected_item()

    def draw(
        self,
        surface: pygame.Surface,
        state_name: str,
        engine: GameEngine | None,
        elapsed_ms: int,
        highscore_entries: tuple[HighscoreEntry, ...] = (),
        pending_score: int | None = None,
        pending_name: str = "",
        current_resolution: Resolution = (1000, 900),
        fullscreen: bool = False,
        sound_enabled: bool = True,
    ) -> None:
        """Draw the screen matching ``state_name``."""
        if state_name == "MAIN_MENU":
            self.main_menu.draw(surface, elapsed_ms)
            return

        if engine is not None and state_name in (
            "PLAYING",
            "PAUSED",
            "GAME_OVER",
            "VICTORY",
            "CONFIRM_QUIT",
            "CONFIRM_MAIN_MENU",
        ):
            top_score = highscore_entries[0].score if highscore_entries else 0
            self.playing.draw(surface, engine, elapsed_ms, top_score)

        if state_name == "PAUSED":
            self.pause.draw(surface, elapsed_ms, sound_enabled)
        elif state_name == "CONFIRM_QUIT":
            self.pause.draw_confirm_quit(surface, elapsed_ms)
        elif state_name == "CONFIRM_MAIN_MENU":
            self.pause.draw_confirm_main_menu(surface, elapsed_ms)
        elif state_name == "GAME_OVER" and engine is not None:
            self.game_over.draw(surface, engine.score, elapsed_ms)
        elif state_name == "VICTORY" and engine is not None:
            self.victory.draw(surface, engine.score, elapsed_ms)
        elif state_name == "INSTRUCTIONS":
            self.instructions.draw(surface, elapsed_ms)
        elif state_name == "LEADERBOARD":
            self.leaderboard.draw(surface, highscore_entries, elapsed_ms)
        elif state_name == "OPTIONS":
            self.options.draw(
                surface,
                current_resolution,
                fullscreen,
                sound_enabled,
                elapsed_ms,
            )
        elif state_name == "HIGHSCORE_ENTRY" and pending_score is not None:
            self.highscore_entry.draw(
                surface,
                pending_score,
                pending_name,
                elapsed_ms,
            )
