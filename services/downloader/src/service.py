# services/downloader/src/downloader/service.py

from __future__ import annotations

from dataclasses import asdict
import pandas as pd
from pathlib import Path
from datetime import timedelta

from .client import YahooFinanceClient
from .aggregator import HistoricalAggregator
from .schemas import PriceHistoryRequest
from .cache import PriceHistoryCache, TickerMetadataCache, DividendCache


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
        self.divedend = dividend or DividendCache(cache_dir=Path("data"),
                                                    ttl=timedelta(days=1), )
    
    @staticmethod
    def _filter_period(
        data: pd.DataFrame,
        period: str,
    ) -> pd.DataFrame:
        if period == "10y":
            return data

        supported_periods = {
            "1y": 1,
            "2y": 2,
            "5y": 5,
        }

        years = supported_periods.get(period)

        if years is None:
            raise ValueError(
                f"Unsupported period '{period}'."
            )

        latest_date = data.index.max()
        cutoff_date = latest_date - pd.DateOffset(years=years)

        return data.loc[data.index >= cutoff_date]
    
    @staticmethod
    def _filter_dividend_period(
        dividends: pd.Series,
        period: str,
    ) -> pd.Series:
        """
        Filter dividend history to the requested period.
        """
        if dividends.empty:
            return dividends

        supported_periods = {
            "1y": 1,
            "2y": 2,
            "5y": 5,
            "10y": 10,
        }

        years = supported_periods.get(period)

        if years is None:
            raise ValueError(
                f"Unsupported period '{period}'."
            )

        latest_date = dividends.index.max()

        cutoff_date = (
            latest_date
            - pd.DateOffset(years=years)
        )

        return dividends.loc[
            dividends.index >= cutoff_date
        ]

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
                            auto_adjust: bool = True, aggregate: bool = True, ) -> pd.DataFrame:
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
                                        interval='1d', auto_adjust=auto_adjust, aggregate=aggregate)

        cached_history = self.cache.get_if_fresh(request)
        if cached_history is not None:
            to_return = cached_history
        else:
            data = self.client.download_price_history(request)
            self.cache.save(request,  data)
            to_return = data
        
        to_return = self._filter_period(to_return, period, )
        
        if aggregate:
            aggregator = HistoricalAggregator()
            to_return = aggregator.aggregate(df=to_return, interval=interval)

        return to_return
    
    def get_dividends(
        self,
        ticker: str,
        period: str = "10y",
    ) -> pd.Series:
        """
        Retrieve dividend history for a ticker.

        Cached dividend history is preferred. If no cached
        history exists, download it and populate the cache.
        """
        ticker = ticker.strip().upper()

        dividends = self.cache.get_dividends(
            ticker
        )

        if dividends is None:
            dividends = self.client.download_dividends(
                ticker
            )

            self.cache.save_dividends(
                ticker,
                dividends,
            )

        return self._filter_dividend_period(
            dividends,
            period,
        )