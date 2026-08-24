# services/downloader/src/downloader/service.py

from __future__ import annotations

from dataclasses import asdict
import pandas as pd
from pathlib import Path
from datetime import timedelta
from typing import Any

from .client import YahooFinanceClient
from .aggregator import HistoricalAggregator
from .schemas import PriceHistoryRequest
from .cache import DownloaderCache


class DownloaderService:
    def __init__(self, client: YahooFinanceClient | None = None,
                cache: DownloaderCache | None = None, ) -> None:
        self.client = client or YahooFinanceClient()
        self.cache = cache or DownloaderCache(cache_dir=Path("data"), ttl=timedelta(days=1),)
    
    @staticmethod
    def _filter_period(data: pd.DataFrame, period: str, ) -> pd.DataFrame:
        if period == "10y":
            return data

        supported_periods = {"1y": 1, "2y": 2, "5y": 5, }

        years = supported_periods.get(period)

        if years is None:
            raise ValueError(f"Unsupported period '{period}'.")

        latest_date = data.index.max()
        cutoff_date = latest_date - pd.DateOffset(years=years)

        return data.loc[data.index >= cutoff_date]
    
    @staticmethod
    def _filter_dividend_period(dividends: pd.Series, period: str, ) -> pd.Series:
        """
        Filter dividend history to the requested period.
        """
        if dividends.empty:
            return dividends

        supported_periods = {"1y": 1, "2y": 2, "5y": 5, "10y": 10, }

        years = supported_periods.get(period)

        if years is None:
            raise ValueError(f"Unsupported period '{period}'.")

        latest_date = dividends.index.max()

        cutoff_date = (latest_date - pd.DateOffset(years=years))

        return dividends.loc[dividends.index >= cutoff_date]
    
    def _download_and_save(self, request:PriceHistoryRequest, kind:str|None=None) -> Any:
        data = self.client.download(request)
        self.cache.save(request, data)
        return self.cache.load(request, kind)

    def get_metadata(self, ticker: str, period: str = "10y",  interval: str = "1mo", 
                            auto_adjust: bool = True, aggregate: bool = True,  ) -> dict:
        
        request = PriceHistoryRequest(ticker=ticker, period="10y", interval="1d", 
                                        auto_adjust=auto_adjust, aggregate=aggregate)

        cached_metadata = self.cache.get_if_fresh(request, "metadata")
        if cached_metadata is not None:
            return asdict(cached_metadata)
        metadata = self._download_and_save(request, "metadata")
        return asdict(metadata)
    
    def get_price_history(self, ticker: str, period: str = "10y",  interval: str = "1mo", 
                            auto_adjust: bool = True, aggregate: bool = True, ) -> pd.DataFrame:
        
        request = PriceHistoryRequest(ticker=ticker, period="10y", interval="1d", 
                                        auto_adjust=auto_adjust, aggregate=aggregate)

        cached_history = self.cache.get_if_fresh(request)
        if cached_history is not None:
            to_return = cached_history
        else:
            to_return = self._download_and_save(request)
        
        to_return = self._filter_period(to_return, period, )
        
        if aggregate:
            aggregator = HistoricalAggregator()
            to_return = aggregator.aggregate(df=to_return, interval=interval)

        return to_return
    
    def get_dividends(self, ticker: str, period: str = "10y",  interval: str = "1mo", 
                            auto_adjust: bool = True, aggregate: bool = True, ) -> pd.Series:
        request = PriceHistoryRequest(ticker=ticker, period="10y", interval="1d", 
                                        auto_adjust=auto_adjust, aggregate=aggregate)

        dividends = self.cache.get_if_fresh(request, "dividends")
        if dividends is not None:
            to_return = dividends
        else:
            to_return = self._download_and_save(request, "dividends")

        return self._filter_dividend_period(to_return, period, )