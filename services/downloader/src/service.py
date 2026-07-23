# services/downloader/src/downloader/service.py

from __future__ import annotations

import pandas as pd
from pathlib import Path
from datetime import timedelta

from .client import YahooFinanceClient
from .schemas import PriceHistoryRequest
from .cache import PriceHistoryCache, TickerMetadataCache


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

    def __init__(self, client: YahooFinanceClient | None = None,
                cache: PriceHistoryCache | None = None,
                metadata: TickerMetadataCache | None = None) -> None:
        self.client = client or YahooFinanceClient()
        self.cache = cache or PriceHistoryCache(cache_dir=Path("data"),
                                                ttl=timedelta(days=1),)
        self.metadata = metadata or TickerMetadataCache(cache_dir=Path("data"),
                                                        ttl=timedelta(days=1),)

    def get_price_history(
        self,
        ticker: str,
        period: str = "10y",
        interval: str = "1mo",
        auto_adjust: bool = False,
    ) -> pd.DataFrame:
        request = PriceHistoryRequest(
            ticker=ticker,
            period=period,
            interval=interval,
            auto_adjust=auto_adjust,
        )

        cached_history = self.cache.get_if_fresh(request)
        if cached_history is not None:
            cached_metadata = self.metadata.get_if_fresh(ticker)
            return cached_history, cached_metadata
        
        data, metadata = self.client.download_price_history(request)
        self.cache.save(request,  data)
        self.metadata.save(metadata)
        return data, metadata