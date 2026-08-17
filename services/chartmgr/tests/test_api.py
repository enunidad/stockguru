from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from src.api import create_app
from src.client import AnalyzerApiClient, DownloaderApiClient
from src.exceptions import (
    DownloaderClientError,
    DownloaderResponseError,
    InvalidDownloaderResponseError,
)
from src.schemas import ChartResponse
from src.service import ChartMgrService


# =========================================================
# Fixtures
# =========================================================

@pytest.fixture
def chartmgr_service():
    service = AsyncMock(spec=ChartMgrService)
    return service


@pytest_asyncio.fixture
async def client(aiohttp_client, chartmgr_service):
    app = create_app(chartmgr_service=chartmgr_service)
    return await aiohttp_client(app)


# =========================================================
# /health
# =========================================================

@pytest.mark.asyncio
async def test_health_returns_ok(client) -> None:
    response = await client.get("/health")

    assert response.status == 200
    assert await response.json() == {
        "status": "ok",
        "service": "chartmgr",
    }


# =========================================================
# /charting/price_history/{ticker}
# =========================================================

@pytest.mark.asyncio
async def test_price_history_returns_chart_response(
    client,
    chartmgr_service,
) -> None:
    chartmgr_service.get_price_history.return_value = ChartResponse(
        chart_type="candlestick",
        title="Monthly OHLC",
        xaxis_label="Date",
        yaxis_label="Value",
        legend=True,
        x_values=[
            "2026-01",
            "2026-02",
        ],
        y_values={
            "Open": [100.0, 108.0],
            "High": [110.0, 115.0],
            "Low": [95.0, 102.0],
            "Close": [108.0, 112.0],
        },
    )

    response = await client.get(
        "/charting/price_history/AAPL"
    )

    assert response.status == 200

    assert await response.json() == {
        "chart_type": "candlestick",
        "title": "Monthly OHLC",
        "data": {
            "x_values": [
                "2026-01",
                "2026-02",
            ],
            "y_values": {
                "Open": [100.0, 108.0],
                "High": [110.0, 115.0],
                "Low": [95.0, 102.0],
                "Close": [108.0, 112.0],
            },
        },
        "labels": {
            "x": "Date",
            "y": "Value",
        },
        "legend": True,
    }


@pytest.mark.asyncio
async def test_price_history_uses_defaults(
    client,
    chartmgr_service,
) -> None:
    chartmgr_service.get_price_history.return_value = ChartResponse(
        chart_type="candlestick",
        title="Monthly OHLC",
    )

    await client.get(
        "/charting/price_history/AAPL"
    )

    chartmgr_service.get_price_history.assert_awaited_once_with(
        "AAPL",
        period="10y",
        interval="1mo",
    )


@pytest.mark.asyncio
async def test_price_history_passes_query_parameters(
    client,
    chartmgr_service,
) -> None:
    chartmgr_service.get_price_history.return_value = ChartResponse(
        chart_type="candlestick",
        title="Monthly OHLC",
    )

    await client.get(
        "/charting/price_history/MSFT"
        "?period=5y&interval=1wk"
    )

    chartmgr_service.get_price_history.assert_awaited_once_with(
        "MSFT",
        period="5y",
        interval="1wk",
    )


# =========================================================
# /charting/volume/{ticker}
# =========================================================

@pytest.mark.asyncio
async def test_volume_returns_chart_response(
    client,
    chartmgr_service,
) -> None:
    chartmgr_service.get_volume_history.return_value = ChartResponse(
        chart_type="bar",
        title="Monthly Volume",
        xaxis_label="Date",
        yaxis_label="Volume",
        legend=True,
        x_values=[
            "2026-01",
            "2026-02",
        ],
        y_values={
            "Volume": [
                1000000,
                1200000,
            ],
        },
    )

    response = await client.get(
        "/charting/volume/AAPL"
    )

    assert response.status == 200

    assert await response.json() == {
        "chart_type": "bar",
        "title": "Monthly Volume",
        "data": {
            "x_values": [
                "2026-01",
                "2026-02",
            ],
            "y_values": {
                "Volume": [
                    1000000,
                    1200000,
                ],
            },
        },
        "labels": {
            "x": "Date",
            "y": "Volume",
        },
        "legend": True,
    }


