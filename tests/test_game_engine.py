"""Tests for the gameplay engine layer."""

import pytest

from characters import Direction, EyesState, FrightenedState, MovingPacmanState
from game_engine import (
    BonusFruitSlot,
    EatenItem,
    EdibleType,
    EngineState,
    GameEngine,
    GameEvent,
    ItemEatenEvent,
)
from parser.validator import GameConfig, LevelConfig

PACMAN_STEP_MS = MovingPacmanState.step_interval_ms


def _config(
    lives: int = 3,
    pacgum: int = 1,
    seed: int = 42,
    level_max_time: int = 90,
    points_per_pacgum: int = 10,
) -> GameConfig:
    """Build a compact valid config for engine tests."""
    return GameConfig(
        lives=lives,
        pacgum=pacgum,
        seed=seed,
        level_max_time=level_max_time,
        points_per_pacgum=points_per_pacgum,
        level=[LevelConfig(width=15, height=15) for _ in range(10)],
    )


def test_engine_builds_first_level_from_config() -> None:
    """The engine owns a maze and characters for level one."""
    engine = GameEngine(_config())

    assert engine.lives == 3
    assert engine.characters.pacman.position == engine.maze.player_spawn


def test_queued_direction_collects_pacgum_and_scores() -> None:
    """Auto-stepping into a pacgum consumes it and scores."""
    engine = GameEngine(_config(points_per_pacgum=15))
    start = engine.characters.pacman.position
    target, wall = engine.maze.reachable_neighbors(start)[0]
    engine.pacgums = {target}
    engine.super_pacgums = set()

    engine.queue_player_direction(Direction.from_wall(wall))
    # 1ms triggers the logical step; PACMAN_STEP_MS advances the sprite.
    engine.update(1)
    engine.update(PACMAN_STEP_MS)

    assert engine.characters.pacman.position == target
    assert engine.score == 15
    assert engine.pacgums == set()
    assert engine.state == EngineState.LEVEL_TRANSITION


def test_blocked_intent_keeps_pacman_in_place() -> None:
    """A queued blocked direction leaves Pac-Man on his cell."""
    engine = GameEngine(_config())
    blocked = [
        direction
        for direction in Direction
        if not engine.maze.can_move(
            engine.characters.pacman.position,
            direction.to_wall(),
        )
    ]
    if not blocked:
        return
    before = engine.characters.pacman.position

    engine.queue_player_direction(blocked[0])
    engine.update(PACMAN_STEP_MS)

    assert engine.characters.pacman.position == before


def test_pacman_idle_until_first_input() -> None:
    """Without any queued direction, Pac-Man does not move on its own."""
    engine = GameEngine(_config())
    before = engine.characters.pacman.position

    engine.update(PACMAN_STEP_MS * 5)

    assert engine.characters.pacman.position == before
    assert not engine.characters.pacman.is_moving


def test_first_input_kicks_step_with_no_perceptible_delay() -> None:
    """An idle Pac-Man steps on the very next update after first input."""
    engine = GameEngine(_config(pacgum=999, points_per_pacgum=1))
    start = engine.characters.pacman.position
    open_dirs = [
        d for d in Direction if engine.maze.can_move(start, d.to_wall())
    ]
    if not open_dirs:
        return

    engine.queue_player_direction(open_dirs[0])
    engine.update(1)  # tiny dt — without the kick, no step would fire

    assert engine.characters.pacman.position != start


def test_subsequent_input_does_not_reset_step_timer() -> None:
    """Direction changes mid-run don't kick the accumulator."""
    engine = GameEngine(_config(pacgum=999, points_per_pacgum=1))
    start = engine.characters.pacman.position
    open_dirs = [
        d for d in Direction if engine.maze.can_move(start, d.to_wall())
    ]
    if not open_dirs:
        return

    engine.queue_player_direction(open_dirs[0])
    engine.update(PACMAN_STEP_MS)
    pacman = engine.characters.pacman
    elapsed_before = pacman._step_elapsed_ms

    # Already moving — second queue should NOT re-kick the accumulator.
    engine.queue_player_direction(open_dirs[0])
    assert pacman._step_elapsed_ms == elapsed_before


