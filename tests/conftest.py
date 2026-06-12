"""Pytest setup shared by every test module.

Forces SDL into headless/dummy mode **before** Pygame is imported
anywhere else, so tests that touch :mod:`pygame.mixer` or
:mod:`pygame.display` work on systems without an audio device or
display (CI runners, locked-down containers).
"""

import os

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402

import pygame  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _pygame_session() -> Iterator[None]:
    """Initialise Pygame once for the whole test session."""
    pygame.init()
    yield
    pygame.quit()
