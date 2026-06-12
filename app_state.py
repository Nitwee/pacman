"""Top-level application states."""

from enum import Enum, auto


class State(Enum):
    """Top-level application states.

    See ``docs/state-machine.svg`` for the full transition graph.
    """

    MAIN_MENU = auto()
    PLAYING = auto()
    PAUSED = auto()
    INSTRUCTIONS = auto()
    GAME_OVER = auto()
    VICTORY = auto()
    HIGHSCORE_ENTRY = auto()
    LEADERBOARD = auto()
    OPTIONS = auto()
    CONFIRM_QUIT = auto()
    CONFIRM_MAIN_MENU = auto()
