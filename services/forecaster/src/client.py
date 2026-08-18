from __future__ import annotations

from json import JSONDecodeError
from typing import Any

import aiohttp

from .exceptions import (
    DownloaderClientError,
    DownloaderResponseError,
    InvalidDownloaderResponseError,
)


class DownloaderApiClient:
    """HTTP client for the StocksGuru downloader service."""

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
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

    async def price_history(
        self,
        ticker: str,
        *,
        period: str = "10y",
        interval: str = "1d",
        aggregate: bool = False,
        auto_adjust: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Retrieve price history from Downloader.
        """
        normalized_ticker = self._normalize_ticker(ticker)

        url = (
            f"{self._base_url}/history/"
            f"{normalized_ticker}"
        )

        params = {
            "period": period,
            "interval": interval,
            "aggregate": str(aggregate).lower(),
            "autoadjust": str(auto_adjust).lower(),
        }

        try:
            async with aiohttp.ClientSession(
                timeout=self._timeout,
            ) as session:
                async with session.get(
                    url,
                    params=params,
                ) as response:
                    payload = await self._read_response(response)

        except aiohttp.ClientConnectionError as exc:
            raise DownloaderClientError(
                "Unable to connect to the Downloader service."
            ) from exc

        except aiohttp.ServerTimeoutError as exc:
            raise DownloaderClientError(
                "The Downloader service timed out."
            ) from exc

        except aiohttp.ClientError as exc:
            raise DownloaderClientError(
                "The Downloader request failed."
            ) from exc

        data = payload.get("data")

        if not isinstance(data, list):
            raise InvalidDownloaderResponseError(
                "Downloader response 'data' must be a list."
            )

        return data

    async def latest_close(
        self,
        ticker: str,
    ) -> float:
        """
        Retrieve the most recent closing price for a ticker.
        """
        history = await self.price_history(
            ticker,
            period="1y",
            interval="1d",
            aggregate=False,
            auto_adjust=True,
        )

        if not history:
            raise InvalidDownloaderResponseError(
                "Downloader returned no price history."
            )

        latest = history[-1]

        if not isinstance(latest, dict):
            raise InvalidDownloaderResponseError(
                "Latest price history row must be an object."
            )

        close = latest.get("Close")

        if close is None:
            raise InvalidDownloaderResponseError(
                "Latest price history row is missing Close."
            )

        try:
            close_value = float(close)
        except (TypeError, ValueError) as exc:
            raise InvalidDownloaderResponseError(
                "Latest closing price must be numeric."
            ) from exc

        if close_value <= 0:
            raise InvalidDownloaderResponseError(
                "Latest closing price must be greater than zero."
            )

        return close_value
    
    async def get_dividends(
        self,
        ticker: str,
        *,
        period: str = "10y",
    ) -> list[dict[str, Any]]:
        """
        Retrieve dividend history from Downloader.
        """
        normalized_ticker = self._normalize_ticker(ticker)

        url = (
            f"{self._base_url}/dividends/"
            f"{normalized_ticker}"
        )

        params = {
            "period": period,
        }

        try:
            async with aiohttp.ClientSession(
                timeout=self._timeout,
            ) as session:
                async with session.get(
                    url,
                    params=params,
                ) as response:
                    payload = await self._read_response(
                        response
                    )

        except aiohttp.ClientConnectionError as exc:
            raise DownloaderClientError(
                "Unable to connect to the Downloader service."
            ) from exc

        except aiohttp.ServerTimeoutError as exc:
            raise DownloaderClientError(
                "The Downloader service timed out."
            ) from exc

        except aiohttp.ClientError as exc:
            raise DownloaderClientError(
                "The Downloader request failed."
            ) from exc

        data = payload.get("data")

        if not isinstance(data, list):
            raise InvalidDownloaderResponseError(
                "Downloader dividend response 'data' must be a list."
            )

        return data

    @staticmethod
    async def _read_response(
        response: aiohttp.ClientResponse,
    ) -> dict[str, Any]:
        """
        Validate and deserialize a Downloader response.
        """
        if response.status >= 400:
            message = await DownloaderApiClient._read_error_message(
                response
            )

            raise DownloaderResponseError(
                status=response.status,
                message=message,
            )

        try:
            payload = await response.json()

        except (
            aiohttp.ContentTypeError,
            JSONDecodeError,
        ) as exc:
            raise InvalidDownloaderResponseError(
                "Downloader returned invalid JSON."
            ) from exc

        if not isinstance(payload, dict):
            raise InvalidDownloaderResponseError(
                "Downloader response must be a JSON object."
            )

        return payload

    @staticmethod
    async def _read_error_message(
        response: aiohttp.ClientResponse,
    ) -> str:
        """
        Extract a useful message from a Downloader error response.
        """
        try:
            payload = await response.json()

        except (
            aiohttp.ContentTypeError,
            JSONDecodeError,
        ):
            text = await response.text()

            return (
                text.strip()
                or "Downloader returned an error."
            )

        if isinstance(payload, dict):
            message = (
                payload.get("message")
                or payload.get("error")
            )

            if message:
                return str(message)

        return "Downloader returned an error."

class AnalyzerApiClient:
    """HTTP client for the StocksGuru analyzer service."""

    def __init__(
        self,
        base_url: str = "http://localhost:8090",
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(
            total=timeout_seconds,
        )

    @staticmethod
    def _normalize_ticker(ticker: str) -> str:
        """
        Normalize and validate a ticker symbol.
        """
        if not isinstance(ticker, str):
            raise InvalidAnalyzerResponseError(
                "Ticker must be a string."
            )

        normalized_ticker = ticker.strip().upper()

        if not normalized_ticker:
            raise InvalidAnalyzerResponseError(
                "Ticker cannot be empty."
            )

        return normalized_ticker

    async def get_analysis(
        self,
        ticker: str,
        *,
        period: str = "10y",
        interval: str = "1d",
        aggregate: bool = False,
    ) -> dict[str, Any]:
        """
        Retrieve historical analysis for a ticker.
        """
        normalized_ticker = self._normalize_ticker(
            ticker
        )

        url = (
            f"{self._base_url}/analysis/"
            f"{normalized_ticker}"
        )

        params = {
            "period": period,
            "interval": interval,
            "aggregate": str(aggregate).lower(),
        }

        try:
            async with aiohttp.ClientSession(
                timeout=self._timeout,
            ) as session:
                async with session.get(
                    url,
                    params=params,
                ) as response:
                    payload = await self._read_response(
                        response
                    )

        except aiohttp.ClientConnectionError as exc:
            raise AnalyzerClientError(
                "Unable to connect to the Analyzer service."
            ) from exc

        except aiohttp.ServerTimeoutError as exc:
            raise AnalyzerClientError(
                "The Analyzer service timed out."
            ) from exc

        except aiohttp.ClientError as exc:
            raise AnalyzerClientError(
                "The Analyzer request failed."
            ) from exc

        return payload

    @staticmethod
    async def _read_response(
        response: aiohttp.ClientResponse,
    ) -> dict[str, Any]:
        """
        Validate and deserialize an Analyzer response.
        """
        if response.status >= 400:
            message = (
                await AnalyzerApiClient._read_error_message(
                    response
                )
            )

            raise AnalyzerResponseError(
                status=response.status,
                message=message,
            )

        try:
            payload = await response.json()

        except (
            aiohttp.ContentTypeError,
            JSONDecodeError,
        ) as exc:
            raise InvalidAnalyzerResponseError(
                "Analyzer returned invalid JSON."
            ) from exc

        if not isinstance(payload, dict):
            raise InvalidAnalyzerResponseError(
                "Analyzer response must be a JSON object."
            )

        return payload

    @staticmethod
    async def _read_error_message(
        response: aiohttp.ClientResponse,
    ) -> str:
        """
        Extract a useful message from an Analyzer error response.
        """
        try:
            payload = await response.json()

        except (
            aiohttp.ContentTypeError,
            JSONDecodeError,
        ):
            text = await response.text()

            return (
                text.strip()
                or "Analyzer returned an error."
            )

        if isinstance(payload, dict):
            message = (
                payload.get("message")
                or payload.get("error")
            )

            if message:
                return str(message)

        return "Analyzer returned an error."