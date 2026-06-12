"""Tests for the AssetManager and grouped sprite structures."""

import pytest

from graphics.assets import AnimationDef, AssetManager, Font, PaletteColors


SHEET_PATH = (
    "assets/sprites/"
    "Arcade - Pac-Man - Miscellaneous - All Assets_Palettes.png"
)


@pytest.fixture
def am() -> AssetManager:
    return AssetManager(SHEET_PATH)


def test_loads_sheet(am: AssetManager) -> None:
    assert am.sheet.get_size() == (1000, 750)


def test_default_palette_is_set(am: AssetManager) -> None:
    assert am.current_palette == "red-blue-white"


def test_register_and_get_sprite(am: AssetManager) -> None:
    am.register_sprite("test", (0, 0, 16, 16))
    sprite = am.get_sprite("test")
    assert sprite.get_size() == (16, 16)


def test_register_sprite_out_of_bounds_raises(am: AssetManager) -> None:
    with pytest.raises(ValueError, match="out of sheet bounds"):
        am.register_sprite("oob", (990, 0, 16, 16))


def test_register_sprite_duplicate_raises(am: AssetManager) -> None:
    am.register_sprite("dup", (0, 0, 16, 16))
    with pytest.raises(ValueError, match="already registered"):
        am.register_sprite("dup", (0, 0, 16, 16))


def test_get_unknown_sprite_raises(am: AssetManager) -> None:
    with pytest.raises(KeyError, match="not registered"):
        am.get_sprite("ghost")


def test_palette_offsets_resolve_different_regions(
    am: AssetManager,
) -> None:
    am.register_palette("alt", (250, 0))
    am.register_sprite("pac", (0, 0, 16, 16))

    am.set_palette("red-blue-white")
    s_default = am.get_sprite("pac")
    am.set_palette("alt")
    s_alt = am.get_sprite("pac")

    assert s_default.get_size() == s_alt.get_size()
    assert s_default.get_offset() != s_alt.get_offset()


def test_sprite_cache_is_keyed_by_palette(am: AssetManager) -> None:
    am.register_palette("alt", (250, 0))
    am.register_sprite("pac", (0, 0, 16, 16))
    a = am.get_sprite("pac")
    am.set_palette("alt")
    b = am.get_sprite("pac")
    am.set_palette("red-blue-white")
    a2 = am.get_sprite("pac")
    assert a is a2
    assert a is not b


def test_set_palette_unknown_raises(am: AssetManager) -> None:
    with pytest.raises(KeyError, match="not registered"):
        am.set_palette("nope")


def test_register_palette_duplicate_raises(am: AssetManager) -> None:
    am.register_palette("alt", (250, 0))
    with pytest.raises(ValueError, match="already registered"):
        am.register_palette("alt", (500, 0))


def test_palette_offset_out_of_bounds_at_get_raises(
    am: AssetManager,
) -> None:
    am.register_palette("alt", (995, 0))
    am.register_sprite("pac", (0, 0, 16, 16))
    am.set_palette("alt")
    with pytest.raises(ValueError, match="out of sheet bounds"):
        am.get_sprite("pac")


def test_register_palette_with_colors(am: AssetManager) -> None:
    colors = PaletteColors(
        primary=(255, 0, 0),
        wall_fill=(0, 0, 255),
        secondary=(255, 255, 255),
    )
    am.register_palette("themed", (250, 0), colors=colors)
    assert am.get_palette_colors("themed") is colors


def test_get_palette_colors_unknown_raises(am: AssetManager) -> None:
    with pytest.raises(KeyError, match="not registered"):
        am.get_palette_colors("nope")


def test_get_palette_colors_no_colors_raises(am: AssetManager) -> None:
    am.register_palette("nocols", (250, 0))
    with pytest.raises(KeyError, match="no colours registered"):
        am.get_palette_colors("nocols")


def test_animation_register_and_get(am: AssetManager) -> None:
    anim = AnimationDef(
        frames=("p1", "p2", "p3"), frame_duration_ms=80
    )
    am.register_animation("pacman_chomp", anim)
    assert am.get_animation("pacman_chomp") is anim


def test_animation_unknown_raises(am: AssetManager) -> None:
    with pytest.raises(KeyError, match="not registered"):
        am.get_animation("absent")


def test_font_register_and_get(am: AssetManager) -> None:
    f = Font(glyphs={"A": "letter_a"})
    am.register_font("score", f)
    assert am.get_font("score") is f


# -- derived sprites ---------------------------------------------


def test_register_derived_flip_x(am: AssetManager) -> None:
    am.register_sprite("right", (0, 0, 16, 16))
    am.register_derived_sprite("left", source="right", flip_x=True)
    sprite = am.get_sprite("left")
    assert sprite.get_size() == (16, 16)
    source = am.get_sprite("right")
    # The leftmost pixel of the source matches the rightmost pixel
    # of the horizontally flipped derived sprite.
    assert source.get_at((0, 0)) == sprite.get_at((15, 0))


