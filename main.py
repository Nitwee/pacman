"""Web entry point used by Pygbag."""

import asyncio
from pathlib import Path
import sys
import zipfile


async def main() -> None:
    """Install the local maze package and start the web game."""
    if sys.platform == "emscripten":
        from web_compat import install

        install()
        wheel = Path("mazegen-0.2.0-py3-none-any.whl")
        with zipfile.ZipFile(wheel) as archive:
            archive.extractall(".")

    from app import App

    await App("config.json").run_async()


asyncio.run(main())
