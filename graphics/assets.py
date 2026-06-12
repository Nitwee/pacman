"""Pygame asset manager.

Loads a single sprite sheet and exposes named registries for sprites,
palettes, animations and fonts.

The sheet is expected to be organised as repeated palette blocks:
each palette is registered as a constant ``(dx, dy)`` offset, and a
single sprite name resolves to a different region of the sheet
depending on the active palette. Switching palette is therefore a
single attribute change.

Animations and fonts sets are pure data structures grouping
sprite names by purpose; the actual surfaces are still resolved
through :meth:`AssetManager.get_sprite`.
"""

from dataclasses import dataclass
from typing import Optional

import pygame


@dataclass(frozen=True)
class AnimationDef:
    """Ordered list of sprite names composing one animation.

    Attributes:
        frames: Sprite names in playback order.
        frame_duration_ms: Time per frame in milliseconds.
        loop: Restart at the end (True) or hold the last frame.
    """

    frames: tuple[str, ...]
    frame_duration_ms: int = 100
    loop: bool = True


@dataclass(frozen=True)
class Font:
    """Bitmap font: one sprite per character.

    Glyph dimensions are not stored — they are derived on demand from
    each glyph's underlying sprite via
    :meth:`AssetManager.get_sprite`.

    Attributes:
        glyphs: Mapping from character to sprite name.
    """

    glyphs: dict[str, str]


@dataclass(frozen=True)
class PaletteColors:
    """Three theme colours derived from a palette block.

    Attributes:
        primary: Body colour of entities (Blinky red, Pinky pink…).
            Also used as the wall outline colour.
        wall_fill: Interior colour of maze walls (and the 42 logo).
        secondary: Colour of bonuses and ghost eyes.
    """

    primary: tuple[int, int, int]
    wall_fill: tuple[int, int, int]
    secondary: tuple[int, int, int]


@dataclass(frozen=True)
class DerivedSpriteSpec:
    """Spec for a sprite derived from another via geometric transform.

    Attributes:
        source: Name of the source sprite (raw or derived).
        flip_x: Mirror horizontally if True.
        flip_y: Mirror vertically if True.
    """

    source: str
    flip_x: bool = False
    flip_y: bool = False


_DEFAULT_PALETTE = "red-blue-white"


