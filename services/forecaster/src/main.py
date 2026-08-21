from __future__ import annotations

from aiohttp import web

from .api import create_app
from .config import (
    ANALYZER_BASE_URL,
    DOWNLOADER_BASE_URL,
    HOST,
    PORT,
)


def main() -> None:
    """
    Start the StocksGuru Forecaster service.
    """
    app = create_app()

    web.run_app(
        app,
        host=HOST,
        port=PORT,
    )


if __name__ == "__main__":
    main()