def test_register_derived_flip_y(am: AssetManager) -> None:
    am.register_sprite("down", (0, 0, 16, 16))
    am.register_derived_sprite("up", source="down", flip_y=True)
    sprite = am.get_sprite("up")
    assert sprite.get_size() == (16, 16)
    source = am.get_sprite("down")
    assert source.get_at((0, 0)) == sprite.get_at((0, 15))


def test_register_derived_unknown_source_raises(
    am: AssetManager,
) -> None:
    with pytest.raises(ValueError, match="not registered"):
        am.register_derived_sprite("foo", source="nope", flip_x=True)


def test_register_derived_duplicate_name_raises(
    am: AssetManager,
) -> None:
    am.register_sprite("a", (0, 0, 16, 16))
    am.register_derived_sprite("b", source="a", flip_x=True)
    with pytest.raises(ValueError, match="already registered"):
        am.register_derived_sprite("b", source="a", flip_y=True)


def test_register_sprite_collides_with_derived_raises(
    am: AssetManager,
) -> None:
    am.register_sprite("a", (0, 0, 16, 16))
    am.register_derived_sprite("b", source="a", flip_x=True)
    with pytest.raises(ValueError, match="already registered"):
        am.register_sprite("b", (16, 0, 16, 16))


def test_derived_sprite_palette_aware(am: AssetManager) -> None:
    am.register_palette("alt", (250, 0))
    am.register_sprite("right", (0, 0, 16, 16))
    am.register_derived_sprite("left", source="right", flip_x=True)
    am.set_palette("red-blue-white")
    default_left = am.get_sprite("left")
    am.set_palette("alt")
    alt_left = am.get_sprite("left")
    assert default_left is not alt_left


def test_derived_of_derived(am: AssetManager) -> None:
    """A derived sprite can be the source of another derived sprite."""
    am.register_sprite("right", (0, 0, 16, 16))
    am.register_derived_sprite("left", source="right", flip_x=True)
    am.register_derived_sprite("right_2", source="left", flip_x=True)
    # right_2 = flip_x(left) = flip_x(flip_x(right)) = right
    source = am.get_sprite("right")
    sprite = am.get_sprite("right_2")
    assert source.get_at((0, 0)) == sprite.get_at((0, 0))


# -- palette pinning ---------------------------------------------


def test_pinned_sprite_resolves_to_its_palette(
    am: AssetManager,
) -> None:
    am.register_palette("alt", (250, 0))
    am.register_sprite("blinky", (0, 0, 16, 16), palette="alt")
    sprite = am.get_sprite("blinky")
    assert sprite.get_offset() == (250, 0)


def test_pinned_sprite_ignores_current_palette(
    am: AssetManager,
) -> None:
    am.register_palette("alt", (250, 0))
    am.register_sprite("pinned", (0, 0, 16, 16), palette="alt")
    am.set_palette("red-blue-white")
    a = am.get_sprite("pinned")
    am.set_palette("alt")
    b = am.get_sprite("pinned")
    # Same Surface from the cache regardless of current_palette.
    assert a is b
    assert a.get_offset() == (250, 0)


def test_register_sprite_pin_unknown_palette_raises(
    am: AssetManager,
) -> None:
    with pytest.raises(ValueError, match="Palette 'nope' not "):
        am.register_sprite("x", (0, 0, 16, 16), palette="nope")


def test_register_sprite_pin_out_of_bounds_raises(
    am: AssetManager,
) -> None:
    am.register_palette("far", (995, 0))
    with pytest.raises(ValueError, match="out of sheet bounds"):
        am.register_sprite("x", (0, 0, 16, 16), palette="far")


def test_animation_can_alternate_two_palettes(
    am: AssetManager,
) -> None:
    """A scared-blink-style animation pulling from two palettes."""
    am.register_palette("blue", (200, 0))
    am.register_palette("white", (400, 0))
    am.register_sprite("scared_b_0", (0, 0, 16, 16), palette="blue")
    am.register_sprite("scared_b_1", (16, 0, 16, 16), palette="blue")
    am.register_sprite("scared_w_0", (0, 0, 16, 16), palette="white")
    am.register_sprite("scared_w_1", (16, 0, 16, 16), palette="white")
    anim = AnimationDef(
        frames=(
            "scared_b_0", "scared_b_1",
            "scared_w_0", "scared_w_1",
        ),
        frame_duration_ms=200,
    )
    am.register_animation("scared_blink", anim)
    # Each frame resolves to its own palette region irrespective of
    # the current palette.
    am.set_palette("red-blue-white")
    assert am.get_sprite("scared_b_0").get_offset() == (200, 0)
    assert am.get_sprite("scared_w_0").get_offset() == (400, 0)


def test_derived_sprite_inherits_pinned_palette(
    am: AssetManager,
) -> None:
    am.register_palette("alt", (250, 0))
    am.register_sprite("right", (0, 0, 16, 16), palette="alt")
    am.register_derived_sprite("left", source="right", flip_x=True)
    am.set_palette("red-blue-white")
    a = am.get_sprite("left")
    am.set_palette("alt")
    b = am.get_sprite("left")
    # Source is pinned, so the derived sprite is stable across
    # current_palette changes — same cache entry, same Surface.
    assert a is b
