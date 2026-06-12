"""Runtime game state and rules for one Pac-Man play session."""

import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto

from characters import (
    BoostedPacmanState,
    Character,
    CharacterManager,
    ChaseState,
    Direction,
    EyesState,
    FrightenedState,
    Ghost,
    MovingPacmanState,
)
from characters.step_context import StepContext
from maze import Maze, MazeError, Position
from parser.validator import GameConfig

logger = logging.getLogger(__name__)


class EdibleType(Enum):
    """Type of edible item in the game."""

    PACGUM = auto()
    SUPER_PACGUM = auto()
    BONUS_FRUIT = auto()
    GHOST = auto()


@dataclass
class EatenItem:
    """Information about an eaten item for display and audio cues.

    Attributes:
        edible_type: Type of the eaten item.
        position: Position where the item was eaten.
        points: Points awarded for eating.
        ghost: The ghost object (only for GHOST type).
    """

    edible_type: EdibleType
    position: Position
    points: int
    ghost: Ghost | None = None


@dataclass(frozen=True)
class ItemEatenEvent:
    """One-frame event emitted whenever Pac-Man eats an item."""

    item: EatenItem


class GameEvent(Enum):
    """Discrete one-frame gameplay events used to drive audio cues.

    The engine appends events to :attr:`GameEngine.events` during
    :meth:`GameEngine.update`; the list is cleared at the start of
    the next update so consumers (App audio dispatch, tests) read
    exactly the events of the latest tick.
    """

    EXTRA_LIFE_EARNED = auto()
    PAC_DEATH_STARTED = auto()
    LEVEL_COMPLETE = auto()


class EngineState(Enum):
    """The high-level state of the game engine."""

    STARTING = auto()
    PLAYING = auto()
    DYING = auto()
    LEVEL_TRANSITION = auto()
    GAME_OVER = auto()
    GAME_WON = auto()


@dataclass
class Cheats:
    """Active debug toggles. Read-only from outside the engine.

    Action methods on :class:`GameEngine` (``toggle_invincibility``,
    ``toggle_ghost_freeze``, ``toggle_timer_freeze``, ``gain_life``,
    ``speed_up_pacman``, ``slow_down_pacman``, ``toggle_noclip``,
    ``clear_pacgums``) own the mutations.
    """

    invincibility: bool = False
    ghost_freeze: bool = False
    timer_freeze: bool = False


class MusicCue(Enum):
    """Hint for which background loop should play.

    The engine publishes a cue every frame from gameplay state;
    callers map each cue to a concrete audio asset. The engine has
    no opinion about which ``.wav`` file is appropriate.
    """

    NONE = auto()
    GHOST_RETURN = auto()
    FRIGHT = auto()
    SIREN = auto()


@dataclass
class Timer:
    """Millisecond countdown helper.

    Encapsulates the engine's ``if x_ms > 0: x_ms = max(0, x_ms - dt)``
    pattern so timed states (intro, death, level transition, freezes,
    super-pacgum window, score overlay) all share one tested helper.
    """

    remaining_ms: int = 0

    @property
    def active(self) -> bool:
        """Whether the timer is still counting down."""
        return self.remaining_ms > 0

    def start(self, duration_ms: int) -> None:
        """(Re)start the timer with ``duration_ms`` remaining."""
        self.remaining_ms = duration_ms

    def extend(self, duration_ms: int) -> None:
        """Add ``duration_ms`` to the current remaining time."""
        if self.active:
            self.remaining_ms += duration_ms
        else:
            self.remaining_ms = duration_ms

    def stop(self) -> None:
        """Force the timer to inactive."""
        self.remaining_ms = 0

    def tick(self, dt_ms: int) -> bool:
        """Decrement by ``dt_ms``. Return True if this tick reached 0."""
        if self.remaining_ms <= 0:
            return False
        self.remaining_ms = max(0, self.remaining_ms - dt_ms)
        return self.remaining_ms == 0


