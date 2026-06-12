"""Registration catalogue for every sound shipped with the game.

A single :func:`setup` call from :class:`app.App` populates the
:class:`audio.manager.SoundManager` with every WAV in
:file:`assets/sounds/`. Even sounds that are not played yet (extra
life, fruit, intermission second-loop variants) are registered so
that adding them later is a one-line consumer change with no setup
churn.
"""

from pathlib import Path

from audio.manager import SoundManager

SOUNDS_DIR = Path("assets/sounds")

# Names mirror the filenames on disk (without the ``.wav`` suffix).
_SOUND_NAMES: tuple[str, ...] = (
    # One-shot SFX
    "credit",
    "eat_dot_0",
    "eat_dot_1",
    "eat_fruit",
    "eat_ghost",
    "death_0",
    "death_1",
    "extend",
    "start",
    "intermission",
    # Background loops with their intro-only variants
    "fright",
    "fright_firstloop",
    "eyes",
    "eyes_firstloop",
    "siren0",
    "siren0_firstloop",
    "siren1",
    "siren1_firstloop",
    "siren2",
    "siren2_firstloop",
    "siren3",
    "siren3_firstloop",
    "siren4",
    "siren4_firstloop",
)


def setup(sm: SoundManager) -> None:
    """Register every game sound on ``sm``.

    Args:
        sm: The SoundManager instantiated by :class:`app.App`.
    """
    for name in _SOUND_NAMES:
        sm.register_sound(name, str(SOUNDS_DIR / f"{name}.wav"))
