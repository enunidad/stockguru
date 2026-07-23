from __future__ import annotations

import os

from aiohttp import web

from .api import create_app


def main() -> None:
    """Start the analyzer HTTP service."""
    downloader_base_url = os.getenv(
        "DOWNLOADER_BASE_URL",
        "http://localhost:8080",
    )

    host = os.getenv(
        "ANALYZER_HOST",
        "0.0.0.0",
    )

    port = int(
        os.getenv(
            "ANALYZER_PORT",
            "8090",
        )
    )

    app = create_app(
        downloader_base_url=downloader_base_url,
    )

    web.run_app(
        app,
        host=host,
        port=port,
    )


if __name__ == "__main__":
    main()