from __future__ import annotations

import pandas as pd
from typing import Any

from .schemas import PriceHistoryRequest, TickerMetadata
from .exceptions import DownloaderClientError, EmptyDownloadError, InvalidTickerError

class YahooFinanceClient:

    def download(self, request: PriceHistoryRequest) -> dict[str, Any]:
        return {"metadata": self.download_metadata(request),
                "price_history": self.download_price_history(request),
                "dividends": self.download_dividends(request)}
    
    def download_metadata(self, request: PriceHistoryRequest, ) -> TickerMetadata:
        ticker = request.ticker
        try:
            fast_info = dict(ticker.fast_info)
            info = ticker.info or {}
        except Exception as exc:
            raise DownloaderClientError(f"Failed to download metadata for ticker '{ticker.ticker}'.") from exc

        return TickerMetadata(
            ticker=ticker.ticker,
            currency=self._as_optional_string(fast_info.get("currency") or info.get("currency"), ),
            exchange=self._as_optional_string(fast_info.get("exchange") or info.get("exchange"), ),
            timezone=self._as_optional_string(fast_info.get("timezone") or info.get("exchangeTimezoneName"), ),
            quote_type=self._as_optional_string(fast_info.get("quoteType") or info.get("quoteType"), ),

            name=self._as_optional_string(info.get("longName") or info.get("shortName"), ),
            sector=self._as_optional_string(info.get("sector"), ),
            industry=self._as_optional_string(info.get("industry"), ),
            country=self._as_optional_string(info.get("country"), ),

            raw=self._make_json_safe({"fast_info": fast_info, "info": info, }),
        )

    def download_price_history(self, request: PriceHistoryRequest, ) -> pd.DataFrame:
        ticker = request.ticker
        params = {"period": request.period,
                    "interval": request.interval,
                    "auto_adjust": request.auto_adjust,}

        try:
            data = ticker.history(**params)
        except Exception as exc:
            raise DownloaderClientError(f"Failed to download price history for ticker '{ticker.ticker}'." ) from exc

        if data is None or data.empty:
            raise EmptyDownloadError(f"No price history returned for ticker '{ticker.ticker}'.")

        data = self._flatten_columns(data)
        data = self._standardize_index(data)

        if "Close" not in data.columns:
            raise InvalidTickerError(f"Downloaded data for ticker '{ticker.ticker}' is missing Close price.")

        return data
    
    def download_dividends(self, request: PriceHistoryRequest, ) -> pd.Series:
        ticker = request.ticker
        try:
            dividends = ticker.get_dividends()
        except Exception as exc:
            raise DownloaderClientError(f"Failed to download dividends for ticker '{ticker.ticker}'.") from exc
        return dividends

    @staticmethod
    def _as_optional_string(value: object) -> str | None:
        if value is None:
            return None
        return str(value)
    
    def _make_json_safe(self, value: Any, ) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {str(key): self._make_json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._make_json_safe(item) for item in value ]
        return str(value)

    @staticmethod
    def _flatten_columns(data: pd.DataFrame) -> pd.DataFrame:
        if isinstance(data.columns, pd.MultiIndex):
            data = data.copy()
            data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]

        return data

    @staticmethod
    def _standardize_index(data: pd.DataFrame, ) -> pd.DataFrame:
        data = data.copy()
        data.index = pd.to_datetime(data.index)
        data.index.name = "Date"

        return data