class Edible(ABC):
    """Item that Pac-Man can eat during the unified collision pass."""

    @property
    @abstractmethod
    def edible_type(self) -> EdibleType:
        """Public type emitted in the item-eaten event."""

    @property
    @abstractmethod
    def position(self) -> Position:
        """Position recorded if the item is eaten."""

    def collision_position(self, engine: "GameEngine") -> tuple[float, float]:
        """Position used to test collision with Pac-Man."""
        return self.position

    @abstractmethod
    def collision_threshold(self, engine: "GameEngine") -> float:
        """Distance below which Pac-Man eats this item."""

    @abstractmethod
    def eat(self, engine: "GameEngine") -> EatenItem | None:
        """Apply gameplay effects and return the eaten-item payload."""


@dataclass(frozen=True)
class Pacgum(Edible):
    """Regular pacgum edible item."""

    item_position: Position

    @property
    def edible_type(self) -> EdibleType:
        """Return the public edible type."""
        return EdibleType.PACGUM

    @property
    def position(self) -> Position:
        """Return the pacgum position."""
        return self.item_position

    def collision_threshold(self, engine: "GameEngine") -> float:
        """Return the pacgum collection threshold."""
        return engine.PACGUM_COLLECT_THRESHOLD

    def eat(self, engine: "GameEngine") -> EatenItem | None:
        """Remove the pacgum, score it and return the event payload."""
        if self.position not in engine.pacgums:
            return None
        engine.pacgums.remove(self.position)
        points = engine.config.points_per_pacgum
        engine.collectibles_eaten += 1
        engine._add_score(points)
        engine.score_overlay.stop()
        return EatenItem(self.edible_type, self.position, points)


@dataclass(frozen=True)
class SuperPacgum(Edible):
    """Power pacgum edible item."""

    item_position: Position

    @property
    def edible_type(self) -> EdibleType:
        """Return the public edible type."""
        return EdibleType.SUPER_PACGUM

    @property
    def position(self) -> Position:
        """Return the super-pacgum position."""
        return self.item_position

    def collision_threshold(self, engine: "GameEngine") -> float:
        """Return the super-pacgum collection threshold."""
        return engine.PACGUM_COLLECT_THRESHOLD

    def eat(self, engine: "GameEngine") -> EatenItem | None:
        """Remove the super-pacgum, score it and activate its effect."""
        if self.position not in engine.super_pacgums:
            return None
        engine.super_pacgums.remove(self.position)
        points = engine.config.points_per_super_pacgum
        engine.collectibles_eaten += 1
        engine._add_score(points)
        engine.score_overlay.stop()
        engine._activate_super_pacgum()
        return EatenItem(self.edible_type, self.position, points)


@dataclass(frozen=True)
class BonusFruit(Edible):
    """Active bonus fruit backed by a timed slot."""

    slot: "BonusFruitSlot"

    @property
    def edible_type(self) -> EdibleType:
        """Return the public edible type."""
        return EdibleType.BONUS_FRUIT

    @property
    def position(self) -> Position:
        """Return the current fruit position."""
        if self.slot.position is None:
            raise ValueError("bonus fruit edible has no position")
        return self.slot.position

    def collision_threshold(self, engine: "GameEngine") -> float:
        """Return the bonus-fruit collection threshold."""
        return engine.BONUS_FRUIT_COLLECT_THRESHOLD

    def eat(self, engine: "GameEngine") -> EatenItem | None:
        """Remove the fruit, score it and return the event payload."""
        if self.slot.position is None:
            return None
        position = self.slot.position
        points = self.slot.points
        self.slot.position = None
        self.slot.remaining_ms = 0
        engine._add_score(points)
        engine.score_overlay.start(
            engine.bonus_fruit_score_overlay_duration_ms
        )
        engine.collected_fruits_in_level.append(
            engine.bonus_fruit_sprite_name
        )
        return EatenItem(self.edible_type, position, points)


