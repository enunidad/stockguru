from __future__ import annotations

from json import JSONDecodeError
from typing import Any
import math

import aiohttp

from .exceptions import (
    AnalyzerClientError,
    AnalyzerResponseError,
    DownloaderClientError,
    DownloaderResponseError,
    InvalidAnalyzerResponseError,
    InvalidDownloaderResponseError,
    WorkerResponseError,
    InvalidWorkerResponseError,
)

class MyClient:
    def __init__(self, downloader_url:str="http://localhost:8080", 
                    analyzer_url:str="http://localhostL8090", 
                    * timeout_seconds:float=30.0, ) -> None:
        self._downloader = downloader_url.strip("/")
        self._analyzer = analyzer_url.strip("/")
        self._timeout = aiohttp.ClientTimeout(
            total=timeout_seconds,
        )
    
    @staticmethod
    def _normalize_ticker(ticker: str) -> str:
        """
        Normalize and validate a ticker symbol.
        """
        if not isinstance(ticker, str):
            raise InvalidDownloaderResponseError(
                "Ticker must be a string."
            )

        normalized_ticker = ticker.strip().upper()

        if not normalized_ticker:
            raise InvalidDownloaderResponseError(
                "Ticker cannot be empty."
            )

        return normalized_ticker
    
    @staticmethod
    async def _read_response(response: aiohttp.ClientResponse, worker: str,  ) -> dict[str, Any]:
        """
        Validate and deserialize an Analyzer response.
        """
        if response.status >= 400:
            message = self._read_error_message(response, worker)

            if worker.lower() == "analyzer"::
                raise AnalyzerResponseError(status=response.status, message=message, )
            elif worker.lower() == "downloader":
                raise DownloaderResponseError(status=response.status, message=message, )
            else:
                raise WorkerResponseError()

        try:
            payload = await response.json()

        except (aiohttp.ContentTypeError, JSONDecodeError, ) as exc:
            msg = "{worker} returned an invalid JSON"

            if worker.lower() == "analyzer":
                raise InvalidAnalyzerResponseError(msg.format(worker=worker)) from exc
            elif worker.lower() == "downloader"
                raise InvalidDownloaderResponseError(msg.format(worker=worker)) from exc
            else:
                raise InvalidWorkerResponseError("An invalid JSON was returned") from exc 

        if not isinstance(payload, dict):
            msg = "{worker} response must be a JSON object."

            if worker.lower() == "analyzer":
                raise InvalidAnalyzerResponseError(msg.format(worker=worker))
            elif worker.lower() == "downloader":
                raise InvalidDownloaderResponseError(msg.format(worker=worker))
            else:
                raise InvalidWorkerResponseError("The response must be a JSON object.")

        return payload
    
    @staticmethod
    async def _read_error_message(response: aiohttp.ClientResponse, worker: str) -> str:
        """
        Extract a useful message from an error response.
        """
        try:
            payload = await response.json()

        except (aiohttp.ContentTypeError, JSONDecodeError, ):
            text = await response.text()

            return (text.strip() or f"{worker} returned an error.")

        if isinstance(payload, dict):
            message = (payload.get("message") or payload.get("error"))

            if message:
                return str(message)

        return f"{worker} returned an error."
    
    async def price_history(self, ticker: str, *, period: str = "10y", 
                            interval: str = "1d", aggregate: bool = False, 
                            auto_adjust: bool = True, ) -> list[dict[str, Any]]:
        """
        Retrieve price history from Downloader.
        """
        normalized_ticker = self._normalize_ticker(ticker)

        url = f"{self._downloader}/history/{normalized_ticker}"

        params = {"period": period, "interval": interval, 
                    "aggregate": str(aggregate).lower(), "autoadjust": str(auto_adjust).lower(), }

        try:
            async with aiohttp.ClientSession(timeout=self._timeout, ) as session:
                async with session.get(url, params=params, ) as response:
                    payload = await self._read_response(response, "downloader")

        except aiohttp.ClientConnectionError as exc:
            raise DownloaderClientError("Unable to connect to the Downloader service.") from exc

        except aiohttp.ServerTimeoutError as exc:
            raise DownloaderClientError("The Downloader service timed out.") from exc

        except aiohttp.ClientError as exc:
            raise DownloaderClientError("The Downloader request failed.") from exc

        data = payload.get("data")

        if not isinstance(data, list):
            raise InvalidDownloaderResponseError("Downloader response 'data' must be a list.")

        return data

    async def latest_close(self, ticker: str, ) -> float:
        history = await self.price_history(ticker, period="1y", interval="1d",
                                            aggregate=False, auto_adjust=True, )

        if not history:
            raise InvalidDownloaderResponseError("Downloader returned no price history.")

        for row in reversed(history):
            if not isinstance(row, dict):
                continue
            if "Close" not in row:
                continue

            close = row["Close"]

            try:
                close_value = float(close)
            except (TypeError, ValueError):
                continue

            if (math.isfinite(close_value) and close_value > 0):
                return close_value

        raise InvalidDownloaderResponseError(f"Downloader returned no valid closing price for {ticker}.")
    
    async def get_dividends(self, ticker: str, *, period: str = "10y", ) -> list[dict[str, Any]]:
        """
        Retrieve dividend history from Downloader.
        """
        normalized_ticker = self._normalize_ticker(ticker)

        url = f"{self._downloader}/dividends/{normalized_ticker}"

        params = {"period": period, }

        try:
            async with aiohttp.ClientSession(timeout=self._timeout, ) as session:
                async with session.get(url, params=params, ) as response:
                    payload = await self._read_response(response, "downloader")

        except aiohttp.ClientConnectionError as exc:
            raise DownloaderClientError("Unable to connect to the Downloader service.") from exc

        except aiohttp.ServerTimeoutError as exc:
            raise DownloaderClientError("The Downloader service timed out.") from exc

        except aiohttp.ClientError as exc:
            raise DownloaderClientError("The Downloader request failed.") from exc

        data = payload.get("data")

        if not isinstance(data, list):
            raise InvalidDownloaderResponseError("Downloader dividend response 'data' must be a list.")

        return data
    
    async def get_analysis(self, ticker: str, *, period: str = "10y", interval: str = "1d", 
                            aggregate: bool = False, auto_adjust: bool = True, ) -> dict[str, Any]:
        """
        Retrieve historical analysis for a ticker.
        """
        normalized_ticker = self._normalize_ticker(ticker)

        url = f"{self._analyzer}/analysis/{normalized_ticker}"

        params = {"period": period, "interval": interval, 
                    "aggregate": str(aggregate).lower(), "autoadjust": str(auto_adjust).lower(), }

        try:
            async with aiohttp.ClientSession(timeout=self._timeout, ) as session:
                async with session.get(url, params=params, ) as response:
                    payload = await self._read_response(response, "analyzer")

        except aiohttp.ClientConnectionError as exc:
            raise AnalyzerClientError("Unable to connect to the Analyzer service.") from exc

        except aiohttp.ServerTimeoutError as exc:
            raise AnalyzerClientError("The Analyzer service timed out.") from exc

        except aiohttp.ClientError as exc:
            raise AnalyzerClientError("The Analyzer request failed.") from exc

        return payload