class AssetManager:
    """Sprite sheet loader with palettes and grouped registries.

    Attributes:
        sheet: Loaded sprite sheet surface.
        current_palette: Identifier of the palette in effect.
    """

    def __init__(self, sprite_sheet_path: str) -> None:
        """Load the sprite sheet and seed the default identity palette.

        Args:
            sprite_sheet_path: Path to the sprite sheet image.
        """
        self.sheet: pygame.Surface = pygame.image.load(
            sprite_sheet_path
        )
        # Treat pure black as transparent so sprite backgrounds drop
        # out and entities float above the maze instead of being
        # framed by a black square. The sheet is RGBA so set_colorkey
        # would be silently ignored (per-pixel alpha takes precedence);
        # we rewrite the alpha channel of black pixels directly.
        self._make_black_transparent(self.sheet)
        self._sprites: dict[str, pygame.Rect] = {}
        self._sprite_palette: dict[str, str] = {}
        self._derived: dict[str, DerivedSpriteSpec] = {}
        self._palettes: dict[str, tuple[int, int]] = {
            _DEFAULT_PALETTE: (0, 0),
        }
        self._palette_colors: dict[str, PaletteColors] = {}
        self.current_palette: str = _DEFAULT_PALETTE
        self._cache: dict[tuple[str, str], pygame.Surface] = {}
        self._animations: dict[str, AnimationDef] = {}
        self._fonts: dict[str, Font] = {}

    @staticmethod
    def _make_black_transparent(sheet: pygame.Surface) -> None:
        """Replace pure-black opaque pixels with fully transparent ones.

        On RGBA surfaces ``set_colorkey`` is ignored because per-pixel
        alpha takes precedence at blit time. We rewrite the pixel
        values directly using a :class:`pygame.PixelArray` so the
        change is permanent and inherits to subsurfaces and scaled
        copies. Pure black ``(0, 0, 0)`` is the sprite-sheet
        background; black pixels inside sprites (ghost pupils,
        Pac-Man's mouth) typically use a non-pure black so they
        survive this pass.
        """
        opaque_black = sheet.map_rgb((0, 0, 0))
        transparent = sheet.map_rgb((0, 0, 0, 0))
        if opaque_black == transparent:
            return
        with pygame.PixelArray(sheet) as pixels:
            pixels.replace(opaque_black, transparent)

    # -- palettes --------------------------------------------------

    def register_palette(
        self,
        name: str,
        offset: tuple[int, int],
        colors: Optional[PaletteColors] = None,
    ) -> None:
        """Declare a palette as a sheet offset and optional colours.

        Re-registering an existing palette is allowed **only** if the
        offset matches; in that case colours are set/updated. This
        makes it safe for :func:`asset_setup.setup` to declare a
        palette that the AssetManager auto-seeds at construction
        (typically the default theme).

        Args:
            name: Palette identifier.
            offset: ``(dx, dy)`` added to every sprite rect when this
                palette is active.
            colors: Optional theme colours sampled or hand-set. If
                omitted, :meth:`get_palette_colors` will raise.

        Raises:
            ValueError: If the palette is already registered with a
                different offset.
        """
        if name in self._palettes:
            if self._palettes[name] != offset:
                raise ValueError(
                    f"Palette '{name}' already registered with "
                    f"a different offset"
                )
        else:
            self._palettes[name] = offset
        if colors is not None:
            self._palette_colors[name] = colors

    def get_palette_colors(self, name: str) -> PaletteColors:
        """Return the theme colours of a palette.

        Args:
            name: Palette identifier.

        Returns:
            The :class:`PaletteColors` registered for that palette.

        Raises:
            KeyError: If the palette is unknown or has no colours
                registered.
        """
        if name not in self._palettes:
            raise KeyError(f"Palette '{name}' not registered")
        if name not in self._palette_colors:
            raise KeyError(
                f"Palette '{name}' has no colours registered"
            )
        return self._palette_colors[name]

    def set_palette(self, name: str) -> None:
        """Switch the active palette.

        Args:
            name: Palette identifier previously registered.

        Raises:
            KeyError: If the palette is unknown.
        """
        if name not in self._palettes:
            raise KeyError(f"Palette '{name}' not registered")
        self.current_palette = name

    # -- sprites ---------------------------------------------------

    def register_sprite(
        self,
        name: str,
        rect: tuple[int, int, int, int],
        palette: Optional[str] = None,
    ) -> None:
        """Declare a sprite as a region of a palette block.

        With ``palette=None`` the rect is interpreted relative to the
        default palette and follows :attr:`current_palette` at lookup
        time. With ``palette="<name>"`` the sprite is **pinned** to
        that palette and ignores ``current_palette`` — useful for
        assets whose colour is gameplay-defined (each ghost, eyes,
        scared-blue / scared-white) rather than a theme choice.

        Args:
            name: Sprite identifier (e.g. ``"pacman_right_0"``).
            rect: ``(x, y, width, height)`` in palette-local pixels.
            palette: If set, pin the sprite to this palette.

        Raises:
            ValueError: If the rect is out of bounds, the palette is
                unknown, or the name is already used.
        """
        if name in self._sprites or name in self._derived:
            raise ValueError(
                f"Sprite '{name}' already registered"
            )
        if palette is not None and palette not in self._palettes:
            raise ValueError(
                f"Palette '{palette}' not registered"
            )
        x, y, w, h = rect
        sw, sh = self.sheet.get_size()
        if palette is not None:
            dx, dy = self._palettes[palette]
            eff_x, eff_y = x + dx, y + dy
        else:
            eff_x, eff_y = x, y
        if (
            eff_x < 0
            or eff_y < 0
            or eff_x + w > sw
            or eff_y + h > sh
        ):
            raise ValueError(
                f"Sprite '{name}' rect {rect} (palette={palette}) "
                f"out of sheet bounds {(sw, sh)}"
            )
        self._sprites[name] = pygame.Rect(rect)
        if palette is not None:
            self._sprite_palette[name] = palette

    def register_derived_sprite(
        self,
        name: str,
        source: str,
        flip_x: bool = False,
        flip_y: bool = False,
    ) -> None:
        """Declare a sprite derived by flipping another one.

        Resolution happens lazily inside :meth:`get_sprite`, so a
        palette switch transparently re-derives from the new
        palette's source.

        Args:
            name: Identifier for the derived sprite.
            source: Name of an existing sprite (raw or derived).
            flip_x: Mirror horizontally.
            flip_y: Mirror vertically.

        Raises:
            ValueError: If ``name`` is already used or ``source`` is
                not registered.
        """
        if name in self._sprites or name in self._derived:
            raise ValueError(
                f"Sprite '{name}' already registered"
            )
        if (
            source not in self._sprites
            and source not in self._derived
        ):
            raise ValueError(
                f"Source sprite '{source}' not registered"
            )
        self._derived[name] = DerivedSpriteSpec(
            source=source, flip_x=flip_x, flip_y=flip_y
        )

    def _effective_palette(self, name: str) -> str:
        """Resolve the palette governing a sprite's lookup.

        Pinned sprites return their pin; derived sprites inherit
        through their source; everything else falls back to
        :attr:`current_palette`.

        Args:
            name: Sprite identifier.

        Returns:
            Palette identifier in effect for this sprite.

        Raises:
            KeyError: If the sprite is unknown.
        """
        if name in self._sprite_palette:
            return self._sprite_palette[name]
        if name in self._derived:
            return self._effective_palette(self._derived[name].source)
        if name in self._sprites:
            return self.current_palette
        raise KeyError(f"Sprite '{name}' not registered")

    def get_sprite(self, name: str) -> pygame.Surface:
        """Return the sprite surface under its effective palette.

        Args:
            name: Sprite identifier.

        Returns:
            A cached surface (subsurface for raw sprites, flipped
            copy for derived sprites).

        Raises:
            KeyError: If the sprite is not registered.
            ValueError: If the effective palette pushes the rect out
                of the sheet bounds.
        """
        effective = self._effective_palette(name)
        cache_key = (effective, name)
        if cache_key in self._cache:
            return self._cache[cache_key]
        if name in self._derived:
            spec = self._derived[name]
            source_surface = self.get_sprite(spec.source)
            derived = pygame.transform.flip(
                source_surface, spec.flip_x, spec.flip_y
            )
            self._cache[cache_key] = derived
            return derived
        base = self._sprites[name]
        dx, dy = self._palettes[effective]
        rect = pygame.Rect(base.x + dx, base.y + dy, base.w, base.h)
        sw, sh = self.sheet.get_size()
        if (
            rect.x < 0
            or rect.y < 0
            or rect.right > sw
            or rect.bottom > sh
        ):
            raise ValueError(
                f"Sprite '{name}' under palette '{effective}' "
                f"falls out of sheet bounds"
            )
        surface = self.sheet.subsurface(rect)
        self._cache[cache_key] = surface
        return surface

    # -- animations ------------------------------------------------

    def register_animation(
        self,
        name: str,
        definition: AnimationDef,
    ) -> None:
        """Declare an animation grouping several sprites.

        Args:
            name: Animation identifier.
            definition: Frame list and timing.

        Raises:
            ValueError: If the name is already used.
        """
        if name in self._animations:
            raise ValueError(
                f"Animation '{name}' already registered"
            )
        self._animations[name] = definition

    def get_animation(self, name: str) -> AnimationDef:
        """Return a registered animation definition.

        Args:
            name: Animation identifier.

        Returns:
            The :class:`AnimationDef` previously registered.

        Raises:
            KeyError: If the animation is not registered.
        """
        if name not in self._animations:
            raise KeyError(
                f"Animation '{name}' not registered"
            )
        return self._animations[name]

    # -- fonts -----------------------------------------------------

    def register_font(self, name: str, font: Font) -> None:
        """Declare a bitmap font.

        Args:
            name: Font identifier.
            font: Font definition.

        Raises:
            ValueError: If the name is already used.
        """
        if name in self._fonts:
            raise ValueError(f"Font '{name}' already registered")
        self._fonts[name] = font

    def get_font(self, name: str) -> Font:
        """Return a registered font.

        Args:
            name: Font identifier.

        Returns:
            The :class:`Font` previously registered.

        Raises:
            KeyError: If the font is not registered.
        """
        if name not in self._fonts:
            raise KeyError(f"Font '{name}' not registered")
        return self._fonts[name]

    def next_palette(self) -> str:
        """Return the next palette in registration order after the current.

        Wraps around to the first palette when the current is last.

        Returns:
            Palette identifier.
        """
        keys = list(self._palettes.keys())
        idx = keys.index(self.current_palette)
        next_idx = (idx + 1) % len(keys)
        return keys[next_idx]