@dataclass(frozen=True)
class FrightenedGhost(Edible):
    """Edible view of a ghost while it is frightened."""

    ghost: Ghost

    @property
    def edible_type(self) -> EdibleType:
        """Return the public edible type."""
        return EdibleType.GHOST

    @property
    def position(self) -> Position:
        """Return the ghost's current cell position."""
        col, row = self.ghost.position
        return (col, row)

    def collision_position(
        self, engine: "GameEngine"
    ) -> tuple[float, float]:
        """Return the ghost's interpolated visual position."""
        return engine._visual_position(self.ghost, self.ghost.step_progress())

    def collision_threshold(self, engine: "GameEngine") -> float:
        """Return the ghost-eating collision threshold."""
        return engine.COLLISION_THRESHOLD

    def eat(self, engine: "GameEngine") -> EatenItem | None:
        """Turn the ghost into eyes, score it and return the payload."""
        if not isinstance(self.ghost.state, FrightenedState):
            return None
        self.ghost.state = EyesState()
        engine.ghost_eat_streak += 1
        points = engine.config.points_per_ghost * (
            2 ** (engine.ghost_eat_streak - 1)
        )
        engine._add_score(points)
        engine.gameplay_freeze.start(engine.ghost_eat_freeze_duration_ms)
        engine.score_overlay.start(engine.ghost_score_overlay_duration_ms)
        return EatenItem(self.edible_type, self.position, points, self.ghost)


@dataclass
class BonusFruitSlot:
    """Timed bonus-fruit slot for one level threshold.

    Attributes:
        threshold_percent: Percentage of collectibles before spawning.
        spawned: Whether this slot has been triggered.
        position: Current position or None if not spawned/collected.
        remaining_ms: Time left before fruit expires (0 = expired).
        points: Score awarded when collected.
    """

    threshold_percent: int
    spawned: bool = False
    position: Position | None = None
    remaining_ms: int = 0
    points: int = 0


