"""Pac-Man entry point.

Validates the single CLI argument (config file path) and launches the
:class:`App` orchestrator.

When run as a PyInstaller bundle (``sys.frozen`` is set), the working
directory is changed to the resource directory (``sys._MEIPASS``) so
that all relative asset and config paths resolve correctly without any
changes to the rest of the codebase.  A missing ``config.json``
argument is also supplied automatically in that context.
"""

import os
import sys

# -- PyInstaller compatibility ----------------------------------------
# Must happen before importing App so that module-level Path constants
# in app.py, audio/setup.py, etc. are evaluated in the right directory.
# App itself is imported inside main(), after argv validation, so usage
# errors stay quiet and do not print Pygame's import banner.
if getattr(sys, "frozen", False):
    _base: str = str(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)))
    os.chdir(_base)
    if len(sys.argv) == 1:
        sys.argv.append("config.json")
# ---------------------------------------------------------------------


def main() -> int:
    """Parse argv and start the application.

    Returns:
        Process exit code: ``0`` on success, ``1`` on usage error.
    """
    if len(sys.argv) != 2:
        print(
            "Program must be launched as followed:\n"
            "python3 pac-man.py config.json"
        )
        return 1
    from app import App

    App(sys.argv[1]).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
