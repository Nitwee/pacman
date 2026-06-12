"""Tests for the SoundManager registry and routing logic."""

from pathlib import Path

import pygame
import pytest

from audio.manager import SoundManager
from audio.setup import setup as audio_setup_setup


SOUNDS_DIR = Path("assets/sounds")
SAMPLE = SOUNDS_DIR / "credit.wav"


@pytest.fixture
def sm() -> SoundManager:
    """Return a fresh SoundManager."""
    return SoundManager()


def test_register_and_play_sfx(sm: SoundManager) -> None:
    """Registering a sound makes it playable."""
    sm.register_sound("ding", str(SAMPLE))
    sm.play_sfx("ding")  # must not raise


def test_register_duplicate_raises(sm: SoundManager) -> None:
    """Re-registering an existing name raises."""
    sm.register_sound("ding", str(SAMPLE))
    with pytest.raises(ValueError, match="already registered"):
        sm.register_sound("ding", str(SAMPLE))


def test_play_unknown_sfx_raises(sm: SoundManager) -> None:
    """Playing an unregistered sound raises KeyError."""
    with pytest.raises(KeyError, match="not registered"):
        sm.play_sfx("missing")


def test_play_music_sets_current_music(sm: SoundManager) -> None:
    """play_music records the active loop name."""
    sm.register_sound("loop", str(SAMPLE))
    assert sm.current_music is None
    sm.play_music("loop")
    assert sm.current_music == "loop"


def test_play_music_idempotent(sm: SoundManager) -> None:
    """Re-asking the same loop does not restart playback."""
    sm.register_sound("loop", str(SAMPLE))
    sm.play_music("loop")
    busy_first = sm._music_channel.get_busy()
    sm.play_music("loop")  # no-op
    assert sm.current_music == "loop"
    # Channel state survives the no-op call.
    assert sm._music_channel.get_busy() == busy_first


def test_play_music_switches_loop(sm: SoundManager) -> None:
    """Asking a different loop swaps the current music name."""
    sm.register_sound("a", str(SAMPLE))
    sm.register_sound("b", str(SAMPLE))
    sm.play_music("a")
    sm.play_music("b")
    assert sm.current_music == "b"


def test_stop_music_clears_state(sm: SoundManager) -> None:
    """stop_music drops the loop and clears the tracked name."""
    sm.register_sound("loop", str(SAMPLE))
    sm.play_music("loop")
    sm.stop_music()
    assert sm.current_music is None


def test_stop_music_when_already_stopped_is_noop(sm: SoundManager) -> None:
    """Calling stop_music with no music playing is harmless."""
    sm.stop_music()
    assert sm.current_music is None


def test_setup_registers_every_shipped_sound(sm: SoundManager) -> None:
    """audio_setup.setup loads each WAV under assets/sounds."""
    audio_setup_setup(sm)
    # Spot-check a representative subset across the catalogue.
    for name in ("credit", "eat_dot_0", "death_0", "fright", "siren0"):
        sm.play_sfx(name)  # must not raise


# --- Intro → loop chaining ----------------------------------------


def test_play_music_with_intro_defers_loop(sm: SoundManager) -> None:
    """When ``{name}_firstloop`` exists, the intro plays first."""
    sm.register_sound("siren0", str(SAMPLE))
    sm.register_sound("siren0_firstloop", str(SAMPLE))

    sm.play_music("siren0")

    assert sm.current_music == "siren0"
    # A pending loop is set: the intro just started, the loop is
    # waiting for it to finish.
    assert sm._pending_loop is sm._sounds["siren0"]


def test_play_music_without_intro_loops_immediately(
    sm: SoundManager,
) -> None:
    """Without a firstloop variant, the loop starts straight away."""
    sm.register_sound("siren0", str(SAMPLE))

    sm.play_music("siren0")

    assert sm.current_music == "siren0"
    assert sm._pending_loop is None


def test_update_music_switches_to_loop_when_intro_done(
    sm: SoundManager,
) -> None:
    """After the intro finishes, update_music starts the loop."""
    sm.register_sound("siren0", str(SAMPLE))
    sm.register_sound("siren0_firstloop", str(SAMPLE))
    sm.play_music("siren0")
    # Drain the intro: wait for the channel to drop busy.
    while sm._music_channel.get_busy():
        pygame.time.wait(20)

    sm.update_music()

    assert sm._pending_loop is None
    assert sm._music_channel.get_busy()


def test_update_music_keeps_intro_while_busy(sm: SoundManager) -> None:
    """update_music is a no-op while the intro is still playing."""
    sm.register_sound("siren0", str(SAMPLE))
    sm.register_sound("siren0_firstloop", str(SAMPLE))
    sm.play_music("siren0")
    intro = sm._sounds["siren0_firstloop"]
    pending_before = sm._pending_loop

    sm.update_music()

    assert sm._pending_loop is pending_before
    # The channel still plays the intro, not the loop.
    assert sm._music_channel.get_sound() is intro


def test_stop_music_drops_pending_loop(sm: SoundManager) -> None:
    """stop_music clears the intro→loop chain entirely."""
    sm.register_sound("siren0", str(SAMPLE))
    sm.register_sound("siren0_firstloop", str(SAMPLE))
    sm.play_music("siren0")

    sm.stop_music()

    assert sm.current_music is None
    assert sm._pending_loop is None


def test_get_duration_ms_returns_positive(sm: SoundManager) -> None:
    """get_duration_ms reports the sound length in milliseconds."""
    sm.register_sound("ding", str(SAMPLE))

    assert sm.get_duration_ms("ding") > 0


def test_get_duration_ms_unknown_raises(sm: SoundManager) -> None:
    """Unknown sound durations raise KeyError, like play_sfx."""
    with pytest.raises(KeyError, match="not registered"):
        sm.get_duration_ms("missing")


# --- Pause / resume -----------------------------------------------


def test_pause_then_unpause_preserves_music_state(sm: SoundManager) -> None:
    """pause_all/unpause_all keep the tracked music alive and playing."""
    sm.register_sound("loop", str(SAMPLE))
    sm.play_music("loop")

    sm.pause_all()
    assert sm.current_music == "loop"

    sm.unpause_all()
    assert sm.current_music == "loop"
    assert sm._music_channel.get_sound() is sm._sounds["loop"]


def test_pause_unpause_when_idle_is_noop(sm: SoundManager) -> None:
    """Pausing/unpausing without any active sound is harmless."""
    sm.pause_all()
    sm.unpause_all()
    assert sm.current_music is None
