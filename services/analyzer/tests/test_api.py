from unittest.mock import AsyncMock

import pytest

from src.api import create_app
from src.exceptions import (
    DownloaderClientError,
    DownloaderResponseError,
    InvalidDownloaderResponseError,
    InvalidPriceHistoryError,
)
from src.schemas import AnalysisResult


def make_result() -> AnalysisResult:
    return AnalysisResult(
        ticker="AAPL",
        period="10y",
        interval="1d",
        observations=120,
        start_date="2016-01-31",
        end_date="2026-01-31",
        start_price=100.0,
        current_price=200.0,
        total_return=1.0,
        cagr=0.0718,
        annualized_volatility=0.20,
        max_drawdown=-0.30,
        moving_average_50=180.0,
        moving_average_200=None,
    )


@pytest.mark.asyncio
async def test_health_endpoint(
    aiohttp_client,
):
    app = create_app(analyzer_service=AsyncMock(), )
    client = await aiohttp_client(app)

    response = await client.get("/health")
    body = await response.json()

    assert response.status == 200
    assert body == {"status": "ok", "service": "analyzer",
    }


@pytest.mark.asyncio
async def test_analysis_endpoint_returns_json_and_forwards_period(aiohttp_client, ):
    service = AsyncMock()
    service.analyze_ticker.return_value = make_result()

    app = create_app(analyzer_service=service, )
    client = await aiohttp_client(app)

    response = await client.get("/analysis/aapl?period=5y&interval=1wk", )
    body = await response.json()

    assert response.status == 200

    service.analyze_ticker.assert_awaited_once_with("aapl", period="5y", )

    assert body == make_result().to_dict()


@pytest.mark.asyncio
async def test_analysis_endpoint_uses_defaults(aiohttp_client, ):
    service = AsyncMock()
    service.analyze_ticker.return_value = make_result()

    app = create_app(analyzer_service=service, )
    client = await aiohttp_client(app)

    response = await client.get("/analysis/AAPL", )

    assert response.status == 200

    service.analyze_ticker.assert_awaited_once_with("AAPL", period="10y", )


@pytest.mark.asyncio
@pytest.mark.parametrize(("error", "status", "error_code", ),
                        [(DownloaderResponseError(404, "Unknown ticker.", ), 404, "downloader_request_error", ),
                         (DownloaderResponseError(500, "Downloader failed.", ), 502, "downloader_error", ),
                         (InvalidDownloaderResponseError("Bad payload.", ), 502, "invalid_downloader_response", ),
                         (DownloaderClientError("Unavailable.", ), 503, "downloader_unavailable", ),
                         (InvalidPriceHistoryError("Not enough rows.", ), 400, "calculation_error", ), ], )
async def test_analysis_endpoint_translates_errors(aiohttp_client, error, status, error_code, ):
    service = AsyncMock()
    service.analyze_ticker.side_effect = error

    app = create_app(analyzer_service=service, )
    client = await aiohttp_client(app)

    response = await client.get("/analysis/AAPL", )
    body = await response.json()

    assert response.status == status
    assert body["error"] == error_code
    assert body["message"]