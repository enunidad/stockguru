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
                    "aggregate":str(req.aggregate).lower(), "autoadjust": str(req.auto_adjust).lower(), }

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

        data = payload.get('data')
        if not isinstance(data, list):
            raise InvalidDownloaderResponseError("Downloader response 'data' must be a list.")
        
        return payload['data']
    
    @staticmethod
    async def _read_response(response: aiohttp.ClientResponse, ) -> dict[str, Any]:
        """
        helper method on validating expected datatype return

        Args:
            response (aiohttp.ClientResponse): The response to be validated
        
        Returns:
            dict[str, Any]: The validated response
        
        Raises:
            DownloaderResponseError: If the response status to be validated is less than 400
            InvalidDownloaderResponseError: If the response is an invalid json or is not a json.
        """
        if response.status >= 400:
            message = await DownloaderApiClient._read_error_message(response, )

            raise DownloaderResponseError(status=response.status, message=message, )

        try:
            payload = await response.json()

        except (aiohttp.ContentTypeError, JSONDecodeError, ) as exc:
            raise InvalidDownloaderResponseError("Downloader returned invalid JSON.") from exc

        if not isinstance(payload, dict):
            raise InvalidDownloaderResponseError("Downloader response must be a JSON object.")

        return payload
    
    @staticmethod
    async def _read_error_message(response: aiohttp.ClientResponse, ) -> str:
        """
        helper method in reading error responses

        Args:
            response (aiohttp:ClientResponse): the error response to be read

        Returns:
            str: The message for the error that occured
        """
        try:
            payload = await response.json()

        except (aiohttp.ContentTypeError, JSONDecodeError, ):
            text = await response.text()

            return (text.strip() or "Downloader returned an error.")

        if isinstance(payload, dict):
            message = (payload.get("message") or payload.get("error"))

            if message:
                return str(message)

        return "Downloader returned an error."

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