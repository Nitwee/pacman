"""Catalogue of sprites, palettes, animations and fonts.

A single :func:`setup` call is invoked from :class:`app.App` once the
:class:`graphics.assets.AssetManager` is built; this module owns every
sprite-coordinate declaration so the rest of the codebase stays free
of magic offsets.

Use :mod:`tools.sprite_picker` to identify rects in the sheet, then
paste them into the appropriate private helper below.
"""

from graphics.assets import (
    AnimationDef,
    AssetManager,
    Font,
    PaletteColors,
)

# Relative position (within a 200x186 palette block) of the three
# colour-reference squares.
COLOR_SAMPLE_POSITIONS: tuple[
    tuple[int, int], tuple[int, int], tuple[int, int]
] = (
    (184, 170),  # primary  — entity body / wall outline
    (184, 145),  # wall_fill — wall interior + 42 logo
    (184, 120),  # secondary — bonuses / ghost eyes
)


def _sample_palette(
    am: AssetManager, offset: tuple[int, int]
) -> PaletteColors:
    """Sample the three theme colours from a palette block.

    Reads one pixel inside each of the three reference squares
    declared in :data:`COLOR_SAMPLE_POSITIONS`, offset to the given
    palette block.

    Args:
        am: The AssetManager (whose ``sheet`` we sample from).
        offset: ``(dx, dy)`` of the palette block in sheet pixels.

    Returns:
        Sampled :class:`PaletteColors`.
    """
    dx, dy = offset
    samples: list[tuple[int, int, int]] = []
    for sx, sy in COLOR_SAMPLE_POSITIONS:
        rgba = am.sheet.get_at((dx + sx, dy + sy))
        samples.append((rgba.r, rgba.g, rgba.b))
    return PaletteColors(
        primary=samples[0],
        wall_fill=samples[1],
        secondary=samples[2],
    )


def _register_palette(
    am: AssetManager, name: str, offset: tuple[int, int]
) -> None:
    """Register a palette and auto-sample its colours from the sheet."""
    am.register_palette(name, offset, colors=_sample_palette(am, offset))


def setup(am: AssetManager) -> None:
    """Register every visual asset of the game on ``am``.

    Args:
        am: The AssetManager instantiated by :class:`app.App`.
    """
    _register_palettes(am)
    _register_pacman(am)
    _register_ghosts(am)
    _register_font(am)
    _register_pacgums(am)


def _register_pacgums(am: AssetManager) -> None:
    """Declare the pacgum and super-pacgum sprites.

    Example::

        am.register_sprite("pacgum", (1, 1, 4, 4))
        am.register_sprite("super_pacgum", (10, 1, 10, 10))
    """
    am.register_sprite("pacgum", (136, 10, 8, 8))
    am.register_sprite("pacgum_half", (136, 19, 8, 8))
    am.register_sprite("super_pacgum", (136, 28, 8, 8))
    am.register_sprite("empty", (19, 64, 8, 8))
    am.register_animation(
        "pacgum_blink",
        AnimationDef(
            frames=("super_pacgum", "pacgum_half", "empty", "pacgum_half"),
            frame_duration_ms=100,
        ),
    )
    am.register_sprite("bonus_cherry", (1, 117, 16, 16))
    am.register_sprite("bonus_strawberry", (18, 117, 16, 16))
    am.register_sprite("bonus_orange", (35, 117, 16, 16))
    am.register_sprite("bonus_apple", (52, 117, 16, 16))
    am.register_sprite("bonus_melon", (69, 117, 16, 16))
    am.register_sprite("bonus_galaxian", (86, 117, 16, 16))
    am.register_sprite("bonus_bell", (103, 117, 16, 16))
    am.register_sprite("bonus_key", (120, 117, 16, 16))


def _register_palettes(am: AssetManager) -> None:
    """Declare palette offsets relative to the default block.

    The ``"default"`` palette at offset ``(0, 0)`` is already seeded
    by :class:`AssetManager` itself.

    Example::

        am.register_palette("halloween", (250, 0))
    """
    _register_palette(am, "red-blue-white", (0, 0))
    _register_palette(am, "pink-blue-white", (200, 0))
    _register_palette(am, "cyan-blue-white", (400, 0))
    _register_palette(am, "orange-blue-white", (600, 0))
    _register_palette(am, "peach-blue-green", (800, 0))
    _register_palette(am, "red-white-green", (0, 186))
    _register_palette(am, "black-blue-white", (200, 186))
    _register_palette(am, "yellow-pink-cyan", (400, 186))
    _register_palette(am, "blue-black-peach", (600, 186))
    _register_palette(am, "white-black-peach", (800, 186))
    _register_palette(am, "red-peach-white", (0, 372))
    _register_palette(am, "peach-blue-white", (200, 372))
    _register_palette(am, "white-brown-red", (400, 372))
    _register_palette(am, "white-green-red", (600, 372))
    _register_palette(am, "brown-green-brown", (800, 372))
    _register_palette(am, "white-green-duck", (0, 558))
    _register_palette(am, "yellow-red-blue", (200, 558))
    _register_palette(am, "white-skyblue-yellow", (400, 558))
    _register_palette(am, "peach-black-white", (600, 558))


