"""Top-level state machine and dependency container.

This module defines :class:`App`, the orchestrator that routes typed
:class:`Event` instances between :class:`app_state.State` values. It
owns the long-lived dependencies (config, highscore store, assets,
screens) and a transient :class:`GameEngine` instantiated on each new
game.

No game logic lives here — App only routes transitions.
"""

import asyncio
from collections.abc import Callable

import pygame

from audio import SoundManager
from audio import setup as audio_setup
from app_state import State
from data_classes import (
    Back,
    CancelQuit,
    ConfirmQuit,
    Continue,
    Event,
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
    ViewOptions,
)
from display import DisplayManager
from controls import (
    AskQuit,
    CancelQuitInput,
    CheatInput,
    ConfirmQuitInput,
    ConfirmSelection,
    GoBack,
    InputAction,
    InputRouter,
    MoveCursor,
    MovePlayer,
    ResumeInput,
    TogglePauseInput,
    TypeHighscore,
)
from game_engine import (
    EdibleType,
    EngineState,
    GameEngine,
    GameEvent,
    ItemEatenEvent,
    MusicCue,
)
from graphics import asset_setup
from graphics.assets import AssetManager
from graphics.renderer import Colors
from highscore import HighscoreStore
from parser.manager import ConfigManager
from screens import ScreenManager

SPRITE_SHEET_PATH = (
    "assets/sprites/"
    "Arcade - Pac-Man - Miscellaneous - All Assets_Palettes.png"
)
FONT_PATH = "assets/fonts/emulogic.ttf"
__all__ = ("App", "State")


