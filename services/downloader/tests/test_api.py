# services/downloader/tests/test_api.py

from __future__ import annotations

import pandas as pd
import pytest

from src.api import create_app
from src.exceptions import (
    DownloaderClientError,
    EmptyDownloadError,
    InvalidParameterError,
)


# =========================================================
# Fake Services
# =========================================================


class FakeDownloaderService:
    def __init__(self):
        self.history_args = None
        self.metadata_ticker = None
        self.dividend_args = None

    def get_price_history(
        self,
        ticker: str,
        period: str,
        interval: str,
        auto_adjust,
        aggregate,
    ) -> pd.DataFrame:
        self.history_args = {
            "ticker": ticker,
            "period": period,
            "interval": interval,
            "auto_adjust": auto_adjust,
            "aggregate": aggregate,
        }

        data = pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "Close": [110.0, 111.0],
            },
            index=pd.to_datetime(
                [
                    "2024-01-01 00:00:00-05:00",
                    "2024-01-02 00:00:00-05:00",
                ],
            ),
        )

        data.index.name = "Date"
        return data

    def get_metadata(self, ticker: str) -> dict:
        self.metadata_ticker = ticker

        return {
            "ticker": ticker.upper(),
            "currency": "USD",
            "exchange": "NMS",
            "timezone": "America/New_York",
            "quote_type": "EQUITY",
            "name": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "country": "United States",
            "raw": {},
        }

    def get_dividends(
        self,
        ticker: str,
        period: str,
    ) -> pd.Series:
        self.dividend_args = {
            "ticker": ticker,
            "period": period,
        }

        dividends = pd.Series(
            [0.24, 0.25, 0.26],
            index=pd.to_datetime(
                [
                    "2026-02-08 00:00:00-05:00",
                    "2026-05-08 00:00:00-04:00",
                    "2026-08-08 00:00:00-04:00",
                ],
                utc=True,
            ),
            name="Dividends",
            dtype=float,
        )

        dividends.index.name = "Date"

        return dividends


class EmptyDividendService:
    def get_dividends(
        self,
        ticker: str,
        period: str,
    ) -> pd.Series:
        result = pd.Series(
            dtype=float,
            name="Dividends",
        )

        result.index.name = "Date"

        return result


class ValueErrorHistoryService:
    def get_price_history(self, **kwargs):
        raise ValueError(
            f"Unsupported period '{kwargs['period']}'."
        )


class DownloaderErrorHistoryService:
    def get_price_history(self, **kwargs):
        raise EmptyDownloadError(
            "No price history returned for ticker 'BAD'."
        )


class ValueErrorDividendService:
    def get_dividends(
        self,
        ticker: str,
        period: str,
    ):
        raise ValueError(
            f"Unsupported period '{period}'."
        )


class DownloaderErrorDividendService:
    def get_dividends(
        self,
        ticker: str,
        period: str,
    ):
        raise EmptyDownloadError(
            f"No dividend history returned for ticker '{ticker.upper()}'."
        )


class DownloaderErrorMetadataService:
    def get_metadata(self, ticker: str):
        raise DownloaderClientError(
            f"Failed to download metadata for ticker '{ticker.upper()}'."
        )


# =========================================================
# Health
# =========================================================


@pytest.mark.asyncio
async def test_health_endpoint(
    aiohttp_client,
):
    app = create_app(
        service=FakeDownloaderService()
    )

    client = await aiohttp_client(app)

    response = await client.get("/health")
    body = await response.json()

    assert response.status == 200

    assert body == {
        "status": "ok",
        "code": "200",
    }


# =========================================================
# Metadata
# =========================================================


@pytest.mark.asyncio
async def test_get_metadata_returns_json(
    aiohttp_client,
):
    service = FakeDownloaderService()

    app = create_app(service=service)
    client = await aiohttp_client(app)

    response = await client.get(
        "/metadata/aapl"
    )

    body = await response.json()

    assert response.status == 200

    assert body == {
        "ticker": "AAPL",
        "currency": "USD",
        "exchange": "NMS",
        "timezone": "America/New_York",
        "quote_type": "EQUITY",
        "name": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "country": "United States",
        "raw": {},
    }

    assert service.metadata_ticker == "aapl"