def test_intent_persists_across_steps() -> None:
    """A queued direction keeps driving Pac-Man on subsequent steps."""
    engine = GameEngine(_config(pacgum=999, points_per_pacgum=1))
    start = engine.characters.pacman.position
    open_dirs = [
        d for d in Direction if engine.maze.can_move(start, d.to_wall())
    ]
    direction = open_dirs[0]
    engine.queue_player_direction(direction)

    engine.update(PACMAN_STEP_MS)
    after_one = engine.characters.pacman.position
    assert after_one != start

    # No new input — the intent still drives the next step. Pac-Man
    # should at least not regress; if the corridor continues he
    # advances another cell.
    engine.update(PACMAN_STEP_MS)
    assert engine.characters.pacman.is_moving
    assert engine.characters.pacman.intended_direction == direction


def test_timer_expiry_costs_lives_then_game_over() -> None:
    """Running out of time respawns until no life remains."""
    engine = GameEngine(_config(lives=2, level_max_time=1))

    # First timer expiry triggers the death animation; life is
    # consumed immediately but gameplay pauses until the anim ends.
    engine.update(1000)
    assert engine.lives == 1
    assert engine.state == EngineState.DYING

    # Letting the death animation complete respawns and resets timer.
    engine.update(GameEngine.DEATH_ANIM_MS)
    state_after_anim: EngineState = engine.state
    assert state_after_anim == EngineState.PLAYING
    assert engine.lives == 1

    # Second timer expiry: last life lost, game over set.
    engine.update(1000)
    engine.update(GameEngine.DEATH_ANIM_MS)
    assert engine.lives == 0
    final_state: EngineState = engine.state
    assert final_state == EngineState.GAME_OVER


# --- Audio-driving events -----------------------------------------


def test_eating_pacgum_emits_item_event() -> None:
    """Collecting a regular pacgum fires a typed item event."""
    engine = GameEngine(_config(pacgum=2))
    start = engine.characters.pacman.position
    target, wall = engine.maze.reachable_neighbors(start)[0]
    # Keep a second pacgum so the move does not also end the level.
    engine.pacgums = {target, (-1.0, -1.0)}
    engine.super_pacgums = set()

    engine.queue_player_direction(Direction.from_wall(wall))
    engine.update(1)
    engine.update(PACMAN_STEP_MS)

    assert any(
        isinstance(event, ItemEatenEvent)
        and event.item.edible_type == EdibleType.PACGUM
        for event in engine.events
    )


def test_last_pacgum_emits_level_complete() -> None:
    """Clearing the last pacgum fires LEVEL_COMPLETE."""
    engine = GameEngine(_config(pacgum=1))
    start = engine.characters.pacman.position
    target, wall = engine.maze.reachable_neighbors(start)[0]
    engine.pacgums = {target}
    engine.super_pacgums = set()

    engine.queue_player_direction(Direction.from_wall(wall))
    engine.update(1)
    engine.update(PACMAN_STEP_MS)

    assert GameEvent.LEVEL_COMPLETE in engine.events


def test_last_pacgum_on_final_level_wins_without_transition() -> None:
    """Clearing the final configured level goes straight to victory."""
    engine = GameEngine(_config(pacgum=1))
    engine.level_index = len(engine.config.level) - 1
    start = engine.characters.pacman.position
    target, wall = engine.maze.reachable_neighbors(start)[0]
    engine.pacgums = {target}
    engine.super_pacgums = set()

    engine.queue_player_direction(Direction.from_wall(wall))
    engine.update(1)
    engine.update(PACMAN_STEP_MS)

    assert engine.state == EngineState.GAME_WON
    assert GameEvent.LEVEL_COMPLETE not in engine.events


def test_super_pacgum_emits_item_event_and_triggers_frightened() -> None:
    """Picking up a super pacgum fires a typed item event."""
    engine = GameEngine(_config(pacgum=2))
    start = engine.characters.pacman.position
    target, wall = engine.maze.reachable_neighbors(start)[0]
    engine.pacgums = {(-1.0, -1.0)}  # keep level alive
    engine.super_pacgums = {target}

    engine.queue_player_direction(Direction.from_wall(wall))
    engine.update(1)
    engine.update(PACMAN_STEP_MS)

    assert any(
        isinstance(event, ItemEatenEvent)
        and event.item.edible_type == EdibleType.SUPER_PACGUM
        for event in engine.events
    )
    assert engine.super_pacgum_collected


def test_timer_expiry_emits_death_event() -> None:
    """Running out of time fires PAC_DEATH_STARTED."""
    engine = GameEngine(_config(lives=2, level_max_time=1))

    engine.update(1000)

    assert GameEvent.PAC_DEATH_STARTED in engine.events


