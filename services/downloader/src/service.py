# services/downloader/src/downloader/service.py

from __future__ import annotations

import pandas as pd

from .client import YahooFinanceClient
from .schemas import PriceHistoryRequest


class DownloaderService:
    """
    Orchestration layer for the downloader service.

    For now, this simply delegates to the Yahoo Finance client.
    Later, this will handle:
    - cache checks
    - cache writes
    - ETL/cleaning
    - provider selection
    - service-level validation
    """

    def __init__(self, client: YahooFinanceClient | None = None) -> None:
        self.client = client or YahooFinanceClient()

    def get_price_history(
        self,
        ticker: str,
        period: str = "10y",
        interval: str = "1d",
        auto_adjust: bool = False,
    ) -> pd.DataFrame:
        request = PriceHistoryRequest(
            ticker=ticker,
            period=period,
            interval=interval,
            auto_adjust=auto_adjust,
        )

        return self.client.download_price_history(request)