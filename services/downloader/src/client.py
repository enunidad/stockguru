from __future__ import annotations

from typing import Optional, Union, Any

import pandas as pd
import yfinance as yf

from .schemas import PriceHistoryRequest, TickerMetadata
from .exceptions import DownloaderClientError, EmptyDownloadError, InvalidTickerError

class YahooFinanceClient:

    @staticmethod
    def _ticker_history_helper(ticker: yf.Ticker, period: str = '10y', 
                                auto_adjust: bool = True, ) -> pd.DataFrame:
        """
        helper method. this one will aconnect with yfinance to get back the data

        Args:
            ticker (yf.Ticker): ticker object from yFinance
            period (str): how far back you you want price history. Deafult "10y" for 10 years.
            auto_adjust (bool): a flag for if prices have been subject to splits will normalize
                                the results. Defalt True.
        
        Returns:
            pd.DataFrame: the ticker history requested
        """
        try:
            data = ticker.history(
                period=period,
                interval='1d',
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
    

    def _ticker_metadata_helper(self, ticker: yf.Ticker) -> TickerMetadata:
        """
        helper method for getting metadata information

        Args:
            ticker (yf.Ticker): ticker object from yFinance

        Returns:
            TickerMetadata (object): the metadata information
        """
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
    

    @staticmethod
    def _as_optional_string(value: object) -> str | None:
        """
        Helper method for making json serializable strings

        Args:
            value (object): the object to be turned into a string
        
        Returns:
            str: JSON safe string
        """
        if value is None:
            return None

        return str(value)
    

    def _make_json_safe(self, value: Any, ) -> Any:
        """
        Helper method for turning any object into a string, recursively

        Args:
            value (object): can be any object, even nested dictionaries
        
        Returns:
            Any: JSON safe string
        """
        if value is None or isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, dict):
            return {str(key): self._make_json_safe(item) for key, item in value.items()}

        if isinstance(value, (list, tuple, set)):
            return [self._make_json_safe(item) for item in value ]

        return str(value)


    def download_metadata(self, request:PriceHistoryRequest, ) -> TickerMetadata:
        """
        Main function for getting metadata

        Args:
            request (PriceHistoryRequest): the requested information
        
        Returns:
            TickerMetadata: ticker metadata formatted to expected fields
        """
        symbol = self._normalize_ticker(request.ticker)
        ticker = yf.Ticker(symbol)

        metadata = self._ticker_metadata_helper(ticker)

        return metadata
    
    def download_price_history(self, request: PriceHistoryRequest, ) -> pd.DataFrame:
        """
        Main function for getting historical data. The client will always download a daily frequency
        but then aggregator will aggregate it to requested interval

        Args:
            request (PriceHistoryRequest): the requested information
        
        Returns:
            pd.DataFrame: the ticker historical prices
        """
        symbol = self._normalize_ticker(request.ticker)
        ticker = yf.Ticker(symbol)

        data = self._ticker_history_helper(
            ticker=ticker, 
            period=request.period, 
            interval='1d', 
            auto_adjust=request.auto_adjust
        )

        data = self._flatten_columns(data)
        data = self._standardize_index(data)

        if "Close" not in data.columns:
            raise InvalidTickerError(f"Downloaded data for ticker '{symbol}' is missing Close price.")

        return data

    @staticmethod
    def _normalize_ticker(ticker: str) -> str:
        """
        Helper method to standardize the ticker string input

        Args:
            ticker (str): the ticker being requested
        
        Returns:
            str: normalized string.
        """
        cleaned = ticker.strip().upper()

        if not cleaned:
            raise InvalidTickerError("Ticker cannot be empty.")

        return cleaned

    @staticmethod
    def _flatten_columns(data: pd.DataFrame) -> pd.DataFrame:
        """
        yfinance can sometimes return MultiIndex columns.
        For one ticker, flatten them back into simple column names.

        Args:
            data (pd.DataFrame): the dataframe to be flattened

        Returns:
            pd.DataFrame: dataframe with simple columns
        """
        if isinstance(data.columns, pd.MultiIndex):
            data = data.copy()
            data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]

        return data

    @staticmethod
    def _standardize_index(data: pd.DataFrame, ) -> pd.DataFrame:
        """
        Keep the date as the DataFrame index and give it
        a predictable name.

        Args:
            data (pd.DataFrame): the dataframe to be standardized
        
        Returns:
            pd.DataFrame: dataframe index set to something predictable
        """
        data = data.copy()
        data.index = pd.to_datetime(data.index)
        data.index.name = "Date"

        return data