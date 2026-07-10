from __future__ import annotations

from typing import Any
import aiohttp

from .exceptions import ApiClientError, ServiceUnavailableError, InvalidResponseError
from .schemas import PriceHistoryRequest

class DownloaderApiClient:
    """
    Thin HTTP client around the Downloader service.

    This class should not know:
    - HTML
    - Templates
    - JavaScript
    - Charts
    - Browser requests

    It only communicates with the Downloader API.
    """

    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")

    async def get_price_history(
        self,
        request: PriceHistoryRequest,
    ) -> dict[str, Any]:

        url = f"{self._base_url}/prices/{request.ticker}"

        params = {
            "period": request.period,
            "interval": request.interval,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params,
                ) as response:

                    response.raise_for_status()

                    data = await response.json()

        except aiohttp.ClientConnectionError as exc:
            raise ServiceUnavailableError(
                "Unable to connect to Downloader service."
            ) from exc

        except aiohttp.ClientResponseError as exc:
            raise ApiClientError(
                f"Downloader returned HTTP {exc.status}."
            ) from exc

        except Exception as exc:
            raise ApiClientError(
                "Unexpected error calling Downloader."
            ) from exc

        self._validate_price_history(data)

        return data

    @staticmethod
    def _validate_price_history(data: dict[str, Any]) -> None:
        """
        Ensure the Downloader returned the minimum
        structure we expect.
        """

        if "ticker" not in data:
            raise InvalidResponseError(
                "Missing ticker."
            )

        if "rows" not in data:
            raise InvalidResponseError(
                "Missing price history."
            )