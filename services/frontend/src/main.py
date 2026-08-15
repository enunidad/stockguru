from __future__ import annotations

from aiohttp import web

from .app import create_app
from .client import AnalyzerApiClient, DownloaderApiClient, ChartMgrApiClient
from .config import ANALYZER_BASE_URL, DOWNLOADER_BASE_URL, CHARTMGR_BASE_URL, HOST, PORT


def main() -> None:
    """Configure and start the frontend HTTP service."""

    downloader_client = DownloaderApiClient(base_url=DOWNLOADER_BASE_URL, )

    analyzer_client = AnalyzerApiClient(base_url=ANALYZER_BASE_URL, )

    chartmgr_client = ChartMgrApiClient(base_url=CHARTMGR_BASE_URL, )

    app = create_app(downloader_client=downloader_client, analyzer_client=analyzer_client, 
                        chartmgr_client=chartmgr_client)

    web.run_app(app, host=HOST, port=PORT, )


if __name__ == "__main__":
    main()