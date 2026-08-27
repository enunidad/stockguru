from __future__ import annotations

from json import JSONDecodeError
from typing import Any

import aiohttp
import math

from .exceptions import (
    DownloaderClientError,
    DownloaderResponseError,
    InvalidDownloaderResponseError,
)
from .schemas import PriceHistory

def _parse_price_history(payload: dict[str, Any], ) -> PriceHistory:
    cleaned_payload = payload.copy()

    data = payload.get("data")

    if not isinstance(data, list):
        raise InvalidDownloaderResponseError(
            "Downloader price-history data must be a list."
        )

    valid_rows = []

    for row in data:
        if not isinstance(row, dict):
            continue

        close = row.get("Close")

        try:
            close_value = float(close)
        except (TypeError, ValueError):
            continue

        if not math.isfinite(close_value):
            continue

        valid_rows.append(row)

    cleaned_payload["data"] = valid_rows
    cleaned_payload["rows"] = len(valid_rows)

    try:
        history = PriceHistory.from_dict(cleaned_payload)

    except (KeyError, TypeError, ValueError, ) as exc:
        raise InvalidDownloaderResponseError("Downloader returned an invalid price-history response.") from exc

    if not history.rows:
        raise InvalidDownloaderResponseError("Downloader returned no price-history rows.")

    return history

class DownloaderClient:
    """Base client class"""

class LocalDownloaderClient(DownloaderClient):
    def __init__(self, service:DownloaderService|None = None) -> None:
        if service is None:
            from services.downloader import DownloaderService
            service = DownloaderService()
        self.service = service

    async def get_price_history(self, ticker: str, *, period: str = "10y", interval: str = "1d", 
                                aggregate: bool = False, auto_adjust: bool = True,) -> PriceHistory:
        resp = self.service.get_price_history(ticker=ticker, period=period, interval=interval, 
                                aggregate=aggregate, auto_adjust=auto_adjust,)
        
        payload = {
                "ticker": ticker.upper(),
                "period": period,
                "interval": interval,
                "rows": len(resp),
                "data": resp.to_dict(orient="records"),
            }
        return _parse_price_history(payload)
    
class HttpDownloaderClient(DownloaderClient):
    def __init__(self, base_url: str = "http://localhost:8080", *, timeout_seconds: float = 30.0, ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds, )

    async def get_price_history(self, ticker: str, *, period: str = "10y", interval: str = "1d", 
                                aggregate: bool = False, auto_adjust: bool = True,) -> PriceHistory:
        url = (f"{self._base_url}/history/{ticker}")

        params = {"period": period, "interval": interval, "aggregate":str(aggregate).lower(), 
                    "autoadjust": str(auto_adjust).lower(),}

        try:
            async with aiohttp.ClientSession(timeout=self._timeout, ) as session:
                async with session.get(url, params=params, ) as response:
                    payload = await self._read_response(response, )

        except aiohttp.ServerTimeoutError as exc:
            raise DownloaderClientError("The downloader service timed out.") from exc

        except aiohttp.ClientConnectionError as exc:
            raise DownloaderClientError("Unable to connect to the downloader service.") from exc
        
        except aiohttp.ClientError as exc:
            raise DownloaderClientError("The downloader request failed.") from exc

        return _parse_price_history(payload)

    @staticmethod
    async def _read_response(response: aiohttp.ClientResponse, ) -> dict[str, Any]:
        if response.status >= 400:
            message = await HttpDownloaderClient._read_error_message(response, )

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