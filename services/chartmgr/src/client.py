from __future__ import annotations

from json import JSONDecodeError
from typing import Any

import aiohttp

from .exceptions import (
    DownloaderClientError,
    DownloaderResponseError,
    InvalidDownloaderResponseError,
)
from .schemas import ChartRequest


class DownloaderApiClient:
    """HTTP client for the StocksGuru downloader service."""

    def __init__(self, base_url: str = "http://localhost:8080", *, timeout_seconds: float = 30.0, ) -> None:
        """
        initializes the connection to downloader

        Args:
            base_url (str): The root url where the downloader api is active
            timeout_seconds (float): duration to wait for a response

        Returns:
            None
        """
        self._base_url = base_url.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds, )
    
    @staticmethod
    def _normalize_ticker(ticker: str, ) -> str:
        """
        helper method on standaradizing ticker inputs

        Args:
            ticker (str): the symbol for the stock requested
        
        Returns:
            str: The standardized ticker string
        
        Raises:
            InvalidDownloaderResponseError: If the passed value is not a string or an empty string
        """
        if not isinstance(ticker, str):
            raise InvalidDownloaderResponseError("Ticker must be a string.")

        normalized_ticker = ticker.strip().upper()

        if not normalized_ticker:
            raise InvalidDownloaderResponseError("Ticker cannot be empty.")

        return normalized_ticker
    
    async def price_history(self, req: ChartRequest) -> list[dict[str, Any]] :
        normalized_ticker = self._normalize_ticker(req.ticker)

        url = (f"{self._base_url}/history/{normalized_ticker}")

        params = {"period": req.period, "interval": req.interval, 
                    "aggregate":str(req.aggregate).lower(), "auto_adjust": str(req.auto_adjust).lower(), }

        try:
            async with aiohttp.ClientSession(timeout=self._timeout, ) as session:
                async with session.get(url, params=params, ) as response:
                    payload = await self._read_response(response, )

        except aiohttp.ClientConnectionError as exc:
            raise DownloaderClientError("Unable to connect to the downloader service.") from exc

        except aiohttp.ServerTimeoutError as exc:
            raise DownloaderClientError("The downloader service timed out.") from exc

        except aiohttp.ClientError as exc:
            raise DownloaderClientError("The downloader request failed.") from exc

        return payload['data']

class AnalyzerApiClient:
    """HTTP client for the StocksGuru downloader service."""

    def __init__(self, base_url: str = "http://localhost:8090", *, timeout_seconds: float = 30.0, ) -> None:
        """
        initializes the connection to analyzer

        Args:
            base_url (str): The root url where the downloader api is active
            timeout_seconds (float): duration to wait for a response

        Returns:
            None
        """
        self._base_url = base_url.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds, )