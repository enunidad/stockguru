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