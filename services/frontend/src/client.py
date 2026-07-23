from __future__ import annotations

from typing import Any

import aiohttp
from json import JSONDecodeError

from .exceptions import (
    ApiClientError,
    InvalidResponseError,
    ServiceUnavailableError,
)
from .schemas import PriceHistoryRequest


class DownloaderApiClient:
    """
    Thin HTTP client around the Downloader service.

    This class only handles communication with the Downloader API.
    """

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def get_price_history(
        self,
        request: PriceHistoryRequest,
    ) -> dict[str, Any]:
        url = f"{self._base_url}/history/{request.ticker}"

        params = {
            "period": request.period,
            "interval": request.interval,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()

        except aiohttp.ContentTypeError as exc:
            raise InvalidResponseError(
                "Downloader returned invalid JSON."
            ) from exc

        except JSONDecodeError as exc:
            raise InvalidResponseError(
                "Downloader returned invalid JSON."
            ) from exc

        except aiohttp.ClientConnectionError as exc:
            raise ServiceUnavailableError(
                "Unable to connect to Downloader service."
            ) from exc

        except aiohttp.ClientResponseError as exc:
            raise ApiClientError(
                f"Downloader returned HTTP {exc.status}."
            ) from exc

        self._validate_price_history(data)

        return data

    @staticmethod
    def _validate_price_history(data: Any) -> None:
        if not isinstance(data, dict):
            raise InvalidResponseError(
                "Downloader response must be a JSON object."
            )

        if "ticker" not in data:
            raise InvalidResponseError(
                "Missing ticker."
            )

        if "rows" not in data:
            raise InvalidResponseError(
                "Missing price history."
            )

class AnalyzerApiClient:
    """Client for the StocksGuru analyzer service."""

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

    async def get_analysis(
        self,
        ticker: str,
        *,
        period: str = "10y",
        interval: str = "1d",
    ) -> dict[str, Any]:
        normalized_ticker = ticker.strip().upper()

        url = (
            f"{self._base_url}/analysis/"
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
                    if response.status >= 400:
                        message = await response.text()

                        raise ApiClientError(
                            f"Analyzer returned HTTP "
                            f"{response.status}: {message}"
                        )

                    try:
                        payload = await response.json()
                    except (
                        aiohttp.ContentTypeError,
                        JSONDecodeError,
                    ) as exc:
                        raise InvalidResponseError(
                            "Analyzer returned invalid JSON."
                        ) from exc

        except aiohttp.ClientError as exc:
            raise ApiClientError(
                "Unable to communicate with analyzer."
            ) from exc

        if not isinstance(payload, dict):
            raise InvalidResponseError(
                "Analyzer response must be a JSON object."
            )

        return payload