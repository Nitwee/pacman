"""Interactive sprite coordinate picker for the AssetManager.

Helps identify ``(x, y, width, height)`` rects in a sprite sheet so
they can be passed to :meth:`AssetManager.register_sprite`.

Run::

    python3 tools/sprite_picker.py path/to/sheet.png

Inputs::

    Mouse drag       Define a rectangle (red overlay).
    Shift + drag     Snap rect corners to the 16x16 grid.
    Enter            Print the current rect to stdout.
    G                Toggle 16x16 grid overlay.
    + / -            Zoom in / out (1x..4x).
    Arrows           Pan the view when zoomed in.
    Esc              Quit.
"""

import sys
from typing import Optional

import pygame


CELL_SIZE = 16
DEFAULT_ZOOM = 2
MIN_ZOOM = 1
MAX_ZOOM = 4
WINDOW_W = 1024
WINDOW_H = 768
HUD_H = 32
PAN_STEP = 32

GRID_COLOR = (60, 60, 60)
SELECTION_COLOR = (255, 50, 50)
HUD_COLOR = (200, 200, 200)
HUD_BG = (0, 0, 0)


def _snap_to_grid(value: int, *, ceil: bool = False) -> int:
    """Snap a coordinate to the 16-pixel grid.

    Args:
        value: Raw coordinate in sheet pixels.
        ceil: Round up instead of down.

    Returns:
        The snapped coordinate.
    """
    if ceil:
        return ((value + CELL_SIZE - 1) // CELL_SIZE) * CELL_SIZE
    return (value // CELL_SIZE) * CELL_SIZE


def _to_sheet_coords(
    mouse_pos: tuple[int, int],
    view_x: int,
    view_y: int,
    zoom: int,
) -> tuple[int, int]:
    """Convert a window pixel into a sheet pixel."""
    mx, my = mouse_pos
    return (view_x + mx // zoom, view_y + my // zoom)


def _draw_grid(
    screen: pygame.Surface,
    view_x: int,
    view_y: int,
    zoom: int,
    visible_w: int,
    visible_h: int,
) -> None:
    """Draw a 16-pixel grid overlay on the visible region."""
    first_x = -(view_x % CELL_SIZE)
    first_y = -(view_y % CELL_SIZE)
    for gx in range(first_x, visible_w + 1, CELL_SIZE):
        pygame.draw.line(
            screen,
            GRID_COLOR,
            (gx * zoom, 0),
            (gx * zoom, visible_h * zoom),
        )
    for gy in range(first_y, visible_h + 1, CELL_SIZE):
        pygame.draw.line(
            screen,
            GRID_COLOR,
            (0, gy * zoom),
            (visible_w * zoom, gy * zoom),
        )


def _draw_selection(
    screen: pygame.Surface,
    rect: tuple[int, int, int, int],
    view_x: int,
    view_y: int,
    zoom: int,
) -> None:
    """Outline the current selection rect on screen."""
    rx, ry, rw, rh = rect
    vx = (rx - view_x) * zoom
    vy = (ry - view_y) * zoom
    pygame.draw.rect(
        screen,
        SELECTION_COLOR,
        (vx, vy, rw * zoom, rh * zoom),
        2,
    )


def _draw_hud(
    screen: pygame.Surface,
    font: pygame.font.Font,
    cursor: tuple[int, int],
    view: tuple[int, int],
    zoom: int,
    show_grid: bool,
    rect: Optional[tuple[int, int, int, int]],
) -> None:
    """Render the bottom HUD with cursor info and current rect."""
    pygame.draw.rect(
        screen, HUD_BG, (0, WINDOW_H - HUD_H, WINDOW_W, HUD_H)
    )
    grid_state = "on" if show_grid else "off"
    text = (
        f"cursor=({cursor[0]},{cursor[1]})  "
        f"view=({view[0]},{view[1]})  "
        f"zoom={zoom}x  grid={grid_state}  "
        f"rect={rect if rect else '-'}"
    )
    surf = font.render(text, True, HUD_COLOR)
    screen.blit(surf, (8, WINDOW_H - HUD_H + 8))


def main(sheet_path: str) -> int:
    """Run the sprite picker against ``sheet_path``.

    Args:
        sheet_path: Path to the sprite sheet image.

    Returns:
        Process exit code (0 on normal termination).
    """
    pygame.init()
    try:
        sheet = pygame.image.load(sheet_path)
        sheet_w, sheet_h = sheet.get_size()
        screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption(f"Sprite picker - {sheet_path}")
        font = pygame.font.SysFont(None, 18)
        clock = pygame.time.Clock()

        zoom = DEFAULT_ZOOM
        view_x = 0
        view_y = 0
        show_grid = True
        drag_start: Optional[tuple[int, int]] = None
        rect: Optional[tuple[int, int, int, int]] = None

        running = True
        while running:
            mods = pygame.key.get_mods()
            visible_w = WINDOW_W // zoom
            visible_h = (WINDOW_H - HUD_H) // zoom

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    continue
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_g:
                        show_grid = not show_grid
                    elif event.key in (pygame.K_PLUS, pygame.K_EQUALS):
                        zoom = min(zoom + 1, MAX_ZOOM)
                    elif event.key == pygame.K_MINUS:
                        zoom = max(zoom - 1, MIN_ZOOM)
                    elif event.key == pygame.K_LEFT:
                        view_x = max(0, view_x - PAN_STEP)
                    elif event.key == pygame.K_RIGHT:
                        view_x = min(
                            max(0, sheet_w - visible_w),
                            view_x + PAN_STEP,
                        )
                    elif event.key == pygame.K_UP:
                        view_y = max(0, view_y - PAN_STEP)
                    elif event.key == pygame.K_DOWN:
                        view_y = min(
                            max(0, sheet_h - visible_h),
                            view_y + PAN_STEP,
                        )
                    elif event.key == pygame.K_RETURN and rect:
                        print(
                            f"({rect[0]}, {rect[1]}, "
                            f"{rect[2]}, {rect[3]})"
                        )
                elif (
                    event.type == pygame.MOUSEBUTTONDOWN
                    and event.button == 1
                    and event.pos[1] < WINDOW_H - HUD_H
                ):
                    sx, sy = _to_sheet_coords(
                        event.pos, view_x, view_y, zoom
                    )
                    if mods & pygame.KMOD_SHIFT:
                        sx = _snap_to_grid(sx)
                        sy = _snap_to_grid(sy)
                    drag_start = (sx, sy)
                    rect = None
                elif (
                    event.type == pygame.MOUSEBUTTONUP
                    and event.button == 1
                    and drag_start is not None
                ):
                    sx, sy = _to_sheet_coords(
                        event.pos, view_x, view_y, zoom
                    )
                    if mods & pygame.KMOD_SHIFT:
                        sx = _snap_to_grid(sx, ceil=True)
                        sy = _snap_to_grid(sy, ceil=True)
                    x0, y0 = drag_start
                    x = min(x0, sx)
                    y = min(y0, sy)
                    w = abs(sx - x0)
                    h = abs(sy - y0)
                    if w > 0 and h > 0:
                        rect = (x, y, w, h)
                        print(f"({x}, {y}, {w}, {h})")
                    drag_start = None

            sub_w = min(visible_w, sheet_w - view_x)
            sub_h = min(visible_h, sheet_h - view_y)
            sub = sheet.subsurface(
                pygame.Rect(view_x, view_y, sub_w, sub_h)
            )
            scaled = pygame.transform.scale(
                sub, (sub_w * zoom, sub_h * zoom)
            )

            screen.fill((0, 0, 0))
            screen.blit(scaled, (0, 0))

            if show_grid:
                _draw_grid(
                    screen, view_x, view_y, zoom, sub_w, sub_h
                )
            if rect:
                _draw_selection(screen, rect, view_x, view_y, zoom)

            cursor = _to_sheet_coords(
                pygame.mouse.get_pos(), view_x, view_y, zoom
            )
            _draw_hud(
                screen,
                font,
                cursor,
                (view_x, view_y),
                zoom,
                show_grid,
                rect,
            )

            pygame.display.flip()
            clock.tick(60)
    finally:
        pygame.quit()
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Usage: python3 tools/sprite_picker.py path/to/sheet.png",
            file=sys.stderr,
        )
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
