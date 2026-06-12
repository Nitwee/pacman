"""Stateful animation playback for sprite sequences.

An :class:`Animation` is the runtime state of an
:class:`graphics.assets.AnimationDef` — it knows the current frame, the
elapsed time inside that frame, and advances on every
:meth:`update` call. One instance per animated entity (Pac-Man,
each ghost, …) so that two entities playing the same animation can
be at different points in their cycle.

Time is measured in milliseconds, the unit returned by
``pygame.time.Clock.tick(...)``. The class itself does not depend on
Pygame.
"""

from graphics.assets import AnimationDef


class Animation:
    """Playback state for one :class:`AnimationDef` instance.

    Attributes:
        definition: The immutable spec being played back.
    """

    def __init__(self, definition: AnimationDef) -> None:
        """Start the animation at frame 0.

        Args:
            definition: The frame list and timing to play.
        """
        self.definition = definition
        self._index: int = 0
        self._elapsed_ms: int = 0

    def update(self, dt_ms: int) -> None:
        """Advance the animation by ``dt_ms`` milliseconds.

        Multi-frame jumps are handled when ``dt_ms`` exceeds the
        per-frame budget — useful when the render loop hitches. For
        a non-looping animation the index clamps at the last frame
        and further updates become no-ops.

        Args:
            dt_ms: Real time elapsed since the previous update.
        """
        if self.finished:
            return
        self._elapsed_ms += dt_ms
        frame_ms = self.definition.frame_duration_ms
        last = len(self.definition.frames) - 1
        while self._elapsed_ms >= frame_ms:
            self._elapsed_ms -= frame_ms
            if self._index < last:
                self._index += 1
            elif self.definition.loop:
                self._index = 0
            else:
                self._elapsed_ms = 0
                return

    def current_frame(self) -> str:
        """Return the sprite name to render this tick.

        Returns:
            Name of the current frame's sprite.
        """
        return self.definition.frames[self._index]

    def reset(self) -> None:
        """Rewind to frame 0 and clear the elapsed counter."""
        self._index = 0
        self._elapsed_ms = 0

    def set_definition(self, definition: AnimationDef) -> None:
        """Swap the playback definition while preserving phase.

        Used when an entity changes facing direction — the new
        animation continues at the same frame index (clamped if the
        new definition has fewer frames) so the chomp / wobble
        rhythm stays smooth across turns. Calling with the current
        definition is a no-op.

        Args:
            definition: New :class:`AnimationDef` to play.
        """
        if definition is self.definition:
            return
        self.definition = definition
        if self._index >= len(definition.frames):
            self._index = 0

    @property
    def finished(self) -> bool:
        """True if a non-looping animation has reached its last frame.

        Always False for looping animations.
        """
        if self.definition.loop:
            return False
        return self._index == len(self.definition.frames) - 1