def test_events_are_cleared_on_each_update() -> None:
    """Events from the previous tick don't bleed into the next one."""
    engine = GameEngine(_config(lives=2, level_max_time=1))
    engine.update(1000)
    assert engine.events  # death fired

    engine.update(GameEngine.DEATH_ANIM_MS)
    # Respawn finishes silently — no audio cue expected this tick.
    assert engine.events == []


def test_eating_ghost_records_temporary_score_marker() -> None:
    """The engine remembers which ghost should show the score overlay."""
    engine = GameEngine(_config())
    ghosts = list(engine.characters.ghosts.values())
    ghosts[0].state = FrightenedState()
    ghosts[1].state = FrightenedState()

    engine._eat_ghost(ghosts[0])
    engine._eat_ghost(ghosts[1])

    assert engine.last_eaten_item is not None
    assert engine.last_eaten_item.ghost is ghosts[1]
    assert engine.last_eaten_item.points == engine.config.points_per_ghost * 2
    assert engine.score == engine.config.points_per_ghost * 3


def test_frightened_ghost_is_collected_by_unified_edible_pass() -> None:
    """Frightened ghosts join the same edible collision list as items."""
    engine = GameEngine(_config())
    pacman = engine.characters.pacman
    ghost = next(iter(engine.characters.ghosts.values()))
    pacman.position = (5, 5)
    pacman.previous_position = (5, 5)
    ghost.position = (5, 5)
    ghost.previous_position = (5, 5)
    ghost.state = FrightenedState()

    engine._collect_edibles()

    assert isinstance(ghost.state, EyesState)
    assert any(
        isinstance(event, ItemEatenEvent)
        and event.item.edible_type == EdibleType.GHOST
        and event.item.ghost is ghost
        for event in engine.events
    )