@pytest.mark.asyncio
async def test_get_metadata_returns_400_for_downloader_error(
    aiohttp_client,
):
    app = create_app(
        service=DownloaderErrorMetadataService()
    )

    client = await aiohttp_client(app)

    response = await client.get(
        "/metadata/BAD"
    )

    body = await response.json()

    assert response.status == 400

    assert body == {
        "error": "DownloaderClientError",
        "message": (
            "Failed to download metadata "
            "for ticker 'BAD'."
        ),
    }


# =========================================================
# Price History
# =========================================================


@pytest.mark.asyncio
async def test_get_price_history_returns_json(
    aiohttp_client,
):
    service = FakeDownloaderService()

    app = create_app(service=service)
    client = await aiohttp_client(app)

    response = await client.get(
        "/history/aapl"
        "?period=5y"
        "&interval=1mo"
        "&autoadjust=false"
        "&aggregate=false"
    )

    body = await response.json()

    assert response.status == 200

    assert body == {
        "ticker": "AAPL",
        "period": "5y",
        "interval": "1mo",
        "rows": 2,
        "data": [
            {
                "Date": "2024-01-01",
                "Open": 100.0,
                "Close": 110.0,
            },
            {
                "Date": "2024-01-02",
                "Open": 101.0,
                "Close": 111.0,
            },
        ],
    }


@pytest.mark.asyncio
async def test_get_price_history_passes_query_parameters_to_service(
    aiohttp_client,
):
    service = FakeDownloaderService()

    app = create_app(service=service)
    client = await aiohttp_client(app)

    response = await client.get(
        "/history/msft"
        "?period=2y"
        "&interval=2wk"
        "&autoadjust=false"
        "&aggregate=false"
    )

    assert response.status == 200

    assert service.history_args == {
        "ticker": "msft",
        "period": "2y",
        "interval": "2wk",
        "auto_adjust": "false",
        "aggregate": "false",
    }


@pytest.mark.asyncio
async def test_get_price_history_uses_defaults(
    aiohttp_client,
):
    service = FakeDownloaderService()

    app = create_app(service=service)
    client = await aiohttp_client(app)

    response = await client.get(
        "/history/AAPL"
    )

    assert response.status == 200

    assert service.history_args == {
        "ticker": "AAPL",
        "period": "10y",
        "interval": "1d",
        "auto_adjust": "true",
        "aggregate": "true",
    }


@pytest.mark.asyncio
async def test_get_price_history_formats_dates_without_time(
    aiohttp_client,
):
    app = create_app(
        service=FakeDownloaderService()
    )

    client = await aiohttp_client(app)

    response = await client.get(
        "/history/AAPL"
    )

    body = await response.json()

    assert response.status == 200

    assert body["data"][0]["Date"] == "2024-01-01"
    assert body["data"][1]["Date"] == "2024-01-02"

    assert "T" not in body["data"][0]["Date"]
    assert " " not in body["data"][0]["Date"]
    assert ":" not in body["data"][0]["Date"]


@pytest.mark.asyncio
async def test_get_price_history_returns_400_for_value_error(
    aiohttp_client,
):
    app = create_app(
        service=ValueErrorHistoryService()
    )

    client = await aiohttp_client(app)

    response = await client.get(
        "/history/AAPL?period=3y"
    )

    body = await response.json()

    assert response.status == 400

    assert body == {
        "error": "ValueError",
        "message": "Unsupported period '3y'.",
    }


@pytest.mark.asyncio
async def test_get_price_history_returns_400_for_downloader_error(
    aiohttp_client,
):
    app = create_app(
        service=DownloaderErrorHistoryService()
    )

    client = await aiohttp_client(app)

    response = await client.get(
        "/history/BAD"
    )

    body = await response.json()

    assert response.status == 400

    assert body == {
        "error": "EmptyDownloadError",
        "message": (
            "No price history returned "
            "for ticker 'BAD'."
        ),
    }


# =========================================================
# Dividends
# =========================================================


