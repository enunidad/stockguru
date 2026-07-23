# services/downloader/src/downloader/client.py

from __future__ import annotations

from typing import Optional

import pandas as pd
import yfinance as yf

from .schemas import PriceHistoryRequest, TickerMetadata
from .exceptions import DownloaderClientError, EmptyDownloadError, InvalidTickerError

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

    @staticmethod
    def _ticker_history_helper(ticker, period, interval, auto_adjust):
        try:
            data = ticker.history(
                period=period,
                interval=interval,
                auto_adjust=auto_adjust,
            )
        except Exception as exc:
            raise DownloaderClientError(
                f"Failed to download price history for ticker '{ticker.ticker}'."
            ) from exc

        if data is None or data.empty:
            raise EmptyDownloadError(
                f"No price history returned for ticker '{ticker.ticker}'."
            )
        
        return data
    
    def _ticker_metadata_helper(self, ticker):
        try:
            raw_metadata = dict(ticker.fast_info)
        except Exception as exc:
            raise DownloaderClientError(
                f"Failed to download metadata for ticker '{ticker.ticker}'."
            ) from exc

        return TickerMetadata(
            ticker=ticker.ticker,
            currency=self._as_optional_string(
                raw_metadata.get("currency"),
            ),
            exchange=self._as_optional_string(
                raw_metadata.get("exchange"),
            ),
            timezone=self._as_optional_string(
                raw_metadata.get("timezone"),
            ),
            quote_type=self._as_optional_string(
                raw_metadata.get("quoteType"),
            ),
            raw=self._make_json_safe(raw_metadata),
        )
    
    @staticmethod
    def _as_optional_string(value: object) -> str | None:
        if value is None:
            return None

        return str(value)
    
    @staticmethod
    def _make_json_safe(
        values: dict[str, Any],
    ) -> dict[str, Any]:
        json_safe: dict[str, Any] = {}

        for key, value in values.items():
            if value is None or isinstance(
                value,
                (str, int, float, bool),
            ):
                json_safe[key] = value
            else:
                json_safe[key] = str(value)

        return json_safe


    def download_price_history(
        self,
        request: PriceHistoryRequest,
    ) -> pd.DataFrame:
        symbol = self._normalize_ticker(request.ticker)
        ticker = yf.Ticker(symbol)

        data = self._ticker_history_helper(
            ticker=ticker, 
            period=request.period, 
            interval=request.interval, 
            auto_adjust=request.auto_adjust
        )

        metadata = self._ticker_metadata_helper(ticker)

        data = self._flatten_columns(data)
        data = self._standardize_index(data)

        if "Close" not in data.columns:
            raise InvalidTickerError(
                f"Downloaded data for ticker '{ticker}' is missing Close price."
            )

        return data, metadata

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