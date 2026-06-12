"""Tests for gameplay rendering helpers."""

import pygame
import pytest

from graphics import asset_setup
from graphics.animation import Animation
from graphics.assets import AssetManager
from graphics.renderer import (
    GHOST_ANIMATIONS,
    PACMAN_ANIMATION,
    draw_engine,
    maze_pixel_size,
)
from game_engine import (
    BonusFruitSlot,
    EatenItem,
    EdibleType,
    EngineState,
    GameEngine,
)
from parser.validator import GameConfig, LevelConfig

SHEET_PATH = (
    "assets/sprites/"
    "Arcade - Pac-Man - Miscellaneous - All Assets_Palettes.png"
)


def _config() -> GameConfig:
    return GameConfig(
        lives=3,
        pacgum=1,
        seed=42,
        level_max_time=90,
        level=[LevelConfig(width=15, height=15) for _ in range(10)],
    )


def test_draw_engine_replaces_recently_eaten_ghost_with_score(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The eaten ghost is drawn as score text while the sound is active."""
    assets = AssetManager(SHEET_PATH)
    asset_setup.setup(assets)
    engine = GameEngine(_config())
    ghost = next(iter(engine.characters.ghosts.values()))
    engine.last_eaten_item = EatenItem(
        edible_type=EdibleType.GHOST,
        position=ghost.position,
        points=engine.config.points_per_ghost,
        ghost=ghost,
    )
    engine.gameplay_freeze.start(250)
    engine.score_overlay.start(250)

    surface = pygame.Surface(maze_pixel_size(engine.maze))
    pacman_chomp_anim = Animation(assets.get_animation(PACMAN_ANIMATION))
    pacman_death_anim = Animation(assets.get_animation("pacman_death"))
    ghost_anims = [
        Animation(assets.get_animation(name)) for name in GHOST_ANIMATIONS
    ]
    super_pacgum_anim = Animation(assets.get_animation("pacgum_blink"))

    captured: list[tuple[int, tuple[int, int]]] = []
    blit_calls: list[tuple[tuple[int, int], tuple[int, int]]] = []

    def fake_draw_item_score(
        surface: pygame.Surface,
        score: int,
        pixel: tuple[int, int],
        colors: object,
    ) -> None:
        captured.append((score, pixel))

    def fake_blit_at_pixel(
        surface: pygame.Surface,
        sprite: pygame.Surface,
        pixel: tuple[int, int],
    ) -> None:
        blit_calls.append((sprite.get_size(), pixel))

    monkeypatch.setattr(
        "graphics.renderer._draw_item_score",
        fake_draw_item_score,
    )
    monkeypatch.setattr(
        "graphics.renderer._blit_at_pixel",
        fake_blit_at_pixel,
    )
    # Mute static decorations (pacgums, super-pacgums, fruits) so the
    # blit log only records character draws.
    monkeypatch.setattr(
        "graphics.renderer._blit_centred",
        lambda *_args, **_kwargs: None,
    )

    draw_engine(
        surface,
        engine,
        (0, 0),
        assets,
        pacman_chomp_anim,
        pacman_death_anim,
        ghost_anims,
        super_pacgum_anim,
    )

    expected_pixel = (
        ghost.position[0] * 52 + 36,
        ghost.position[1] * 52 + 36,
    )
    assert captured == [(engine.config.points_per_ghost, expected_pixel)]
    assert len(blit_calls) == len(engine.characters.ghosts) - 1


def test_draw_engine_renders_active_bonus_fruit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An active bonus fruit is drawn with the current level sprite."""
    assets = AssetManager(SHEET_PATH)
    asset_setup.setup(assets)
    engine = GameEngine(_config())
    engine.state = EngineState.DYING
    engine.pacgums = set()
    engine.super_pacgums = set()
    engine.bonus_fruit_sprite_name = "bonus_cherry"
    engine.bonus_fruit_slots = [BonusFruitSlot(30, True, (5, 5), 8000)]

    surface = pygame.Surface(maze_pixel_size(engine.maze))
    pacman_chomp_anim = Animation(assets.get_animation(PACMAN_ANIMATION))
    pacman_death_anim = Animation(assets.get_animation("pacman_death"))
    ghost_anims = [
        Animation(assets.get_animation(name)) for name in GHOST_ANIMATIONS
    ]
    super_pacgum_anim = Animation(assets.get_animation("pacgum_blink"))

    seen_sprites: list[str] = []
    original_get_sprite = assets.get_sprite

    def fake_get_sprite(name: str) -> pygame.Surface:
        seen_sprites.append(name)
        return original_get_sprite(name)

    monkeypatch.setattr(assets, "get_sprite", fake_get_sprite)

    draw_engine(
        surface,
        engine,
        (0, 0),
        assets,
        pacman_chomp_anim,
        pacman_death_anim,
        ghost_anims,
        super_pacgum_anim,
    )

    assert "bonus_cherry" in seen_sprites