@pytest.mark.asyncio
async def test_get_dividends_returns_json(
    aiohttp_client,
):
    service = FakeDownloaderService()

    app = create_app(service=service)
    client = await aiohttp_client(app)

    response = await client.get(
        "/dividends/aapl?period=5y"
    )

    body = await response.json()

    assert response.status == 200

    assert body == {
        "ticker": "AAPL",
        "period": "5y",
        "rows": 3,
        "data": [
            {
                "Date": "2026-02-08",
                "Dividend": 0.24,
            },
            {
                "Date": "2026-05-08",
                "Dividend": 0.25,
            },
            {
                "Date": "2026-08-08",
                "Dividend": 0.26,
            },
        ],
    }


@pytest.mark.asyncio
async def test_get_dividends_passes_parameters_to_service(
    aiohttp_client,
):
    service = FakeDownloaderService()

    app = create_app(service=service)
    client = await aiohttp_client(app)

    response = await client.get(
        "/dividends/msft?period=2y"
    )

    assert response.status == 200

    assert service.dividend_args == {
        "ticker": "msft",
        "period": "2y",
    }


@pytest.mark.asyncio
async def test_get_dividends_uses_default_period(
    aiohttp_client,
):
    service = FakeDownloaderService()

    app = create_app(service=service)
    client = await aiohttp_client(app)

    response = await client.get(
        "/dividends/AAPL"
    )

    body = await response.json()

    assert response.status == 200

    assert service.dividend_args["period"] == "10y"
    assert body["period"] == "10y"


@pytest.mark.asyncio
async def test_get_dividends_formats_dates_without_time(
    aiohttp_client,
):
    app = create_app(
        service=FakeDownloaderService()
    )

    client = await aiohttp_client(app)

    response = await client.get(
        "/dividends/AAPL"
    )

    body = await response.json()

    assert response.status == 200

    for record in body["data"]:
        assert len(record["Date"]) == 10
        assert "T" not in record["Date"]
        assert ":" not in record["Date"]


@pytest.mark.asyncio
async def test_get_dividends_values_are_floats(
    aiohttp_client,
):
    app = create_app(
        service=FakeDownloaderService()
    )

    client = await aiohttp_client(app)

    response = await client.get(
        "/dividends/AAPL"
    )

    body = await response.json()

    assert response.status == 200

    assert all(
        isinstance(
            record["Dividend"],
            float,
        )
        for record in body["data"]
    )


@pytest.mark.asyncio
async def test_get_dividends_returns_empty_history(
    aiohttp_client,
):
    app = create_app(
        service=EmptyDividendService()
    )

    client = await aiohttp_client(app)

    response = await client.get(
        "/dividends/AAPL"
    )

    body = await response.json()

    assert response.status == 200

    assert body == {
        "ticker": "AAPL",
        "period": "10y",
        "rows": 0,
        "data": [],
    }


@pytest.mark.asyncio
async def test_get_dividends_returns_400_for_value_error(
    aiohttp_client,
):
    app = create_app(
        service=ValueErrorDividendService()
    )

    client = await aiohttp_client(app)

    response = await client.get(
        "/dividends/AAPL?period=3y"
    )

    body = await response.json()

    assert response.status == 400

    assert body == {
        "error": "ValueError",
        "message": "Unsupported period '3y'.",
    }


@pytest.mark.asyncio
async def test_get_dividends_returns_400_for_downloader_error(
    aiohttp_client,
):
    app = create_app(
        service=DownloaderErrorDividendService()
    )

    client = await aiohttp_client(app)

    response = await client.get(
        "/dividends/BAD"
    )

    body = await response.json()

    assert response.status == 400

    assert body == {
        "error": "EmptyDownloadError",
        "message": (
            "No dividend history returned "
            "for ticker 'BAD'."
        ),
    }


# =========================================================
# Routing
# =========================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/health",
        "/history/AAPL",
        "/metadata/AAPL",
        "/dividends/AAPL",
    ],
)
async def test_public_routes_exist(
    aiohttp_client,
    path,
):
    app = create_app(
        service=FakeDownloaderService()
    )

    client = await aiohttp_client(app)

    response = await client.get(path)

    assert response.status != 404