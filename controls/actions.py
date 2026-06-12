"""Intentions produced by keyboard input."""

from dataclasses import dataclass

from characters import Direction


class InputAction:
    """Marker base class for all keyboard intentions."""


@dataclass(frozen=True)
class MoveCursor(InputAction):
    """Move the cursor of the current menu."""

    offset: int


@dataclass(frozen=True)
class ConfirmSelection(InputAction):
    """Confirm the currently selected item."""


@dataclass(frozen=True)
class GoBack(InputAction):
    """Return to the previous/menu screen."""


@dataclass(frozen=True)
class AskQuit(InputAction):
    """Ask the app to quit or open quit confirmation."""


@dataclass(frozen=True)
class ConfirmQuitInput(InputAction):
    """Confirm the quit dialog."""


@dataclass(frozen=True)
class CancelQuitInput(InputAction):
    """Cancel the quit dialog."""


@dataclass(frozen=True)
class TogglePauseInput(InputAction):
    """Pause the game."""


@dataclass(frozen=True)
class ResumeInput(InputAction):
    """Resume the paused game."""


@dataclass(frozen=True)
class MovePlayer(InputAction):
    """Move Pac-Man in a direction."""

    direction: Direction


@dataclass(frozen=True)
class CheatInput(InputAction):
    """Trigger one cheat key."""

    key: int


@dataclass(frozen=True)
class TypeHighscore(InputAction):
    """Type into the highscore name input."""

    key: int
    text: str
