# services/downloader/src/downloader/service.py

from __future__ import annotations

from dataclasses import asdict
import pandas as pd
from pathlib import Path
from datetime import timedelta

from .client import YahooFinanceClient
from .aggregator import HistoricalAggregator
from .schemas import PriceHistoryRequest
from .cache import PriceHistoryCache, TickerMetadataCache


class DownloaderService:
    """
    Orchestration layer for the downloader service.
    """

    def __init__(self, client: YahooFinanceClient | None = None,
                cache: PriceHistoryCache | None = None,
                metadata: TickerMetadataCache | None = None, ) -> None:
        self.client = client or YahooFinanceClient()
        self.cache = cache or PriceHistoryCache(cache_dir=Path("data"),
                                                ttl=timedelta(days=1),)
        self.metadata = metadata or TickerMetadataCache(cache_dir=Path("data"),
                                                        ttl=timedelta(days=1),)

    def get_metadata(self, ticker:str, ) -> dict:
        """
        metadata cache and retrieval

        Args:
            ticker (str): the ticker being requested
        
        Returns:
            dict: the metadata dataclass as a dict foreasy use by api
        """
        request = PriceHistoryRequest(ticker=ticker, )
        
        cached_metadata = self.metadata.get_if_fresh(ticker)
        if cached_metadata is not None:
            return asdict(cached_metadata)
        
        metadata = self.client.download_metadata(request)
        self.metadata.save(metadata)
        return asdict(metadata)
    
    def get_price_history(self, ticker: str, period: str = "10y",  interval: str = "1mo", 
                            auto_adjust: bool = True, aggregate: bool = False, ) -> pd.DataFrame:
        """
        price history cache and retrieval

        Args:
            ticker (str): the ticker name being requested
            period (str): how far back the data comes from. Default "10y"
            interval (str): How the data should be reported. Default "1mo"
            auto_adjust (bool): adjust if the stock went through splits. Default True.
            aggregate (bool): flag for aggregating interval data. if False, the returned
                                data will just be the boundaries of periods. Default True.
                                e.g.: interval = "1mo", aggregate = False returns just the
                                OHLC for the start of the month. aggregate = True will return
                                OHLC values for the month itself regardles of when it 
                                happens during the month
        """
        request = PriceHistoryRequest(ticker=ticker, period='10y', 
                                        interval='1d', auto_adjust=auto_adjust, )

        cached_history = self.cache.get_if_fresh(request)
        if cached_history is not None:
            to_return = cached_history
        else:
            data = self.client.download_price_history(request)
            self.cache.save(request,  data)
            to_return = data
        
        if aggregate:
            aggregator = HistoricalAggregator()
            to_return = aggregator.aggregate(df=to_return, interval=interval)

        return to_return