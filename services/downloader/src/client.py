# services/downloader/src/downloader/client.py

from __future__ import annotations

from typing import Optional

import pandas as pd
import yfinance as yf

from .schemas import PriceHistoryRequest
from .exception import DownloaderClientError, EmptyDownloadError, InvalidTickerError

class YahooFinanceClient:
    """
    Thin client around yfinance.

    This class should not know anything about:
    - where files are saved
    - how data is cleaned
    - how data is cached
    - how the API works

    It only downloads raw market data.
    """

    def download_price_history(
        self,
        request: PriceHistoryRequest,
    ) -> pd.DataFrame:
        ticker = self._normalize_ticker(request.ticker)

        try:
            data = yf.download(
                tickers=ticker,
                period=request.period,
                interval=request.interval,
                auto_adjust=request.auto_adjust,
                progress=False,
                threads=False,
            )
        except Exception as exc:
            raise DownloaderClientError(
                f"Failed to download price history for ticker '{ticker}'."
            ) from exc

        if data is None or data.empty:
            raise EmptyDownloadError(
                f"No price history returned for ticker '{ticker}'."
            )

        data = self._flatten_columns(data)
        data = self._standardize_index(data)

        if "Close" not in data.columns:
            raise InvalidTickerError(
                f"Downloaded data for ticker '{ticker}' is missing Close price."
            )

        return data

    @staticmethod
    def _normalize_ticker(ticker: str) -> str:
        cleaned = ticker.strip().upper()

        if not cleaned:
            raise InvalidTickerError("Ticker cannot be empty.")

        return cleaned

    @staticmethod
    def _flatten_columns(data: pd.DataFrame) -> pd.DataFrame:
        """
        yfinance can sometimes return MultiIndex columns.
        For one ticker, flatten them back into simple column names.
        """
        if isinstance(data.columns, pd.MultiIndex):
            data = data.copy()
            data.columns = [
                col[0] if isinstance(col, tuple) else col
                for col in data.columns
            ]

        return data

    @staticmethod
    def _standardize_index(data: pd.DataFrame) -> pd.DataFrame:
        """
        Keep the raw data mostly untouched, but make the index predictable.
        """
        data = data.copy()
        data.index.name = "Date"
        return data