def _register_pacman(am: AssetManager) -> None:
    """Declare Pac-Man sprites and the animations that group them.

    Example::

        am.register_sprite("pacman_right_0", (488, 64, 16, 16))
        am.register_sprite("pacman_right_1", (504, 64, 16, 16))
        am.register_animation(
            "pacman_chomp_right",
            AnimationDef(
                frames=("pacman_right_0", "pacman_right_1"),
                frame_duration_ms=80,
            ),
        )
    """
    pacman_palette = "yellow-red-blue"

    am.register_sprite("pacman", (103, 168, 16, 16), palette=pacman_palette)

    am.register_sprite(
        "pacman_right_0", (103, 151, 16, 16), palette=pacman_palette
    )
    am.register_sprite(
        "pacman_right_1", (103, 134, 16, 16), palette=pacman_palette
    )
    am.register_sprite(
        "pacman_down_0", (120, 151, 16, 16), palette=pacman_palette
    )
    am.register_sprite(
        "pacman_down_1", (120, 134, 16, 16), palette=pacman_palette
    )
    am.register_derived_sprite(
        "pacman_left_0", source="pacman_right_0", flip_x=True
    )
    am.register_derived_sprite(
        "pacman_left_1", source="pacman_right_1", flip_x=True
    )
    am.register_derived_sprite(
        "pacman_up_0", source="pacman_down_0", flip_y=True
    )
    am.register_derived_sprite(
        "pacman_up_1", source="pacman_down_1", flip_y=True
    )
    am.register_animation(
        "pacman_chomp_right",
        AnimationDef(
            frames=(
                "pacman_right_0",
                "pacman_right_1",
                "pacman_right_0",
                "pacman",
            ),
            frame_duration_ms=80,
        ),
    )
    am.register_animation(
        "pacman_chomp_down",
        AnimationDef(
            frames=(
                "pacman_down_0",
                "pacman_down_1",
                "pacman_down_0",
                "pacman",
            ),
            frame_duration_ms=80,
        ),
    )
    am.register_animation(
        "pacman_chomp_up",
        AnimationDef(
            frames=("pacman_up_0", "pacman_up_1", "pacman_up_0", "pacman"),
            frame_duration_ms=80,
        ),
    )
    am.register_animation(
        "pacman_chomp_left",
        AnimationDef(
            frames=(
                "pacman_left_0",
                "pacman_left_1",
                "pacman_left_0",
                "pacman",
            ),
            frame_duration_ms=80,
        ),
    )
    am.register_sprite(
        "pacman_death_0", (1, 134, 16, 16), palette=pacman_palette
    )
    am.register_sprite(
        "pacman_death_1", (18, 134, 16, 16), palette=pacman_palette
    )
    am.register_sprite(
        "pacman_death_2", (35, 134, 16, 16), palette=pacman_palette
    )
    am.register_sprite(
        "pacman_death_3", (52, 134, 16, 16), palette=pacman_palette
    )
    am.register_sprite(
        "pacman_death_4", (69, 134, 16, 16), palette=pacman_palette
    )
    am.register_sprite(
        "pacman_death_5", (86, 134, 16, 16), palette=pacman_palette
    )
    am.register_sprite(
        "pacman_death_6", (1, 151, 16, 16), palette=pacman_palette
    )
    am.register_sprite(
        "pacman_death_7", (18, 151, 16, 16), palette=pacman_palette
    )
    am.register_sprite(
        "pacman_death_8", (35, 151, 16, 16), palette=pacman_palette
    )
    am.register_sprite(
        "pacman_death_9", (52, 151, 16, 16), palette=pacman_palette
    )
    am.register_sprite(
        "pacman_death_10", (69, 151, 16, 16), palette=pacman_palette
    )
    am.register_sprite(
        "pacman_death_11", (86, 151, 16, 16), palette=pacman_palette
    )
    am.register_animation(
        "pacman_death",
        AnimationDef(
            frames=(
                "pacman",
                "pacman_death_0",
                "pacman_death_1",
                "pacman_death_2",
                "pacman_death_3",
                "pacman_death_4",
                "pacman_death_5",
                "pacman_death_6",
                "pacman_death_7",
                "pacman_death_8",
                "pacman_death_9",
                "pacman_death_10",
                "pacman_death_11",
            ),
            frame_duration_ms=250,
        ),
    )


