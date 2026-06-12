"""Display sizes shared by the app and options screen."""

Resolution = tuple[int, int]

CANVAS_SIZE: Resolution = (1000, 900)
DEFAULT_WINDOW_SIZE: Resolution = CANVAS_SIZE
WINDOWED_RESOLUTIONS: tuple[Resolution, ...] = (
    (800, 720),
    (1000, 900),
    (1280, 960),
)


def resolution_label(resolution: Resolution) -> str:
    """Return a readable resolution label."""
    width, height = resolution
    return f"{width}x{height}"