@pytest.mark.asyncio
async def test_volume_uses_defaults(
    client,
    chartmgr_service,
) -> None:
    chartmgr_service.get_volume_history.return_value = ChartResponse(
        chart_type="bar",
        title="Monthly Volume",
    )

    await client.get(
        "/charting/volume/AAPL"
    )

    chartmgr_service.get_volume_history.assert_awaited_once_with(
        "AAPL",
        period="10y",
        interval="1mo",
    )


@pytest.mark.asyncio
async def test_volume_passes_query_parameters(
    client,
    chartmgr_service,
) -> None:
    chartmgr_service.get_volume_history.return_value = ChartResponse(
        chart_type="bar",
        title="Monthly Volume",
    )

    await client.get(
        "/charting/volume/MSFT"
        "?period=1y&interval=1wk"
    )

    chartmgr_service.get_volume_history.assert_awaited_once_with(
        "MSFT",
        period="1y",
        interval="1wk",
    )


# =========================================================
# DownloaderResponseError
# =========================================================

@pytest.mark.asyncio
async def test_price_history_returns_downloader_4xx_error(
    client,
    chartmgr_service,
) -> None:
    chartmgr_service.get_price_history.side_effect = (
        DownloaderResponseError(
            status=404,
            message="Ticker not found.",
        )
    )

    response = await client.get(
        "/charting/price_history/INVALID"
    )

    assert response.status == 404

    assert await response.json() == {
        "error": "downloader_request_error",
        "message": "Ticker not found.",
    }


@pytest.mark.asyncio
async def test_price_history_converts_downloader_5xx_to_bad_gateway(
    client,
    chartmgr_service,
) -> None:
    chartmgr_service.get_price_history.side_effect = (
        DownloaderResponseError(
            status=500,
            message="Downloader failed.",
        )
    )

    response = await client.get(
        "/charting/price_history/AAPL"
    )

    assert response.status == 502

    assert await response.json() == {
        "error": "downloader_error",
        "message": "Downloader failed.",
    }


# =========================================================
# InvalidDownloaderResponseError
# =========================================================

@pytest.mark.asyncio
async def test_price_history_returns_bad_gateway_for_invalid_downloader_response(
    client,
    chartmgr_service,
) -> None:
    chartmgr_service.get_price_history.side_effect = (
        InvalidDownloaderResponseError(
            "Some data missing required values."
        )
    )

    response = await client.get(
        "/charting/price_history/AAPL"
    )

    assert response.status == 502

    assert await response.json() == {
        "error": "invalid_downloader_response",
        "message": "Some data missing required values.",
    }


# =========================================================
# DownloaderClientError
# =========================================================

@pytest.mark.asyncio
async def test_price_history_returns_service_unavailable_when_downloader_unreachable(
    client,
    chartmgr_service,
) -> None:
    chartmgr_service.get_price_history.side_effect = (
        DownloaderClientError(
            "Unable to connect to the downloader service."
        )
    )

    response = await client.get(
        "/charting/price_history/AAPL"
    )

    assert response.status == 503

    assert await response.json() == {
        "error": "downloader_unavailable",
        "message": (
            "Unable to connect to the downloader service."
        ),
    }


# =========================================================
# Unexpected exceptions
# =========================================================

@pytest.mark.asyncio
async def test_price_history_returns_internal_server_error_for_unexpected_exception(
    client,
    chartmgr_service,
) -> None:
    chartmgr_service.get_price_history.side_effect = RuntimeError(
        "Something unexpected happened."
    )

    response = await client.get(
        "/charting/price_history/AAPL"
    )

    assert response.status == 500

    assert await response.json() == {
        "error": "Unexpected internal Error",
        "message": "Something unexpected happened.",
    }


# =========================================================
# Volume error handling
# =========================================================

@pytest.mark.asyncio
async def test_volume_uses_same_error_handling(
    client,
    chartmgr_service,
) -> None:
    chartmgr_service.get_volume_history.side_effect = (
        DownloaderClientError(
            "Unable to connect to the downloader service."
        )
    )

    response = await client.get(
        "/charting/volume/AAPL"
    )

    assert response.status == 503

    assert await response.json() == {
        "error": "downloader_unavailable",
        "message": (
            "Unable to connect to the downloader service."
        ),
    }