def test_bonus_fruit_spawns_and_scores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Crossing the first threshold spawns and awards the level fruit."""
    engine = GameEngine(_config())
    target = engine.characters.pacman.position
    pacman = engine.characters.pacman
    pacman.position = target
    pacman.previous_position = target
    engine.pacgums = {target, (-1.0, -1.0)}
    engine.super_pacgums = set()
    engine.collectibles_total = 10
    engine.collectibles_eaten = 3
    engine.bonus_fruit_slots = [BonusFruitSlot(30), BonusFruitSlot(70)]
    engine.bonus_fruit_sprite_name = "bonus_cherry"
    engine.bonus_fruit_points = 100
    monkeypatch.setattr(engine, "_choose_bonus_fruit_position", lambda: (5, 5))

    engine._collect_edibles()

    slot = engine.bonus_fruit_slots[0]
    assert slot.spawned
    assert slot.position == (5, 5)
    assert slot.remaining_ms == engine.BONUS_FRUIT_DURATION_MS
    assert slot.points == engine.bonus_fruit_points

    pacman.position = (5, 5)
    pacman.previous_position = (5, 5)
    engine._collect_edibles()

    assert slot.position is None
    assert any(
        isinstance(event, ItemEatenEvent)
        and event.item.edible_type == EdibleType.BONUS_FRUIT
        for event in engine.events
    )
    assert engine.score == engine.config.points_per_pacgum + 100
    assert engine.collected_fruits_in_level == ["bonus_cherry"]


def test_extra_life_is_awarded_every_ten_thousand_points() -> None:
    """Score milestones grant extra lives in 10k increments."""
    engine = GameEngine(_config())
    engine.score = 9900
    engine.next_extra_life_score = 10000
    lives_before = engine.lives

    engine._add_score(200)

    assert engine.score == 10100
    assert engine.lives == lives_before + 1
    assert GameEvent.EXTRA_LIFE_EARNED in engine.events


def test_super_pacgum_resets_ghost_streak() -> None:
    """Eating a new super pacgum restarts the ghost combo."""
    engine = GameEngine(_config())
    target = engine.maze.super_pacgums[0]
    pacman = engine.characters.pacman
    pacman.position = target
    pacman.previous_position = target
    engine.pacgums = set()
    engine.super_pacgums = {target}
    engine.ghost_eat_streak = 3

    engine._collect_edibles()

    assert engine.super_pacgum_collected
    assert engine.ghost_eat_streak == 0


def test_bonus_fruit_sprite_falls_back_to_key_after_level_eight() -> None:
    """The level fruit becomes the key from level nine onward."""
    engine = GameEngine(_config())

    engine._load_level(7)
    assert engine.bonus_fruit_sprite_name == "bonus_key"

    engine._load_level(9)
    assert engine.bonus_fruit_sprite_name == "bonus_key"


def test_unified_item_eaten_event() -> None:
    """All item collections emit the unified payload event."""
    engine = GameEngine(_config())
    pacman = engine.characters.pacman

    # Test pacgum collection
    target = next(iter(engine.pacgums))
    pacman.position = target
    pacman.previous_position = target
    engine._collect_edibles()

    item_events = [
        event for event in engine.events if isinstance(event, ItemEatenEvent)
    ]
    assert len(item_events) == 1
    assert engine.last_eaten_item is not None
    assert engine.last_eaten_item.edible_type == EdibleType.PACGUM
    assert engine.last_eaten_item.position == target
    assert item_events[0].item is engine.last_eaten_item


def test_ghost_freeze_on_collection() -> None:
    """Only eating ghosts freezes the game; display works independently."""
    engine = GameEngine(_config())
    ghost = next(iter(engine.characters.ghosts.values()))
    ghost.state = FrightenedState()
    engine._eat_ghost(ghost)

    # Update should freeze and not advance gameplay
    engine.update(50)
    assert (
        engine.gameplay_freeze.remaining_ms
        == engine.ghost_eat_freeze_duration_ms - 50
    )
    assert (
        engine.score_overlay.remaining_ms
        == engine.ghost_score_overlay_duration_ms - 50
    )
    assert engine.last_eaten_item is not None


def test_engine_uses_configured_sound_durations_for_timers() -> None:
    """Runtime timers are owned by the engine but configured from audio."""
    engine = GameEngine(_config())
    engine.configure_durations(
        death_ms=333,
        level_transition_ms=444,
        ghost_eat_ms=555,
        fruit_eat_ms=666,
    )

    ghost = next(iter(engine.characters.ghosts.values()))
    ghost.state = FrightenedState()
    engine._eat_ghost(ghost)
    assert engine.gameplay_freeze.remaining_ms == 555
    assert engine.score_overlay.remaining_ms == 555

    engine.score_overlay.stop()
    engine.bonus_fruit_slots = [BonusFruitSlot(30, True, (5, 5), 8000, 100)]
    pacman = engine.characters.pacman
    pacman.position = (5, 5)
    pacman.previous_position = (5, 5)
    engine._collect_edibles()
    assert engine.score_overlay.remaining_ms == 666

    engine._lose_life()
    assert engine.death_hold.remaining_ms == 333

    engine._start_level_transition()
    assert engine.level_transition_hold.remaining_ms == 444


def test_fruit_no_freeze_on_collection() -> None:
    """Eating bonus fruits displays score but doesn't freeze the game."""
    engine = GameEngine(_config())
    pacman = engine.characters.pacman
    target = engine.characters.pacman.position
    pacman.position = target
    pacman.previous_position = target
    engine.collectibles_eaten = 7
    engine.collectibles_total = 10
    engine.bonus_fruit_points = 100
    engine.bonus_fruit_slots = [BonusFruitSlot(30, True, (5, 5), 8000, 100)]

    engine.score_overlay.stop()

    pacman.position = (5, 5)
    pacman.previous_position = (5, 5)
    engine._collect_edibles()

    # Item eaten with no game freeze
    assert engine.last_eaten_item is not None
    assert engine.last_eaten_item.edible_type == EdibleType.BONUS_FRUIT
    assert not engine.gameplay_freeze.active
    assert (
        engine.score_overlay.remaining_ms
        == engine.bonus_fruit_score_overlay_duration_ms
    )
    assert any(
        isinstance(event, ItemEatenEvent)
        and event.item.edible_type == EdibleType.BONUS_FRUIT
        for event in engine.events
    )


def test_item_overlay_display_independent() -> None:
    """Item overlay display duration counts down independently."""
    engine = GameEngine(_config())

    engine.last_eaten_item = EatenItem(
        edible_type=EdibleType.BONUS_FRUIT,
        position=(5, 5),
        points=200,
        ghost=None,
    )
    engine.score_overlay.start(100)

    # Update without freeze (fruit only has display)
    engine.update(50)

    # Display timer counts down, game continues
    assert engine.score_overlay.remaining_ms == 50
    assert engine.last_eaten_item is not None
    assert not engine.gameplay_freeze.active

    # Display expires
    engine.update(50)
    assert not engine.score_overlay.active
    assert engine.last_eaten_item is None
