"""Transition events used by :class:`app.App`."""

from dataclasses import dataclass


class Event:
    """Marker base class for all transition events."""


@dataclass(frozen=True)
class StartGame(Event):
    """User starts a new game from the main menu."""


@dataclass(frozen=True)
class ViewInstructions(Event):
    """User opens the instructions screen."""


@dataclass(frozen=True)
class ViewOptions(Event):
    """User opens the options screen."""


@dataclass(frozen=True)
class ViewHighscores(Event):
    """User opens the leaderboard from the main menu."""


@dataclass(frozen=True)
class Quit(Event):
    """User asks to quit the application."""


@dataclass(frozen=True)
class TogglePause(Event):
    """User toggles pause during play (P / Esc)."""


@dataclass(frozen=True)
class Resume(Event):
    """User resumes from the pause menu."""


@dataclass(frozen=True)
class QuitToMenu(Event):
    """User returns to the main menu from the pause screen."""


@dataclass(frozen=True)
class GameWon(Event):
    """Last level cleared — overall victory."""

    score: int


@dataclass(frozen=True)
class GameLost(Event):
    """Player ran out of lives or time."""

    score: int


@dataclass(frozen=True)
class Continue(Event):
    """User dismisses the Victory / GameOver screen."""


@dataclass(frozen=True)
class HighscoreConfirmed(Event):
    """User confirmed their name on the highscore entry screen."""

    name: str
    score: int


@dataclass(frozen=True)
class Back(Event):
    """User goes back from Instructions, Options or LeaderBoard."""


@dataclass(frozen=True)
class ConfirmQuit(Event):
    """User confirmed quitting from the confirmation screen."""


@dataclass(frozen=True)
class CancelQuit(Event):
    """User cancelled quitting; return to the paused game."""
