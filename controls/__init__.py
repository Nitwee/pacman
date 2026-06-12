"""Keyboard controls routing."""

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
from controls.router import InputRouter

__all__ = (
    "AskQuit",
    "CancelQuitInput",
    "CheatInput",
    "ConfirmQuitInput",
    "ConfirmSelection",
    "GoBack",
    "InputAction",
    "InputRouter",
    "MoveCursor",
    "MovePlayer",
    "ResumeInput",
    "TogglePauseInput",
    "TypeHighscore",
)
