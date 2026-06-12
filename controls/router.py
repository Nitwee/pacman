"""Translate raw keyboard presses into app-level intentions."""

import pygame

from app_state import State
from characters import Direction
from controls.actions import (
    AskQuit,
    CancelQuitInput,
    CheatInput,
    ConfirmQuitInput,
    ConfirmSelection,
    GoBack,
    InputAction,
    MoveCursor,
    MovePlayer,
    ResumeInput,
    TogglePauseInput,
    TypeHighscore,
)

CHEAT_KEYS = {
    pygame.K_i,
    pygame.K_f,
    pygame.K_t,
    pygame.K_w,
    pygame.K_e,
    pygame.K_UP,
    pygame.K_DOWN,
    pygame.K_l,
    pygame.K_c,
}


class InputRouter:
    """Convert one key press into an intention, without mutating the app."""

    def handle_keydown(
        self,
        state: State,
        key: int,
        text: str = "",
        ctrl_pressed: bool = False,
    ) -> InputAction | None:
        """Return the action represented by ``key`` in ``state``."""
        if state in (State.CONFIRM_QUIT, State.CONFIRM_MAIN_MENU):
            return self._confirm_quit_action(key)

        if state == State.HIGHSCORE_ENTRY:
            return TypeHighscore(key, text)

        if key == pygame.K_ESCAPE:
            return self._escape_action(state)

        if state in (
            State.MAIN_MENU,
            State.OPTIONS,
            State.INSTRUCTIONS,
            State.LEADERBOARD,
            State.PAUSED,
        ):
            return self._menu_action(state, key)

        if state == State.PLAYING:
            return self._playing_action(key, ctrl_pressed)

        if state in (State.GAME_OVER, State.VICTORY):
            if key == pygame.K_RETURN:
                return ConfirmSelection()

        return None

    def _confirm_quit_action(self, key: int) -> InputAction | None:
        """Return the action for the quit confirmation dialog."""
        if key in (pygame.K_RETURN, pygame.K_y):
            return ConfirmQuitInput()
        if key in (pygame.K_ESCAPE, pygame.K_n, pygame.K_BACKSPACE):
            return CancelQuitInput()
        return None

    def _escape_action(self, state: State) -> InputAction:
        """Return the action triggered by Escape in ``state``."""
        if state == State.PLAYING:
            return TogglePauseInput()
        if state == State.PAUSED:
            return ResumeInput()
        if state in (
            State.INSTRUCTIONS,
            State.LEADERBOARD,
            State.OPTIONS,
        ):
            return GoBack()
        return AskQuit()

    def _menu_action(
        self,
        state: State,
        key: int,
    ) -> InputAction | None:
        """Return the action for menu-like screens."""
        cursor_offset = self._cursor_offset_from_key(key)
        if cursor_offset is not None:
            return MoveCursor(cursor_offset)

        if state == State.PAUSED and key == pygame.K_p:
            return ResumeInput()

        if state == State.OPTIONS and key in (
            pygame.K_SPACE,
            pygame.K_BACKSPACE,
        ):
            return GoBack()

        if key == pygame.K_RETURN:
            return ConfirmSelection()
        return None

    def _playing_action(
        self,
        key: int,
        ctrl_pressed: bool,
    ) -> InputAction | None:
        """Return the action for in-game key presses."""
        if ctrl_pressed and key in CHEAT_KEYS:
            return CheatInput(key)

        direction = self._direction_from_key(key)
        if direction is not None:
            return MovePlayer(direction)

        if key == pygame.K_p:
            return TogglePauseInput()
        return None

    def _cursor_offset_from_key(self, key: int) -> int | None:
        """Return -1 or 1 for vertical menu navigation keys."""
        if key in (pygame.K_UP, pygame.K_w):
            return -1
        if key in (pygame.K_DOWN, pygame.K_s):
            return 1
        return None

    def _direction_from_key(self, key: int) -> Direction | None:
        """Translate arrow/WASD keys into character directions."""
        if key in (pygame.K_UP, pygame.K_w):
            return Direction.UP
        if key in (pygame.K_RIGHT, pygame.K_d):
            return Direction.RIGHT
        if key in (pygame.K_DOWN, pygame.K_s):
            return Direction.DOWN
        if key in (pygame.K_LEFT, pygame.K_a):
            return Direction.LEFT
        return None