class App:
    """Top-level state machine and dependency container.

    Attributes:
        game_config: Parsed configuration loaded at startup.
        state: Current top-level state.
        running: Whether the main loop should keep iterating.
    """

    def __init__(self, config_filename: str) -> None:
        """Initialise the application from a config file path.

        Args:
            config_filename: Path to the JSON config file.
        """
        self.game_config = ConfigManager(config_filename).config
        self.state: State = State.MAIN_MENU
        self.running: bool = False
        self._quit_origin: State = State.PAUSED
        self.highscore_store = HighscoreStore(
            self.game_config.highscore_filename
        )
        self.assets = AssetManager(SPRITE_SHEET_PATH)
        asset_setup.setup(self.assets)
        self.input_router = InputRouter()
        self.display = DisplayManager()
        self.engine: GameEngine | None = None
        self.screens: ScreenManager | None = None
        self.sound_enabled = True
        self.screen_elapsed_ms = 0
        self.pending_highscore_score: int | None = None
        self.highscore_name = ""
        # SoundManager is created in run() once pygame.mixer is up.
        self.sounds: SoundManager | None = None
        self._chomp_toggle: bool = False

    def run(self) -> None:
        """Run the game synchronously on desktop platforms."""
        asyncio.run(self.run_async())

    async def run_async(
        self,
        on_ready: Callable[[], None] | None = None,
    ) -> None:
        """Run the game while yielding each frame to an async host."""
        pygame.init()
        try:
            self.running = True
            canvas = self.display.setup()
            pygame.display.set_caption("Pac-Man")
            font = pygame.font.Font(FONT_PATH, 16)
            clock = pygame.time.Clock()
            self.screens = ScreenManager(self.assets, font)
            try:
                self.sounds = SoundManager()
                audio_setup.setup(self.sounds)
            except pygame.error as e:
                print(f"Audio disabled {e}")
                self.sounds = None
            prev_dying = False

            if on_ready is not None:
                on_ready()

            while self.running:
                dt_ms = clock.tick(60)
                self._handle_pygame_events()
                self.screen_elapsed_ms += dt_ms

                in_level_transition = False
                if self.state == State.PLAYING and self.engine is not None:
                    self.engine.update(dt_ms)
                    self._handle_engine_events()
                    engine_state = self.engine.state
                    in_level_transition = (
                        engine_state == EngineState.LEVEL_TRANSITION
                    )
                    is_dying = engine_state == EngineState.DYING
                    # Restart the death animation each time Pac-Man
                    # enters the dying state (so frame 0 is shown
                    # first instead of resuming a stale phase).
                    if (
                        is_dying
                        and not prev_dying
                        and self.screens is not None
                    ):
                        self.screens.reset_death_animation()
                    prev_dying = is_dying
                    if engine_state == EngineState.GAME_OVER:
                        self.dispatch(GameLost(score=self.engine.score))
                    elif engine_state == EngineState.GAME_WON:
                        self.dispatch(GameWon(score=self.engine.score))

                if self.screens is not None:
                    self.screens.update(dt_ms, self.state.name)
                    if (
                        in_level_transition
                        or self.screens.playing.palette_flicker_pending
                    ):
                        self.screens.playing.tick_palette_flicker(
                            dt_ms, in_level_transition
                        )

                self._update_background_music()

                canvas.fill(Colors.BLACK)
                self._draw_current_state(canvas)
                self.display.present_canvas()
                pygame.display.flip()
                await asyncio.sleep(0)
        finally:
            if self.sounds is not None:
                self.sounds.stop_all()
            if pygame.mixer.get_init():
                pygame.mixer.quit()
            pygame.quit()

    def _handle_pygame_events(self) -> None:
        """Handle Pygame input events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.dispatch(Quit())
            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event.key, event.unicode)

    def _handle_keydown(self, key: int, text: str = "") -> None:
        """Route one key press into the app or active engine."""
        keys = pygame.key.get_pressed()
        action = self.input_router.handle_keydown(
            self.state,
            key,
            text,
            ctrl_pressed=keys[pygame.K_LCTRL],
        )
        if action is not None:
            self._apply_input_action(action)

    def _apply_input_action(self, action: InputAction) -> None:
        """Apply a keyboard intention returned by InputRouter."""
        if isinstance(action, MoveCursor):
            self._move_current_cursor(action.offset)
        elif isinstance(action, ConfirmSelection):
            self._confirm_current_selection()
        elif isinstance(action, GoBack):
            self.dispatch(Back())
        elif isinstance(action, AskQuit):
            self.dispatch(Quit())
        elif isinstance(action, ConfirmQuitInput):
            if self.state == State.CONFIRM_MAIN_MENU:
                self.dispatch(QuitToMenu())
            else:
                self.dispatch(ConfirmQuit())
        elif isinstance(action, CancelQuitInput):
            if self.state == State.CONFIRM_MAIN_MENU:
                self.dispatch(Resume())
            else:
                self.dispatch(CancelQuit())
        elif isinstance(action, TogglePauseInput):
            self.dispatch(TogglePause())
        elif isinstance(action, ResumeInput):
            self.dispatch(Resume())
        elif isinstance(action, MovePlayer):
            if self.engine is not None:
                self.engine.queue_player_direction(action.direction)
        elif isinstance(action, CheatInput):
            self._apply_cheat_input(action.key)
        elif isinstance(action, TypeHighscore):
            self._apply_highscore_input(action.key, action.text)

    def _move_current_cursor(self, offset: int) -> None:
        """Move the cursor belonging to the current screen."""
        if self.screens is None:
            return

        if self.state == State.MAIN_MENU:
            self.screens.move_menu_cursor(offset)
        elif self.state == State.OPTIONS:
            self.screens.move_options_cursor(offset)
        elif self.state == State.INSTRUCTIONS:
            self.screens.move_instructions_cursor(offset)
        elif self.state == State.LEADERBOARD:
            self.screens.move_leaderboard_cursor(offset)
        elif self.state == State.PAUSED:
            self.screens.move_pause_cursor(offset)
        else:
            return

        self._play_sfx("credit")

    def _confirm_current_selection(self) -> None:
        """Confirm the currently selected item for the active state."""
        if self.state == State.MAIN_MENU:
            self._confirm_main_menu_selection()
        elif self.state == State.OPTIONS:
            self._confirm_options_selection()
        elif self.state == State.INSTRUCTIONS:
            self._confirm_instructions_selection()
        elif self.state == State.LEADERBOARD:
            self._confirm_leaderboard_selection()
        elif self.state == State.PAUSED:
            self._confirm_pause_selection()
        elif self.state in (State.GAME_OVER, State.VICTORY):
            self.engine = None
            self.dispatch(Continue())

    def _confirm_main_menu_selection(self) -> None:
        """Apply the selected main menu item."""
        if self.screens is None:
            return

        selected_item = self.screens.selected_menu_item()
        if selected_item == "Play":
            self._play_sfx("start")
            self.engine = GameEngine(self.game_config)
            self._configure_engine_sound_durations(self.engine)
            if self.sound_enabled and self.sounds is not None:
                self.engine.start_intro(self.sounds.get_duration_ms("start"))
            self.dispatch(StartGame())
        elif selected_item == "Options":
            self.dispatch(ViewOptions())
        elif selected_item == "Leaderboard":
            self.dispatch(ViewHighscores())
        elif selected_item == "Instructions":
            self.dispatch(ViewInstructions())
        elif selected_item == "Quit":
            self.dispatch(Quit())

    def _confirm_options_selection(self) -> None:
        """Apply the selected options menu item."""
        if self.screens is None:
            return

        if self.screens.selected_option_back():
            self.dispatch(Back())
            return
        if self.screens.selected_option_fullscreen():
            self.display.set_fullscreen()
            return
        if self.screens.selected_option_sound():
            self._toggle_sound()
            return

        resolution = self.screens.selected_option_resolution()
        if resolution is not None:
            self.display.set_windowed_resolution(resolution)

    def _confirm_instructions_selection(self) -> None:
        """Apply the selected instructions item."""
        if self.screens is None:
            return

        if self.screens.selected_instructions_item() == "Back":
            self.dispatch(Back())

    def _confirm_leaderboard_selection(self) -> None:
        """Apply the selected leaderboard item."""
        if self.screens is None:
            return

        if self.screens.selected_leaderboard_item() == "Back":
            self.dispatch(Back())

    def _confirm_pause_selection(self) -> None:
        """Apply the selected pause menu item."""
        if self.screens is None:
            return

        selected_item = self.screens.selected_pause_item()
        if selected_item == "Resume":
            self.dispatch(Resume())
        elif selected_item == "Sound":
            self._toggle_sound()
        elif selected_item == "Main Menu":
            self._set_state(State.CONFIRM_MAIN_MENU)
        elif selected_item == "Quit":
            self.dispatch(Quit())

    def _apply_cheat_input(self, key: int) -> None:
        """Apply one Ctrl-modified cheat key."""
        if self.engine is None:
            return
        if key == pygame.K_i:
            self.engine.toggle_invincibility()
        elif key == pygame.K_f:
            self.engine.toggle_ghost_freeze()
        elif key == pygame.K_t:
            self.engine.toggle_timer_freeze()
        elif key == pygame.K_w:
            self.engine.toggle_noclip()
        elif key == pygame.K_e:
            self.engine.gain_life()
        elif key == pygame.K_UP:
            self.engine.speed_up_pacman()
        elif key == pygame.K_DOWN:
            self.engine.slow_down_pacman()
        elif key == pygame.K_l:
            self.engine.clear_pacgums()
        elif key == pygame.K_c:
            self.assets.set_palette(self.assets.next_palette())

    def _apply_highscore_input(self, key: int, text: str) -> None:
        """Apply name entry for a new highscore."""
        if key == pygame.K_BACKSPACE:
            self.highscore_name = self.highscore_name[:-1]
            return
        if key == pygame.K_RETURN and self.pending_highscore_score is not None:
            name = self.highscore_name or HighscoreStore.DEFAULT_NAME
            self.dispatch(
                HighscoreConfirmed(
                    name=name,
                    score=self.pending_highscore_score,
                )
            )
            return
        if len(self.highscore_name) >= HighscoreStore.MAX_NAME_LENGTH:
            return
        if len(text) == 1 and (text.isalnum() or text == " "):
            self.highscore_name += text.upper()

    def _toggle_sound(self) -> None:
        """Toggle every game sound and music cue."""
        self.sound_enabled = not self.sound_enabled
        if not self.sound_enabled and self.sounds is not None:
            self.sounds.stop_all()

    def _draw_current_state(
        self,
        screen: pygame.Surface,
    ) -> None:
        """Draw the current top-level state."""
        if self.screens is None:
            return
        self.screens.draw(
            screen,
            self.state.name,
            self.engine,
            self.screen_elapsed_ms,
            tuple(self.highscore_store.entries),
            self.pending_highscore_score,
            self.highscore_name,
            self.display.window_size,
            self.display.fullscreen,
            self.sound_enabled,
        )

    def _set_state(self, state: State) -> None:
        """Transition to ``state``, reset screen timer and sync audio."""
        if self.state != state:
            previous = self.state
            self.state = state
            self.screen_elapsed_ms = 0
            if self.sounds is not None:
                if state == State.MAIN_MENU:
                    # Returning to the menu severs all audio.
                    try:
                        self.sounds.stop_all()
                    except Exception:
                        self.sounds.stop_music()
                elif previous == State.PLAYING and state == State.PAUSED:
                    self.sounds.pause_all()
                elif previous == State.PAUSED and state == State.PLAYING:
                    self.sounds.unpause_all()

    # -- Audio --------------------------------------------------------

    def _play_sfx(self, name: str) -> None:
        """Play a one-shot sound if the SoundManager is ready."""
        if self.sound_enabled and self.sounds is not None:
            self.sounds.play_sfx(name)

    def _configure_engine_sound_durations(self, engine: GameEngine) -> None:
        """Sync engine timing knobs with the loaded SFX durations.

        The arcade-original sounds are immutable, so the gameplay
        holds (death animation, intermission, ghost-eat freeze,
        fruit-score overlay) are pulled from the matching ``.wav``
        files. App owns this linkage; the engine stays unaware.
        """
        if self.sounds is None:
            return
        engine.configure_durations(
            death_ms=self._sound_duration_ms("death_0"),
            level_transition_ms=self._sound_duration_ms("intermission"),
            ghost_eat_ms=self._sound_duration_ms("eat_ghost"),
            fruit_eat_ms=self._sound_duration_ms("eat_fruit"),
        )

    def _sound_duration_ms(self, name: str) -> int | None:
        """Return a registered sound duration, or None to keep defaults."""
        if self.sounds is None:
            return None
        try:
            return self.sounds.get_duration_ms(name)
        except KeyError:
            return None

    def _handle_engine_events(self) -> None:
        """Translate the latest engine events into SFX cues.

        Uses the unified ItemEatenEvent payload. Distinguishes
        between ghost collection (which freezes the game) and other items
        (which just display a score overlay).
        """
        if (
            self.engine is None
            or self.sounds is None
            or not self.sound_enabled
        ):
            return
        for event in self.engine.events:
            if isinstance(event, ItemEatenEvent):
                item = event.item
                if item.edible_type == EdibleType.PACGUM:
                    self.sounds.play_sfx(self._next_chomp_name())
                elif item.edible_type == EdibleType.SUPER_PACGUM:
                    # No dedicated SFX for super pacgum — background
                    # music switch to ``fright`` carries the cue.
                    pass
                elif item.edible_type == EdibleType.GHOST:
                    self.sounds.play_sfx("eat_ghost")
                elif item.edible_type == EdibleType.BONUS_FRUIT:
                    self.sounds.play_sfx("eat_fruit")
            elif event == GameEvent.EXTRA_LIFE_EARNED:
                self.sounds.play_sfx("extend")
            elif event == GameEvent.PAC_DEATH_STARTED:
                self.sounds.play_sfx("death_0")
            elif event == GameEvent.LEVEL_COMPLETE:
                self.sounds.play_sfx("intermission")

    def _next_chomp_name(self) -> str:
        """Return the next chomp sound, alternating between dot 0 / 1."""
        name = "eat_dot_1" if self._chomp_toggle else "eat_dot_0"
        self._chomp_toggle = not self._chomp_toggle
        return name

    def _update_background_music(self) -> None:
        """Pick and play the background loop for the current state.

        Also advances the intro→loop chain so a freshly started
        ``{name}_firstloop`` cleanly switches to its infinite
        ``{name}`` companion once it finishes.
        """
        if self.sounds is None:
            return
        if not self.sound_enabled:
            self.sounds.stop_music()
            return
        self.sounds.update_music()
        target = self._target_music()
        if target is None:
            # Menu-like screens and the death animation kill the
            # siren; pause keeps the loop alive (paused) so it can
            # resume in place.
            if self.state in (
                State.MAIN_MENU,
                State.INSTRUCTIONS,
                State.LEADERBOARD,
                State.OPTIONS,
                State.CONFIRM_QUIT,
            ):
                self.sounds.stop_music()
            elif (
                self.state == State.PLAYING
                and self.engine is not None
                and self.engine.music_cue == MusicCue.NONE
            ):
                self.sounds.stop_music()
        else:
            self.sounds.play_music(target)

    def _target_music(self) -> str | None:
        """Name of the background loop expected in the current state.

        Returns ``None`` when no loop should play (menus, pause,
        dying animation, level transition, or while the start.wav
        intro is still playing after the user pressed Play).
        """
        if self.state != State.PLAYING or self.engine is None:
            return None
        cue = self.engine.music_cue
        if cue == MusicCue.NONE:
            return None
        if cue == MusicCue.GHOST_RETURN:
            return "eyes"
        if cue == MusicCue.FRIGHT:
            return "fright"
        return f"siren{self.engine.level_index % 4}"

    def dispatch(self, event: Event) -> None:
        """Route a transition event according to the current state.

        Args:
            event: The transition event fired by a screen or the engine.
        """
        match (self.state, event):
            case (
                State.PLAYING
                | State.PAUSED
                | State.VICTORY
                | State.GAME_OVER
                | State.HIGHSCORE_ENTRY,
                Quit(),
            ):
                self._quit_origin = self.state
                self._set_state(State.CONFIRM_QUIT)
            case (_, Quit()):
                self.running = False
            case (State.CONFIRM_QUIT, ConfirmQuit()):
                self.running = False
            case (State.CONFIRM_QUIT, CancelQuit()):
                self._set_state(self._quit_origin)
            case (State.CONFIRM_MAIN_MENU, QuitToMenu()):
                self._clear_play_session()
                self._set_state(State.MAIN_MENU)
            case (State.CONFIRM_MAIN_MENU, Resume()):
                self._set_state(State.PAUSED)
            case (State.MAIN_MENU, StartGame()):
                self._set_state(State.PLAYING)
            case (State.MAIN_MENU, ViewInstructions()):
                self._set_state(State.INSTRUCTIONS)
            case (State.MAIN_MENU, ViewHighscores()):
                self._set_state(State.LEADERBOARD)
            case (State.MAIN_MENU, ViewOptions()):
                self._set_state(State.OPTIONS)
            case (State.PLAYING, TogglePause()):
                self._set_state(State.PAUSED)
            case (State.PAUSED, TogglePause() | Resume()):
                self._set_state(State.PLAYING)
            case (State.PAUSED, QuitToMenu()):
                self._set_state(State.MAIN_MENU)
            case (State.PLAYING, GameWon(score=score)):
                self._end_game(score, State.VICTORY)
            case (State.PLAYING, GameLost(score=score)):
                self._end_game(score, State.GAME_OVER)
            case (State.VICTORY | State.GAME_OVER, Continue()):
                if self._pending_score_qualifies():
                    self._set_state(State.HIGHSCORE_ENTRY)
                else:
                    self._clear_play_session()
                    self._set_state(State.MAIN_MENU)
            case (
                State.HIGHSCORE_ENTRY,
                HighscoreConfirmed(name=name, score=score),
            ):
                self.highscore_store.add(name, score)
                self._clear_play_session()
                self._set_state(State.LEADERBOARD)

            case (
                State.INSTRUCTIONS | State.LEADERBOARD | State.OPTIONS,
                Back(),
            ):
                self._set_state(State.MAIN_MENU)

    def _end_game(self, score: int, target: State) -> None:
        """Stash the final score and switch to the end-of-game screen."""
        self.pending_highscore_score = score
        self.highscore_name = ""
        self._set_state(target)

    def _clear_play_session(self) -> None:
        """Drop the engine and any pending end-game state."""
        self.engine = None
        self.pending_highscore_score = None
        self.highscore_name = ""

    def _pending_score_qualifies(self) -> bool:
        """Return True if the last end-game score should be saved."""
        score = self.pending_highscore_score
        if score is None:
            return False
        return self.highscore_store.qualifies(score)
