from __future__ import annotations

import os

from aiohttp import web

from .api import create_app
from .config import DOWNLOADER_BASE_URL, HOST, PORT


def main() -> None:
    """Start the analyzer HTTP service."""
    app = create_app(downloader_base_url=DOWNLOADER_BASE_URL, )

    web.run_app(app, host=HOST, port=PORT, )


if __name__ == "__main__":
    main()