class GameEngine:
    """Owns gameplay state independently from rendering and UI.

    The engine keeps positions, score, lives, timers, collectibles
    and the :class:`EngineState` machine. It does not draw anything
    and does not read Pygame events directly; callers translate
    input into method calls such as :meth:`queue_player_direction`
    and read public state (``state``, ``score``, ``music_cue``,
    ``events``) once per frame.
    """

    DEATH_ANIM_MS = 1200
    DEATH_HOLD_MS = DEATH_ANIM_MS
    LEVEL_TRANSITION_HOLD_MS = 4200
    SUPER_PACGUM_DURATION = 5000
    BONUS_FRUIT_DURATION_MS = 8000
    BONUS_FRUIT_SCORE_OVERLAY_MS = 800
    BONUS_FRUIT_COLLECT_THRESHOLD = 0.45
    BONUS_FRUIT_THRESHOLDS = (30, 70)
    BONUS_FRUIT_SPRITES = (
        "bonus_cherry",
        "bonus_strawberry",
        "bonus_orange",
        "bonus_apple",
        "bonus_melon",
        "bonus_galaxian",
        "bonus_bell",
        "bonus_key",
    )
    BONUS_FRUIT_POINTS = (100, 300, 500, 700, 1000, 2000, 3000, 5000)
    EXTRA_LIFE_SCORE_STEP = 10000
    PACMAN_SPEED_STEP = 0.25
    PACMAN_SPEED_MIN = 0.5
    PACMAN_SPEED_MAX = 2.0
    # Distance in cell units below which Pac-Man and a ghost count as
    # touching. Sprites are 16 px in 32 px cells so they overlap when
    # their centres are within roughly half a cell of each other.
    COLLISION_THRESHOLD = 0.5
    PACGUM_COLLECT_THRESHOLD = 0.4
    GHOST_EAT_FREEZE_MS = 600
    GHOST_SCORE_OVERLAY_MS = GHOST_EAT_FREEZE_MS

    def __init__(self, config: GameConfig) -> None:
        """Create a play session from validated game configuration."""
        self.config = config
        self._rng = random.Random(self.config.seed)
        self.level_index = 0
        self.score = 0
        self.lives = config.lives
        self.state: EngineState = EngineState.PLAYING
        self.intro_hold = Timer()
        self.death_hold = Timer()
        self.level_transition_hold = Timer()
        self.gameplay_freeze = Timer()
        self.score_overlay = Timer()
        self.super_pacgum_timer = Timer()
        self.cheats = Cheats()
        self.events: list[GameEvent | ItemEatenEvent] = []
        self.next_extra_life_score = self.EXTRA_LIFE_SCORE_STEP
        self.death_hold_duration_ms = self.DEATH_HOLD_MS
        self.level_transition_duration_ms = self.LEVEL_TRANSITION_HOLD_MS
        self.ghost_eat_freeze_duration_ms = self.GHOST_EAT_FREEZE_MS
        self.ghost_score_overlay_duration_ms = self.GHOST_SCORE_OVERLAY_MS
        self.bonus_fruit_score_overlay_duration_ms = (
            self.BONUS_FRUIT_SCORE_OVERLAY_MS
        )
        self.reset()
        self._load_level(self.level_index)

    def configure_durations(
        self,
        *,
        death_ms: int | None = None,
        level_transition_ms: int | None = None,
        ghost_eat_ms: int | None = None,
        fruit_eat_ms: int | None = None,
    ) -> None:
        """Override gameplay duration knobs.

        Each argument left as ``None`` keeps the engine default. The
        caller decides where the durations come from — the engine
        does not know or care.
        """
        if death_ms is not None:
            self.death_hold_duration_ms = death_ms
        if level_transition_ms is not None:
            self.level_transition_duration_ms = level_transition_ms
        if ghost_eat_ms is not None:
            self.ghost_eat_freeze_duration_ms = ghost_eat_ms
            self.ghost_score_overlay_duration_ms = ghost_eat_ms
        if fruit_eat_ms is not None:
            self.bonus_fruit_score_overlay_duration_ms = fruit_eat_ms

    def _transition_to(self, new_state: EngineState) -> None:
        """Move the engine to a new high-level state.

        Centralising state writes keeps the lifecycle searchable and
        gives a single place to hook future logging or invariants.
        """
        self.state = new_state

    def start_intro(self, duration_ms: int) -> None:
        """Freeze gameplay until the start-of-game intro finishes.

        Lets the caller play the ``start.wav`` jingle while keeping
        Pac-Man and the ghosts frozen on the spawn screen. The next
        ``update()`` ticks the hold down and transitions to
        :attr:`EngineState.PLAYING` once it expires.
        """
        self._transition_to(EngineState.STARTING)
        self.intro_hold.start(duration_ms)

    # -- Cheats ------------------------------------------------------

    def toggle_invincibility(self) -> None:
        """Flip the invincibility cheat flag."""
        self.cheats.invincibility = not self.cheats.invincibility

    def toggle_ghost_freeze(self) -> None:
        """Flip the ghost-freeze cheat flag."""
        self.cheats.ghost_freeze = not self.cheats.ghost_freeze

    def toggle_timer_freeze(self) -> None:
        """Flip the level-timer freeze cheat flag."""
        self.cheats.timer_freeze = not self.cheats.timer_freeze

    def toggle_noclip(self) -> None:
        """Flip Pac-Man's wall-pass cheat."""
        pacman = self.characters.pacman
        pacman.noclip = not pacman.noclip

    def gain_life(self) -> None:
        """Cheat: award one extra life."""
        self.lives += 1

    def speed_up_pacman(self) -> None:
        """Cheat: bump Pac-Man's speed multiplier by one notch up."""
        self._adjust_pacman_speed(self.PACMAN_SPEED_STEP)

    def slow_down_pacman(self) -> None:
        """Cheat: bump Pac-Man's speed multiplier by one notch down."""
        self._adjust_pacman_speed(-self.PACMAN_SPEED_STEP)

    def _adjust_pacman_speed(self, delta: float) -> None:
        """Nudge Pac-Man's speed multiplier, clamped to a safe range.

        Positive deltas speed Pac-Man up, negative slow him down. The
        multiplier is rounded to the nearest :attr:`PACMAN_SPEED_STEP`
        so repeated +/- presses stay on a clean grid (floating-point
        drift can otherwise push 1.00 to 0.9999…).
        """
        pacman = self.characters.pacman
        new_multiplier = pacman.speed_multiplier + delta
        new_multiplier = max(
            self.PACMAN_SPEED_MIN,
            min(self.PACMAN_SPEED_MAX, new_multiplier),
        )
        snapped = round(new_multiplier / self.PACMAN_SPEED_STEP)
        pacman.speed_multiplier = snapped * self.PACMAN_SPEED_STEP

    # ----------------------------------------------------------------

    @property
    def music_cue(self) -> MusicCue:
        """Background music hint reflecting the current gameplay phase.

        Returns :attr:`MusicCue.NONE` outside of active play (intro,
        death, transition, end). During play, ghosts returning home
        take priority, then the super-pacgum window, then the
        regular siren.
        """
        if self.state != EngineState.PLAYING:
            return MusicCue.NONE
        for ghost in self.characters.ghosts.values():
            if isinstance(ghost.state, EyesState):
                return MusicCue.GHOST_RETURN
        if self.super_pacgum_collected:
            return MusicCue.FRIGHT
        return MusicCue.SIREN

    def reset(self) -> None:
        """Reset transient state flags and timers for the current level."""
        self.death_hold.stop()
        self.level_transition_hold.stop()
        self.gameplay_freeze.stop()
        self.score_overlay.stop()
        self.last_eaten_item: EatenItem | None = None
        self.ghost_eat_streak: int = 0
        self.super_pacgum_timer.stop()
        self.super_pacgum_collected = False

    def _load_level(self, level_index: int) -> None:
        """Build maze, characters and collectibles for ``level_index``.

        Character-level cheat state (Pac-Man's ``noclip`` and
        ``speed_multiplier``) is preserved across the rebuild so the
        cheats are consistent with the engine-level :class:`Cheats`
        flags, which survive level transitions naturally because the
        engine itself is not recreated.
        """
        level = self.config.level[level_index]
        self.level_config = level
        seed_for_level = self.config.seed if level_index == 0 else None
        try:
            self.maze = Maze(
                width=level.width,
                height=level.height,
                seed=seed_for_level,
                pacgum_count=self.config.pacgum,
            )
        except MazeError as exc:
            logger.error(
                "Failed to generate maze for level %d: %s", level_index, exc
            )
            self._transition_to(EngineState.GAME_OVER)
            return
        prev: CharacterManager | None = getattr(self, "characters", None)
        carry_noclip = prev.pacman.noclip if prev is not None else False
        carry_speed = (
            prev.pacman.speed_multiplier if prev is not None else 1.0
        )
        self.characters = CharacterManager(self.maze)
        self.characters.pacman.noclip = carry_noclip
        self.characters.pacman.speed_multiplier = carry_speed
        self.pacgums: set[Position] = set(self.maze.pacgums)
        self.super_pacgums: set[Position] = set(self.maze.super_pacgums)
        fruit_index = min(
            level_index,
            len(self.BONUS_FRUIT_SPRITES) - 1,
        )
        self.bonus_fruit_sprite_name = self.BONUS_FRUIT_SPRITES[fruit_index]
        self.bonus_fruit_points = self.BONUS_FRUIT_POINTS[fruit_index]
        self.bonus_fruit_slots = [
            BonusFruitSlot(threshold_percent=threshold)
            for threshold in self.BONUS_FRUIT_THRESHOLDS
        ]
        self.collected_fruits_in_level: list[str] = []
        self.collectibles_total = len(self.pacgums) + len(self.super_pacgums)
        self.collectibles_eaten = 0
        self.remaining_time_ms = self.config.level_max_time * 1000
        self.reset()

    def update(self, dt_ms: int) -> None:
        """Advance timers, characters and collisions for one frame."""
        self.events.clear()
        if self.state == EngineState.STARTING:
            self._tick_intro(dt_ms)
            return
        if self.gameplay_freeze.active:
            self.gameplay_freeze.tick(dt_ms)
            self._tick_score_overlay(dt_ms)
            return
        if self.state == EngineState.LEVEL_TRANSITION:
            self._tick_level_transition(dt_ms)
            return
        if self.state == EngineState.DYING:
            self._tick_death(dt_ms)
            return
        if self.state in (EngineState.GAME_OVER, EngineState.GAME_WON):
            return
        if not self.cheats.timer_freeze:
            self.remaining_time_ms = max(0, self.remaining_time_ms - dt_ms)
            if self.remaining_time_ms == 0:
                self._lose_life()
                return
        self._tick_super_pacgum_timer(dt_ms)
        self._tick_bonus_fruits(dt_ms)
        self._tick_score_overlay(dt_ms)
        self.characters.step_all(dt_ms, self._step_context())
        if self._collect_edibles():
            if self._is_last_level():
                self._transition_to(EngineState.GAME_WON)
            else:
                self._start_level_transition()
            return
        self._check_dangerous_ghost_collision()

    def _step_context(self) -> StepContext:
        """Build the per-frame context handed to character steps."""
        return StepContext(
            maze=self.maze,
            super_pacgum_collected=self.super_pacgum_collected,
            manager=self.characters,
            ghost_freeze=self.cheats.ghost_freeze,
        )

    def queue_player_direction(self, direction: Direction) -> None:
        """Set Pac-Man's intended direction.

        Doesn't move Pac-Man directly — the next :meth:`update` will
        try the intended direction at the next Pac-Man step interval,
        falling back to the current direction if the intended one is
        blocked.

        First input from idle "kicks" Pac-Man's step accumulator so
        the very next update triggers a step instead of forcing the
        player to wait a full interval to unfreeze. Subsequent
        direction changes (already moving) don't reset the timer —
        they just buffer the new intent.
        """
        if self.state not in (EngineState.PLAYING, EngineState.STARTING):
            return
        pacman = self.characters.pacman
        direction_changed = direction != pacman.intended_direction

        # Pac-Man is physically stuck (his last movement failed)
        is_stuck = pacman.position == pacman.previous_position

        # Detects a U-turn: the target cell is the one we came from
        target = self.maze.neighbor(pacman.position, direction.to_wall())
        is_u_turn = not is_stuck and target == pacman.previous_position

        pacman.queue_direction(direction)

        if not pacman.is_moving or (direction_changed and is_stuck):
            # avoid waiting for the next step if we're starting to move,
            # or if we changed direction while stuck
            pacman._step_elapsed_ms = pacman.step_interval_ms
        elif direction_changed and is_u_turn:
            # U-turn : target and previous positions swap, time is reversed
            prev = pacman.previous_position
            pacman.previous_position = pacman.position
            pacman.position = prev
            pacman.direction = direction
            pacman._step_elapsed_ms = max(
                0, pacman.step_interval_ms - pacman._step_elapsed_ms
            )

    def _tick_intro(self, dt_ms: int) -> None:
        """Count down the intro hold and start gameplay when it expires."""
        self.intro_hold.tick(dt_ms)
        if self.intro_hold.active:
            return
        self._transition_to(EngineState.PLAYING)

    def _tick_death(self, dt_ms: int) -> None:
        """Respawn once the death SFX hold time has elapsed.

        The visible death animation is driven by the renderer; this
        method only counts down the death hold and respawns the
        moment it hits zero.
        """
        self.death_hold.tick(dt_ms)
        if self.death_hold.active:
            return
        if self.lives <= 0:
            self._transition_to(EngineState.GAME_OVER)
            return
        self._transition_to(EngineState.PLAYING)
        self.characters.reset_positions()
        for ghost in self.characters.ghosts.values():
            ghost.state = ChaseState()
            ghost._step_elapsed_ms = 0
        self.remaining_time_ms = self.config.level_max_time * 1000
        self.super_pacgum_timer.stop()
        self.super_pacgum_collected = False

    def _tick_super_pacgum_timer(self, dt_ms: int) -> None:
        """Advance the super pacgum timer and trigger transitions on expiry."""
        if not self.super_pacgum_timer.active:
            # Edge: super pacgum window just ended this frame (the
            # ``super_pacgum_collected`` guard makes this idempotent
            # on subsequent frames).
            if self.super_pacgum_collected:
                self.super_pacgum_collected = False
                pacman = self.characters.pacman
                if isinstance(pacman.state, BoostedPacmanState):
                    pacman.state = MovingPacmanState()
                for ghost in self.characters.ghosts.values():
                    if isinstance(ghost.state, FrightenedState):
                        ghost.state = ChaseState()
            return
        self.super_pacgum_timer.tick(dt_ms)

    def _tick_bonus_fruits(self, dt_ms: int) -> None:
        """Advance active bonus-fruit timers and hide expired fruits."""
        for slot in self.bonus_fruit_slots:
            if slot.position is None:
                continue
            slot.remaining_ms = max(0, slot.remaining_ms - dt_ms)
            if slot.remaining_ms == 0:
                slot.position = None

    def _tick_score_overlay(self, dt_ms: int) -> None:
        """Advance eaten-item score overlay lifetime."""
        if self.score_overlay.tick(dt_ms):
            self.last_eaten_item = None

    def _add_score(self, points: int) -> None:
        """Add score and award extra lives every 10,000 points."""
        self.score += points
        while self.score >= self.next_extra_life_score:
            self.lives += 1
            self.next_extra_life_score += self.EXTRA_LIFE_SCORE_STEP
            self.events.append(GameEvent.EXTRA_LIFE_EARNED)

    def _tick_level_transition(self, dt_ms: int) -> None:
        """Advance to the next level once the intermission SFX ends.

        Counts down the level transition hold and triggers the level
        switch the moment it reaches zero.
        """
        self.level_transition_hold.tick(dt_ms)
        if self.level_transition_hold.active:
            return
        self._transition_to(EngineState.PLAYING)
        self.start_next_level()

    def _check_dangerous_ghost_collision(self) -> None:
        """Lose a life when Pac-Man and a ghost overlap on screen.

        Compares interpolated sub-cell positions (the same ones the
        renderer uses), so collision matches what the player sees:
        no false positives when sprites are on adjacent cells, and
        no logical-only collisions when Pac-Man has just *committed*
        to a ghost's cell but is still visually on the previous one.
        """
        pacman = self.characters.pacman
        pacman_visual = self._visual_position(pacman, pacman.step_progress())
        threshold_sq = self.COLLISION_THRESHOLD**2
        for ghost in self.characters.ghosts.values():
            if not ghost.state.is_collidable:
                continue
            if isinstance(ghost.state, FrightenedState):
                continue
            ghost_visual = self._visual_position(ghost, ghost.step_progress())
            dx = pacman_visual[0] - ghost_visual[0]
            dy = pacman_visual[1] - ghost_visual[1]
            if dx * dx + dy * dy < threshold_sq:
                if not self.cheats.invincibility:
                    self._lose_life()
                return

    def _eat_ghost(self, ghost: Ghost) -> None:
        """Eat a ghost and add points."""
        self._resolve_eaten_item(FrightenedGhost(ghost))

    @staticmethod
    def _visual_position(
        character: Character,
        progress: float,
    ) -> tuple[float, float]:
        """Sub-cell ``(col, row)`` lerped between previous and current."""
        prev_col, prev_row = character.previous_position
        curr_col, curr_row = character.position
        return (
            prev_col + (curr_col - prev_col) * progress,
            prev_row + (curr_row - prev_row) * progress,
        )

    def start_next_level(self) -> None:
        """Advance to the next level or mark the game as won."""
        if self._is_last_level():
            self._transition_to(EngineState.GAME_WON)
            return
        self.level_index += 1
        self._load_level(self.level_index)

    def _is_last_level(self) -> bool:
        """Return True when the current level is the final configured one."""
        return self.level_index + 1 >= len(self.config.level)

    def _collect_edibles(self) -> bool:
        """Collect every edible item currently overlapping Pac-Man.

        Returns:
            True when the collection emptied the level (all pacgums
            and super-pacgums gone). The caller is responsible for
            transitioning the state machine — this keeps state
            mutations out of the collision pass and lets the type
            checker reason about state across the call.
        """
        pacman = self.characters.pacman
        pacman_visual = self._visual_position(pacman, pacman.step_progress())
        for edible in self._edibles():
            if self._overlaps(
                pacman_visual,
                edible.collision_position(self),
                edible.collision_threshold(self),
            ):
                self._resolve_eaten_item(edible)

        self._maybe_spawn_bonus_fruits()

        return not self.pacgums and not self.super_pacgums

    def _start_level_transition(self) -> None:
        """Enter the inter-level intermission state and start its hold."""
        self._transition_to(EngineState.LEVEL_TRANSITION)
        self.level_transition_hold.start(self.level_transition_duration_ms)
        self.events.append(GameEvent.LEVEL_COMPLETE)

    def _edibles(self) -> list[Edible]:
        """Build the edible collision list for the current frame."""
        edibles: list[Edible] = []
        for position in sorted(self.pacgums):
            edibles.append(Pacgum(position))
        for position in sorted(self.super_pacgums):
            edibles.append(SuperPacgum(position))
        for slot in self.bonus_fruit_slots:
            if slot.position is None:
                continue
            edibles.append(BonusFruit(slot))
        for ghost in self.characters.ghosts.values():
            if not isinstance(ghost.state, FrightenedState):
                continue
            edibles.append(FrightenedGhost(ghost))
        return edibles

    def _resolve_eaten_item(self, edible: Edible) -> None:
        """Apply gameplay effects for one edible item."""
        eaten_item = edible.eat(self)
        if eaten_item is None:
            return
        self.last_eaten_item = eaten_item
        self.events.append(ItemEatenEvent(eaten_item))

    def _activate_super_pacgum(self) -> None:
        """Start or extend the frightened/boosted item effect."""
        self.super_pacgum_collected = True
        self.ghost_eat_streak = 0
        self.super_pacgum_timer.extend(self.SUPER_PACGUM_DURATION)
        self.characters.pacman.state = BoostedPacmanState()
        for ghost in self.characters.ghosts.values():
            if isinstance(ghost.state, ChaseState):
                ghost.state = FrightenedState()

    @staticmethod
    def _overlaps(
        lhs: tuple[float, float],
        rhs: tuple[float, float],
        threshold: float,
    ) -> bool:
        """Return whether two visual positions overlap enough to collect."""
        dx = lhs[0] - rhs[0]
        dy = lhs[1] - rhs[1]
        return dx * dx + dy * dy < threshold * threshold

    def _maybe_spawn_bonus_fruits(self) -> None:
        """Spawn bonus fruits when progress crosses thresholds."""
        if self.collectibles_total <= 0:
            return
        for slot in self.bonus_fruit_slots:
            if slot.spawned:
                continue
            if (
                self.collectibles_eaten * 100
                <= self.collectibles_total * slot.threshold_percent
            ):
                continue
            position = self._choose_bonus_fruit_position()
            if position is None:
                continue
            slot.spawned = True
            slot.position = position
            slot.remaining_ms = self.BONUS_FRUIT_DURATION_MS
            slot.points = self.bonus_fruit_points

    def _choose_bonus_fruit_position(self) -> Position | None:
        """Pick a random free corridor cell for a bonus fruit."""
        occupied: set[Position] = {self.maze.player_spawn}
        occupied |= {
            ghost.position for ghost in self.characters.ghosts.values()
        }
        occupied |= set(self.pacgums)
        occupied |= set(self.super_pacgums)
        occupied |= {
            slot.position
            for slot in self.bonus_fruit_slots
            if slot.position is not None
        }
        candidates = [
            (cell.col, cell.row)
            for row in self.maze.grid
            for cell in row
            if not cell.is_pattern and (cell.col, cell.row) not in occupied
        ]
        if not candidates:
            return None
        return self._rng.choice(candidates)

    def _lose_life(self) -> None:
        """Consume one life and start the death animation.

        Snaps every character's ``previous_position`` to its current
        position so the renderer freezes them in place during the
        death animation (otherwise they'd keep sliding mid-step).
        """
        self.lives -= 1
        self._transition_to(EngineState.DYING)
        self.death_hold.start(self.death_hold_duration_ms)
        # Snap previous_position so the renderer's lerp freezes each
        # sprite in place. The renderer hides ghosts entirely while
        # the engine is in DYING state, so no state mutation is needed
        # — ghosts keep whatever mode they were in until the post-anim
        # reset in :meth:`_tick_death` flips them all back to Chase.
        for ghost in self.characters.ghosts.values():
            ghost.previous_position = ghost.position
        self.events.append(GameEvent.PAC_DEATH_STARTED)

    def clear_pacgums(self) -> None:
        """Cheat: collect every remaining pacgum at once.

        Awards the equivalent score (regular + super pacgums), bumps
        ``collectibles_eaten`` so the bonus-fruit threshold logic
        stays consistent, then empties the sets. Bonus fruits in
        flight are cancelled (no points — they're a timed reward,
        not a collectible-progress one).
        """
        regular = len(self.pacgums)
        super_count = len(self.super_pacgums)
        self.collectibles_eaten += regular + super_count
        points = (
            regular * self.config.points_per_pacgum
            + super_count * self.config.points_per_super_pacgum
        )
        if points:
            self._add_score(points)
        self.pacgums.clear()
        self.super_pacgums.clear()
        for slot in self.bonus_fruit_slots:
            slot.position = None
            slot.remaining_ms = 0
