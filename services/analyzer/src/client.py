from __future__ import annotations

from json import JSONDecodeError
from typing import Any

import aiohttp

from .exceptions import (
    DownloaderClientError,
    DownloaderResponseError,
    InvalidDownloaderResponseError,
)
from .schemas import PriceHistory


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

    async def get_price_history(
        self,
        ticker: str,
        *,
        period: str = "10y",
        interval: str = "1d",
    ) -> PriceHistory:
        """
        Retrieve historical price data from the downloader service.

        Args:
            ticker:
                Stock ticker symbol, such as ``AAPL``.
            period:
                Requested historical period, such as ``1y`` or ``10y``.
            interval:
                Requested observation interval, such as ``1d``.

        Returns:
            Parsed and validated price history.

        Raises:
            DownloaderClientError:
                If the downloader cannot be reached.
            DownloaderResponseError:
                If the downloader returns an unsuccessful HTTP status.
            InvalidDownloaderResponseError:
                If the downloader returns malformed or unexpected data.
        """
        normalized_ticker = self._normalize_ticker(ticker)

        url = (
            f"{self._base_url}/history/"
            f"{normalized_ticker}"
        )

        params = {
            "period": period,
            "interval": interval,
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
                        response,
                    )

        except aiohttp.ClientConnectionError as exc:
            raise DownloaderClientError(
                "Unable to connect to the downloader service."
            ) from exc

        except aiohttp.ServerTimeoutError as exc:
            raise DownloaderClientError(
                "The downloader service timed out."
            ) from exc

        except aiohttp.ClientError as exc:
            raise DownloaderClientError(
                "The downloader request failed."
            ) from exc

        return self._parse_price_history(payload)

    @staticmethod
    def _normalize_ticker(
        ticker: str,
    ) -> str:
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
    async def _read_response(
        response: aiohttp.ClientResponse,
    ) -> dict[str, Any]:
        if response.status >= 400:
            message = await DownloaderApiClient._read_error_message(
                response,
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

    @staticmethod
    def _parse_price_history(
        payload: dict[str, Any],
    ) -> PriceHistory:
        try:
            history = PriceHistory.from_dict(payload)

        except (
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise InvalidDownloaderResponseError(
                "Downloader returned an invalid price-history response."
            ) from exc

        if not history.rows:
            raise InvalidDownloaderResponseError(
                "Downloader returned no price-history rows."
            )

        return history