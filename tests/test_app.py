"""Unit tests for the App state machine in :mod:`app`.

Tests bypass :meth:`App.__init__` via :meth:`App.__new__` so that no
config file, Pygame surface, or real highscore store is required. Only
the :meth:`App.dispatch` routing logic is exercised.
"""

from unittest.mock import Mock
from typing import cast

from game_engine import EatenItem, EdibleType, GameEvent, ItemEatenEvent

import pytest

from app import (
    App,
    State,
)
from data_classes import (
    Back,
    CancelQuit,
    ConfirmQuit,
    Continue,
    GameLost,
    GameWon,
    HighscoreConfirmed,
    Quit,
    QuitToMenu,
    Resume,
    StartGame,
    TogglePause,
    ViewHighscores,
    ViewInstructions,
)


def make_app(state: State = State.MAIN_MENU) -> App:
    """Build a bare App suitable for state-machine unit tests.

    Args:
        state: Initial state for the test scenario.

    Returns:
        An App instance with a Mock highscore store and no other deps.
    """
    app = App.__new__(App)
    app.state = state
    app.running = True
    app._quit_origin = State.PAUSED
    app.highscore_store = Mock()
    app.pending_highscore_score = None
    app.highscore_name = ""
    app.sounds = None
    app.sound_enabled = True
    app._chomp_toggle = False
    app.screen_elapsed_ms = 0
    app.engine = None
    return app


# --- Main menu transitions ---------------------------------------------


def test_start_game_from_main_menu() -> None:
    app = make_app(State.MAIN_MENU)
    app.dispatch(StartGame())
    assert app.state == State.PLAYING


def test_view_instructions_from_main_menu() -> None:
    app = make_app(State.MAIN_MENU)
    app.dispatch(ViewInstructions())
    assert app.state == State.INSTRUCTIONS


def test_view_highscores_from_main_menu() -> None:
    app = make_app(State.MAIN_MENU)
    app.dispatch(ViewHighscores())
    assert app.state == State.LEADERBOARD


# --- Playing transitions -----------------------------------------------


def test_playing_toggle_pause_pauses_the_game() -> None:
    app = make_app(State.PLAYING)
    app.dispatch(TogglePause())
    assert app.state == State.PAUSED


def test_playing_game_won_goes_to_victory() -> None:
    app = make_app(State.PLAYING)
    app.dispatch(GameWon(score=1234))
    assert app.state == State.VICTORY


def test_playing_game_lost_goes_to_game_over() -> None:
    app = make_app(State.PLAYING)
    app.dispatch(GameLost(score=42))
    assert app.state == State.GAME_OVER


def test_engine_events_trigger_fruit_and_extend_sfx() -> None:
    """Fruit and extra-life events map to their dedicated sounds."""
    app = make_app(State.PLAYING)
    app.engine = Mock()
    app.engine.events = [
        ItemEatenEvent(
            EatenItem(
                edible_type=EdibleType.BONUS_FRUIT,
                position=(1, 1),
                points=100,
            )
        ),
        GameEvent.EXTRA_LIFE_EARNED,
    ]
    app.sounds = Mock()

    app._handle_engine_events()

    app.sounds.play_sfx.assert_any_call("eat_fruit")
    app.sounds.play_sfx.assert_any_call("extend")


def test_item_eaten_event_plays_one_chomp_for_pacgum() -> None:
    """Pacgum audio is driven by the unified payload event."""
    app = make_app(State.PLAYING)
    app.engine = Mock()
    app.engine.events = [
        ItemEatenEvent(
            EatenItem(
                edible_type=EdibleType.PACGUM,
                position=(1, 1),
                points=10,
            )
        )
    ]
    app.sounds = Mock()

    app._handle_engine_events()

    app.sounds.play_sfx.assert_called_once_with("eat_dot_0")


# --- Paused transitions ------------------------------------------------


def test_paused_toggle_pause_resumes() -> None:
    app = make_app(State.PAUSED)
    app.dispatch(TogglePause())
    assert app.state == State.PLAYING


def test_paused_resume_resumes() -> None:
    app = make_app(State.PAUSED)
    app.dispatch(Resume())
    assert app.state == State.PLAYING


def test_paused_quit_to_menu_returns_to_main_menu() -> None:
    app = make_app(State.PAUSED)
    app.dispatch(QuitToMenu())
    assert app.state == State.MAIN_MENU


# --- End-of-game transitions -------------------------------------------