def _register_ghosts(am: AssetManager) -> None:
    """Declare ghost sprites and their per-ghost animations.

    Example::

        am.register_sprite("blinky_right_0", (...))
        am.register_animation(
            "blinky_walk_right",
            AnimationDef(
                frames=("blinky_right_0", "blinky_right_1"),
                frame_duration_ms=120,
            ),
        )
    """
    # Blinky (red): pinned to its own palette.
    am.register_sprite(
        "blinky_right_0", (1, 83, 16, 16), palette="red-blue-white"
    )
    am.register_sprite(
        "blinky_right_1", (18, 83, 16, 16), palette="red-blue-white"
    )
    am.register_animation(
        "blinky_walk_right",
        AnimationDef(
            frames=("blinky_right_0", "blinky_right_1"),
            frame_duration_ms=120,
        ),
    )
    am.register_sprite(
        "blinky_down_0", (35, 83, 16, 16), palette="red-blue-white"
    )
    am.register_sprite(
        "blinky_down_1", (52, 83, 16, 16), palette="red-blue-white"
    )
    am.register_animation(
        "blinky_walk_down",
        AnimationDef(
            frames=("blinky_down_0", "blinky_down_1"),
            frame_duration_ms=120,
        ),
    )
    am.register_sprite(
        "blinky_left_0", (69, 83, 16, 16), palette="red-blue-white"
    )
    am.register_sprite(
        "blinky_left_1", (86, 83, 16, 16), palette="red-blue-white"
    )
    am.register_animation(
        "blinky_walk_left",
        AnimationDef(
            frames=("blinky_left_0", "blinky_left_1"),
            frame_duration_ms=120,
        ),
    )
    am.register_sprite(
        "blinky_up_0", (103, 83, 16, 16), palette="red-blue-white"
    )
    am.register_sprite(
        "blinky_up_1", (120, 83, 16, 16), palette="red-blue-white"
    )
    am.register_animation(
        "blinky_walk_up",
        AnimationDef(
            frames=("blinky_up_0", "blinky_up_1"),
            frame_duration_ms=120,
        ),
    )
    # Pinky (pink): pinned to its own palette.
    am.register_sprite(
        "pinky_right_0", (1, 83, 16, 16), palette="pink-blue-white"
    )
    am.register_sprite(
        "pinky_right_1", (18, 83, 16, 16), palette="pink-blue-white"
    )
    am.register_animation(
        "pinky_walk_right",
        AnimationDef(
            frames=("pinky_right_0", "pinky_right_1"),
            frame_duration_ms=120,
        ),
    )
    am.register_sprite(
        "pinky_down_0", (35, 83, 16, 16), palette="pink-blue-white"
    )
    am.register_sprite(
        "pinky_down_1", (52, 83, 16, 16), palette="pink-blue-white"
    )
    am.register_animation(
        "pinky_walk_down",
        AnimationDef(
            frames=("pinky_down_0", "pinky_down_1"),
            frame_duration_ms=120,
        ),
    )
    am.register_sprite(
        "pinky_left_0", (69, 83, 16, 16), palette="pink-blue-white"
    )
    am.register_sprite(
        "pinky_left_1", (86, 83, 16, 16), palette="pink-blue-white"
    )
    am.register_animation(
        "pinky_walk_left",
        AnimationDef(
            frames=("pinky_left_0", "pinky_left_1"),
            frame_duration_ms=120,
        ),
    )
    am.register_sprite(
        "pinky_up_0", (103, 83, 16, 16), palette="pink-blue-white"
    )
    am.register_sprite(
        "pinky_up_1", (120, 83, 16, 16), palette="pink-blue-white"
    )
    am.register_animation(
        "pinky_walk_up",
        AnimationDef(
            frames=("pinky_up_0", "pinky_up_1"),
            frame_duration_ms=120,
        ),
    )
    # Inky (cyan): pinned to its own palette.
    am.register_sprite(
        "inky_right_0", (1, 83, 16, 16), palette="cyan-blue-white"
    )
    am.register_sprite(
        "inky_right_1", (18, 83, 16, 16), palette="cyan-blue-white"
    )
    am.register_animation(
        "inky_walk_right",
        AnimationDef(
            frames=("inky_right_0", "inky_right_1"),
            frame_duration_ms=120,
        ),
    )
    am.register_sprite(
        "inky_down_0", (35, 83, 16, 16), palette="cyan-blue-white"
    )
    am.register_sprite(
        "inky_down_1", (52, 83, 16, 16), palette="cyan-blue-white"
    )
    am.register_animation(
        "inky_walk_down",
        AnimationDef(
            frames=("inky_down_0", "inky_down_1"),
            frame_duration_ms=120,
        ),
    )
    am.register_sprite(
        "inky_left_0", (69, 83, 16, 16), palette="cyan-blue-white"
    )
    am.register_sprite(
        "inky_left_1", (86, 83, 16, 16), palette="cyan-blue-white"
    )
    am.register_animation(
        "inky_walk_left",
        AnimationDef(
            frames=("inky_left_0", "inky_left_1"),
            frame_duration_ms=120,
        ),
    )
    am.register_sprite(
        "inky_up_0", (103, 83, 16, 16), palette="cyan-blue-white"
    )
    am.register_sprite(
        "inky_up_1", (120, 83, 16, 16), palette="cyan-blue-white"
    )
    am.register_animation(
        "inky_walk_up",
        AnimationDef(
            frames=("inky_up_0", "inky_up_1"),
            frame_duration_ms=120,
        ),
    )
    # Clyde (orange): pinned to its own palette.
    am.register_sprite(
        "clyde_right_0", (1, 83, 16, 16), palette="orange-blue-white"
    )
    am.register_sprite(
        "clyde_right_1", (18, 83, 16, 16), palette="orange-blue-white"
    )
    am.register_animation(
        "clyde_walk_right",
        AnimationDef(
            frames=("clyde_right_0", "clyde_right_1"),
            frame_duration_ms=120,
        ),
    )
    am.register_sprite(
        "clyde_down_0", (35, 83, 16, 16), palette="orange-blue-white"
    )
    am.register_sprite(
        "clyde_down_1", (52, 83, 16, 16), palette="orange-blue-white"
    )
    am.register_animation(
        "clyde_walk_down",
        AnimationDef(
            frames=("clyde_down_0", "clyde_down_1"),
            frame_duration_ms=120,
        ),
    )
    am.register_sprite(
        "clyde_left_0", (69, 83, 16, 16), palette="orange-blue-white"
    )
    am.register_sprite(
        "clyde_left_1", (86, 83, 16, 16), palette="orange-blue-white"
    )
    am.register_animation(
        "clyde_walk_left",
        AnimationDef(
            frames=("clyde_left_0", "clyde_left_1"),
            frame_duration_ms=120,
        ),
    )
    am.register_sprite(
        "clyde_up_0", (103, 83, 16, 16), palette="orange-blue-white"
    )
    am.register_sprite(
        "clyde_up_1", (120, 83, 16, 16), palette="orange-blue-white"
    )
    am.register_animation(
        "clyde_walk_up",
        AnimationDef(
            frames=("clyde_up_0", "clyde_up_1"),
            frame_duration_ms=120,
        ),
    )
    # Scared ghost(blue), shared by all ghosts
    am.register_sprite(
        "ghost_scared_0", (1, 168, 16, 16), palette="red-blue-white"
    )
    am.register_sprite(
        "ghost_scared_1", (18, 168, 16, 16), palette="red-blue-white"
    )
    am.register_animation(
        "ghost_scared",
        AnimationDef(
            frames=("ghost_scared_0", "ghost_scared_1"),
            frame_duration_ms=120,
        ),
    )
    # Almost not scared ghost (white/blue), shared by all ghosts
    am.register_sprite(
        "ghost_almost_scared_0", (1, 354, 16, 16), palette="red-white-green"
    )
    am.register_sprite(
        "ghost_almost_scared_1", (18, 354, 16, 16), palette="red-white-green"
    )
    am.register_animation(
        "ghost_almost_scared",
        AnimationDef(
            frames=(
                "ghost_almost_scared_0",
                "ghost_almost_scared_1",
                "ghost_scared_0",
                "ghost_scared_1",
            ),
            frame_duration_ms=120,
        ),
    )

    # Eyes-only ghost, shared by all ghosts
    am.register_sprite(
        "ghost_eyes_right", (1, 83, 16, 16), palette="black-blue-white"
    )
    am.register_sprite(
        "ghost_eyes_down", (35, 83, 16, 16), palette="black-blue-white"
    )
    am.register_sprite(
        "ghost_eyes_left", (69, 83, 16, 16), palette="black-blue-white"
    )
    am.register_sprite(
        "ghost_eyes_up", (103, 83, 16, 16), palette="black-blue-white"
    )


