"""Pygame mixer wrapper with a named sound registry.

Separates one-shot SFX from background music:

- :meth:`SoundManager.play_sfx` fires a sound on the first available
  Pygame channel (auto-allocation).
- :meth:`SoundManager.play_music` owns a dedicated reserved channel
  so a new background loop cleanly replaces the previous one without
  ever competing with SFX for channel slots. When an intro variant
  ``{name}_firstloop`` is registered, it plays once before the main
  ``{name}`` sound takes over as an infinite loop — driven by
  :meth:`SoundManager.update_music` called once per frame.

:func:`pygame.mixer.init` must run before :class:`SoundManager` is
instantiated — :func:`pygame.init` does this as part of its global
init, so creating the manager inside :meth:`app.App.run` is enough.
"""

from typing import Optional

import pygame


class SoundManager:
    """Loads, registers and plays game sounds.

    Attributes:
        current_music: Name of the music loop currently playing on
            the reserved channel, or ``None`` when music is stopped.
    """

    def __init__(self) -> None:
        """Reserve channel 0 for music and prepare the registry."""
        pygame.mixer.set_reserved(1)
        self._music_channel: pygame.mixer.Channel = pygame.mixer.Channel(0)
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self.current_music: Optional[str] = None
        self._pending_loop: Optional[pygame.mixer.Sound] = None

    def register_sound(self, name: str, path: str) -> None:
        """Load a WAV file and register it under ``name``.

        Args:
            name: Identifier used by :meth:`play_sfx` and
                :meth:`play_music`.
            path: Filesystem path to the sound asset.

        Raises:
            ValueError: If ``name`` is already registered.
        """
        if name in self._sounds:
            raise ValueError(f"Sound '{name}' already registered")
        self._sounds[name] = pygame.mixer.Sound(path)

    def play_sfx(self, name: str) -> None:
        """Play a one-shot sound on the first available channel.

        Args:
            name: Identifier of a previously registered sound.

        Raises:
            KeyError: If the sound is not registered.
        """
        self._get(name).play()

    def get_duration_ms(self, name: str) -> int:
        """Return the duration of a registered sound, in milliseconds.

        Args:
            name: Identifier of a previously registered sound.

        Returns:
            Length of the sound rounded to whole milliseconds.

        Raises:
            KeyError: If the sound is not registered.
        """
        return int(self._get(name).get_length() * 1000)

    def play_music(self, name: str) -> None:
        """Play a looping background sound on the reserved music channel.

        Idempotent: calling with the currently-playing music is a
        no-op so the loop is not restarted from frame zero every
        frame by the App's audio update. When a registered sound
        named ``{name}_firstloop`` exists it is played once first
        as an intro; :meth:`update_music` then chains into the
        main ``name`` sound as an infinite loop.

        Args:
            name: Identifier of a previously registered sound.

        Raises:
            KeyError: If ``name`` is not registered.
        """
        if self.current_music == name:
            return
        loop_sound = self._get(name)
        intro = self._sounds.get(f"{name}_firstloop")
        self.current_music = name
        if intro is None:
            self._music_channel.play(loop_sound, loops=-1)
            self._pending_loop = None
        else:
            self._music_channel.play(intro, loops=0)
            self._pending_loop = loop_sound

    def update_music(self) -> None:
        """Chain the intro into the main loop once the intro finishes.

        Must be called once per frame after audio-affecting state
        changes. No-op when no intro is pending or when the channel
        is still busy playing the intro.
        """
        if self._pending_loop is None:
            return
        if self._music_channel.get_busy():
            return
        self._music_channel.play(self._pending_loop, loops=-1)
        self._pending_loop = None

    def stop_music(self) -> None:
        """Stop the current background loop (no-op if already stopped)."""
        if self.current_music is None:
            return
        self._music_channel.stop()
        self.current_music = None
        self._pending_loop = None

    def stop_all(self) -> None:
        """Stop every sound currently playing and clear music state.

        This is used when transitioning out of gameplay (for example
        returning to the main menu) to ensure no lingering SFX or
        music continues to play.
        """
        # Stop all mixer channels (includes the reserved music
        # channel) and clear the manager's bookkeeping.
        pygame.mixer.stop()
        self.current_music = None
        self._pending_loop = None

    def pause_all(self) -> None:
        """Pause every channel so playback can later resume in place."""
        pygame.mixer.pause()

    def unpause_all(self) -> None:
        """Resume every previously paused channel."""
        pygame.mixer.unpause()

    def _get(self, name: str) -> pygame.mixer.Sound:
        """Return the registered sound or raise :class:`KeyError`."""
        if name not in self._sounds:
            raise KeyError(f"Sound '{name}' not registered")
        return self._sounds[name]