@pytest.mark.parametrize("source", [State.VICTORY, State.GAME_OVER])
def test_continue_from_end_screen_returns_to_main_menu(
    source: State,
) -> None:
    app = make_app(source)
    app.dispatch(Continue())
    assert app.state == State.MAIN_MENU


def test_continue_from_end_screen_with_highscore_opens_entry() -> None:
    """A qualifying final score asks the player for their name."""
    app = make_app(State.GAME_OVER)
    store = cast(Mock, app.highscore_store)
    app.pending_highscore_score = 4242
    store.qualifies.return_value = True

    app.dispatch(Continue())

    assert app.state == State.HIGHSCORE_ENTRY


def test_continue_from_end_screen_without_highscore_returns_to_menu() -> None:
    """A non-qualifying final score skips name entry."""
    app = make_app(State.GAME_OVER)
    store = cast(Mock, app.highscore_store)
    app.pending_highscore_score = 1
    store.qualifies.return_value = False

    app.dispatch(Continue())

    assert app.state == State.MAIN_MENU
    assert app.pending_highscore_score is None


# --- Highscore entry ---------------------------------------------------


def test_highscore_confirmed_persists_and_advances() -> None:
    app = make_app(State.HIGHSCORE_ENTRY)
    store = cast(Mock, app.highscore_store)
    app.dispatch(HighscoreConfirmed(name="JBA", score=4242))
    store.add.assert_called_once_with("JBA", 4242)
    assert app.state == State.LEADERBOARD


# --- Back transitions --------------------------------------------------


@pytest.mark.parametrize("source", [State.INSTRUCTIONS, State.LEADERBOARD])
def test_back_returns_to_main_menu(source: State) -> None:
    app = make_app(source)
    app.dispatch(Back())
    assert app.state == State.MAIN_MENU


# --- Quit policy: states with a score at risk go to confirmation -------


@pytest.mark.parametrize(
    "source",
    [
        State.PLAYING,
        State.PAUSED,
        State.VICTORY,
        State.GAME_OVER,
        State.HIGHSCORE_ENTRY,
    ],
)
def test_quit_with_score_at_risk_opens_confirmation(
    source: State,
) -> None:
    app = make_app(source)
    app.dispatch(Quit())
    assert app.state == State.CONFIRM_QUIT
    assert app.running is True
    assert app._quit_origin == source


# --- Quit policy: safe states exit immediately -------------------------


@pytest.mark.parametrize(
    "source",
    [State.MAIN_MENU, State.INSTRUCTIONS, State.LEADERBOARD],
)
def test_quit_from_safe_state_exits_immediately(
    source: State,
) -> None:
    app = make_app(source)
    app.dispatch(Quit())
    assert app.running is False


def test_quit_from_confirm_quit_exits_immediately() -> None:
    app = make_app(State.CONFIRM_QUIT)
    app.dispatch(Quit())
    assert app.running is False


# --- Confirmation modal events -----------------------------------------


def test_confirm_quit_exits_loop() -> None:
    app = make_app(State.CONFIRM_QUIT)
    app.dispatch(ConfirmQuit())
    assert app.running is False


@pytest.mark.parametrize(
    "origin",
    [
        State.PLAYING,
        State.PAUSED,
        State.VICTORY,
        State.GAME_OVER,
        State.HIGHSCORE_ENTRY,
    ],
)
def test_cancel_quit_returns_to_origin(origin: State) -> None:
    app = make_app(origin)
    app.dispatch(Quit())
    app.dispatch(CancelQuit())
    assert app.state == origin
    assert app.running is True


# --- Illegal transitions are silent no-ops -----------------------------


def test_resume_from_main_menu_is_noop() -> None:
    app = make_app(State.MAIN_MENU)
    app.dispatch(Resume())
    assert app.state == State.MAIN_MENU


def test_start_game_from_playing_is_noop() -> None:
    app = make_app(State.PLAYING)
    app.dispatch(StartGame())
    assert app.state == State.PLAYING


def test_game_won_from_main_menu_is_noop() -> None:
    app = make_app(State.MAIN_MENU)
    app.dispatch(GameWon(score=100))
    assert app.state == State.MAIN_MENU


def test_highscore_confirmed_outside_entry_does_not_persist() -> None:
    app = make_app(State.MAIN_MENU)
    store = cast(Mock, app.highscore_store)
    app.dispatch(HighscoreConfirmed(name="ZZZ", score=0))
    store.add.assert_not_called()
    assert app.state == State.MAIN_MENU