def _register_font(am: AssetManager) -> None:
    """Declare the arcade font glyphs and group them in a Font.

    Example::

        am.register_sprite("char_A", (..., ..., 8, 8))
        am.register_font(
            "arcade",
            Font(glyphs={"A": "char_A", "B": "char_B"}),
        )
    """
    am.register_sprite("char_0", (1, 1, 8, 8))
    am.register_sprite("char_1", (10, 1, 8, 8))
    am.register_sprite("char_2", (19, 1, 8, 8))
    am.register_sprite("char_3", (28, 1, 8, 8))
    am.register_sprite("char_4", (37, 1, 8, 8))
    am.register_sprite("char_5", (46, 1, 8, 8))
    am.register_sprite("char_6", (55, 1, 8, 8))
    am.register_sprite("char_7", (64, 1, 8, 8))
    am.register_sprite("char_8", (73, 1, 8, 8))
    am.register_sprite("char_9", (82, 1, 8, 8))
    am.register_sprite("char_A", (1, 28, 8, 8))
    am.register_sprite("char_B", (10, 28, 8, 8))
    am.register_sprite("char_C", (19, 28, 8, 8))
    am.register_sprite("char_D", (28, 28, 8, 8))
    am.register_sprite("char_E", (37, 28, 8, 8))
    am.register_sprite("char_F", (46, 28, 8, 8))
    am.register_sprite("char_G", (55, 28, 8, 8))
    am.register_sprite("char_H", (64, 28, 8, 8))
    am.register_sprite("char_I", (73, 28, 8, 8))
    am.register_sprite("char_J", (82, 28, 8, 8))
    am.register_sprite("char_K", (91, 28, 8, 8))
    am.register_sprite("char_L", (100, 28, 8, 8))
    am.register_sprite("char_M", (109, 28, 8, 8))
    am.register_sprite("char_N", (1, 37, 8, 8))
    am.register_sprite("char_O", (10, 37, 8, 8))
    am.register_sprite("char_P", (19, 37, 8, 8))
    am.register_sprite("char_Q", (28, 37, 8, 8))
    am.register_sprite("char_R", (37, 37, 8, 8))
    am.register_sprite("char_S", (46, 37, 8, 8))
    am.register_sprite("char_T", (55, 37, 8, 8))
    am.register_sprite("char_U", (64, 37, 8, 8))
    am.register_sprite("char_V", (73, 37, 8, 8))
    am.register_sprite("char_W", (82, 37, 8, 8))
    am.register_sprite("char_X", (91, 37, 8, 8))
    am.register_sprite("char_Y", (100, 37, 8, 8))
    am.register_sprite("char_Z", (109, 37, 8, 8))
    am.register_sprite("char_space", (19, 64, 8, 8))
    am.register_sprite("char_exclamation", (109, 19, 8, 8))
    am.register_sprite("char_backslash", (91, 10, 8, 8))
    am.register_sprite("char_arobase", (100, 19, 8, 8))
    am.register_sprite("char_dash", (100, 10, 8, 8))
    am.register_sprite("char_dot", (109, 10, 8, 8))
    am.register_sprite("char_quote", (91, 19, 8, 8))
    am.register_font(
        "arcade",
        Font(
            glyphs={
                "A": "char_A",
                "B": "char_B",
                "C": "char_C",
                "D": "char_D",
                "E": "char_E",
                "F": "char_F",
                "G": "char_G",
                "H": "char_H",
                "I": "char_I",
                "J": "char_J",
                "K": "char_K",
                "L": "char_L",
                "M": "char_M",
                "N": "char_N",
                "O": "char_O",
                "P": "char_P",
                "Q": "char_Q",
                "R": "char_R",
                "S": "char_S",
                "T": "char_T",
                "U": "char_U",
                "V": "char_V",
                "W": "char_W",
                "X": "char_X",
                "Y": "char_Y",
                "Z": "char_Z",
                " ": "char_space",
                "!": "char_exclamation",
                "\\": "char_backslash",
                "@": "char_arobase",
                "-": "char_dash",
                ".": "char_dot",
                '"': "char_quote",
            },
        ),
    )
